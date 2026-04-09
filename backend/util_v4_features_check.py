
import sys
import os
sys.path.append(os.getcwd())

from app.core.error_gym import generate_error_gym_drills
from app.core.database import SessionLocal, ErrorLog
from app.api.v1.endpoints.exams import get_error_gym

def test_error_gym_generation():
    print("Testing Error Gym Generation...")
    
    # Test 1: Generate drills for a common error
    error_type = "Subject-Verb Agreement"
    print(f"Generating drills for: {error_type}")
    
    try:
        session = generate_error_gym_drills(error_type)
        print("Success! Generated session:")
        print(f"Focus Area: {session.focus_area}")
        print(f"Number of Drills: {len(session.drills)}")
        for i, drill in enumerate(session.drills):
            print(f"  Drill {i+1}: {drill.sentence_with_error} -> {drill.correct_sentence}")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_error_gym_generation()
