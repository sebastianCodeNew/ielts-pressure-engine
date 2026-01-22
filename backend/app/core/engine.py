from sqlalchemy.orm import Session
from app.schemas import UserAttempt, Intervention
from app.core.transcriber import transcribe_audio
from app.core.evaluator import extract_signals
from app.core.agent import formulate_strategy
from app.core.state import AgentState, update_state
from app.core.database import SessionModel

def process_user_attempt(
    file_path: str, 
    task_id: str, 
    db: Session, 
    session_id: str = "default_user"
) -> Intervention:
    """
    Orchestrates the full loop: 
    Audio -> Text -> Analysis -> Strategy -> State Update
    """
    
    # 1. LOAD STATE FROM DB
    db_session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if not db_session:
        # Create new session if not exists
        db_session = SessionModel(
            session_id=session_id,
            current_prompt="Describe the room you are in right now." # Default
        )
        db.add(db_session)
        db.commit()
    
    # Hydrate AgentState from DB
    # We load history from JSON if available, relying on Pydantic to parse it back
    current_state = AgentState(
        session_id=db_session.session_id,
        stress_level=db_session.stress_level,
        consecutive_failures=db_session.consecutive_failures,
        fluency_trend=db_session.fluency_trend,
        # TODO: Hydrate history from db_session.history_json if needed for context
        # history=[AttemptResult(**h) for h in db_session.history_json] if db_session.history_json else []
    )
    
    # 2. TRANSCRIBE
    print("--- Transcribing ---")
    transcript_data = transcribe_audio(file_path)
    
    # 3. ANALYZE
    attempt = UserAttempt(
        task_id=task_id,
        transcript=transcript_data['text'],
        audio_duration=transcript_data['duration']
    )
    
    current_prompt = db_session.current_prompt
    print(f"--- Analyzing: '{attempt.transcript}' against prompt: '{current_prompt}' ---")
    
    signals = extract_signals(attempt, current_prompt_text=current_prompt)
    
    # 4. AGENT DECISION
    intervention = formulate_strategy(current_state, signals)
    
    # 5. UPDATE STATE
    outcome = 'FAIL' if intervention.action_id == 'FAIL' else 'PASS'
    
    # Calculate new state
    new_state = update_state(current_state, attempt, signals, outcome, current_prompt)
    
    # 6. SAVE SESSION TO DB
    db_session.stress_level = new_state.stress_level
    db_session.consecutive_failures = new_state.consecutive_failures
    db_session.fluency_trend = new_state.fluency_trend
    
    # Update prompt for NEXT turn if agent provided one
    if intervention.topic_core:
        db_session.current_prompt = intervention.topic_core
    elif intervention.next_task_prompt:
         # Fallback: if topic_core is empty but prompt exists, might want to use that or stay on same
         # For now, let's assume topic_core is the source of truth for the "topic" state
         pass

    # Save history (optional, if we want to build it up)
    # db_session.history_json = [h.dict() for h in new_state.history]
    
    db.commit()
    db.refresh(db_session)

    print(f"--- DB Updated: Stress={new_state.stress_level:.2f}, Prompt={db_session.current_prompt} ---")
    
    return intervention
