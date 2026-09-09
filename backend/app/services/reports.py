from datetime import datetime
from fastapi import Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    ActivitySession,
    User,
)
from app.access import patient_access


def performance(
    patient_id: str, _: User = Depends(patient_access), db: Session = Depends(get_db)
):
    sessions = (
        db.query(ActivitySession)
        .filter(
            ActivitySession.user_id == patient_id,
            ActivitySession.completed_at.is_not(None),
        )
        .order_by(ActivitySession.completed_at.asc())
        .limit(30)
        .all()
    )
    if not sessions:
        return {
            "patientId": patient_id,
            "note": "Supportive activity performance, not a medical assessment.",
            "accuracy": 0,
            "responseTime": 0,
            "difficulty": 2,
            "completion": [],
            "accuracyScores": [],
            "responseTimes": [],
            "difficultyProgression": [],
            "sessions": 0,
        }
    return {
        "patientId": patient_id,
        "note": "Supportive activity performance, not a medical assessment.",
        "accuracy": round(
            sum(item.accuracy or 0 for item in sessions) / len(sessions), 2
        ),
        "responseTime": round(
            sum(item.response_time or 0 for item in sessions) / len(sessions), 2
        ),
        "difficulty": round(
            sum(item.difficulty_level for item in sessions) / len(sessions), 1
        ),
        "completion": [
            round((1 if item.completion_status == "completed" else 0) * 100)
            for item in sessions
        ],
        "accuracyScores": [round((item.accuracy or 0) * 100) for item in sessions],
        "responseTimes": [item.response_time or 0 for item in sessions],
        "difficultyProgression": [item.difficulty_level for item in sessions],
        "sessions": len(sessions),
    }


def activity_report(
    patient_id: str,
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    activity_id: str | None = None,
    limit: int = Query(default=30, ge=1, le=100),
    _: User = Depends(patient_access),
    db: Session = Depends(get_db),
):
    query = db.query(ActivitySession).filter(ActivitySession.user_id == patient_id)
    if from_date:
        query = query.filter(ActivitySession.started_at >= from_date)
    if to_date:
        query = query.filter(ActivitySession.started_at <= to_date)
    if activity_id:
        query = query.filter(ActivitySession.activity_id == activity_id)
    sessions = (
        query.filter(ActivitySession.completed_at.is_not(None))
        .order_by(ActivitySession.started_at.asc())
        .limit(limit)
        .all()
    )
    completion_rate = (
        sum(item.completion_status == "completed" for item in sessions) / len(sessions)
        if sessions
        else 0
    )
    return {
        "patientId": patient_id,
        "summary": {
            "sessions": len(sessions),
            "completionRate": round(completion_rate, 2),
            "averageAccuracy": round(
                sum(item.accuracy or 0 for item in sessions) / len(sessions), 2
            )
            if sessions
            else 0,
            "averageResponseTime": round(
                sum(item.response_time or 0 for item in sessions) / len(sessions), 2
            )
            if sessions
            else 0,
            "averageDifficulty": round(
                sum(item.difficulty_level for item in sessions) / len(sessions), 2
            )
            if sessions
            else 0,
        },
        "series": [
            {
                "date": item.completed_at,
                "completionRate": 1 if item.completion_status == "completed" else 0,
                "accuracy": item.accuracy or 0,
                "responseTime": item.response_time or 0,
                "difficulty": item.difficulty_level,
            }
            for item in sessions
        ],
        "note": "Supportive activity performance, not a medical assessment.",
    }
