"""Shared role and patient-assignment authorization dependencies."""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CaregiverPatientAssignment, User
from app.services.authentication import current_user
from app.schemas import Role


def caregiver_only(user: User = Depends(current_user)) -> User:
    if user.role not in {Role.CAREGIVER.value, Role.ADMIN.value}:
        raise HTTPException(status_code=403, detail="Caregiver access is required.")
    return user


def patient_only(user: User = Depends(current_user)) -> User:
    if user.role != Role.PATIENT.value:
        raise HTTPException(status_code=403, detail="Patient access is required.")
    return user


def can_access_patient(user: User, patient_id: str, db: Session) -> bool:
    if user.role == Role.ADMIN.value or user.id == patient_id:
        return True
    if user.role != Role.CAREGIVER.value:
        return False
    return (
        db.query(CaregiverPatientAssignment)
        .filter_by(caregiver_id=user.id, patient_id=patient_id, active=True)
        .first()
        is not None
    )


def patient_access(
    patient_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> User:
    if not can_access_patient(user, patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    return user
