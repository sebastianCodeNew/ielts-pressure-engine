import numpy as np
import librosa
from typing import Dict
from app.core.transcriber import whisper_lock
from app.core.logger import logger

def analyze_pronunciation(audio_path: str) -> Dict[str, float]:
    """
    Extracts acoustic features related to pronunciation clarity and fluency.
    """
    try:
        y, sr = None, None
        
        # 1. OPTIMIZED DECODER (v9.0) - Use faster-whisper as primary for speed and accuracy
        try:
            from faster_whisper.audio import decode_audio
            with whisper_lock:
                # Decodes and resamples in one C++ pass
                y = decode_audio(audio_path, sampling_rate=22050)
            sr = 22050
        except Exception as e:
            logger.error(f"Faster-whisper primary decoder failed: {e}. Falling back to librosa.")

        # 2. LEGACY FALLBACK (Slow)
        if y is None:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    y, sr = librosa.load(audio_path, sr=22050)
                except Exception as e:
                    logger.error(f"Librosa load failed: {e}")
                    return {"pronunciation_score": 0.0, "error": "Audio decode failed"}
        
        if y is None or len(y) < 2048:
            return {
                "pronunciation_score": 0.0,
                "clarity": 0.0,
                "consistency": 0.0,
                "prosody": 0.0,
                "confidence_score": 0.0,
                "avg_zcr": 0.0,
                "error": "Audio too short or silent"
            }

        # 1. Zero Crossing Rate
        zcr = librosa.feature.zero_crossing_rate(y)
        avg_zcr = np.mean(zcr)
        
        # 2. RMS Energy (Volume consistency)
        rms = librosa.feature.rms(y=y)
        avg_rms = np.mean(rms)
        std_rms = np.std(rms)
        
        # 3. Speech Rate Proxy (Spectral Centroid variability)
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        avg_centroid = np.mean(centroid)
        std_centroid = np.std(centroid)
        
        # Heuristic Pronunciation Score (0.0 to 1.0)
        # Based on volume consistency and spectral clarity
        consistency_score = 1.0 - min(std_rms / (avg_rms + 1e-6), 1.0)
        clarity_score = min(avg_zcr * 10, 1.0) # Normalizing ZCR roughly
        
        # 4. Confidence Score (v3.0 - Prosody proxy)
        # Higher spectral centroid variance often means more expressive/dynamic speech vs monotone
        prosody_score = min(std_centroid / (avg_centroid + 1e-6) * 2, 1.0)
        confidence_score = (consistency_score * 0.5 + prosody_score * 0.5)

        final_score = (consistency_score * 0.3 + clarity_score * 0.5 + prosody_score * 0.2)
        
        return {
            "pronunciation_score": round(float(final_score), 2),
            "clarity": round(float(clarity_score), 2),
            "consistency": round(float(consistency_score), 2),
            "prosody": round(float(prosody_score), 2),
            "confidence_score": round(float(confidence_score), 2),
            "avg_zcr": round(float(avg_zcr), 4)
        }
    except Exception as e:
        logger.error(f"PRONUNCIATION ERROR: {e}", exc_info=True)
        return {"pronunciation_score": 0.0, "error": str(e)}
