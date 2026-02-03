from sqlalchemy.orm import Session
from datetime import datetime
from app.schemas import UserAttempt, Intervention, DetailedScores, SignalMetrics
from app.core.transcriber import transcribe_audio
from app.core.evaluator import extract_signals
from app.core.agent import formulate_strategy
from app.core.state import AgentState, update_state
from app.core.database import SessionModel, ExamSession, QuestionAttempt, User
from app.core.pronunciation import analyze_pronunciation

def process_user_attempt(
    file_path: str, 
    task_id: str, 
    db: Session, 
    session_id: str = "default_user",
    is_exam_mode: bool = False,
    is_retry: bool = False,
    is_refactor: bool = False
) -> Intervention:
    """
    Orchestrates the full loop: 
    Audio -> Text -> Analysis -> Strategy -> State Update
    """
    
    # 1. LOAD STATE FROM DB
    current_part = "PART_1" # Default
    current_prompt = "Tell me about your hometown." # Better default for IELTS PART 1
    
    chronic_issues_str = ""

    if is_exam_mode:
        exam_session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
        if not exam_session:
            raise ValueError(f"Exam session {session_id} not found")
        
        current_part = exam_session.current_part
        current_prompt = exam_session.current_prompt or "General topic"
        
        # Load User Profile
        user = db.query(User).filter(User.id == exam_session.user_id).first()
        target_band = user.target_band if user else "7.5"
        weakness = user.weakness if user else "General"

        # PHASE 11: PERSISTENT MEMORY
        from app.core.database import ErrorLog
        error_logs = db.query(ErrorLog).filter(
            ErrorLog.user_id == exam_session.user_id
        ).order_by(ErrorLog.count.desc()).limit(3).all()
        
        if error_logs:
            issues = [f"{e.error_type} ({e.count}x)" for e in error_logs]
            chronic_issues_str = ", ".join(issues)

        # Load History for Adaptation
        from app.core.state import AttemptResult
        past_attempts = db.query(QuestionAttempt).filter(
            QuestionAttempt.session_id == session_id
        ).order_by(QuestionAttempt.id.asc()).all()
        
        history = []
        for p in past_attempts:
            history.append(AttemptResult(
                attempt_id=str(p.id),
                prompt=p.question_text,
                transcript=p.transcript or "",
                metrics=SignalMetrics(
                    fluency_wpm=p.wpm or 0.0,
                    hesitation_ratio=p.hesitation_ratio or 0.0,
                    grammar_error_count=0,
                    filler_count=0,
                    coherence_score=p.coherence_score or 0.0,
                    lexical_diversity=p.lexical_diversity or 0.0,
                    grammar_complexity=p.grammar_complexity or 0.0,
                    pronunciation_score=p.pronunciation_score or 0.0
                ),
                outcome='PASS'
            ))

        current_state = AgentState(
            session_id=session_id,
            stress_level=0.5,
            consecutive_failures=0,
            fluency_trend="stable",
            history=history, 
            current_part=current_part,
            target_band=target_band,
            weakness=weakness
        )
    else:
        # Legacy/Testing mode support
        current_state = AgentState(session_id=session_id, stress_level=0.5, consecutive_failures=0, fluency_trend="stable")
        current_prompt = "Describe the room you are in right now."
    
    # 2. TRANSCRIBE
    print(f"--- Processing Attempt (ExamMode={is_exam_mode}, Prompt='{current_prompt}') ---")
    try:
        transcript_data = transcribe_audio(file_path)
        print(f"DEBUG: Transcript -> {transcript_data['text']}")
    except Exception as e:
        print(f"TRANSCRIPTION ERROR: {e}")
        transcript_data = {"text": "", "duration": 0.0, "language": "en"}

    # 3. ANALYZE (Linguistic)
    attempt = UserAttempt(
        task_id=task_id,
        transcript=transcript_data['text'],
        audio_duration=transcript_data['duration']
    )
    signals = extract_signals(attempt, current_prompt_text=current_prompt)
    
    # 4. PRONUNCIATION ANALYSIS
    try:
        pron_results = analyze_pronunciation(file_path)
        signals.pronunciation_score = pron_results.get("pronunciation_score", 0.0)
    except Exception as e:
        print(f"PRONUNCIATION ANALYSIS ERROR: {e}")
        signals.pronunciation_score = 0.0
    
    # 5. AGENT DECISION
    context_msg = None
    if is_refactor:
        context_msg = f"REFACTOR_MISSION_ATTEMPT: User is trying to improve their previous response based on your mission."

    intervention = formulate_strategy(
        current_state, 
        signals, 
        current_part=current_part if is_exam_mode else None,
        user_transcript=attempt.transcript,
        chronic_issues=chronic_issues_str,
        context_override=context_msg
    )
    intervention.user_transcript = attempt.transcript
    
    # 6. UPDATE STATE & PERSIST
    if is_exam_mode:
        # Load or create new attempt
        new_qa = None
        if is_retry:
            new_qa = db.query(QuestionAttempt).filter(
                QuestionAttempt.session_id == session_id,
                QuestionAttempt.part == current_part
            ).order_by(QuestionAttempt.id.desc()).first()
            
        if not new_qa:
            new_qa = QuestionAttempt(session_id=session_id, part=current_part)
            db.add(new_qa)

        # Update metadata
        new_qa.question_text = current_prompt
        new_qa.transcript = attempt.transcript
        new_qa.duration_seconds = attempt.audio_duration
        new_qa.wpm = signals.fluency_wpm
        new_qa.coherence_score = signals.coherence_score
        new_qa.hesitation_ratio = signals.hesitation_ratio
        new_qa.lexical_diversity = signals.lexical_diversity
        new_qa.grammar_complexity = signals.grammar_complexity
        new_qa.pronunciation_score = signals.pronunciation_score
        new_qa.feedback_markdown = intervention.feedback_markdown
        new_qa.improved_response = intervention.ideal_response
        
        # Keyword Hit Detection
        # Keyword Hit Detection
        # Safe retrieval of previous attempt to find target keywords
        last_qa = None
        if is_retry and new_qa.id:
             # If retrying, we want the attempt BEFORE the current one (which we just overwrote)
             last_qa = db.query(QuestionAttempt).filter(
                QuestionAttempt.session_id == session_id,
                QuestionAttempt.id < new_qa.id
            ).order_by(QuestionAttempt.id.desc()).first()
        else:
             # If new attempt (not flushed yet), the latest in DB is the previous turn
             last_qa = db.query(QuestionAttempt).filter(
                QuestionAttempt.session_id == session_id
            ).order_by(QuestionAttempt.id.desc()).first()
        
        if last_qa and last_qa.target_keywords and attempt.transcript:
            lower_ts = attempt.transcript.lower()
            hits = []
            for kw in last_qa.target_keywords:
                if re.search(rf"\b{re.escape(kw.lower())}\b", lower_ts):
                    hits.append(kw)
            intervention.keywords_hit = hits
        elif not last_qa and exam_session.initial_keywords and attempt.transcript:
            # Check against initial keywords for first turn
            lower_ts = attempt.transcript.lower()
            hits = []
            for kw in exam_session.initial_keywords:
                if re.search(rf"\b{re.escape(kw.lower())}\b", lower_ts):
                    hits.append(kw)
            intervention.keywords_hit = hits
        else:
            intervention.keywords_hit = []

        # Save current keywords for the NEXT turn
        new_qa.target_keywords = intervention.target_keywords
        
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
        
        # Transition Logic (Skip if RETRY or REFACTOR)
        if is_retry or is_refactor:
            # If retry, we maintain the same prompt and status
            exam_session.current_prompt = current_prompt
            intervention.next_task_prompt = current_prompt # Repeat the prompt
            db.commit()
            intervention.stress_level = current_state.stress_level
            return intervention

        part_count = db.query(QuestionAttempt).filter(
            QuestionAttempt.session_id == session_id,
            QuestionAttempt.part == current_part
        ).count() + 1
        
        if part_count >= 3 and current_part == "PART_1":
            # End of Part 1 -> Transition to Part 2
            exam_session.current_part = "PART_2"
            new_prompt = "Describe a place you like to visit."
            exam_session.current_prompt = new_prompt
            intervention.next_task_prompt = new_prompt
            intervention.action_id = "TRANSITION_PART_2"
        elif part_count >= 1 and current_part == "PART_2":
            # End of Part 2 -> Transition to Part 3
            exam_session.current_part = "PART_3"
            
            # Socratic Bridge: Pull the Part 2 content to seed Part 3
            part2_attempt = db.query(QuestionAttempt).filter(
                QuestionAttempt.session_id == session_id,
                QuestionAttempt.part == "PART_2"
            ).first()
            
            p2_context = part2_attempt.transcript if part2_attempt else ""
            
            # Re-run strategy with Part 3 context
            intervention = formulate_strategy(
                current_state, 
                signals, 
                current_part="PART_3",
                context_override=f"TRANSITION_FROM_PART_2: {p2_context}",
                user_transcript=attempt.transcript
            )
            intervention.user_transcript = attempt.transcript
            
            exam_session.current_prompt = intervention.next_task_prompt
        elif part_count >= 4 and current_part == "PART_3":
            # End of Part 3 -> Finish
            exam_session.status = "COMPLETED"
            exam_session.end_time = datetime.utcnow()
            exam_session.current_prompt = "Exam Completed"
            intervention.next_task_prompt = "Thank you, the exam is finished."
            
            # Summary scoring
            all_attempts = db.query(QuestionAttempt).filter(QuestionAttempt.session_id == session_id).all()
            if all_attempts:
                def safe_avg(values):
                    nums = [v for v in values if v is not None]
                    return sum(nums) / len(nums) if nums else 1.0
                
                avg_wpm = safe_avg([a.wpm for a in all_attempts])
                avg_coherence = safe_avg([a.coherence_score for a in all_attempts])
                avg_lexical = safe_avg([a.lexical_diversity for a in all_attempts])
                avg_grammar = safe_avg([a.grammar_complexity for a in all_attempts])
                avg_pron = safe_avg([a.pronunciation_score for a in all_attempts])
                
                exam_session.fluency_score = min(max(avg_wpm / 15, 1.0), 9.0)
                exam_session.coherence_score = min(max(avg_coherence * 9, 1.0), 9.0)
                exam_session.lexical_resource_score = min(max(avg_lexical * 15, 1.0), 9.0)
                exam_session.grammatical_range_score = min(max(avg_grammar * 40, 1.0), 9.0)
                exam_session.pronunciation_score = min(max(avg_pron * 9, 1.0), 9.0)
                
                exam_session.overall_band_score = round((
                    exam_session.fluency_score + exam_session.coherence_score + 
                    exam_session.lexical_resource_score + exam_session.grammatical_range_score + 
                    exam_session.pronunciation_score
                ) / 5, 1)

                # Aggregates
                user = db.query(User).filter(User.id == exam_session.user_id).first()
                if user:
                    all_scores = db.query(ExamSession.overall_band_score).filter(
                        ExamSession.user_id == user.id,
                        ExamSession.overall_band_score.isnot(None)
                    ).all()
                    score_list = [s[0] for s in all_scores]
                    score_list.append(exam_session.overall_band_score)
                    user.total_exams_taken = len(score_list)
                    user.average_band_score = round(sum(score_list) / len(score_list), 1)
        else:
            # Same part, step prompt
            exam_session.current_prompt = intervention.next_task_prompt
    else:
        # Testing mode
        outcome = 'FAIL' if intervention.action_id == 'FAIL' else 'PASS'
        new_state = update_state(current_state, attempt, signals, outcome, current_prompt)
        # Testing mode uses dummy session ID if not real, but we don't have db_session here in scope
        # unless it's session_id = default_user. Skipping testing state persist for brevity in repair.
        pass

    db.commit()
    intervention.stress_level = current_state.stress_level
    return intervention
