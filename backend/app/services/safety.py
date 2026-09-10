from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.audit import record
from app.models import (
    LocationUpdate,
    SafetyAlert,
    SafetySettings,
    SOSEvent,
    User,
)
from app.schemas import (
    LocationUpdateCreate,
    SafetyAcknowledgement,
    SafetySettingsUpdate,
    SOSEventCreate,
)
from app.services.authentication import current_user
from app.access import caregiver_only, can_access_patient, patient_access
from app.presenters import public_contact

from app.services.safety_state import (
    active_contacts,
    public_safety_settings,
    public_location,
    public_alert,
    public_sos,
    latest_location,
    evaluate_safety,
)


def location_history(
    patient_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(patient_access),
    db: Session = Depends(get_db),
):
    settings = db.get(SafetySettings, patient_id)
    if user.id != patient_id and (
        not settings or not settings.location_sharing_enabled
    ):
        return []
    locations = (
        db.query(LocationUpdate)
        .filter_by(patient_id=patient_id)
        .order_by(LocationUpdate.captured_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [public_location(item) for item in locations]


# Get a patient's safety status
def safety(
    patient_id: str, user: User = Depends(patient_access), db: Session = Depends(get_db)
):
    evaluate_safety(patient_id, db)
    location = latest_location(patient_id, db)
    settings = db.get(SafetySettings, patient_id)
    alerts = (
        db.query(SafetyAlert)
        .filter_by(patient_id=patient_id, status="open")
        .order_by(SafetyAlert.created_at.desc())
        .all()
    )
    sos_events = (
        db.query(SOSEvent)
        .filter_by(patient_id=patient_id, status="open")
        .order_by(SOSEvent.created_at.desc())
        .all()
    )
    location_data = public_location(location)
    if user.id != patient_id and (
        not settings or not settings.location_sharing_enabled
    ):
        location_data = None
    status_text = (
        "Needs acknowledgement" if alerts or sos_events else "No open safety alerts"
    )
    if location_data and location_data["connectionState"] == "offline":
        status_text = f"{status_text} - showing last known location"
    return {
        "patientId": patient_id,
        "status": status_text,
        "location": location_data,
        "settings": public_safety_settings(settings),
        "contacts": [public_contact(item) for item in active_contacts(patient_id, db)],
        "alerts": [public_alert(item, db) for item in alerts],
        "sosEvents": [public_sos(item, db) for item in sos_events],
        "workflowNote": "Safety support is permission-aware caregiver coordination. SOS notifies configured caregivers and does not contact government or emergency services directly.",
    }


# Configure patient safety settings
def update_safety_settings(
    patient_id: str,
    request: SafetySettingsUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not can_access_patient(user, patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    settings = db.get(SafetySettings, patient_id)
    if not settings:
        settings = SafetySettings(patient_id=patient_id)
        db.add(settings)
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    settings.updated_at = datetime.now(timezone.utc)
    record(
        db,
        actor_id=user.id,
        patient_id=patient_id,
        action="safety.settings_updated",
        target_id=patient_id,
        metadata={"fields": sorted(request.model_dump(exclude_unset=True))},
    )
    db.commit()
    evaluate_safety(patient_id, db)
    db.refresh(settings)
    return public_safety_settings(settings)


# Save a patient location update
def create_location_update(
    patient_id: str,
    request: LocationUpdateCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.id != patient_id:
        raise HTTPException(
            status_code=403, detail="Only the patient can share a new location."
        )
    settings = db.get(SafetySettings, patient_id)
    if not settings or not settings.location_sharing_enabled:
        raise HTTPException(
            status_code=403,
            detail="Location sharing is off. Turn it on before sharing a location.",
        )
    if not can_access_patient(user, patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    location = LocationUpdate(patient_id=patient_id, **request.model_dump())
    db.add(location)
    db.commit()
    db.refresh(location)
    evaluate_safety(patient_id, db)
    return public_location(location)


# Create an SOS caregiver workflow event
def create_sos_event(
    patient_id: str,
    request: SOSEventCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not can_access_patient(user, patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    event = SOSEvent(patient_id=patient_id, **request.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    evaluate_safety(patient_id, db)
    return public_sos(event, db)


# Acknowledge an SOS event
def acknowledge_sos_event(
    patient_id: str,
    event_id: str,
    _: SafetyAcknowledgement,
    user: User = Depends(caregiver_only),
    db: Session = Depends(get_db),
):
    if not can_access_patient(user, patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    event = db.get(SOSEvent, event_id)
    if not event or event.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="SOS event not found.")
    event.status = "acknowledged"
    event.acknowledged_at = datetime.now(timezone.utc)
    event.acknowledged_by = user.id
    record(
        db,
        actor_id=user.id,
        patient_id=patient_id,
        action="safety.sos_acknowledged",
        target_id=event.id,
    )
    db.commit()
    db.refresh(event)
    return public_sos(event, db)


# Acknowledge a safety alert
def acknowledge_safety_alert(
    patient_id: str,
    alert_id: str,
    _: SafetyAcknowledgement,
    user: User = Depends(caregiver_only),
    db: Session = Depends(get_db),
):
    if not can_access_patient(user, patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )
    alert = db.get(SafetyAlert, alert_id)
    if not alert or alert.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Safety alert not found.")
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = user.id
    record(
        db,
        actor_id=user.id,
        patient_id=patient_id,
        action="safety.alert_acknowledged",
        target_id=alert.id,
    )
    db.commit()
    db.refresh(alert)
    return public_alert(alert, db)


# Process one offline mutation against the same persistence models as online APIs.
