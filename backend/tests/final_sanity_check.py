import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

def final_sanity_check():
    print("📋 Final Sanity Check Starting...")
    
    # 1. Check Backend Imports
    try:
        from app.core.agent import formulate_strategy_async
        from app.core.cleanup import cleanup_old_audio
        from app.core.config import settings
        print("✅ Backend Imports: OK")
    except Exception as e:
        print(f"❌ Backend Imports Failed: {e}")
        return

    # 2. Check Database Settings
    if "sqlite" in settings.DATABASE_URL:
        print(f"✅ Database Config (SQLite): OK")
    
    # 3. Check Storage
    if not os.path.exists(settings.AUDIO_STORAGE_DIR):
        os.makedirs(settings.AUDIO_STORAGE_DIR)
        print(f"✅ Storage Directory Created: {settings.AUDIO_STORAGE_DIR}")
    else:
        print(f"✅ Storage Directory: OK")

    # 4. Check LLM Factoy
    from app.core.llm import get_llm
    try:
        llm = get_llm()
        print(f"✅ LLM Factory: OK (Using {settings.EVALUATOR_MODEL})")
    except Exception as e:
        print(f"❌ LLM Factory Failed: {e}")

    print("\n🚀 ALL SYSTEMS GO. Engine is hardened and ready.")

if __name__ == "__main__":
    final_sanity_check()
