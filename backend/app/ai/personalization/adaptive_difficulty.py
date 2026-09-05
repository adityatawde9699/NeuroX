"""Supportive activity personalization; never a clinical assessment."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceInput:
    accuracy: float
    response_time_seconds: float
    completion_rate: float
    current_difficulty: int


def recommend_difficulty(data: PerformanceInput) -> tuple[int, float]:
    """Return a bounded next activity level and transparent performance score."""
    normalized_response = max(0.0, min(1.0, 1 - (data.response_time_seconds - 2) / 8))
    score = 0.6 * data.accuracy + 0.2 * normalized_response + 0.2 * data.completion_rate
    adjustment = 1 if score >= 0.80 else -1 if score < 0.50 else 0
    return max(1, min(5, data.current_difficulty + adjustment)), round(score, 2)
