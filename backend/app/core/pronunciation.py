import numpy as np
import librosa
from typing import Dict

def analyze_pronunciation(audio_path: str) -> Dict[str, float]:
    """
    Extracts acoustic features related to pronunciation clarity and fluency.
    """
    try:
        y, sr = None, None
        
        # Proactively check for .webm to avoid librosa warnings
        if audio_path.endswith(".webm"):
            try:
                # Local import to avoid overhead if not used, but wrapped safely
                from faster_whisper.audio import decode_audio
                y = decode_audio(audio_path, sampling_rate=22050)
                sr = 22050
            except ImportError:
                print("Faster-whisper not installed or audio module missing.")
            except Exception as e:
                print(f"Faster-whisper decoder failed for webm: {e}")

        # If not webm or if decoder failed, try librosa with silenced warnings
        if y is None:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    y, sr = librosa.load(audio_path, sr=22050)
                except Exception as e:
                    print(f"Librosa load failed: {e}")
                    # Final fallback try
                    try:
                        from faster_whisper.audio import decode_audio
                        y = decode_audio(audio_path, sampling_rate=22050)
                        sr = 22050
                    except Exception as e2:
                        print(f"Final audio decode fallback failed: {e2}")
                        return {"pronunciation_score": 0.0, "error": "Audio decode failed"}
        
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
        import traceback
        print(f"PRONUNCIATION ERROR: {e}")
        traceback.print_exc()
        return {"pronunciation_score": 0.0, "error": str(e)}
