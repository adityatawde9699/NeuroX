"""Patient profiles, caregiver assignments, contacts, and reminders."""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.access import can_access_patient, patient_access
from app.database import get_db
from app.models import (
    Reminder,
    User,
)
from app.presenters import public_reminder
from app.services.authentication import current_user
from app.schemas import (
    ReminderCreate,
    ReminderUpdate,
)


def reminders(
    patient_id: str,
    _: User = Depends(patient_access),
    db: Session = Depends(get_db),
):
    return [
        public_reminder(item)
        for item in db.query(Reminder)
        .filter(Reminder.patient_id == patient_id)
        .order_by(Reminder.scheduled_time)
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
    reminder = Reminder(**request.model_dump())
    db.add(reminder)
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
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(reminder, field, value)
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
