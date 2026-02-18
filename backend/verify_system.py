
import requests
import json
import os
import sys

BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/api"
V1_URL = f"{BASE_URL}/api/v1"

def check_feature(name, condition, data=None):
    if condition:
        print(f"[PASS] {name}")
        return True
    else:
        print(f"[FAIL] {name}")
        if data:
            print(f"   Debug Data: {json.dumps(data, indent=2)[:500]}...")
        return False

def run_verification():
    print("--- STARTING SYSTEM VERIFICATION ---")
    
    # 1. Health Check
    try:
        r = requests.get(f"{BASE_URL}/")
        r.raise_for_status()
        check_feature("System Health", r.status_code == 200, r.json())
    except Exception as e:
        print(f"[FATAL] System not running: {e}")
        return

    # 2. Start Exam (Phase 11: Briefing & Persistence)
    print("\n--- TEST: Start Exam ---")
    session_id = None
    try:
        payload = {"user_id": "verify_bot", "exam_type": "FULL_MOCK"}
        r = requests.post(f"{V1_URL}/exams/start", json=payload)
        r.raise_for_status()
        data = r.json()
        
        session_id = data.get("id")
        check_feature("Session Created", bool(session_id), data)
        check_feature("Prompt Sync (Bug Fix)", bool(data.get("current_prompt")), data)
        check_feature("Briefing Text (Phase 11)", bool(data.get("briefing_text")), data)
        check_feature("Initial Keywords", isinstance(data.get("initial_keywords"), list), data)
        
    except Exception as e:
        print(f"[FATAL] Start Exam Failed: {e}")
        return

    # 3. Submit Audio (Core Engine)
    print("\n--- TEST: Submit Audio ---")
    if not os.path.exists("test_audio.webm"):
        print("[SKIP] test_audio.webm not found")
        return

    try:
        # Simulate form data upload
        with open("test_audio.webm", "rb") as f:
            files = {"file": ("recording.webm", f, "audio/webm")}
            data = {"task_id": session_id, "is_retry": "false"} 
            # Note: task_id used as session_id in our fix
            
            r = requests.post(f"{API_URL}/submit-audio", files=files, data=data)
            r.raise_for_status()
            res = r.json()
            
            # --- FEATURE CHECKS ---
            
            # Core AI
            check_feature("AI Feedback Generation", bool(res.get("feedback_markdown")), res)
            check_feature("Transcript Generated", bool(res.get("user_transcript")), res)
            
            # Phase 13.4: Radar Metrics
            metrics = res.get("radar_metrics")
            check_feature("Micro-Wins Radar Metrics", 
                          isinstance(metrics, dict) and "fluency" in metrics, res)
            
            # Phase 13.1: Word Bank
            wb = res.get("realtime_word_bank")
            check_feature("Real-time Word Bank", isinstance(wb, list) and len(wb) > 0, res)
            
            # Phase 13.3: Confidence Score
            conf = res.get("confidence_score")
            check_feature("Confidence Score Analysis", isinstance(conf, float), res)
            
            # Phase B: Active Recall Quiz
            # Note: Might not trigger on every turn, but check if keys exist
            check_feature("Quiz Schema Presence", "quiz_question" in res, res)
            
            # Correction Drill
            check_feature("Correction Drill", bool(res.get("correction_drill")), res)

    except Exception as e:
        print(f"[FAIL] Audio Submission Failed: {e}")
        if 'r' in locals():
            print(f"Server Response: {r.text[:1000]}")

if __name__ == "__main__":
    run_verification()
