from sqlalchemy.orm import Session
import re
import random
import asyncio
from datetime import datetime
from app.schemas import UserAttempt, Intervention, DetailedScores, SignalMetrics
from app.core.transcriber import transcribe_audio
from app.core.state import AgentState, update_state
from app.core.database import SessionModel, ExamSession, QuestionAttempt, User, VocabularyItem
from app.core.pronunciation import analyze_pronunciation
from app.core.logger import logger
from app.core.transcript_processor import post_process_transcript
from app.core.translator import (
    translate_checkpoint_words_async, 
    translate_to_indonesian_async,
    batch_translate_to_indonesian_async
)
from app.core.config import settings
from app.core.evaluator import extract_signals_async
from app.core.agent import formulate_strategy_async

# Global registry for per-session locks to prevent race conditions during state updates
# (v16.0 - Structural Hardening)
session_locks: dict[str, asyncio.Lock] = {}

async def process_user_attempt(
    file_path: str, 
    task_id: str, 
    db: Session, 
    session_id: str = "default_user",
    is_exam_mode: bool = False,
    is_retry: bool = False,
    is_refactor: bool = False
) -> Intervention:
    """
    Orchestrates the full loop (Async/Parallel): 
    Audio -> Text -> Analysis -> Strategy -> State Update
    """
    
    # 0. GET OR CREATE SESSION LOCK (Serialization safety)
    if session_id not in session_locks:
        session_locks[session_id] = asyncio.Lock()
        
    async with session_locks[session_id]:
        # 1. LOAD STATE FROM DB
        current_part = "PART_1"
        current_prompt = settings.INITIAL_PROMPT
        chronic_issues_str = ""

        if is_exam_mode:
            exam_session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
            if not exam_session:
                raise ValueError(f"Exam session {session_id} not found")
            
            # Ensure we have the latest state from other potential parallel workers
            db.refresh(exam_session)
            
            current_part = exam_session.current_part
            current_prompt = exam_session.current_prompt or "General topic"
            
            user = db.query(User).filter(User.id == exam_session.user_id).first()
            # ENFORCE BAND 9 (v13.0 - User Request)
            target_band = "9.0" 
            weakness = user.weakness if user else "General"

            from app.core.database import ErrorLog
            error_logs = db.query(ErrorLog).filter(
                ErrorLog.user_id == exam_session.user_id
            ).order_by(ErrorLog.count.desc()).limit(3).all()
            
            if error_logs:
                issues = [f"{e.error_type} ({e.count}x)" for e in error_logs]
                chronic_issues_str = ", ".join(issues)

            from app.core.state import AttemptResult
            past_attempts = db.query(QuestionAttempt).filter(
                QuestionAttempt.session_id == session_id
            ).order_by(QuestionAttempt.id.asc()).all()
            
            history = [AttemptResult(
                attempt_id=str(p.id),
                prompt=p.question_text or "",
                transcript=p.transcript or "",
                metrics=SignalMetrics(
                    fluency_wpm=float(p.wpm or 0.0),
                    hesitation_ratio=float(p.hesitation_ratio or 0.0),
                    grammar_error_count=0,
                    filler_count=0,
                    coherence_score=float(p.coherence_score or 0.0),
                    lexical_diversity=float(p.lexical_diversity or 0.0),
                    grammar_complexity=float(p.grammar_complexity or 0.0),
                    pronunciation_score=float(p.pronunciation_score or 0.0)
                ),
                outcome='PASS'
            ) for p in past_attempts]

            current_state = AgentState(
                session_id=session_id,
                stress_level=exam_session.stress_level,
                consecutive_failures=exam_session.consecutive_failures,
                fluency_trend=exam_session.fluency_trend,
                history=history, 
                current_part=current_part,
                target_band=target_band,
                weakness=weakness
            )
        else:
            current_state = AgentState(session_id=session_id, stress_level=0.5, consecutive_failures=0, fluency_trend="stable")
            current_prompt = "Describe the room you are in right now."
        
        # 2. START PARALLEL STAGE 1: Transcription + Prompt Translation
        logger.info(f"--- Processing Attempt (ExamMode={is_exam_mode}, Prompt='{current_prompt}') ---")
        
        # Whisper is sync, so we run it in a thread to not block the event loop
        loop = asyncio.get_running_loop()
        transcription_task = loop.run_in_executor(None, transcribe_audio, file_path)
        
        # Prompt translation (optional but good to overlap)
        prompt_tr_task = translate_to_indonesian_async(current_prompt)
        
        # Wait for transcription to finish before we can do signals
        transcript_data = await transcription_task
        current_prompt_tr = await prompt_tr_task
        
        # 2. TRANSCRIPTION POST-PROCESSING (v12.0)
        transcript_text = transcript_data['text']
        transcript_text = post_process_transcript(transcript_text)
        transcript_data['text'] = transcript_text
        
        logger.info(f"DEBUG: Processed Transcript -> {transcript_text}")

        # 3. ANALYZE (Linguistic)
        attempt = UserAttempt(
            task_id=task_id,
            transcript=transcript_data['text'],
            audio_duration=transcript_data['duration']
        )
        
        # 3b. RECORD PERSISTENCE (v8.0) - Ensure record exists even if LLM fails
        if is_exam_mode:
            new_qa = None
            if is_retry:
                new_qa = db.query(QuestionAttempt).filter(
                    QuestionAttempt.session_id == session_id,
                    QuestionAttempt.part == current_part
                ).order_by(QuestionAttempt.id.desc()).first()
                
            if not new_qa:
                new_qa = QuestionAttempt(session_id=session_id, part=current_part)
                db.add(new_qa)
            
            db.flush() 
            new_qa.question_text = current_prompt
            new_qa.transcript = attempt.transcript
            new_qa.duration_seconds = attempt.audio_duration
            # NOTE: Removed premature db.commit() here — row is flushed but
            # the full transaction commits at the end of the pipeline (line ~543).

        # SILENCE GUARD (v15.0) - Early exit if transcript is empty/noise after filtering
        transcript_is_empty = not transcript_data['text'].strip() or len(transcript_data['text'].split()) < 2
        if transcript_is_empty:
            logger.warning("Silence Guard triggered: transcript empty after post-processing.")
            silence_intervention = Intervention(
                action_id="FORCE_RETRY",
                next_task_prompt=current_prompt,
                feedback_markdown="⚠️ **Microphone Error**: Saya tidak bisa mendengar suara Anda dengan jelas. Tolong pastikan mic aktif dan coba lagi.",
                stress_level=current_state.stress_level if is_exam_mode else 0.5,
            )
            if is_exam_mode:
                exam_session.current_prompt = current_prompt
                db.commit()
            return silence_intervention
            
    # 4. START PARALLEL STAGE 2 (v8.0 - Restored)
    signals_task = extract_signals_async(attempt, current_prompt_text=current_prompt)
    pron_task = loop.run_in_executor(None, analyze_pronunciation, file_path)
    transcript_tr_task = translate_to_indonesian_async(attempt.transcript)
    
    signals = await signals_task
    pron_results = await pron_task
    transcript_tr = await transcript_tr_task
    
    signals.pronunciation_score = pron_results.get("pronunciation_score", 0.0)
    signals.prosody_score = pron_results.get("prosody", 0.0)
    signals.confidence_score = pron_results.get("confidence_score", 0.0)
    
    # 5. FORMULATE STRATEGY (Major LLM call)
    context_msg = f"CURRENT_QUESTION: {current_prompt}"
    
    intervention = await formulate_strategy_async(
        current_state, 
        signals, 
        current_part=current_part if is_exam_mode else None,
        user_transcript=attempt.transcript,
        chronic_issues=chronic_issues_str,
        context_override=context_msg
    )
    intervention.user_transcript = attempt.transcript
    intervention.confidence_score = signals.confidence_score
    intervention.user_transcript_translated = transcript_tr

    # 6. POPULATE REGRESSION-DRIVEN RADAR METRICS (v16.0 - Unified Calibration)
    # Mapping raw signals (0-1) to IELTS Band 1.0 - 9.0 using summary-aligned multipliers
    intervention.radar_metrics = {
        "Fluency": round(min(max(signals.fluency_wpm / 18.0, 1.0), 9.0), 1),
        "Coherence": round(min(max(signals.coherence_score * 9.0, 1.0), 9.0), 1),
        "Lexical": round(min(max(signals.lexical_diversity * 14.0, 1.0), 9.0), 1),
        "Grammar": round(min(max(signals.grammar_complexity * 35.0, 1.0), 9.0), 1),
        "Pronunciation": round(min(max(signals.pronunciation_score * 9.0, 1.0), 9.0), 1)
    }

    # 7. QUIZ SHUFFLING (v16.0 - Educational Integrity)
    if intervention.quiz_options and len(intervention.quiz_options) >= 2:
        correct_answer = intervention.quiz_options[0]
        shuffled_options = list(intervention.quiz_options)
        import random
        random.shuffle(shuffled_options)
        intervention.quiz_options = shuffled_options
        intervention.quiz_correct_index = shuffled_options.index(correct_answer)

    # 8. BATCH TRANSLATIONS (End of pipeline)
    # Collect all English output that needs translation
    segments_to_translate = [
        intervention.feedback_markdown,
        intervention.ideal_response
    ]
    # Checkpoint words translation already handled if requested or we can batch it here
    
    tr_results = await batch_translate_to_indonesian_async(segments_to_translate)
    intervention.feedback_translated = tr_results[0]
    intervention.ideal_response_translated = tr_results[1]

    if is_exam_mode:
        outcome = 'FAIL' if intervention.action_id == 'FAIL' else 'PASS'
        new_state = update_state(current_state, attempt, signals, outcome, current_prompt)
        
        exam_session.stress_level = new_state.stress_level
        exam_session.fluency_trend = new_state.fluency_trend
        exam_session.consecutive_failures = new_state.consecutive_failures
        
        # TRANSACTION CONSOLIDATION (v15.0) - Reuse the QA row created in early persistence
        new_qa = db.query(QuestionAttempt).filter(
            QuestionAttempt.session_id == session_id,
            QuestionAttempt.part == current_part
        ).order_by(QuestionAttempt.id.desc()).first()
        
        if not new_qa:
            # Fallback: should never happen, but safety net
            logger.warning("v15.0: Early-persisted QA not found, creating new one.")
            new_qa = QuestionAttempt(session_id=session_id, part=current_part)
            db.add(new_qa)
        
        db.flush()

        new_qa.question_text = current_prompt
        new_qa.question_translated = current_prompt_tr
        new_qa.transcript = attempt.transcript
        new_qa.transcript_translated = transcript_tr
        new_qa.duration_seconds = attempt.audio_duration
        new_qa.wpm = signals.fluency_wpm
        new_qa.coherence_score = signals.coherence_score
        new_qa.hesitation_ratio = signals.hesitation_ratio
        new_qa.lexical_diversity = signals.lexical_diversity
        new_qa.grammar_complexity = signals.grammar_complexity
        new_qa.pronunciation_score = signals.pronunciation_score
        new_qa.feedback_markdown = intervention.feedback_markdown
        new_qa.feedback_translated = intervention.feedback_translated
        new_qa.improved_response = intervention.ideal_response
        new_qa.improved_response_translated = intervention.ideal_response_translated
        
        # Keyword + Checkpoint Word Detection (Keep sync for now)
        last_qa = None
        if is_retry:
            # If retrying, we want the attempt BEFORE the current one
            last_qa = db.query(QuestionAttempt).filter(
                QuestionAttempt.session_id == session_id,
                QuestionAttempt.id < new_qa.id
            ).order_by(QuestionAttempt.id.desc()).first()
        else:
            # If new attempt, the latest aside from current is the previous turn
            last_qa = db.query(QuestionAttempt).filter(
                QuestionAttempt.session_id == session_id,
                QuestionAttempt.id != new_qa.id
            ).order_by(QuestionAttempt.id.desc()).first()
        
        # Determine which checkpoint words were REQUIRED for THIS turn
        required_checkpoint_words: list[str] = []
        required_checkpoint_words_translated: list[str] = []
        required_checkpoint_words_meanings: list[str] = []

        if last_qa and last_qa.checkpoint_words_required:
            required_checkpoint_words = last_qa.checkpoint_words_required or []
            required_checkpoint_words_translated = last_qa.checkpoint_words_translated or []
            required_checkpoint_words_meanings = last_qa.checkpoint_words_meanings or []
        elif not last_qa and exam_session.initial_keywords:
            # First turn uses initial keywords as checkpoint words
            required_checkpoint_words = exam_session.initial_keywords or []
            # Translate once here (also persisted into QA rows below)
            try:
                required_checkpoint_words_translated, required_checkpoint_words_meanings = await translate_checkpoint_words_async(required_checkpoint_words)
            except Exception as e:
                logger.error(f"Checkpoint translation error (initial): {e}", exc_info=True)

        # Compute hits for THIS turn
        lower_ts = (attempt.transcript or "").lower()
        checkpoint_hits: list[str] = []
        if required_checkpoint_words and attempt.transcript:
            for w in required_checkpoint_words:
                if re.search(rf"\b{re.escape(w.lower())}\b", lower_ts):
                    checkpoint_hits.append(w)

        # For backwards compatibility, we keep keywords_hit aligned with checkpoint hits
        intervention.keywords_hit = checkpoint_hits
        new_qa.keywords_hit = checkpoint_hits

        # Persist checkpoint compliance for analytics (THIS turn)
        # Note: the required checkpoint words for THIS turn live on the previous QA row.
        new_qa.checkpoint_words_hit = checkpoint_hits
        new_qa.checkpoint_compliance_score = (len(checkpoint_hits) / len(required_checkpoint_words)) if required_checkpoint_words else 1.0

        # Also expose checkpoint results on the API response (THIS turn)
        intervention.checkpoint_words_hit = checkpoint_hits
        intervention.checkpoint_compliance_score = new_qa.checkpoint_compliance_score

        # --- AUTO-SAVE TO WORD BANK ---
        if is_exam_mode and checkpoint_hits:
            from app.core.database import VocabularyItem
            for word in checkpoint_hits:
                existing_vocab = db.query(VocabularyItem).filter(
                    VocabularyItem.user_id == exam_session.user_id,
                    VocabularyItem.word == word
                ).first()
                if not existing_vocab:
                    vocab_item = VocabularyItem(
                        user_id=exam_session.user_id,
                        word=word,
                        word_translated=await translate_to_indonesian_async(word),
                        definition="Used correctly in session.",
                        definition_translated="Digunakan dengan benar dalam sesi.",
                        context_sentence=attempt.transcript,
                        source_type="EXAM_HIT"
                    )
                    db.add(vocab_item)

        # Generate NEXT turn checkpoint words
        next_checkpoint_words: list[str] = []
        if intervention.realtime_word_bank:
            pool = list(dict.fromkeys(intervention.realtime_word_bank))
            import random
            next_checkpoint_words = random.sample(pool, k=min(3, len(pool)))
        elif intervention.target_keywords:
            pool = list(dict.fromkeys(intervention.target_keywords or []))
            import random
            next_checkpoint_words = random.sample(pool, k=min(3, len(pool)))

        cp_tr: list[str] = []
        cp_mn: list[str] = []
        if next_checkpoint_words:
            # Store checkpoint word translations/meanings in DB for consistency
            existing_vocab = db.query(VocabularyItem).filter(
                VocabularyItem.user_id == exam_session.user_id,
                VocabularyItem.word.in_(next_checkpoint_words),
            ).all()
            vocab_map = {v.word.lower(): v for v in existing_vocab}

            missing_words = [w for w in next_checkpoint_words if w.lower() not in vocab_map]
            if missing_words:
                try:
                    tr_list, mn_list = await translate_checkpoint_words_async(missing_words)
                except Exception as e:
                    logger.error(f"Checkpoint translation error (next): {e}", exc_info=True)
                    tr_list, mn_list = [], []

                for i, w in enumerate(missing_words):
                    tr = tr_list[i] if i < len(tr_list) else await translate_to_indonesian_async(w)
                    mn = mn_list[i] if i < len(mn_list) else "Makna sederhana tidak tersedia."
                    v = VocabularyItem(
                        user_id=exam_session.user_id,
                        word=w,
                        word_translated=tr,
                        definition="IELTS checkpoint word.",
                        definition_translated=mn,
                        context_sentence=intervention.next_task_prompt,
                        source_type="CHECKPOINT_SEED",
                    )
                    db.add(v)
                    vocab_map[w.lower()] = v

                db.flush()

            cp_tr = [
                (vocab_map.get(w.lower()).word_translated if vocab_map.get(w.lower()) else await translate_to_indonesian_async(w))
                for w in next_checkpoint_words
            ]
            cp_mn = [
                (vocab_map.get(w.lower()).definition_translated if vocab_map.get(w.lower()) else "Makna sederhana tidak tersedia.")
                for w in next_checkpoint_words
            ]

        intervention.checkpoint_words = next_checkpoint_words
        intervention.checkpoint_words_translated = cp_tr
        intervention.checkpoint_words_meanings = cp_mn

        # Save checkpoint words for the NEXT turn on this QA
        new_qa.checkpoint_words_required = next_checkpoint_words
        new_qa.checkpoint_words_translated = cp_tr
        new_qa.checkpoint_words_meanings = cp_mn

        # Save current keywords for the NEXT turn (legacy support)
        new_qa.target_keywords = intervention.target_keywords

        # Enforce mandatory checkpoint words (skip if retry/refactor or transcription failed)
        if required_checkpoint_words and attempt.transcript and attempt.transcript != "[TRANSCRIPTION_FAILED]":
            missing = [w for w in required_checkpoint_words if w not in checkpoint_hits]
            if missing:
                intervention.action_id = "FORCE_RETRY"
                intervention.refactor_mission = (
                    "Checkpoint Words wajib dipakai. Ulangi jawaban, dan gunakan kata ini: "
                    + ", ".join(missing)
                    + "."
                )
                # Re-send the CURRENT checkpoint requirement so UI can show it during retry
                intervention.checkpoint_words = required_checkpoint_words
                intervention.checkpoint_words_translated = required_checkpoint_words_translated
                intervention.checkpoint_words_meanings = required_checkpoint_words_meanings
                # Persist the same requirement so retries don't accidentally advance the checkpoint
                new_qa.checkpoint_words_required = required_checkpoint_words
                new_qa.checkpoint_words_translated = required_checkpoint_words_translated
                new_qa.checkpoint_words_meanings = required_checkpoint_words_meanings
                # Keep the same question
                intervention.next_task_prompt = current_prompt
                exam_session.current_prompt = current_prompt
                db.commit()
                intervention.stress_level = current_state.stress_level
                return intervention
        
        # Micro-Skill Error Tracking
        from app.core.error_taxonomy import classify_errors
        from app.core.database import ErrorLog
        if intervention.feedback_markdown:
            detected_errors = classify_errors(intervention.feedback_markdown)
            for error_type in detected_errors:
                existing = db.query(ErrorLog).filter(
                    ErrorLog.user_id == exam_session.user_id,
                    ErrorLog.error_type == error_type.value
                ).first()
                if existing:
                    existing.count += 1
                    existing.last_seen = datetime.utcnow()
                else:
                    db.add(ErrorLog(
                        user_id=exam_session.user_id,
                        error_type=error_type.value,
                        session_id=session_id
                    ))
        
        # Transition Logic (Skip if RETRY or MIC ERROR)
        if is_retry or is_refactor or intervention.action_id == "FORCE_RETRY":
            exam_session.current_prompt = current_prompt
            intervention.next_task_prompt = current_prompt
            db.commit()
            intervention.stress_level = current_state.stress_level
            return intervention

        # Count unique non-retry questions for transition logic
        from sqlalchemy import func
        part_count = db.query(func.count(func.distinct(QuestionAttempt.question_text))).filter(
            QuestionAttempt.session_id == session_id,
            QuestionAttempt.part == current_part,
            QuestionAttempt.transcript.isnot(None),
            QuestionAttempt.transcript != "[TRANSCRIPTION_FAILED]"
        ).scalar()
        
        if part_count >= 3 and current_part == "PART_1":
            exam_session.current_part = "PART_2"
            
            p2_topics = settings.PART_2_CUES
            if not p2_topics:
                # v16.0: Emergency Fallback to prevent IndexError
                cue_card = {
                    "main_prompt": "Describe a difficult challenge you have faced and how you overcame it.",
                    "cues": ["What the challenge was", "When it happened", "What you did to overcome it", "Explain how you felt after overcoming it"]
                }
            else:
                import random
                cue_card = random.choice(p2_topics)
            
            # Format Cue Card for UI and AI
            cues_text = "\n".join([f"- {c}" for c in cue_card['cues']])
            new_prompt = f"{cue_card['main_prompt']}\n\nYou should say:\n{cues_text}"
            
            exam_session.current_prompt = new_prompt
            intervention.next_task_prompt = f"Thank you. Now, for Part 2, I'm going to give you a topic and I'd like you to talk about it for one to two minutes. {new_prompt}"
            intervention.action_id = "TRANSITION_PART_2"
        elif part_count >= 1 and current_part == "PART_2":
            # v16.0 Optimization: Preserve the feedback from the first LLM call
            # which evaluated the mono-logue, then transition to Part 3.
            exam_session.current_part = "PART_3"
            
            # Bridge the next prompt manually or with a lightweight bridge
            bridge = "Thank you. We've been talking about the topic, and now I'd like to discuss one or two more general questions related to this."
            # Reuse the intervention's next_task_prompt if it already shifted to Part 3 
            # (formulate_strategy sometimes auto-detects transition if current_part is passed)
            if "PART_3" not in str(intervention.next_task_prompt):
                intervention.next_task_prompt = f"{bridge} {intervention.next_task_prompt}"
            
            intervention.action_id = "TRANSITION_PART_3"
            exam_session.current_prompt = intervention.next_task_prompt
        elif part_count >= 4 and current_part == "PART_3":
            exam_session.status = "COMPLETED"
            exam_session.end_time = datetime.utcnow()
            exam_session.current_prompt = "Exam Completed"
            intervention.next_task_prompt = "Thank you, the exam is finished."
            
            # Summary scoring (v16.0 Recalibrated - Fairness Hardened)
            all_attempts_raw = db.query(QuestionAttempt).filter(QuestionAttempt.session_id == session_id).all()
            
            # Filter out technical failures/silence from the final average (v14.0)
            all_attempts = [
                a for a in all_attempts_raw 
                if a.transcript and a.transcript != "[TRANSCRIPTION_FAILED]" and a.transcript.strip() != ""
            ]

            if all_attempts:
                def safe_avg(values):
                    nums = [v for v in values if v is not None]
                    return sum(nums) / max(1, len(nums)) if nums else 1.0
                
                avg_wpm = safe_avg([a.wpm for a in all_attempts])
                avg_coherence = safe_avg([a.coherence_score for a in all_attempts])
                avg_lexical = safe_avg([a.lexical_diversity for a in all_attempts])
                avg_grammar = safe_avg([a.grammar_complexity for a in all_attempts])
                avg_pron = safe_avg([a.pronunciation_score for a in all_attempts])
                
                # Safeguard against checkpoint hits being NULL in old database records
                checkpoint_compliance_list = [
                    (len(getattr(a, "checkpoint_words_hit", []) or []) / max(1, len(getattr(a, "checkpoint_words_required", []) or []))) 
                    for a in all_attempts if getattr(a, "checkpoint_words_required", None)
                ]
                avg_checkpoint = sum(checkpoint_compliance_list) / max(1, len(checkpoint_compliance_list)) if checkpoint_compliance_list else 1.0
                
                # Calibrated multipliers for 1.0 - 9.0 range
                exam_session.fluency_score = min(max(avg_wpm / 18.0, 1.0), 9.0)
                exam_session.coherence_score = min(max(avg_coherence * 9.0, 1.0), 9.0)
                exam_session.lexical_resource_score = min(max(avg_lexical * 14.0, 1.0), 9.0)
                exam_session.grammatical_range_score = min(max(avg_grammar * 35.0, 1.0), 9.0)
                exam_session.pronunciation_score = min(max(avg_pron * 9.0, 1.0), 9.0)
                
                exam_session.overall_band_score = round((
                    exam_session.fluency_score + exam_session.coherence_score + 
                    exam_session.lexical_resource_score + exam_session.grammatical_range_score + 
                    exam_session.pronunciation_score
                ) / 5.0, 1)

                user = db.query(User).filter(User.id == exam_session.user_id).first()
                if user:
                    all_scores = db.query(ExamSession.overall_band_score).filter(
                        ExamSession.user_id == user.id,
                        ExamSession.overall_band_score.isnot(None)
                    ).all()
                    score_list = [s[0] for s in all_scores if s[0] is not None]
                    score_list.append(exam_session.overall_band_score)
                    user.total_exams_taken = len(score_list)
                    user.average_band_score = round(sum(score_list) / max(1, len(score_list)), 1)
            else:
                exam_session.current_prompt = intervention.next_task_prompt

        # Normal path: persist the authoritative next prompt so the NEXT attempt is evaluated
        # against the same question shown in the UI.
        if intervention.next_task_prompt and exam_session.current_prompt not in ["Exam Completed"]:
            exam_session.current_prompt = intervention.next_task_prompt

        # FINAL STEP: Ensure the NEXT prompt is translated (handling transitions)
        if intervention.next_task_prompt:
            try:
                exam_session.current_prompt_translated = await translate_to_indonesian_async(intervention.next_task_prompt)
                intervention.next_task_prompt_translated = exam_session.current_prompt_translated
            except Exception as e:
                logger.error(f"Translation error (next prompt): {e}", exc_info=True)

    try:
        # Most of the function body will be moved inside here or handled by the caller.
        # However, since this is a large function, I'll add a catch-all at the end 
        # for logic that happens BEFORE the final return.
        
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"CRITICAL ENGINE ERROR: {e}", exc_info=True)
        # We don't re-raise here if we want to return the intervention 
        # (which might contain a FORCE_RETRY or MIC_ERROR already)
        # but for unexpected crashes, it's better to ensure rollback.
        raise

    intervention.stress_level = current_state.stress_level
    return intervention
