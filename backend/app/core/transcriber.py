from faster_whisper import WhisperModel
import os
import threading
from app.core.logger import logger
from app.core.config import settings

# Global lock to synchronize access to the Whisper model (not thread-safe on CPU)
whisper_lock = threading.Lock()
_model = None

# 1. HARDWARE DEPENDENCY CHECK (v8.0/v18.0)
import shutil
FFMPEG_PATH = shutil.which("ffmpeg")
if not FFMPEG_PATH:
    # Fallback to discovered extension path on Windows
    local_ff = r"C:\Users\user\.vscode\extensions\video-binaries\ffmpeg.exe"
    if os.path.exists(local_ff):
        FFMPEG_PATH = local_ff
        os.environ["PATH"] += os.pathsep + os.path.dirname(local_ff)

FFMPEG_AVAILABLE = FFMPEG_PATH is not None
if not FFMPEG_AVAILABLE:
    logger.error("CRITICAL: FFmpeg not found in system PATH. Audio transcription will fail.")
else:
    logger.info(f"--- FFmpeg detected: {FFMPEG_PATH} ---")

def get_whisper_model():
    """Thread-safe singleton loader for the Whisper model (v16.0)"""
    global _model
    if _model is None:
        with whisper_lock:
            if _model is None:
                logger.info(f"--- Loading Whisper Model ({settings.WHISPER_MODEL_SIZE}) ---")
                try:
                    # Model loading is a heavy operation; using int8 for better efficiency on CPU
                    _model = WhisperModel(settings.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
                    logger.info("--- Whisper Model Loaded ---")
                except Exception as e:
                    logger.error(f"CRITICAL: Failed to load Whisper model: {e}")
                    raise
    return _model

def transcribe_audio(file_path: str) -> dict:
    if not FFMPEG_AVAILABLE:
        return {"text": "[SYSTEM_ERROR: FFmpeg Missing]", "duration": 0.0, "language": "en", "error": True}
    # 2. VALIDATE FILE
    if not os.path.exists(file_path) or os.path.getsize(file_path) < 100:
        logger.warning(f"Audio file {file_path} is missing or too small.")
        return {"text": "", "duration": 0.0, "language": "en", "error": True}

    try:
        # Load or retrieve model (Thread-safe)
        whisper_model = get_whisper_model()
        
        # 3. TUNE PARAMETERS
        # Use a timeout (v9.0/v12.0 relaxed) to prevent deadlocks on corrupt files
        lock_acquired = whisper_lock.acquire(timeout=120)
        if lock_acquired:
            try:
                # transcribe is a generator, so we must consume it to get segments
                segments, info = whisper_model.transcribe(file_path, beam_size=5)
                full_text = " ".join([s.text for s in segments]).strip()
                return {"text": full_text, "duration": info.duration, "language": info.language}
            finally:
                whisper_lock.release()
        else:
            logger.error("CRITICAL: Whisper lock timeout. Transcription engine busy or hung.")
            return {"text": "[SYSTEM_ERROR: Engine Timeout]", "duration": 0.0, "language": "en", "error": True}
             
    except Exception as e:
        logger.error(f"TRANSCRIPTION CRASH: {e}", exc_info=True)
        return {"text": "[TRANSCRIPTION_FAILED]", "duration": 0.0, "language": "en", "error": True}