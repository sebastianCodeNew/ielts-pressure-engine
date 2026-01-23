import numpy as np
import librosa
from typing import Dict

def analyze_pronunciation(audio_path: str) -> Dict[str, float]:
    """
    Extracts acoustic features related to pronunciation clarity and fluency.
    """
    try:
        y, sr = librosa.load(audio_path)
        
        # 1. Zero Crossing Rate (Higher ZCR often correlates with cleaner fricatives/clarity)
        zcr = librosa.feature.zero_crossing_rate(y)
        avg_zcr = np.mean(zcr)
        
        # 2. RMS Energy (Volume consistency)
        rms = librosa.feature.rms(y=y)
        avg_rms = np.mean(rms)
        std_rms = np.std(rms)
        
        # 3. Speech Rate Proxy (Spectral Centroid variability)
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        avg_centroid = np.mean(centroid)
        
        # Heuristic Pronunciation Score (0.0 to 1.0)
        # Based on volume consistency and spectral clarity
        consistency_score = 1.0 - min(std_rms / (avg_rms + 1e-6), 1.0)
        clarity_score = min(avg_zcr * 10, 1.0) # Normalizing ZCR roughly
        
        final_score = (consistency_score * 0.4 + clarity_score * 0.6)
        
        return {
            "pronunciation_score": round(float(final_score), 2),
            "clarity": round(float(clarity_score), 2),
            "consistency": round(float(consistency_score), 2),
            "avg_zcr": round(float(avg_zcr), 4)
        }
    except Exception as e:
        print(f"PRONUNCIATION ERROR: {e}")
        return {"pronunciation_score": 0.0, "error": str(e)}
