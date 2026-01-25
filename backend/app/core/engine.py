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
    is_exam_mode: bool = False
) -> Intervention:
    """
    Orchestrates the full loop: 
    Audio -> Text -> Analysis -> Strategy -> State Update
    """
    
    # 1. LOAD STATE FROM DB
    current_part = "PART_1" # Default
    current_prompt = "Tell me about your hometown." # Better default for IELTS PART 1
    
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

        current_state = AgentState(
            session_id=session_id,
            stress_level=0.5,
            consecutive_failures=0,
            fluency_trend="stable",
            history=[], 
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
    intervention = formulate_strategy(current_state, signals, current_part=current_part if is_exam_mode else None)
    
    # 6. UPDATE STATE & PERSIST
    if is_exam_mode:
        # Save to attempts log
        new_qa = QuestionAttempt(
            session_id=session_id,
            part=current_part,
            question_text=current_prompt, # This is the question the user JUST answered
            transcript=attempt.transcript,
            duration_seconds=attempt.audio_duration,
            wpm=signals.fluency_wpm,
            coherence_score=signals.coherence_score,
            hesitation_ratio=signals.hesitation_ratio,
            lexical_diversity=signals.lexical_diversity,
            grammar_complexity=signals.grammar_complexity,
            pronunciation_score=signals.pronunciation_score,
            feedback_markdown=intervention.feedback_markdown,
            improved_response=intervention.ideal_response
        )
        db.add(new_qa)
        
        # Prepare for NEXT question: store the intervention prompt in QuestionAttempt for next time?
        # Actually, it's better to store it in a way that we know what the user is SUPPOSED to answer next.
        # We'll use QuestionAttempt to track history, but the "current_prompt" for the NEXT turn 
        # comes from intervention.next_task_prompt.
        
        # Transition Logic
        part_count = db.query(QuestionAttempt).filter(
            QuestionAttempt.session_id == session_id,
            QuestionAttempt.part == current_part
        ).count() + 1
        
        if part_count >= 2:
            if current_part == "PART_1":
                exam_session.current_part = "PART_2"
                # FORCE UI Update: Override the agent's follow-up with the hardcoded start of Part 2
                new_prompt = "Describe a place you like to visit."
                exam_session.current_prompt = new_prompt
                intervention.next_task_prompt = new_prompt 
                intervention.action_id = "TRANSITION_PART_2"
                
            elif current_part == "PART_2":
                exam_session.current_part = "PART_3"
                # For Part 3, we use the Agent's follow up or a bridge, 
                # but let's ensure it's explicitly set if null
                if not intervention.next_task_prompt:
                     intervention.next_task_prompt = "Let's discuss this topic further."
                exam_session.current_prompt = intervention.next_task_prompt
            else:
                exam_session.status = "COMPLETED"
                exam_session.end_time = datetime.utcnow()
                exam_session.current_prompt = "Exam Completed"
                intervention.next_task_prompt = "Thank you, the exam is finished."
                
                # Calculate real summary scores from all attempts
                all_attempts = db.query(QuestionAttempt).filter(QuestionAttempt.session_id == session_id).all()
                if all_attempts:
                    def safe_avg(values):
                        nums = [v for v in values if v is not None]
                        return sum(nums) / len(nums) if nums and len(nums) > 0 else 1.0 # Default to 1.0 (lowest band) instead of 0 to avoid skewing logic

                    avg_wpm = safe_avg([a.wpm for a in all_attempts])
                    avg_coherence = safe_avg([a.coherence_score for a in all_attempts])
                    avg_lexical = safe_avg([a.lexical_diversity for a in all_attempts])
                    avg_grammar = safe_avg([a.grammar_complexity for a in all_attempts])
                    avg_pron = safe_avg([a.pronunciation_score for a in all_attempts])
                    
                    # Map to IELTS scale (0-9) - Refined mapping
                    exam_session.fluency_score = min(max(avg_wpm / 15, 1.0), 9.0)
                    exam_session.coherence_score = min(max(avg_coherence * 9, 1.0), 9.0)
                    exam_session.lexical_resource_score = min(max(avg_lexical * 15, 1.0), 9.0)
                    exam_session.grammatical_range_score = min(max(avg_grammar * 40, 1.0), 9.0)
                    exam_session.pronunciation_score = min(max(avg_pron * 9, 1.0), 9.0)
                    
                    exam_session.overall_band_score = round((
                        exam_session.fluency_score + 
                        exam_session.coherence_score +
                        exam_session.lexical_resource_score + 
                        exam_session.grammatical_range_score + 
                        exam_session.pronunciation_score
                    ) / 5, 1) # Divided by 5 metrics now

                    # UPDATE USER AGGREGATE STATS
                    user = db.query(User).filter(User.id == exam_session.user_id).first()
                    if user:
                        # Fetch all completed session scores for this user
                        all_scores = db.query(ExamSession.overall_band_score).filter(
                            ExamSession.user_id == user.id,
                            ExamSession.overall_band_score.isnot(None)
                        ).all()
                        
                        # Add the current one (it might not be committed yet so query might miss it, add manually)
                        score_list = [s[0] for s in all_scores]
                        score_list.append(exam_session.overall_band_score)
                        
                        user.total_exams_taken = len(score_list)
                        user.average_band_score = round(sum(score_list) / len(score_list), 1)

        else:
            # Same part, update prompt for next question
            exam_session.current_prompt = intervention.next_task_prompt
    else:
        outcome = 'FAIL' if intervention.action_id == 'FAIL' else 'PASS'
        new_state = update_state(current_state, attempt, signals, outcome, current_prompt)
        
        db_session.stress_level = new_state.stress_level
        db_session.consecutive_failures = new_state.consecutive_failures
        db_session.fluency_trend = new_state.fluency_trend
        
        if intervention.next_task_prompt:
            db_session.current_prompt = intervention.next_task_prompt # Store the prompt for the next turn

    db.commit()
    return intervention
