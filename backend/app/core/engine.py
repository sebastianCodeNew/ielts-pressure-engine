from sqlalchemy.orm import Session
from datetime import datetime
from app.schemas import UserAttempt, Intervention, DetailedScores, SignalMetrics
from app.core.transcriber import transcribe_audio
from app.core.evaluator import extract_signals
from app.core.agent import formulate_strategy
from app.core.state import AgentState, update_state
from app.core.database import SessionModel, ExamSession, QuestionAttempt
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
        # The prompt is often stored in the session or can be derived from the last intervention
        # For now, we'll try to get the last intervention's prompt if it exists
        last_attempt = db.query(QuestionAttempt).filter(
            QuestionAttempt.session_id == session_id
        ).order_by(QuestionAttempt.created_at.desc()).first()
        
        if last_attempt and last_attempt.improved_response: # Using improved_response or similar to store prompt? 
            # Actually, let's look at how current_prompt was being used.
            # It was being set to exam_session.current_part which is "PART_1" etc.
            # We need to store the actual question text.
            pass 
        
        # If it's the very first attempt in the session, use a default for the part
        if not last_attempt:
            if current_part == "PART_1":
                current_prompt = "Can you tell me about your hometown?"
            elif current_part == "PART_2":
                current_prompt = "Describe a place you like to visit."
            else:
                current_prompt = "Let's talk more about the topic from Part 2."
        else:
            # We should have stored the prompt in QuestionAttempt.question_text
            current_prompt = last_attempt.question_text if last_attempt.question_text else "General topic"

        current_state = AgentState(
            session_id=session_id,
            stress_level=0.5,
            consecutive_failures=0,
            fluency_trend="stable",
            history=[],
            current_part=current_part
        )
    else:
        db_session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
        if not db_session:
            db_session = SessionModel(
                session_id=session_id,
                current_prompt="Describe the room you are in right now."
            )
            db.add(db_session)
            db.commit()
        
        current_state = AgentState(
            session_id=db_session.session_id,
            stress_level=db_session.stress_level,
            consecutive_failures=db_session.consecutive_failures,
            fluency_trend=db_session.fluency_trend,
        )
        current_prompt = db_session.current_prompt
    
    # 2. TRANSCRIBE
    print(f"--- Processing Attempt (ExamMode={is_exam_mode}, Prompt='{current_prompt}') ---")
    try:
        transcript_data = transcribe_audio(file_path)
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
            elif current_part == "PART_2":
                exam_session.current_part = "PART_3"
            else:
                exam_session.status = "COMPLETED"
                exam_session.end_time = datetime.utcnow()
                
                # Calculate real summary scores from all attempts
                all_attempts = db.query(QuestionAttempt).filter(QuestionAttempt.session_id == session_id).all()
                if all_attempts:
                    def safe_avg(values):
                        nums = [v for v in values if v is not None]
                        return sum(nums) / len(nums) if nums else 0.0

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

    db.commit()
    return intervention
