import os
import time
from app.core.config import settings

def cleanup_old_audio(max_age_hours: int = 24):
    """
    Deletes audio files in the storage directory that are older than max_age_hours.
    """
    audio_dir = settings.AUDIO_STORAGE_DIR
    if not os.path.exists(audio_dir):
        return

    now = time.time()
    cutoff = now - (max_age_hours * 3600)
    
    deleted_count = 0
    for filename in os.listdir(audio_dir):
        file_path = os.path.join(audio_dir, filename)
        if os.path.isfile(file_path):
            file_time = os.path.getmtime(file_path)
            if file_time < cutoff:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"Error cleaning up {file_path}: {e}")
                    
    if deleted_count > 0:
        print(f"--- Audio Cleanup: Removed {deleted_count} expired files ---")
