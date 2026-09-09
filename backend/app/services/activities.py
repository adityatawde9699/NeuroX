from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.ai.personalization.adaptive_difficulty import (
    PerformanceInput,
    recommend_from_history,
)
from app.database import get_db
from app.models import (
    ActivitySession,
    Patient,
    User,
)
from app.schemas import (
    ActivityCompletion,
    ActivityStart,
)
from app.services.authentication import current_user
from app.access import patient_access, patient_only

from app.catalog import ACTIVITIES


def activities(_: User = Depends(current_user)):
    return ACTIVITIES


# Start an activity to do
def start_activity(
    activity_id: str,
    session: ActivityStart,
    user: User = Depends(patient_only),
    db: Session = Depends(get_db),
):
    if not any(activity["id"] == activity_id for activity in ACTIVITIES):
        raise HTTPException(status_code=404, detail="Activity not found.")
    if session.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Activity user does not match the signed-in account.",
        )
    existing = (
        db.query(ActivitySession)
        .filter(ActivitySession.event_id == session.event_id)
        .first()
    )
    if existing:
        if existing.user_id != user.id:
            raise HTTPException(
                status_code=403, detail="Activity event belongs to another account."
            )
        if existing.activity_id != activity_id:
            raise HTTPException(
                status_code=409, detail="Activity event belongs to another activity."
            )
        return {
            "session_id": existing.id,
            "event_id": existing.event_id,
            "status": existing.completion_status,
            "duplicate": True,
        }
    activity_session = ActivitySession(
        event_id=session.event_id,
        user_id=user.id,
        activity_id=activity_id,
        started_at=session.started_at,
        difficulty_level=session.difficulty_level,
        offline_created=session.offline_created,
    )
    db.add(activity_session)
    db.commit()
    db.refresh(activity_session)
    return {
        "session_id": activity_session.id,
        "event_id": activity_session.event_id,
        "status": "started",
        "duplicate": False,
    }


# Activity Completion
def complete_activity(
    activity_id: str,
    session: ActivityCompletion,
    user: User = Depends(patient_only),
    db: Session = Depends(get_db),
):
    # Sync calls this function directly, bypassing FastAPI dependency execution.
    patient_only(user)
    if not any(activity["id"] == activity_id for activity in ACTIVITIES):
        raise HTTPException(status_code=404, detail="Activity not found.")
    if session.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Activity user does not match the signed-in account.",
        )
    activity_session = (
        db.query(ActivitySession)
        .filter(ActivitySession.event_id == session.event_id)
        .first()
    )
    if activity_session and activity_session.user_id != user.id:
        raise HTTPException(
            status_code=403, detail="Activity event belongs to another account."
        )
    if session.activity_id != activity_id or (
        activity_session and activity_session.activity_id != activity_id
    ):
        raise HTTPException(
            status_code=409, detail="Activity event belongs to another activity."
        )
    if not activity_session:
        activity_session = ActivitySession(
            event_id=session.event_id,
            user_id=user.id,
            activity_id=activity_id,
            started_at=session.started_at,
            difficulty_level=session.difficulty_level,
            offline_created=session.offline_created,
        )
        db.add(activity_session)
    activity_session.completed_at = session.completed_at
    activity_session.accuracy = session.accuracy
    activity_session.response_time = session.response_time
    activity_session.attempts = session.attempts
    activity_session.completion_status = session.completion_status
    db.commit()
    history_rows = (
        db.query(ActivitySession)
        .filter(
            ActivitySession.user_id == user.id,
            ActivitySession.activity_id == activity_id,
            ActivitySession.completed_at.is_not(None),
            ActivitySession.event_id != session.event_id,
        )
        .order_by(ActivitySession.completed_at.desc())
        .limit(4)
        .all()
    )
    current = PerformanceInput(
        session.accuracy,
        session.response_time,
        1 if session.completion_status == "completed" else 0,
        session.difficulty_level,
    )
    history = [
        PerformanceInput(
            item.accuracy or 0,
            item.response_time or 30,
            1 if item.completion_status == "completed" else 0,
            item.difficulty_level,
        )
        for item in reversed(history_rows)
    ]
    next_level, score = recommend_from_history(current, history)
    # Persist the recommended next difficulty so the Android app can hydrate it
    # from the patient profile without re-computing on every launch.
    patient_row = db.get(Patient, user.id)
    if patient_row:
        patient_row.next_difficulty = next_level
        db.commit()
    return {
        "saved": True,
        "event_id": session.event_id,
        "next_difficulty": next_level,
        "performance_score": score,
        "message": "Your next activity is adjusted to your performance.",
    }


# Get a patient's activity history
def activity_history(
    patient_id: str, _: User = Depends(patient_access), db: Session = Depends(get_db)
):
    sessions = (
        db.query(ActivitySession)
        .filter(ActivitySession.user_id == patient_id)
        .order_by(ActivitySession.started_at.desc())
        .limit(30)
        .all()
    )
    return [
        {
            "id": item.id,
            "activityId": item.activity_id,
            "startedAt": item.started_at,
            "completedAt": item.completed_at,
            "accuracy": item.accuracy,
            "responseTime": item.response_time,
            "attempts": item.attempts,
            "status": item.completion_status,
            "difficulty": item.difficulty_level,
        }
        for item in sessions
    ]


# Get a patient's activity performance
