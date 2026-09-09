"""Patient-controlled consent, access revocation, and data-rights workflows."""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.access import patient_only
from app.database import get_db
from app.models import (
    ActivitySession,
    AuditEvent,
    CaregiverPatientAssignment,
    ConsentRecord,
    LocationUpdate,
    Patient,
    PrivacyRequest,
    Reminder,
    SafetySettings,
    User,
)
from app.schemas import ConsentUpdate, LocationSharingUpdate


def audit(
    db: Session,
    patient_id: str,
    actor_id: str,
    action: str,
    target_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        AuditEvent(
            patient_id=patient_id,
            actor_id=actor_id,
            action=action,
            target_id=target_id,
            metadata_json=metadata or {},
        )
    )


def privacy_status(user: User = Depends(patient_only), db: Session = Depends(get_db)):
    settings = db.get(SafetySettings, user.id)
    latest = {}
    for item in (
        db.query(ConsentRecord)
        .filter_by(patient_id=user.id)
        .order_by(ConsentRecord.recorded_at.desc())
        .all()
    ):
        latest.setdefault(
            item.purpose,
            {
                "granted": item.granted,
                "noticeVersion": item.notice_version,
                "recordedAt": item.recorded_at,
            },
        )
    return {
        "locationSharingEnabled": bool(settings and settings.location_sharing_enabled),
        "consents": latest,
    }


def set_consent(
    request: ConsentUpdate,
    user: User = Depends(patient_only),
    db: Session = Depends(get_db),
):
    db.add(
        ConsentRecord(
            patient_id=user.id,
            purpose=request.purpose,
            granted=request.granted,
            notice_version=request.notice_version,
            recorded_by=user.id,
        )
    )
    audit(
        db,
        user.id,
        user.id,
        "consent_granted" if request.granted else "consent_withdrawn",
        request.purpose,
        {"notice_version": request.notice_version},
    )
    db.commit()
    return {
        "purpose": request.purpose,
        "granted": request.granted,
        "noticeVersion": request.notice_version,
    }


def set_location_sharing(
    request: LocationSharingUpdate,
    user: User = Depends(patient_only),
    db: Session = Depends(get_db),
):
    settings = db.get(SafetySettings, user.id)
    if not settings:
        settings = SafetySettings(patient_id=user.id)
        db.add(settings)
    settings.location_sharing_enabled = request.enabled
    db.add(
        ConsentRecord(
            patient_id=user.id,
            purpose="location",
            granted=request.enabled,
            notice_version="phase1-v1",
            recorded_by=user.id,
        )
    )
    audit(
        db,
        user.id,
        user.id,
        "location_sharing_enabled" if request.enabled else "location_sharing_disabled",
    )
    db.commit()
    return {
        "enabled": request.enabled,
        "message": "Location sharing is on."
        if request.enabled
        else "Location sharing is off. No new locations will be shared.",
    }


def caregivers(user: User = Depends(patient_only), db: Session = Depends(get_db)):
    assignments = (
        db.query(CaregiverPatientAssignment)
        .filter_by(patient_id=user.id, active=True)
        .all()
    )
    return [
        {
            "id": item.caregiver_id,
            "name": db.get(User, item.caregiver_id).name,
            "email": db.get(User, item.caregiver_id).email,
        }
        for item in assignments
    ]


def revoke_caregiver(
    caregiver_id: str, user: User = Depends(patient_only), db: Session = Depends(get_db)
):
    assignment = db.get(CaregiverPatientAssignment, (caregiver_id, user.id))
    if not assignment or not assignment.active:
        raise HTTPException(
            status_code=404, detail="Active caregiver access was not found."
        )
    assignment.active = False
    audit(db, user.id, user.id, "caregiver_access_revoked", caregiver_id)
    db.commit()
    return {"revoked": True, "caregiverId": caregiver_id}


def export_data(user: User = Depends(patient_only), db: Session = Depends(get_db)):
    patient = db.get(Patient, user.id)
    audit(db, user.id, user.id, "data_export_requested")
    db.commit()
    return {
        "profile": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "age": patient.age if patient else None,
            "preferredLanguage": patient.preferred_language if patient else None,
        },
        "reminders": [
            {"id": x.id, "title": x.title, "completed": x.completed}
            for x in db.query(Reminder).filter_by(patient_id=user.id)
        ],
        "activitySessions": [
            {"id": x.id, "activityId": x.activity_id, "completedAt": x.completed_at}
            for x in db.query(ActivitySession).filter_by(user_id=user.id)
        ],
        "locationRecords": [
            {
                "id": x.id,
                "latitude": x.latitude,
                "longitude": x.longitude,
                "accuracyM": x.accuracy_m,
                "capturedAt": x.captured_at,
                "receivedAt": x.received_at,
            }
            for x in db.query(LocationUpdate).filter_by(patient_id=user.id)
        ],
        "consents": privacy_status(user, db)["consents"],
    }


def request_deletion(user: User = Depends(patient_only), db: Session = Depends(get_db)):
    open_request = (
        db.query(PrivacyRequest)
        .filter_by(patient_id=user.id, request_type="deletion", status="submitted")
        .first()
    )
    if not open_request:
        open_request = PrivacyRequest(patient_id=user.id, request_type="deletion")
        db.add(open_request)
        audit(db, user.id, user.id, "deletion_requested", open_request.id)
        db.commit()
    return {
        "requestId": open_request.id,
        "status": open_request.status,
        "message": "Deletion request recorded for review. Data is not deleted automatically while retention rules are pending approval.",
    }
