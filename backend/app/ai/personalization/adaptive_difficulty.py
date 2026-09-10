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


def recommend_from_history(
    current: PerformanceInput, recent: list[PerformanceInput]
) -> tuple[int, float]:
    """Use a short recent history so one unusual session does not change the next level."""
    inputs = (recent + [current])[-5:]
    scores = []
    for item in inputs:
        _, score = recommend_difficulty(item)
        scores.append(score)
    average_score = round(sum(scores) / len(scores), 2)
    strong_count = sum(score >= 0.80 for score in scores[-3:])
    low_count = sum(score < 0.50 for score in scores[-3:])
    adjustment = (
        1
        if len(scores) >= 3 and strong_count == 3
        else -1
        if len(scores) >= 3 and low_count == 3
        else 0
    )
    return max(1, min(5, current.current_difficulty + adjustment)), average_score
