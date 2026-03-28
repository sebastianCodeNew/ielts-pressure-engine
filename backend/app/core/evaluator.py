from app.schemas import UserAttempt, SignalMetrics
from app.core.semantic import calculate_coherence_async
import re

async def extract_signals_async(attempt: UserAttempt, current_prompt_text: str = "general topic") -> SignalMetrics:
    """
    Analyzes the input for both mechanical (WPM) and semantic (Coherence) signals (Async).
    """
    transcript = attempt.transcript or ""
    
    # 0. Short-circuit for failures or silence (v14.0 - Failure Safe)
    if not transcript or transcript.strip() == "" or "[TRANSCRIPTION_FAILED]" in transcript:
        return SignalMetrics(
            fluency_wpm=0.0,
            hesitation_ratio=1.0,
            grammar_error_count=0,
            filler_count=0,
            coherence_score=0.0,
            lexical_diversity=0.0,
            grammar_complexity=0.0,
            is_complete=False
        )

    # 1. Mechanical Analysis
    word_count = len(transcript.split()) if transcript else 0
    wpm = (word_count / (attempt.audio_duration / 60)) if attempt.audio_duration > 0 else 0
    wpm = min(400.0, float(wpm))  # Cap WPM to human bounds in case of timestamp glitches

    # Advanced Filler Detection (v7.0)
    fillers = re.findall(
        r"\b(um|uh|er|ah|like|you know|basically|actually|well|to be honest|as I was saying|what I mean is|sort of|kind of)\b", 
        transcript.lower()
    )
    filler_count = len(fillers)

    # 1b. Redundancy Detection (v14.0 - Elite Band 8/9 Criteria)
    REDUNDANCY_PATTERNS = [
        r"\bin my opinion i think\b",
        r"\bfor me personally\b",
        r"\bi would like to talk about the topic of\b",
        r"\bas i mentioned before\b.*\bas i mentioned before\b",
        r"\bto be honest with you\b",
        r"\bi want to say that\b",
        r"\blet me tell you that\b",
        r"\bwhat i want to say is\b",
    ]
    redundancy_count = sum(
        len(re.findall(p, transcript.lower())) for p in REDUNDANCY_PATTERNS
    )
    # Penalty: each redundancy reduces effective lexical score later
    redundancy_penalty = min(0.3, redundancy_count * 0.1)

    hesitation_score = 0.0
    if attempt.audio_duration > 3:
        hesitation_score = max(0.0, min(1.0, 1.0 - (wpm / 100.0)))
        if filler_count > 3:
            hesitation_score = min(1.0, hesitation_score + 0.1 * (filler_count - 3))

    # 2. Semantic Analysis (Async)
    coherence = await calculate_coherence_async(current_prompt_text, transcript)
    
    # 3. Lexical Diversity (v13.0 - Length Calibrated)
    unique_words = set(transcript.lower().split())
    # PENALTY: Very short responses (<15 words) have their diversity capped 
    # to prevent "perfect" TTR scores for simple sentences.
    ttr = len(unique_words) / word_count if word_count > 0 else 0
    if word_count < 15:
        lexical_diversity = ttr * (word_count / 15.0)
    else:
        lexical_diversity = ttr
    
    # Apply redundancy penalty (v14.0)
    lexical_diversity = max(0.0, lexical_diversity - redundancy_penalty)
    
    # 4. Grammar Complexity & Cohesion (v13.0 - Clause Density)
    # Looking for connectors that typically link subordinate clauses
    connectors = re.findall(
        r"\b(because|although|however|therefore|while|if|which|that|furthermore|moreover|subsequently|consequently|nonetheless|nevertheless|despite|whereas)\b", 
        transcript.lower()
    )
    # Clause density calculation: rewarding connectors appearing between word sequences
    grammar_complexity = len(connectors) / word_count if word_count > 0 else 0

    from app.core.logger import logger
    logger.info(f"Signals (Async) -> WPM: {wpm:.1f}, LexDiv: {lexical_diversity:.2f}, Coherence: {coherence:.2f}")

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
