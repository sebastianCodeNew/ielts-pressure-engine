import requests
import json

# Test the exact flow the frontend would use
def test_frontend_flow():
    print("🧪 Testing Frontend Flow Debug")
    print("=" * 50)
    
    # 1. Start exam
    try:
        response = requests.post('http://127.0.0.1:8000/api/v1/exams/start', 
                               json={'user_id': 'debug_user'}, 
                               timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Start exam failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        session_data = response.json()
        session_id = session_data.get('id')
        print(f"✅ Session started: {session_id[:8]}...")
        
        # 2. Get session status (what frontend would do)
        response = requests.get(f'http://127.0.0.1:8000/api/v1/exams/{session_id}/status', 
                              timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Get status failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        status_data = response.json()
        print(f"✅ Status retrieved")
        print(f"   Current prompt: {status_data.get('current_prompt', 'N/A')[:50]}...")
        print(f"   Checkpoint words: {status_data.get('checkpoint_words', [])}")
        
        # 3. Test audio submission (empty file simulation)
        from io import BytesIO
        empty_audio = BytesIO(b"")
        
        files = {"audio_file": ("test.wav", empty_audio, "audio/wav")}
        data = {
            "is_retry": False,
            "is_refactor": False
        }
        
        print("🎤 Testing audio submission...")
        response = requests.post(f'http://127.0.0.1:8000/api/v1/exams/{session_id}/submit-audio',
                               files=files, data=data, timeout=15)
        
        print(f"📊 Audio submission result: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Action: {result.get('action_id', 'N/A')}")
            print(f"   Feedback: {result.get('feedback_markdown', 'N/A')[:100]}...")
        else:
            print(f"   Error: {response.text[:200]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Frontend flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_frontend_flow()
