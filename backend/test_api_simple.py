import requests

try:
    response = requests.get('http://127.0.0.1:8000/docs', timeout=5)
    print(f"✅ Backend API accessible: {response.status_code}")
    
    # Test start exam
    response = requests.post('http://127.0.0.1:8000/api/v1/exams/start', 
                           json={'user_id': 'test_user'}, 
                           timeout=10)
    print(f"✅ Start exam: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Session ID: {data.get('id', 'N/A')}")
        print(f"   Prompt: {data.get('current_prompt', 'N/A')[:50]}...")
        print(f"   Checkpoint words: {data.get('checkpoint_words', [])}")
    
except Exception as e:
    print(f"❌ API test failed: {e}")
