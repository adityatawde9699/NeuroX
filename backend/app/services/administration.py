from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.access import admin_only
from app.audit import record
from app.database import get_db
from app.models import (
    AuditEvent,
    CaregiverPatientAssignment,
    Patient,
    PrivacyRequest,
    User,
)
from app.schemas import AssignmentCreate, PrivacyReview, Role


def audit_events(
    patient_id: str | None = None,
    action: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    query = db.query(AuditEvent)
    if patient_id:
        query = query.filter(AuditEvent.patient_id == patient_id)
    if action:
        query = query.filter(AuditEvent.action == action)
    return [
        {
            "id": item.id,
            "patientId": item.patient_id,
            "actorId": item.actor_id,
            "action": item.action,
            "targetId": item.target_id,
            "metadata": item.metadata_json,
            "occurredAt": item.occurred_at,
        }
        for item in query.order_by(AuditEvent.occurred_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    ]


def privacy_requests(
    status_filter: str = Query(
        default="submitted", alias="status", pattern="^(submitted|approved|rejected)$"
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    return [
        {
            "id": item.id,
            "patientId": item.patient_id,
            "type": item.request_type,
            "status": item.status,
            "requestedAt": item.requested_at,
            "reviewedBy": item.reviewed_by,
            "reviewedAt": item.reviewed_at,
        }
        for item in db.query(PrivacyRequest)
        .filter(PrivacyRequest.status == status_filter)
        .order_by(PrivacyRequest.requested_at)
        .offset(offset)
        .limit(limit)
        .all()
    ]


def review_privacy_request(
    request_id: str,
    review: PrivacyReview,
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    item = db.get(PrivacyRequest, request_id)
    if not item or item.status != "submitted":
        raise HTTPException(status_code=404, detail="Open privacy request not found.")
    item.status = review.status
    item.reviewed_by = admin.id
    item.reviewed_at = datetime.now(timezone.utc)
    record(
        db,
        actor_id=admin.id,
        patient_id=item.patient_id,
        action=f"privacy_request.{review.status}",
        target_id=item.id,
        metadata={"request_type": item.request_type},
    )
    db.commit()
    return {"id": item.id, "status": item.status}


def create_assignment(
    request: AssignmentCreate,
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    caregiver = db.get(User, request.caregiver_id)
    patient = db.get(Patient, request.patient_id)
    if not caregiver or caregiver.role != Role.CAREGIVER.value or not patient:
        raise HTTPException(
            status_code=400, detail="Valid caregiver and patient are required."
        )
    assignment = db.get(
        CaregiverPatientAssignment, (request.caregiver_id, request.patient_id)
    )
    if not assignment:
        assignment = CaregiverPatientAssignment(
            caregiver_id=request.caregiver_id, patient_id=request.patient_id
        )
        db.add(assignment)
    assignment.active = True
    record(
        db,
        actor_id=admin.id,
        patient_id=request.patient_id,
        action="caregiver_assignment.created",
        target_id=request.caregiver_id,
    )
    db.commit()
    return {"active": True, **request.model_dump()}


def revoke_assignment(
    caregiver_id: str,
    patient_id: str,
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    assignment = db.get(CaregiverPatientAssignment, (caregiver_id, patient_id))
    if not assignment or not assignment.active:
        raise HTTPException(status_code=404, detail="Active assignment not found.")
    assignment.active = False
    record(
        db,
        actor_id=admin.id,
        patient_id=patient_id,
        action="caregiver_assignment.revoked",
        target_id=caregiver_id,
    )
    db.commit()
    return {"active": False, "caregiver_id": caregiver_id, "patient_id": patient_id}
