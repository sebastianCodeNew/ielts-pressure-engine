from faster_whisper import WhisperModel
import os

# 1. UPGRADE MODEL: 'medium.en' for high accuracy
# 'small.en' is a fallback if this is too slow on CPU.
print("--- Loading Whisper Model (medium.en) ---")
model = WhisperModel("medium.en", device="cpu", compute_type="int8")
print("--- Whisper Model Loaded ---")

def transcribe_audio(file_path: str) -> dict:
    # 2. TUNE PARAMETERS
    # beam_size=5: Explores more paths (better accuracy)
    # vad_filter=True: Removes silence so the model focuses on speech
    # word_timestamps=False: Faster, we don't need exact timing yet
    segments, info = model.transcribe(
        file_path, 
        beam_size=5, 
        vad_filter=True,
        #min_silence_duration_ms=500 
    )
    
    text = " ".join([segment.text for segment in segments])
    
    return {
        "text": text.strip(),
        "duration": info.duration,
        "language": info.language
    }