import requests
import json

# Test API health
try:
    response = requests.get('http://127.0.0.1:8000/docs', timeout=5)
    if response.status_code == 200:
        print('✅ Backend API docs accessible')
    else:
        print(f'⚠️ Backend API returned status: {response.status_code}')
        
    # Test start exam endpoint
    response = requests.post('http://127.0.0.1:8000/api/v1/exams/start', 
                           json={'user_id': 'test_user'}, 
                           timeout=10)
    if response.status_code == 200:
        data = response.json()
        print('✅ Start exam endpoint working')
        print(f'  - Session ID: {data.get("id", "N/A")}')
        print(f'  - Initial prompt: {data.get("current_prompt", "N/A")[:50]}...')
    else:
        print(f'❌ Start exam failed: {response.status_code}')
        print(f'  Response: {response.text[:200]}')
        
except requests.exceptions.ConnectionError:
    print('❌ Backend not running - start with: uvicorn app.main:app')
except Exception as e:
    print(f'❌ API test error: {e}')
