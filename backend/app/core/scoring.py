import math
from typing import Dict

# Band 9 Calibration Constants (v22.0 - Centralized)
# These are used to convert raw metrics from evaluator.py into IELTS Band Scores (1.0 - 9.0)

WPM_MULTIPLIER = 15.0  # WPM / 15.0 -> Band (e.g. 135 WPM = 9.0)
COHERENCE_MULTIPLIER = 9.0  # Score * 9.0 -> Band
LEXICAL_MULTIPLIER = 15.0  # Diversity * 15.0 -> Band
GRAMMAR_MULTIPLIER = 40.0  # Complexity * 40.0 -> Band
PRONUNCIATION_MULTIPLIER = 9.0  # Score * 9.0 -> Band


def calculate_band_score(
    raw_value: float,
    multiplier: float,
    high: float = 9.0,
    low: float = 1.0,
    is_wpm: bool = False,
) -> float:
    """Standardized IELTS Band Score calculation from raw signals."""
    if raw_value is None:
        return low
    try:
        val = float(raw_value)
        if is_wpm:
            score = val / multiplier
        else:
            score = val * multiplier

        return round(min(high, max(low, score)), 1)
    except (ValueError, TypeError):
        return low


def round_to_ielts_band(score: float) -> float:
    """Round a score to the nearest IELTS band (0.5 increments).
    In IELTS, .25 rounds up to .5, and .75 rounds up to next whole band.
    """
    fraction = score - math.floor(score)
    if fraction >= 0.75:
        return math.floor(score) + 1.0
    elif fraction >= 0.25:
        return math.floor(score) + 0.5
    else:
        return math.floor(score) + 0.0


def get_radar_metrics(signals) -> Dict[str, float]:
    """Generates standardized radar chart metrics for the frontend."""
    return {
        "Fluency": calculate_band_score(
            getattr(signals, "fluency_wpm", 0.0), WPM_MULTIPLIER, is_wpm=True
        ),
        "Coherence": calculate_band_score(
            getattr(signals, "coherence_score", 0.0), COHERENCE_MULTIPLIER
        ),
        "Lexical": calculate_band_score(
            getattr(signals, "lexical_diversity", 0.0), LEXICAL_MULTIPLIER
        ),
        "Grammar": calculate_band_score(
            getattr(signals, "grammar_complexity", 0.0), GRAMMAR_MULTIPLIER
        ),
        "Pronunciation": calculate_band_score(
            getattr(signals, "pronunciation_score", 0.0), PRONUNCIATION_MULTIPLIER
        ),
    }


def get_overall_band(metrics: Dict[str, float]) -> float:
    """Calculates the overall IELTS band score from the 5 sub-metrics."""
    if not metrics:
        return 0.0
    avg = sum(metrics.values()) / len(metrics)
    # The engine shows micro-progress during training, but overall should be standard IELTS
    return round_to_ielts_band(avg)


# Centralized briefing text to ensure "Band 9" promise is consistent
WELCOME_BRIEFING = "Welcome. We have set your target to Band 9.0 per your request to maximize performance."
