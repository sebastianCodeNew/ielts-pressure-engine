from app.schemas import UserAttempt, SignalMetrics
from app.core.semantic import calculate_coherence_async
import re

async def extract_signals_async(attempt: UserAttempt, current_prompt_text: str = "general topic") -> SignalMetrics:
    """
    Analyzes the input for both mechanical (WPM) and semantic (Coherence) signals (Async).
    """
    transcript = attempt.transcript or ""
    
    # 1. Mechanical Analysis
    word_count = len(transcript.split()) if transcript else 0
    wpm = (word_count / (attempt.audio_duration / 60)) if attempt.audio_duration > 0 else 0

    fillers = re.findall(r"\b(um|uh|er|ah|like|you know)\b", transcript.lower())
    filler_count = len(fillers)

    hesitation_score = 0.0
    if attempt.audio_duration > 3:
        hesitation_score = max(0.0, min(1.0, 1.0 - (wpm / 100.0)))
        if filler_count > 3:
            hesitation_score = min(1.0, hesitation_score + 0.1 * (filler_count - 3))

    # 2. Semantic Analysis (Async)
    coherence = await calculate_coherence_async(current_prompt_text, transcript)
    
    # 3. Lexical Diversity
    unique_words = set(transcript.lower().split())
    lexical_diversity = len(unique_words) / word_count if word_count > 0 else 0
    
    # 4. Grammar Complexity
    conjunctions = re.findall(r"\b(because|although|however|therefore|while|if|which|that)\b", transcript.lower())
    grammar_complexity = len(conjunctions) / word_count if word_count > 0 else 0

    print(f"DEBUG: Signals (Async) -> WPM: {wpm:.1f}, LexDiv: {lexical_diversity:.2f}, Coherence: {coherence:.2f}")

    return SignalMetrics(
        fluency_wpm=round(wpm, 2),
        hesitation_ratio=hesitation_score,
        grammar_error_count=0,
        filler_count=filler_count,
        coherence_score=round(coherence, 2),
        lexical_diversity=round(lexical_diversity, 2),
        grammar_complexity=round(grammar_complexity, 2),
        is_complete=True
    )