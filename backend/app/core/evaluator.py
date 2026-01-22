from app.schemas import UserAttempt, SignalMetrics
from app.core.semantic import calculate_coherence  # Import the function

import re

def extract_signals(attempt: UserAttempt, current_prompt_text: str = "general topic") -> SignalMetrics:
    """
    Analyzes the input for both mechanical (WPM) and semantic (Coherence) signals.
    """
    # 1. Mechanical Analysis
    word_count = len(attempt.transcript.split()) if attempt.transcript else 0
    wpm = (word_count / (attempt.audio_duration / 60)) if attempt.audio_duration > 0 else 0

    hesitation_score = 0.0
    if attempt.audio_duration > 5 and wpm < 40:
        hesitation_score = 0.8 
        
    # --- FILLER WORD DETECTION ---
    # Detects: um, uh, like (as filler), you know, er, ah
    # Note: 'like' is tricky, but we assume frequent usage is bad in IELTS context
    fillers = re.findall(r"\b(um|uh|er|ah|like|you know)\b", attempt.transcript.lower())
    filler_count = len(fillers)
    print(f"DEBUG: Found {filler_count} filler words: {fillers}")

    # 2. Semantic Analysis (The New Part)
    print(f"DEBUG: Calculating coherence for prompt: '{current_prompt_text}' vs response: '{attempt.transcript}...'")
    
    coherence = calculate_coherence(current_prompt_text, attempt.transcript)
    
    print(f"DEBUG: Signals -> WPM: {wpm:.1f}, Fillers: {filler_count}, Coherence: {coherence:.2f}")

    return SignalMetrics(
        fluency_wpm=round(wpm, 2),
        hesitation_ratio=hesitation_score,
        grammar_error_count=0,
        filler_count=filler_count, # Stored
        coherence_score=round(coherence, 2),
        is_complete=True
    )