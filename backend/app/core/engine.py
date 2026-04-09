from sqlalchemy import func
from sqlalchemy.orm import Session
import re
import random
import asyncio
from datetime import datetime
from app.schemas import UserAttempt, Intervention, SignalMetrics
from app.core.transcriber import transcribe_audio, is_hallucination
from app.core.state import AgentState, update_state, AttemptResult
from app.core.database import (
    ExamSession,
    QuestionAttempt,
    User,
    VocabularyItem,
    ErrorLog,
)
from app.core.pronunciation import analyze_pronunciation
from app.core.logger import logger
from app.core.transcript_processor import post_process_transcript
from app.core.translator import (
    translate_checkpoint_words_async,
    translate_to_indonesian_async,
    batch_translate_to_indonesian_async,
)
from app.core.config import settings
from app.core.evaluator import extract_signals_async
from app.core.agent import formulate_strategy_async
from app.core.scoring import (
    get_radar_metrics,
    calculate_band_score,
    WPM_MULTIPLIER,
    COHERENCE_MULTIPLIER,
    LEXICAL_MULTIPLIER,
    GRAMMAR_MULTIPLIER,
    PRONUNCIATION_MULTIPLIER,
)
from app.core.error_taxonomy import classify_errors

import time

# Use a normal dictionary since this is for a single user.
# WeakValueDictionary immediately garbage collects the locks because
# there are no strong references to them created elsewhere.
session_locks: dict[str, asyncio.Lock] = {}
lock_access_times: dict[str, float] = {}
registry_lock = asyncio.Lock()


async def get_session_lock(session_id: str) -> asyncio.Lock:
    """Synchronized factory to prevent registry race conditions."""
    async with registry_lock:
        now = time.time()
        # Cleanup idle locks older than 30 minutes (1800 seconds)
        # Reduced from 1 hour to keep memory footprint small
        if len(session_locks) > 10:
            to_delete = []
            for sid, timestamp in list(lock_access_times.items()):
                # Only delete if idle for a long time AND not currently held
                if (now - timestamp > 1800) and (sid in session_locks):
                    if not session_locks[sid].locked():
                        to_delete.append(sid)
            
            for sid in to_delete:
                session_locks.pop(sid, None)
                lock_access_times.pop(sid, None)

        if session_id not in session_locks:
            session_locks[session_id] = asyncio.Lock()
        
        lock_access_times[session_id] = now
        return session_locks[session_id]


