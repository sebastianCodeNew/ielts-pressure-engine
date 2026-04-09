import requests
import os
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"
AUDIO_FILE = "valid_test_audio.wav"
USER_ID = "e2e_test_user"

def run_e2e_test():
    print(f"--- Starting E2E Test against {BASE_URL} ---")

    # 1. Start Exam
    print("\n1. Starting Exam...")
    start_payload = {
        "user_id": USER_ID,
        "exam_type": "FULL_EXAM",
        "topic_override": "Tell me about your hometown."
    }
    try:
        resp = requests.post(f"{BASE_URL}/exams/start", json=start_payload)
        resp.raise_for_status()
        session_data = resp.json()
        session_id = session_data["id"]
        print(f"   SUCCESS: Session ID: {session_id}")
        print(f"   Briefing: {session_data.get('briefing_text')}")
        print(f"   Initial Prompt: {session_data.get('current_prompt')}")
    except Exception as e:
        print(f"   FAIL: Could not start exam. {e}")
        if 'resp' in locals():
            print(f"   Response: {resp.text}")
        return

    # 2. Submit Audio
    print(f"\n2. Submitting Audio ({AUDIO_FILE})...")
    if not os.path.exists(AUDIO_FILE):
        print(f"   FAIL: Audio file {AUDIO_FILE} not found.")
        return

    try:
        with open(AUDIO_FILE, "rb") as f:
            files = {"file": (AUDIO_FILE, f, "audio/webm")}
            # Note: exams endpoint expects session_id in URL
            url = f"{BASE_URL}/exams/{session_id}/submit-audio"
            resp = requests.post(url, files=files)
            
        resp.raise_for_status()
        intervention = resp.json()
        print(f"   SUCCESS: Audio processed.")
        print(f"   Action: {intervention.get('action_id')}")
        print(f"   Next Prompt: {intervention.get('next_task_prompt')}")
        print(f"   Feedback: {intervention.get('feedback_html')}")
        
    except Exception as e:
        print(f"   FAIL: Audio submission failed. {e}")
        if 'resp' in locals():
            print(f"   Response: {resp.text}")
        return

    # 3. Get Summary (Optional - usually after exam finishes, but let's check endpoint exists)
    print("\n3. Checking Status...")
    try:
        resp = requests.get(f"{BASE_URL}/exams/{session_id}/status")
        resp.raise_for_status()
        status_data = resp.json()
        print(f"   Status: {status_data}")
    except Exception as e:
        print(f"   FAIL: Could not get status. {e}")

if __name__ == "__main__":
    run_e2e_test()
