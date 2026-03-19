import requests
import json

response = requests.post('http://127.0.0.1:8000/api/v1/exams/start', 
                       json={'user_id': 'test_user'}, 
                       timeout=10)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    data = response.json()
    print(f"Checkpoint words: {data.get('checkpoint_words', 'NOT FOUND')}")
    print(f"Available fields: {list(data.keys())}")
