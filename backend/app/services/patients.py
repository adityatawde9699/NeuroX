"""Patient profiles, caregiver assignments, contacts, and reminders."""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.access import caregiver_only, can_access_patient, patient_access
from app.audit import record
from app.database import get_db
from app.models import (
    CaregiverPatientAssignment,
    EmergencyContact,
    Patient,
    User,
)
from app.presenters import public_contact, public_patient
from app.services.authentication import current_user
from app.schemas import (
    EmergencyContactCreate,
    EmergencyContactUpdate,
)


def my_patient(user: User = Depends(current_user), db: Session = Depends(get_db)):
    patient = db.get(Patient, user.id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found.")
    record(
        db,
        actor_id=user.id,
        patient_id=user.id,
        action="patient_data.accessed",
        target_id=user.id,
    )
    db.commit()
    return public_patient(patient, user)


def patient(
    patient_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    patient_user = db.get(User, patient_id)
    patient_profile = db.get(Patient, patient_id)
    if (
        not patient_user
        or not patient_profile
        or not can_access_patient(user, patient_id, db)
    ):
        raise HTTPException(status_code=404, detail="Patient not found.")
    record(
        db,
        actor_id=user.id,
        patient_id=patient_id,
        action="patient_data.accessed",
        target_id=patient_id,
    )
    db.commit()
    return public_patient(patient_profile, patient_user)


def assigned_patients(
    user: User = Depends(caregiver_only), db: Session = Depends(get_db)
):
    assignments = (
        db.query(CaregiverPatientAssignment)
        .filter_by(caregiver_id=user.id, active=True)
        .all()
    )
    for item in assignments:
        record(
            db,
            actor_id=user.id,
            patient_id=item.patient_id,
            action="patient_data.accessed",
            target_id=item.patient_id,
        )
    db.commit()
    return [
        public_patient(db.get(Patient, item.patient_id), db.get(User, item.patient_id))
        for item in assignments
    ]


def emergency_contacts(
    patient_id: str,
    _: User = Depends(patient_access),
    db: Session = Depends(get_db),
):
    return [
        public_contact(item)
        for item in db.query(EmergencyContact)
        .filter_by(patient_id=patient_id, active=True)
        .order_by(EmergencyContact.priority)
        .all()
    ]


def create_emergency_contact(
    patient_id: str,
    request: EmergencyContactCreate,
    _: User = Depends(patient_access),
    db: Session = Depends(get_db),
):
    contact = EmergencyContact(patient_id=patient_id, **request.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return public_contact(contact)


def update_emergency_contact(
    patient_id: str,
    contact_id: str,
    request: EmergencyContactUpdate,
    _: User = Depends(patient_access),
    db: Session = Depends(get_db),
):
    contact = (
        db.query(EmergencyContact)
        .filter_by(id=contact_id, patient_id=patient_id)
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Emergency contact not found.")
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return public_contact(contact)
