import sys
import os
from unittest.mock import patch

# Setup paths to import app
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.core.database import SessionLocal, init_db, ExamSession, User
from app.core.engine import process_user_attempt
import uuid

def run_conversational_test():
    init_db()
    db = SessionLocal()
    user_id = "test_human_user"
    
    # Ensure user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, username="Human Tester", target_band="7.5")
        db.add(user)
        db.commit()

    # 1. Start Exam
    session_id = str(uuid.uuid4())
    from app.core.database import ExamSession
    new_session = ExamSession(
        id=session_id,
        user_id=user_id,
        exam_type="FULL_EXAM",
        current_part="PART_1",
        current_prompt="Tell me about your hometown.",
        status="IN_PROGRESS"
    )
    db.add(new_session)
    db.commit()

    print(f"=== Conversational Simulation Started (Session: {session_id}) ===")
    print(f"AI Prompt: {new_session.current_prompt}")

    # MOCK DATA: Turn 1 (Band 5 - Weak)
    turn_1_mock = {
        "text": "I... uh... from Jakarta. It is big. Many cars. Very busy. Uh... I like it.",
        "duration": 15.0,
        "language": "en"
    }

    # MOCK DATA: Turn 2 (Band 8 - Strong)
    turn_2_mock = {
        "text": "Actually, I'm originally from Jakarta, which is a bustling metropolis known for its vibrant culture and, unfortunately, its notorious traffic congestion. Despite the overcrowding, I've always found the local food scene to be quite exquisite.",
        "duration": 25.0,
        "language": "en"
    }

    # Execute Turn 1
    print("\n[TURN 1] Human: " + turn_1_mock["text"])
    with patch("app.core.engine.transcribe_audio", return_value=turn_1_mock):
        # We need a dummy file path because process_user_attempt checks existence
        dummy_file = "valid_test_audio.wav" 
        intervention = process_user_attempt(dummy_file, "PART_1", db, session_id, is_exam_mode=True)
        
        print(f"AI Feedback: {intervention.feedback_markdown[:100]}...")
        print(f"AI Strategy: {intervention.action_id}")
        print(f"Radar Scores: {intervention.radar_metrics}")
        print(f"Next AI Prompt: {intervention.next_task_prompt}")

    # Execute Turn 2
    print("\n[TURN 2] Human: " + turn_2_mock["text"])
    # We refresh session to get latest state
    db.refresh(new_session)
    
    with patch("app.core.engine.transcribe_audio", return_value=turn_2_mock):
        # We need a dummy file path because process_user_attempt checks existence
        dummy_file = "valid_test_audio.wav" 
        intervention = process_user_attempt(dummy_file, "PART_1", db, session_id, is_exam_mode=True)
        
        print(f"AI Feedback: {intervention.feedback_markdown[:100]}...")
        print(f"AI Strategy: {intervention.action_id}")
        print(f"Radar Scores: {intervention.radar_metrics}")
        print(f"Next AI Prompt: {intervention.next_task_prompt}")

    db.close()

if __name__ == "__main__":
    run_conversational_test()
