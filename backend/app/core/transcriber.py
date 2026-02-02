from faster_whisper import WhisperModel
import os

# 1. UPGRADE MODEL: 'medium.en' for high accuracy
# 'small.en' is a fallback if this is too slow on CPU.
print("--- Loading Whisper Model (medium.en) ---")
model = WhisperModel("medium.en", device="cpu", compute_type="int8")
print("--- Whisper Model Loaded ---")

def transcribe_audio(file_path: str) -> dict:
    # 2. VALIDATE FILE
    if not os.path.exists(file_path) or os.path.getsize(file_path) < 100:
        print(f"WARNING: Audio file {file_path} is missing or too small.")
        return {"text": "", "duration": 0.0, "language": "en"}

    try:
        # 3. TUNE PARAMETERS
        segments, info = model.transcribe(
            file_path, 
            beam_size=5, 
            vad_filter=True,
        )
        
        text = " ".join([segment.text for segment in segments])
        
        return {
            "text": text.strip(),
            "duration": info.duration,
            "language": info.language
        }
    except Exception as e:
        print(f"TRANSCRIPTION CRASH: {e}")
        return {"text": "", "duration": 0.0, "language": "en"}