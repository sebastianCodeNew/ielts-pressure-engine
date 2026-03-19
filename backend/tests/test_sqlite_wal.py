import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.database import SessionLocal, text

def test_wal_mode():
    print("🚀 Verifying SQLite WAL Mode...")
    db = SessionLocal()
    try:
        result = db.execute(text("PRAGMA journal_mode")).fetchone()
        journal_mode = result[0].upper()
        print(f"Current journal mode: {journal_mode}")
        
        assert journal_mode == "WAL", f"Expected WAL mode, got {journal_mode}"
        
        # Test synchronous mode
        sync_result = db.execute(text("PRAGMA synchronous")).fetchone()
        sync_mode = sync_result[0]
        print(f"Current synchronous mode: {sync_mode} (1=NORMAL, 2=FULL)")
        
        assert sync_mode == 1 or sync_mode == 0, f"Expected 1 (NORMAL), got {sync_mode}"
        
        print("\n✅ SQLite WAL mode and Synchronous=NORMAL verified successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    test_wal_mode()
