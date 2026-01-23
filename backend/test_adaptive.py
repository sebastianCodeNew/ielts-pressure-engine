import sys
import os
from dotenv import load_dotenv

# Ensure we can import app
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.core.evaluator import extract_signals
from app.schemas import UserAttempt
from app.core.database import SessionModel, init_db, engine
from sqlalchemy.orm import sessionmaker

# Load env
load_dotenv()

def test_filler_detection():
    print("\n--- TEST 1: Filler Word Detection ---")
    transcript = "I went to the, um, store and it was, uh, really closed, you know?"
    attempt = UserAttempt(task_id="test", transcript=transcript, audio_duration=5.0)
    
    signals = extract_signals(attempt)
    print(f"Transcript: '{transcript}'")
    print(f"Filler Count detected: {signals.filler_count}")
    
    if signals.filler_count >= 3:
        print("SUCCESS: Detected fillers correctly.")
    else:
        print(f"FAIL: Expected >=3 fillers, got {signals.filler_count}")

def test_database_persistence():
    print("\n--- TEST 2: Database Persistence ---")
    # Setup In-Memory DB for test
    init_db()
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    # Create
    session_id = "test_user_v1"
    # Clean up existing test session if it exists
    db.query(SessionModel).filter(SessionModel.session_id == session_id).delete()
    db.commit()

    new_session = SessionModel(session_id=session_id, stress_level=0.5)
    db.add(new_session)
    db.commit()
    
    # Read
    read_session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    print(f"Saved Stress Level: {read_session.stress_level}")
    
    if read_session.stress_level == 0.5:
        print("SUCCESS: Database read/write works.")
    else:
        print("FAIL: DB persistence failed.")
        
    db.close()

if __name__ == "__main__":
    test_filler_detection()
    test_database_persistence()
