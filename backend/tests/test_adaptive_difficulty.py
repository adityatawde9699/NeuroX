from app.ai.personalization.adaptive_difficulty import PerformanceInput, recommend_difficulty

def test_increases_for_strong_completion():
    level, score = recommend_difficulty(PerformanceInput(.95, 2.5, 1, 2))
    assert level == 3
    assert score >= .8

def test_bounds_low_level():
    level, _ = recommend_difficulty(PerformanceInput(.1, 20, 0, 1))
    assert level == 1
