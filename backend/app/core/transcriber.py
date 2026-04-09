import shutil

from faster_whisper import WhisperModel
import os
import threading
from app.core.logger import logger
from app.core.config import settings

# Global lock to synchronize access to the Whisper model (not thread-safe on CPU)
whisper_lock = threading.Lock()
_model = None

# 1. HARDWARE DEPENDENCY CHECK (v18.2 - Robust Multi-Path Detection)
FFMPEG_PATH = shutil.which("ffmpeg")

if not FFMPEG_PATH:
    # Check common local installation paths and VS Code extension fallbacks
    POSSIBLE_FFMPEG_PATHS = [
        os.path.join(os.getcwd(), "ffmpeg.exe"),
        os.path.join(os.getcwd(), "bin", "ffmpeg.exe"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Users\user\Downloads\ffmpeg\bin\ffmpeg.exe",
        r"C:\Users\user\.vscode\extensions\video-binaries\ffmpeg.exe",
    ]
    for path in POSSIBLE_FFMPEG_PATHS:
        if os.path.exists(path):
            FFMPEG_PATH = path
            # Add to PATH so sub-processes can find it if needed
            os.environ["PATH"] += os.pathsep + os.path.dirname(path)
            break

FFMPEG_AVAILABLE = FFMPEG_PATH is not None
if not FFMPEG_AVAILABLE:
    logger.error(
        "CRITICAL: FFmpeg not found. Audio features will fail! Please install FFmpeg and add it to PATH."
    )
else:
    logger.info(f"--- FFmpeg detected: {FFMPEG_PATH} ---")


def is_hallucination(text: str) -> bool:
    """Detects common Whisper hallucinations for silence or noise."""
    if not text:
        return True
    
    # Common artifacts for many-language or noise-heavy models
    hallucinations = [
        "thank you.", "thank you", "thanks for watching", "thanks for watching.",
        "subscribe", "subtitle by", "amara.org", "you", "thanks.", "bye.", "you.",
        "please", "translated by", "managed by", "copyright", "all rights reserved"
    ]
    
    t = text.strip().lower()
    if t in hallucinations:
        return True
    
    # Highly repetitive patterns
    words = t.split()
    if len(words) > 5:
        unique_rate = len(set(words)) / len(words)
        if unique_rate < 0.2: # e.g. "you you you you you"
            return True
            
    return False


def get_whisper_model():
    """Thread-safe singleton loader for the Whisper model (v16.0)"""
    global _model
    if _model is None:
        # v22.0: Use timeout for model load lock to prevent deadlocks
        acquired = whisper_lock.acquire(timeout=60)
        if not acquired:
            logger.error("CRITICAL: whisper_lock timeout during model loading.")
            raise RuntimeError("Transcription engine initialization timed out.")
        
        try:
            if _model is None:
                logger.info(
                    f"--- Loading Whisper Model ({settings.WHISPER_MODEL_SIZE}) ---"
                )
                try:
                    # Model loading is a heavy operation; using int8 for better efficiency on CPU
                    _model = WhisperModel(
                        settings.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8"
                    )
                    logger.info("--- Whisper Model Loaded ---")
                except Exception as e:
                    logger.error(f"CRITICAL: Failed to load Whisper model: {e}")
                    raise
        finally:
            whisper_lock.release()
    return _model


def transcribe_audio(file_path: str) -> dict:
    if not FFMPEG_AVAILABLE:
        return {
            "text": "[SYSTEM_ERROR: FFmpeg Missing]",
            "duration": 0.0,
            "language": "en",
            "error": True,
        }
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
                return {
                    "text": full_text,
                    "duration": info.duration,
                    "language": info.language,
                }
            finally:
                whisper_lock.release()
        else:
            logger.error(
                "CRITICAL: Whisper lock timeout. Transcription engine busy or hung."
            )
            return {
                "text": "[SYSTEM_ERROR: Engine Timeout]",
                "duration": 0.0,
                "language": "en",
                "error": True,
            }

    except Exception as e:
        logger.error(f"TRANSCRIPTION CRASH: {e}", exc_info=True)
        return {
            "text": "[TRANSCRIPTION_FAILED]",
            "duration": 0.0,
            "language": "en",
            "error": True,
        }
