
import sys
import os
sys.path.append(os.getcwd())

from app.core.database import SessionLocal, User
from app.api.v1.endpoints.users import get_user_stats

def test_stats_endpoint():
    print("Testing /me/stats endpoint...")
    db = SessionLocal()
    try:
        # Simulate request
        stats = get_user_stats(user_id="default_user", db=db)
        print("Success! Stats received:")
        print(stats)
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_stats_endpoint()