async def process_user_attempt(
    file_path: str,
    task_id: str,
    db: Session,
    session_id: str = "default_user",
    is_exam_mode: bool = False,
    is_retry: bool = False,
    is_refactor: bool = False,
) -> Intervention:
    """
    Orchestrates the full loop (Async/Parallel):
    Audio -> Text -> Analysis -> Strategy -> State Update
    """

    # 0. GET OR CREATE SESSION LOCK (Serialization safety - v18.0)
    lock = await get_session_lock(session_id)
    async with lock:
        try:
            # 1. LOAD STATE FROM DB
            current_part = "PART_1"
            current_prompt = settings.INITIAL_PROMPT
            chronic_issues_str = ""

            if is_exam_mode:
                exam_session = (
                    db.query(ExamSession).filter(ExamSession.id == session_id).first()
                )
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

                error_logs = (
                    db.query(ErrorLog)
                    .filter(ErrorLog.user_id == exam_session.user_id)
                    .order_by(ErrorLog.count.desc())
                    .limit(3)
                    .all()
                )

                if error_logs:
                    issues = [f"{e.error_type} ({e.count}x)" for e in error_logs]
                    chronic_issues_str = ", ".join(issues)

                past_attempts = (
                    db.query(QuestionAttempt)
                    .filter(QuestionAttempt.session_id == session_id)
                    .order_by(QuestionAttempt.id.asc())
                    .all()
                )

                history = [
                    AttemptResult(
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
                            pronunciation_score=float(p.pronunciation_score or 0.0),
                        ),
                        outcome="PASS",
                    )
                    for p in past_attempts
                ]

                current_state = AgentState(
                    session_id=session_id,
                    stress_level=exam_session.stress_level,
                    consecutive_failures=exam_session.consecutive_failures,
                    fluency_trend=exam_session.fluency_trend,
                    history=history,
                    current_part=current_part,
                    target_band=target_band,
                    weakness=weakness,
                )
            else:
                current_state = AgentState(
                    session_id=session_id,
                    stress_level=0.5,
                    consecutive_failures=0,
                    fluency_trend="stable",
                )
                current_prompt = "Describe the room you are in right now."

            # 2. START PARALLEL STAGE 1: Transcription + Prompt Translation
            logger.info(
                f"--- Processing Attempt (ExamMode={is_exam_mode}, Prompt='{current_prompt}') ---"
            )

            # Whisper is sync, so we run it in a thread to not block the event loop
            loop = asyncio.get_running_loop()
            transcription_task = loop.run_in_executor(None, transcribe_audio, file_path)

            # Prompt translation (optional but good to overlap)
            prompt_tr_task = translate_to_indonesian_async(current_prompt)

            # Wait for transcription to finish before we can do signals
            transcript_data = await transcription_task
            current_prompt_tr = await prompt_tr_task

            # 2. TRANSCRIPTION POST-PROCESSING (v12.0)
            transcript_text = transcript_data["text"]
            transcript_text = post_process_transcript(transcript_text)
            transcript_data["text"] = transcript_text

            logger.info(f"DEBUG: Processed Transcript -> {transcript_text}")

            # SILENCE & JUNK GUARD (v18.1 Hardened - Relocated for DB Cleanliness)
            # Detects empty, repeated words, or typical whisper noise hallucinations
            raw_text = transcript_data["text"]

            # 1. Check for system engine errors first
            if "[SYSTEM_ERROR" in raw_text or "[TRANSCRIPTION_FAILED]" in raw_text:
                logger.error(f"Engine detected transcription failure: {raw_text}")
                error_intervention = Intervention(
                    action_id="MAINTAIN",
                    next_task_prompt=current_prompt,
                    feedback_markdown="⚠️ **System Error**: Sistem tidak dapat memproses audio saat ini. Coba lagi.",
                    constraints={"timer": 45},
                    keywords_hit=[],
                    stress_level=current_state.stress_level if is_exam_mode else 0.5,
                )
                if is_exam_mode:
                    exam_session.current_prompt = current_prompt
                    db.flush()
                    db.commit()
                return error_intervention

            # Hallucination blocklist and repetitive text detection (v24.0 - Centralized)
            is_junk = is_hallucination(raw_text)

            # v22.0: Relaxed guard for Part 1 (allow single-word answers like "Yes")
            min_words = 1 if current_part == "PART_1" else 2
            words = raw_text.strip().split()
            transcript_is_empty = (
                not raw_text.strip() or len(words) < min_words or is_junk
            )

            if transcript_is_empty:
                logger.warning(
                    f"Guard triggered (is_junk={is_junk}): transcript empty or noise."
                )
                msg = "⚠️ **Microphone Error**: Saya tidak bisa mendengar suara Anda dengan jelas. Tolong pastikan mic aktif dan coba lagi."
                if is_junk:
                    msg = "⚠️ **Gangguan Suara**: Rekaman terlalu bising sehingga suara Anda tidak terbaca. Harap bicara di tempat tenang."

                silence_intervention = Intervention(
                    action_id="FORCE_RETRY",
                    next_task_prompt=current_prompt,
                    feedback_markdown=msg,
                    constraints={"timer": 45},
                    keywords_hit=[],
                    stress_level=current_state.stress_level if is_exam_mode else 0.5,
                )
                if is_exam_mode:
                    exam_session.current_prompt = current_prompt
                    db.flush()
                    db.commit()  # Explicit commit for early exit
                return silence_intervention

            # 3. ANALYZE (Linguistic)
            attempt = UserAttempt(
                task_id=task_id,
                transcript=transcript_data["text"],
                audio_duration=transcript_data["duration"],
            )

            # 3b. RECORD PERSISTENCE (v8.1) - Ensure record exists even if LLM fails
            new_qa = None
            if is_exam_mode:
                if is_retry:
                    new_qa = (
                        db.query(QuestionAttempt)
                        .filter(
                            QuestionAttempt.session_id == session_id,
                            QuestionAttempt.part == current_part,
                        )
                        .order_by(QuestionAttempt.id.desc())
                        .first()
                    )

                if not new_qa:
                    new_qa = QuestionAttempt(session_id=session_id, part=current_part)
                    db.add(new_qa)
                    db.flush()
                    db.refresh(new_qa)

                new_qa.question_text = current_prompt
                new_qa.transcript = attempt.transcript
                new_qa.duration_seconds = attempt.audio_duration
                
                # v24.1: Flush basic transcript data immediately to survive downstream LLM crashes
                db.flush()

            # 4. START PARALLEL STAGE 2 (v8.0 - Restored)
            signals_task = extract_signals_async(
                attempt, current_prompt_text=current_prompt
            )
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

            try:
                intervention = await formulate_strategy_async(
                    current_state,
                    signals,
                    current_part=current_part if is_exam_mode else None,
                    user_transcript=attempt.transcript,
                    chronic_issues=chronic_issues_str,
                    context_override=context_msg,
                )
            except Exception as strategy_err:
                logger.error(
                    f"Strategy formulation crashed: {strategy_err}", exc_info=True
                )
                intervention = Intervention(
                    action_id="MAINTAIN",
                    next_task_prompt=current_prompt,
                    feedback_markdown="⚠️ **Koneksi Engine Terganggu**: Gagal menganalisa jawaban. Tolong lanjutkan jawaban Anda.",
                    ideal_response="The AI engine could not generate an ideal response due to a technical error.",
                    constraints={"timer": 45},
                    keywords_hit=[],
                    confidence_score=0.5,
                )

            intervention.user_transcript = attempt.transcript
            intervention.confidence_score = signals.confidence_score
            intervention.user_transcript_translated = transcript_tr

            # 6. POPULATE REGRESSION-DRIVEN RADAR METRICS (v22.0 - Unified Scoring)
            intervention.radar_metrics = get_radar_metrics(signals)

            # 7. QUIZ SHUFFLING (v16.0 - Educational Integrity)
            if intervention.quiz_options and len(intervention.quiz_options) >= 2:
                correct_answer = intervention.quiz_options[0]
                shuffled_options = list(intervention.quiz_options)
                random.shuffle(shuffled_options)
                intervention.quiz_options = shuffled_options
                intervention.quiz_correct_index = shuffled_options.index(correct_answer)

            # 8. BATCH TRANSLATIONS (End of pipeline)
            segments_to_translate = [
                intervention.feedback_markdown,
                intervention.ideal_response,
            ]

            tr_results = await batch_translate_to_indonesian_async(
                segments_to_translate
            )
            intervention.feedback_translated = tr_results[0]
            intervention.ideal_response_translated = tr_results[1]

            if is_exam_mode:
                outcome = "FAIL" if intervention.action_id == "FAIL" else "PASS"
                new_state = update_state(
                    current_state, attempt, signals, outcome, current_prompt
                )

                exam_session.stress_level = new_state.stress_level
                exam_session.fluency_trend = new_state.fluency_trend
                exam_session.consecutive_failures = new_state.consecutive_failures

                # Use the existing QA row created or retrieved in Stage 1
                if not new_qa:
                    # Robust fallback in case logic changed earlier
                    new_qa = (
                        db.query(QuestionAttempt)
                        .filter(
                            QuestionAttempt.session_id == session_id,
                            QuestionAttempt.part == current_part,
                        )
                        .order_by(QuestionAttempt.id.desc())
                        .first()
                    ) or QuestionAttempt(session_id=session_id, part=current_part)
                    
                    if not new_qa.id:
                        db.add(new_qa)
                        db.flush()
                        db.refresh(new_qa)

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
                new_qa.improved_response_translated = (
                    intervention.ideal_response_translated
                )

                # Keyword + Checkpoint Word Detection
                last_qa = None
                if is_retry:
                    last_qa = (
                        db.query(QuestionAttempt)
                        .filter(
                            QuestionAttempt.session_id == session_id,
                            QuestionAttempt.id < new_qa.id,
                        )
                        .order_by(QuestionAttempt.id.desc())
                        .first()
                    )
                else:
                    last_qa = (
                        db.query(QuestionAttempt)
                        .filter(
                            QuestionAttempt.session_id == session_id,
                            QuestionAttempt.id != new_qa.id,
                        )
                        .order_by(QuestionAttempt.id.desc())
                        .first()
                    )

                required_checkpoint_words: list[str] = []
                required_checkpoint_words_translated: list[str] = []
                required_checkpoint_words_meanings: list[str] = []

                if last_qa and last_qa.checkpoint_words_required:
                    required_checkpoint_words = last_qa.checkpoint_words_required or []
                    required_checkpoint_words_translated = (
                        last_qa.checkpoint_words_translated or []
                    )
                    required_checkpoint_words_meanings = (
                        last_qa.checkpoint_words_meanings or []
                    )
                elif not last_qa and exam_session.initial_keywords:
                    required_checkpoint_words = exam_session.initial_keywords or []
                    try:
                        (
                            required_checkpoint_words_translated,
                            required_checkpoint_words_meanings,
                        ) = await translate_checkpoint_words_async(
                            required_checkpoint_words
                        )
                    except Exception as e:
                        logger.error(f"Checkpoint translation error (initial): {e}")

                lower_ts = (attempt.transcript or "").lower()
                checkpoint_hits: list[str] = []
                if required_checkpoint_words and attempt.transcript:
                    for w in required_checkpoint_words:
                        if re.search(rf"\b{re.escape(w.lower())}\b", lower_ts):
                            checkpoint_hits.append(w)

                intervention.keywords_hit = checkpoint_hits
                new_qa.keywords_hit = checkpoint_hits
                new_qa.checkpoint_words_hit = checkpoint_hits
                new_qa.checkpoint_compliance_score = (
                    (len(checkpoint_hits) / len(required_checkpoint_words))
                    if required_checkpoint_words
                    else 1.0
                )

                intervention.checkpoint_words_hit = checkpoint_hits
                intervention.checkpoint_compliance_score = (
                    new_qa.checkpoint_compliance_score
                )

                # AUTO-SAVE TO WORD BANK (v20.0 - Optimized with parallel translations)
                if checkpoint_hits:
                    words_to_translate = []

                    # Fetch existing vocabulary in bulk instead of N+1 queries
                    existing_vocabs = (
                        db.query(VocabularyItem)
                        .filter(
                            VocabularyItem.user_id == exam_session.user_id,
                            VocabularyItem.word.in_(checkpoint_hits),
                        )
                        .all()
                    )
                    existing_words = {v.word.lower() for v in existing_vocabs}

                    for word in checkpoint_hits:
                        if word.lower() not in existing_words:
                            words_to_translate.append(word)

                    if words_to_translate:
                        translated_hits = await asyncio.gather(
                            *[
                                translate_to_indonesian_async(w)
                                for w in words_to_translate
                            ]
                        )
                        for i, word in enumerate(words_to_translate):
                            vocab_item = VocabularyItem(
                                user_id=exam_session.user_id,
                                word=word,
                                word_translated=translated_hits[i],
                                definition="Used correctly in session.",
                                definition_translated="Digunakan dengan benar dalam sesi.",
                                context_sentence=attempt.transcript,
                                source_type="EXAM_HIT",
                            )
                            db.add(vocab_item)

                # Generate NEXT turn checkpoint words
                next_checkpoint_words: list[str] = []
                if intervention.realtime_word_bank:
                    pool = list(dict.fromkeys(intervention.realtime_word_bank))
                    next_checkpoint_words = random.sample(pool, k=min(3, len(pool)))
                elif intervention.target_keywords:
                    pool = list(dict.fromkeys(intervention.target_keywords or []))
                    next_checkpoint_words = random.sample(pool, k=min(3, len(pool)))

                cp_tr: list[str] = []
                cp_mn: list[str] = []
                if next_checkpoint_words:
                    existing_vocab = (
                        db.query(VocabularyItem)
                        .filter(
                            VocabularyItem.user_id == exam_session.user_id,
                            VocabularyItem.word.in_(next_checkpoint_words),
                        )
                        .all()
                    )
                    vocab_map = {v.word.lower(): v for v in existing_vocab}

                    missing_words = [
                        w for w in next_checkpoint_words if w.lower() not in vocab_map
                    ]
                    if missing_words:
                        try:
                            tr_list, mn_list = await translate_checkpoint_words_async(
                                missing_words
                            )
                        except Exception as e:
                            logger.error(f"Checkpoint translation error (next): {e}")
                            tr_list, mn_list = [], []

                        for i, w in enumerate(missing_words):
                            tr = (
                                tr_list[i]
                                if i < len(tr_list)
                                else await translate_to_indonesian_async(w)
                            )
                            mn = (
                                mn_list[i]
                                if i < len(mn_list)
                                else "Makna sederhana tidak tersedia."
                            )
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
                        (
                            vocab_map.get(w.lower()).word_translated
                            if vocab_map.get(w.lower())
                            else await translate_to_indonesian_async(w)
                        )
                        for w in next_checkpoint_words
                    ]
                    cp_mn = [
                        (
                            vocab_map.get(w.lower()).definition_translated
                            if vocab_map.get(w.lower())
                            else "Makna sederhana tidak tersedia."
                        )
                        for w in next_checkpoint_words
                    ]

                intervention.checkpoint_words = next_checkpoint_words
                intervention.checkpoint_words_translated = cp_tr
                intervention.checkpoint_words_meanings = cp_mn

                new_qa.checkpoint_words_required = next_checkpoint_words
                new_qa.checkpoint_words_translated = cp_tr
                new_qa.checkpoint_words_meanings = cp_mn
                new_qa.target_keywords = intervention.target_keywords

                # Mandatory checkpoint words enforcement
                if (
                    required_checkpoint_words
                    and attempt.transcript
                    and attempt.transcript != "[TRANSCRIPTION_FAILED]"
                ):
                    missing = [
                        w for w in required_checkpoint_words if w not in checkpoint_hits
                    ]
                    # Avoid infinite loops: only force retry if it's the first attempt
                    if missing and not is_retry:
                        intervention.action_id = "FORCE_RETRY"
                        intervention.refactor_mission = (
                            "Checkpoint Words wajib dipakai. Ulangi jawaban, dan gunakan kata ini: "
                            + ", ".join(missing)
                            + "."
                        )
                        intervention.checkpoint_words = required_checkpoint_words
                        intervention.checkpoint_words_translated = (
                            required_checkpoint_words_translated
                        )
                        intervention.checkpoint_words_meanings = (
                            required_checkpoint_words_meanings
                        )
                        new_qa.checkpoint_words_required = required_checkpoint_words
                        new_qa.checkpoint_words_translated = (
                            required_checkpoint_words_translated
                        )
                        new_qa.checkpoint_words_meanings = (
                            required_checkpoint_words_meanings
                        )
                        intervention.next_task_prompt = current_prompt
                        exam_session.current_prompt = current_prompt
                        db.flush()
                        db.commit()
                        intervention.stress_level = current_state.stress_level
                        return intervention

                # Micro-Skill Error Tracking
                if intervention.feedback_markdown:
                    detected_errors = classify_errors(intervention.feedback_markdown)
                    for error_type in detected_errors:
                        existing = (
                            db.query(ErrorLog)
                            .filter(
                                ErrorLog.user_id == exam_session.user_id,
                                ErrorLog.error_type == error_type.value,
                            )
                            .first()
                        )
                        if existing:
                            existing.count += 1
                            existing.last_seen = datetime.utcnow()
                        else:
                            db.add(
                                ErrorLog(
                                    user_id=exam_session.user_id,
                                    error_type=error_type.value,
                                    session_id=session_id,
                                )
                            )

                # Transition Logic
                if is_retry or is_refactor or intervention.action_id == "FORCE_RETRY":
                    exam_session.current_prompt = current_prompt
                    intervention.next_task_prompt = current_prompt
                    db.flush()
                    db.commit()
                    intervention.stress_level = current_state.stress_level
                    return intervention

                part_count = (
                    db.query(func.count(func.distinct(QuestionAttempt.question_text)))
                    .filter(
                        QuestionAttempt.session_id == session_id,
                        QuestionAttempt.part == current_part,
                        QuestionAttempt.transcript.isnot(None),
                        QuestionAttempt.transcript != "[TRANSCRIPTION_FAILED]",
                    )
                    .scalar()
                )

                if part_count >= 3 and current_part == "PART_1":
                    exam_session.current_part = "PART_2"
                    p2_topics = settings.PART_2_CUES
                    cue_card = (
                        random.choice(p2_topics)
                        if p2_topics
                        else {"main_prompt": "Describe a challenge...", "cues": []}
                    )
                    cues_text = "\n".join([f"- {c}" for c in cue_card.get("cues", [])])
                    new_prompt = (
                        f"{cue_card['main_prompt']}\n\nYou should say:\n{cues_text}"
                    )
                    exam_session.current_prompt = new_prompt
                    intervention.next_task_prompt = f"Thank you. Now, for Part 2, I'm going to give you a topic... {new_prompt}"
                    intervention.action_id = "TRANSITION_PART_2"
                elif part_count >= 1 and current_part == "PART_2":
                    exam_session.current_part = "PART_3"
                    bridge = "Thank you. We've been talking about the topic..."
                    if "PART_3" not in str(intervention.next_task_prompt):
                        intervention.next_task_prompt = (
                            f"{bridge} {intervention.next_task_prompt}"
                        )
                    intervention.action_id = "TRANSITION_PART_3"
                    exam_session.current_prompt = intervention.next_task_prompt
                elif part_count >= 4 and current_part == "PART_3":
                    exam_session.status = "COMPLETED"
                    exam_session.end_time = datetime.utcnow()
                    exam_session.current_prompt = "Exam Completed"
                    intervention.next_task_prompt = "Thank you, the exam is finished."

                    all_attempts_raw = (
                        db.query(QuestionAttempt)
                        .filter(QuestionAttempt.session_id == session_id)
                        .all()
                    )
                    all_attempts = [
                        a
                        for a in all_attempts_raw
                        if a.transcript
                        and a.transcript != "[TRANSCRIPTION_FAILED]"
                        and a.transcript.strip()
                    ]

                    if all_attempts:

                        def safe_avg(values):
                            nums = [v for v in values if v is not None]
                            return sum(nums) / max(1, len(nums)) if nums else 1.0

                        exam_session.fluency_score = calculate_band_score(
                            safe_avg([a.wpm for a in all_attempts]),
                            WPM_MULTIPLIER,
                            is_wpm=True,
                        )
                        exam_session.coherence_score = calculate_band_score(
                            safe_avg([a.coherence_score for a in all_attempts]),
                            COHERENCE_MULTIPLIER,
                        )
                        exam_session.lexical_resource_score = calculate_band_score(
                            safe_avg([a.lexical_diversity for a in all_attempts]),
                            LEXICAL_MULTIPLIER,
                        )
                        exam_session.grammatical_range_score = calculate_band_score(
                            safe_avg([a.grammar_complexity for a in all_attempts]),
                            GRAMMAR_MULTIPLIER,
                        )
                        exam_session.pronunciation_score = calculate_band_score(
                            safe_avg([a.pronunciation_score for a in all_attempts]),
                            PRONUNCIATION_MULTIPLIER,
                        )

                        from app.core.scoring import round_to_ielts_band

                        exam_session.overall_band_score = round_to_ielts_band(
                            (
                                exam_session.fluency_score
                                + exam_session.coherence_score
                                + exam_session.lexical_resource_score
                                + exam_session.grammatical_range_score
                                + exam_session.pronunciation_score
                            )
                            / 5.0
                        )

                        user = (
                            db.query(User)
                            .filter(User.id == exam_session.user_id)
                            .first()
                        )
                        if user:
                            all_scores = (
                                db.query(ExamSession.overall_band_score)
                                .filter(
                                    ExamSession.user_id == user.id,
                                    ExamSession.overall_band_score.isnot(None),
                                )
                                .all()
                            )
                            score_list = [s[0] for s in all_scores if s[0] is not None]
                            score_list.append(exam_session.overall_band_score)
                            user.total_exams_taken = len(score_list)
                            user.average_band_score = round_to_ielts_band(
                                sum(score_list) / max(1, len(score_list))
                            )
                    else:
                        exam_session.current_prompt = intervention.next_task_prompt

                if (
                    intervention.next_task_prompt
                    and exam_session.current_prompt not in ["Exam Completed"]
                ):
                    exam_session.current_prompt = intervention.next_task_prompt

                if intervention.next_task_prompt:
                    try:
                        exam_session.current_prompt_translated = (
                            await translate_to_indonesian_async(
                                intervention.next_task_prompt
                            )
                        )
                        intervention.next_task_prompt_translated = (
                            exam_session.current_prompt_translated
                        )
                    except Exception:
                        pass

            db.commit()  # FINAL TRANSACTION COMMIT
            intervention.stress_level = current_state.stress_level
            return intervention

        except Exception as e:
            db.rollback()
            logger.error(f"CRITICAL ENGINE ERROR: {e}", exc_info=True)
            # Safe fallback response instead of 500
            error_intervention = Intervention(
                action_id="MAINTAIN",
                next_task_prompt=current_prompt
                if "current_prompt" in locals()
                else "Continue.",
                feedback_markdown="⚠️ **System Error**: Terjadi kesalahan teknis. Silakan coba lagi.",
                stress_level=0.5,
                constraints={"timer": 45},
            )
            return error_intervention
