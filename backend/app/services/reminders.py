"""Authorized reminder schedules and acknowledgement state."""

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.access import can_access_patient, patient_access
from app.audit import record
from app.database import get_db
from app.models import (
    Reminder,
    User,
)
from app.presenters import public_reminder
from app.schemas import ReminderCreate, ReminderUpdate, Role
from app.services.authentication import current_user


def _medication_schedule_change(fields: set[str], reminder_type: str) -> bool:
    return reminder_type == "medication" and bool(
        fields & {"scheduled_time", "repeat_rule", "enabled", "timezone_name"}
    )


def reminders(
    patient_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(patient_access),
    db: Session = Depends(get_db),
):
    return [
        public_reminder(item)
        for item in db.query(Reminder)
        .filter(Reminder.patient_id == patient_id)
        .order_by(Reminder.scheduled_time)
        .offset(offset)
        .limit(limit)
        .all()
    ]


def create_reminder(
    request: ReminderCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not can_access_patient(user, request.patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    if request.type == "medication" and user.role not in {
        Role.CAREGIVER.value,
        Role.ADMIN.value,
    }:
        raise HTTPException(
            status_code=403,
            detail="A caregiver must confirm a medication reminder schedule.",
        )
    reminder = Reminder(**request.model_dump())
    db.add(reminder)
    if request.type == "medication":
        db.flush()
        record(
            db,
            actor_id=user.id,
            patient_id=request.patient_id,
            action="reminder.medication_schedule_confirmed",
            target_id=reminder.id,
            metadata={"fields": ["created"]},
        )
    db.commit()
    db.refresh(reminder)
    return public_reminder(reminder)


def update_reminder(
    reminder_id: str,
    request: ReminderUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    reminder = db.get(Reminder, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    if not can_access_patient(user, reminder.patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    changes = request.model_dump(exclude_unset=True)
    if _medication_schedule_change(set(changes), reminder.type) and user.role not in {
        Role.CAREGIVER.value,
        Role.ADMIN.value,
    }:
        raise HTTPException(
            status_code=403,
            detail="A caregiver must confirm medication schedule changes.",
        )
    if changes.get("status") == "snoozed" and not changes.get("snoozed_until"):
        raise HTTPException(status_code=422, detail="A snooze time is required.")
    if "status" in changes:
        reminder.completed = changes["status"] == "done"
        reminder.acknowledged_at = datetime.now(timezone.utc)
        if changes["status"] != "snoozed":
            reminder.snoozed_until = None
    elif changes.get("completed") is not None:
        reminder.status = "done" if changes["completed"] else "upcoming"
        reminder.acknowledged_at = datetime.now(timezone.utc)
    for field, value in changes.items():
        setattr(reminder, field, value)
    if _medication_schedule_change(set(changes), reminder.type):
        record(
            db,
            actor_id=user.id,
            patient_id=reminder.patient_id,
            action="reminder.medication_schedule_confirmed",
            target_id=reminder.id,
            metadata={
                "fields": sorted(
                    set(changes)
                    & {"scheduled_time", "repeat_rule", "enabled", "timezone_name"}
                )
            },
        )
    db.commit()
    db.refresh(reminder)
    return public_reminder(reminder)


def delete_reminder(
    reminder_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    reminder = db.get(Reminder, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    if not can_access_patient(user, reminder.patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    db.delete(reminder)
    db.commit()
