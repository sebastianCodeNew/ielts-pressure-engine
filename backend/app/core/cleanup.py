import os
import time
from app.core.config import settings
from app.core.logger import logger

def cleanup_old_audio(max_age_hours: int = 24, max_size_mb: int = 500):
    """
    Deletes audio files based on age (max_age_hours) AND folder size (max_size_mb).
    Ensures the student's local machine is never overwhelmed by audio data.
    """
    audio_dir = settings.AUDIO_STORAGE_DIR
    if not os.path.exists(audio_dir):
        return

    # 1. TIME-BASED CLEANUP
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
                    logger.error(f"Error cleaning up expired file {file_path}: {e}")
                    
    if deleted_count > 0:
        logger.info(f"--- Audio Cleanup: Removed {deleted_count} expired files ---")

    # 2. SIZE-BASED EMERGENCY CLEANUP (v16.0 - Physical Safety)
    try:
        files = []
        total_size = 0
        for f in os.listdir(audio_dir):
            fp = os.path.join(audio_dir, f)
            if os.path.isfile(fp):
                size = os.path.getsize(fp)
                total_size += size
                files.append((fp, os.path.getmtime(fp), size))
        
        # Convert total_size to MB
        total_size_mb = total_size / (1024 * 1024)
        
        if total_size_mb > max_size_mb:
            logger.warning(f"Audio storage size ({total_size_mb:.1f}MB) exceeds quota ({max_size_mb}MB). Purging oldest files...")
            
            # Sort by mtime (oldest first)
            files.sort(key=lambda x: x[1])
            
            quota_deleted = 0
            # Target 300MB after cleanup to prevent immediate re-triggering
            target_size = 300 * 1024 * 1024
            
            for fp, _, size in files:
                try:
                    os.remove(fp)
                    total_size -= size
                    quota_deleted += 1
                    if total_size <= target_size:
                        break
                except Exception as e:
                    logger.error(f"Quota cleanup failed for {fp}: {e}")
            
            if quota_deleted > 0:
                logger.info(f"--- Quota Cleanup: Removed {quota_deleted} extra files to free space ({total_size / (1024*1024):.1f}MB remaining) ---")
                
    except Exception as e:
        logger.error(f"Storage quota check failed: {e}")
