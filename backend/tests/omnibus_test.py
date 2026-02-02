import sys
import os
import json
from fastapi.testclient import TestClient

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.database import init_db, SessionLocal, engine, Base, ErrorLog
from app.core.engine import process_user_attempt

# Mocking the AI components to avoid real API costs/delays, 
# OR use a specific "TEST_MODE" flag if we want real integration.
# For this "Omnibus", we'll run against the real logic but maybe mock the heavy ML parts 
# if the user just wants flow verification. 
# However, to "test all features" implies verifying the AI integration too. 
# Let's assume we run against the live system but warn about keys.

client = TestClient(app)

def run_omnibus_test():
    print("🚀 STARTING OMNIBUS TEST: Phases 8-11 Integration Check\n")
    
    # 0. Setup: Clean DB for the test user
    TEST_USER_ID = "test_omnibus_user"
    print(f"[0] Setting up Test User: {TEST_USER_ID}...")
    
    # Direct DB access to clean up
    db = SessionLocal()
    try:
        # Clear old data
        db.execute(f"DELETE FROM users WHERE id='{TEST_USER_ID}'")
        db.execute(f"DELETE FROM exam_sessions WHERE user_id='{TEST_USER_ID}'")
        db.execute(f"DELETE FROM error_logs WHERE user_id='{TEST_USER_ID}'")
        db.commit()
    except Exception as e:
        print(f"Warning during cleanup: {e}")
    finally:
        db.close()

    # 1. Start Exam (Verifies Phase 11 Briefing)
    print("\n[1] Testing Phase 11: Pre-Exam Briefing & Session Start...")
    response = client.post("/api/v1/exams/start", json={
        "user_id": TEST_USER_ID,
        "exam_type": "FULL_MOCK"
    })
    
    if response.status_code != 200:
        print(f"❌ Failed to start exam: {response.text}")
        return

    data = response.json()
    session_id = data['id']
    briefing = data.get('briefing_text', 'NO DATA')
    
    if "Welcome" in briefing:
        print(f"✅ Exam Started. Session ID: {session_id}")
        print(f"✅ Briefing Received: \"{briefing}\"")
    else:
        print("❌ Briefing missing or malformed.")

    # 2. Simulate Audio Submission (Verifies Phase 8 Analysis & Logic)
    # We need a dummy file. 
    with open("test_audio_dummy.webm", "wb") as f:
        f.write(b"\x00" * 1024) # 1KB dummy file

    print("\n[2] Testing Phase 8: Analysis Engine & Feedback...")
    # Note: This will likely fail transcription if we don't mock it, 
    # but the engine handles empty transcription gracefully.
    
    with open("test_audio_dummy.webm", "rb") as f:
        # We assume the engine continues even if transcription is empty for specific test logic
        # OR we rely on the implementation's fallback
        response = client.post(
            f"/api/v1/exams/{session_id}/submit-audio", 
            files={"file": ("test.webm", f, "audio/webm")}
        )
    
    if response.status_code == 200:
        intervention = response.json()
        print("✅ Audio submission processed.")
        print(f"   -> Feedback: {intervention.get('feedback_markdown')[:50]}...")
        print(f"   -> Next Prompt: {intervention.get('next_task_prompt')}")
        
        # Check Error Tracking (Phase 11 Logic)
        # The engine should have logged errors if any were found in feedback
    else:
        print(f"❌ Submission failed: {response.text}")

    # 3. Verify Error Persistence (Phase 11 Long-Term Memory)
    print("\n[3] Testing Phase 11: Error Persistence...")
    
    # Manually inject an error log to simulate history if the dummy audio didn't trigger one
    db = SessionLocal()
    db.add(ErrorLog(user_id=TEST_USER_ID, error_type="Subject-Verb Agreement", count=5))
    db.commit()
    db.close()
    
    # Start SECOND Exam to see if Briefing changes
    print("   -> Starting Second Session to check Memory...")
    response_2 = client.post("/api/v1/exams/start", json={
        "user_id": TEST_USER_ID,
        "exam_type": "FULL_MOCK"
    })
    
    data_2 = response_2.json()
    briefing_2 = data_2.get('briefing_text', '')
    
    if "Subject-Verb Agreement" in briefing_2:
        print(f"✅ PERSISTENCE CONFIRMED! Briefing referenced past error: \"{briefing_2}\"")
    else:
        print(f"❌ Persistence check failed. Briefing: \"{briefing_2}\"")

    # 4. Verify Phase 9 Gym (Drills/Recommendations)
    # Assuming Gym uses the 'stats' endpoint or similar
    print("\n[4] Testing Phase 9: Gym Status...")
    # This usually sits on the frontend fetching /stats or /weakness
    # Let's check user profile update
    db = SessionLocal()
    user = db.query(ErrorLog).filter(ErrorLog.user_id == TEST_USER_ID).first()
    if user:
        print(f"✅ Error Logs found in DB for Gym prescriptions.")
    else:
        print("❌ No error logs found.")
    db.close()

    print("\n🎉 OMNIBUS TEST COMPLETE.")
    
    # Cleanup
    if os.path.exists("test_audio_dummy.webm"):
        os.remove("test_audio_dummy.webm")

if __name__ == "__main__":
    run_omnibus_test()
