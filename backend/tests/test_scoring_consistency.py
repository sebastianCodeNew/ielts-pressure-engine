def test_calculate_band_score():
    from app.core.scoring import calculate_band_score, WPM_MULTIPLIER, COHERENCE_MULTIPLIER
    # Test wpm calculation
    assert calculate_band_score(135.0, WPM_MULTIPLIER, is_wpm=True) == 9.0
    assert calculate_band_score(0.0, WPM_MULTIPLIER, is_wpm=True) == 1.0 # low bound
    
    # Test other multiplier (9.0 * 1.0 = 9.0)
    assert calculate_band_score(1.0, COHERENCE_MULTIPLIER) == 9.0
    assert calculate_band_score(0.5, COHERENCE_MULTIPLIER) == 4.5

def test_round_to_ielts_band():
    from app.core.scoring import round_to_ielts_band
    assert round_to_ielts_band(7.2) == 7.0
    assert round_to_ielts_band(7.3) == 7.5
    assert round_to_ielts_band(7.74) == 7.5
    assert round_to_ielts_band(7.75) == 8.0
    assert round_to_ielts_band(7.8) == 8.0

def test_get_overall_band():
    from app.core.scoring import get_overall_band
    metrics = {
        "Fluency": 7.0,
        "Coherence": 7.0,
        "Lexical": 7.5,
        "Grammar": 7.0,
        "Pronunciation": 8.0
    }
    # Average is 36.5 / 5 = 7.3 => rounds to 7.5
    assert get_overall_band(metrics) == 7.5
