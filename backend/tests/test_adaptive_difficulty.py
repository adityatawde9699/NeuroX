from app.ai.personalization.adaptive_difficulty import (
    PerformanceInput,
    recommend_difficulty,
    recommend_from_history,
)


def test_increases_for_strong_completion():
    level, score = recommend_difficulty(PerformanceInput(0.95, 2.5, 1, 2))
    assert level == 3
    assert score >= 0.8


def test_bounds_low_level():
    level, _ = recommend_difficulty(PerformanceInput(0.1, 20, 0, 1))
    assert level == 1


def test_history_requires_consistent_strong_sessions():
    strong = PerformanceInput(0.95, 2.5, 1, 2)
    assert recommend_from_history(strong, [strong, strong])[0] == 3


def test_history_requires_consistent_low_sessions():
    low = PerformanceInput(0.1, 20, 0, 2)
    assert recommend_from_history(low, [low, low])[0] == 1


def test_history_caps_at_maximum_level():
    strong = PerformanceInput(0.95, 2.5, 1, 5)
    assert recommend_from_history(strong, [strong, strong])[0] == 5
