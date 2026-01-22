from sqlalchemy.orm import Session
from datetime import datetime
from app.schemas import UserAttempt, Intervention, DetailedScores, SignalMetrics
from app.core.transcriber import transcribe_audio
from app.core.evaluator import extract_signals
from app.core.agent import formulate_strategy
from app.core.state import AgentState, update_state
from app.core.database import SessionModel, ExamSession, QuestionAttempt

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
    if is_exam_mode:
        exam_session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
        if not exam_session:
            raise ValueError(f"Exam session {session_id} not found")
        
        current_part = exam_session.current_part
        current_prompt = exam_session.current_part # Use part name as default prompt
        
        current_state = AgentState(
            session_id=session_id,
            stress_level=0.5,
            consecutive_failures=0,
            fluency_trend="stable",
            history=[],
            current_part=current_part # Need to ensure AgentState supports this or pass separate
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
    print(f"--- Processing Attempt (ExamMode={is_exam_mode}) ---")
    transcript_data = transcribe_audio(file_path)
    
    # 3. ANALYZE
    attempt = UserAttempt(
        task_id=task_id,
        transcript=transcript_data['text'],
        audio_duration=transcript_data['duration']
    )
    
    signals = extract_signals(attempt, current_prompt_text=current_prompt)
    
    # 4. AGENT DECISION
    # Pass current_part to formulate_strategy
    intervention = formulate_strategy(current_state, signals, current_part=current_part if is_exam_mode else None)
    
    # 5. UPDATE STATE & PERSIST
    if is_exam_mode:
        # Save to attempts log
        new_qa = QuestionAttempt(
            session_id=session_id,
            part=current_part,
            question_text=current_prompt,
            transcript=attempt.transcript,
            duration_seconds=attempt.audio_duration,
            wpm=signals.fluency_wpm,
            coherence_score=signals.coherence_score,
            hesitation_ratio=signals.hesitation_ratio,
            feedback_markdown=intervention.feedback_markdown,
            improved_response=intervention.ideal_response
        )
        db.add(new_qa)
        
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
                exam_session.overall_band_score = 7.0 
    else:
        outcome = 'FAIL' if intervention.action_id == 'FAIL' else 'PASS'
        new_state = update_state(current_state, attempt, signals, outcome, current_prompt)
        
        db_session.stress_level = new_state.stress_level
        db_session.consecutive_failures = new_state.consecutive_failures
        db_session.fluency_trend = new_state.fluency_trend
        
        if intervention.topic_core:
            db_session.current_prompt = intervention.topic_core

    db.commit()
    return intervention
