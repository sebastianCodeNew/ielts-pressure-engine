from faster_whisper import WhisperModel
import os
import threading
from app.core.logger import logger
from app.core.config import settings

# Global lock to synchronize access to the Whisper model (not thread-safe on CPU)
whisper_lock = threading.Lock()

# Load model based on config
logger.info(f"--- Loading Whisper Model ({settings.WHISPER_MODEL_SIZE}) ---")

# 1. HARDWARE DEPENDENCY CHECK (v8.0)
import shutil
if not shutil.which("ffmpeg"):
    logger.error("CRITICAL: FFmpeg not found in system PATH. Audio transcription will fail.")
    FFMPEG_AVAILABLE = False
else:
    FFMPEG_AVAILABLE = True

model = WhisperModel(settings.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
logger.info("--- Whisper Model Loaded ---")

def transcribe_audio(file_path: str) -> dict:
    if not FFMPEG_AVAILABLE:
        return {"text": "[SYSTEM_ERROR: FFmpeg Missing]", "duration": 0.0, "language": "en", "error": True}
    # 2. VALIDATE FILE
    if not os.path.exists(file_path) or os.path.getsize(file_path) < 100:
        logger.warning(f"Audio file {file_path} is missing or too small.")
        return {"text": "", "duration": 0.0, "language": "en"}

    try:
        # 3. TUNE PARAMETERS
        # Use a timeout (v9.0/v12.0 relaxed) to prevent deadlocks on corrupt files
        # 120s (v12.0) is safer for low-end hardware during transcript load
        lock_acquired = whisper_lock.acquire(timeout=120)
        if not lock_acquired:
            logger.error("CRITICAL: Whisper lock timeout. Transcription engine busy or hung.")
            return {"text": "[SYSTEM_ERROR: Engine Timeout]", "duration": 0.0, "language": "en", "error": True}
            
        try:
            segments, info = model.transcribe(
                file_path, 
                beam_size=5, 
                vad_filter=True,
            )
        except Exception as e:
            logger.error(f"Whisper transcribe failed: {e}", exc_info=True)
            return {"text": "", "duration": 0.0, "language": "en"}
        finally:
            whisper_lock.release()
        
        text = " ".join([segment.text for segment in segments])
        
        return {
            "text": text.strip(),
            "duration": info.duration,
            "language": info.language
        }
    except Exception as e:
        print(f"TRANSCRIPTION CRASH: {e}")
        return {"text": "", "duration": 0.0, "language": "en"}