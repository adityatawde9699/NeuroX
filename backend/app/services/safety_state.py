from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from sqlalchemy.orm import Session
from app.models import (
    EmergencyContact,
    LocationUpdate,
    SafetyAlert,
    SafetySettings,
    SOSEvent,
)
from app.presenters import public_contact


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def minutes_ago(value: datetime, now_value: datetime | None = None) -> int:
    now_value = now_value or datetime.now(timezone.utc)
    return max(0, round((now_value - as_utc(value)).total_seconds() / 60))


def human_freshness(value: datetime) -> str:
    minutes = minutes_ago(value)
    if minutes < 1:
        return "just now"
    if minutes == 1:
        return "1 minute ago"
    if minutes < 60:
        return f"{minutes} minutes ago"
    hours = minutes // 60
    return f"{hours} hour{'s' if hours != 1 else ''} ago"


def distance_meters(lat_a: float, lng_a: float, lat_b: float, lng_b: float) -> float:
    earth_radius_m = 6371000
    d_lat = radians(lat_b - lat_a)
    d_lng = radians(lng_b - lng_a)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat_a)) * cos(radians(lat_b)) * sin(d_lng / 2) ** 2
    )
    return 2 * earth_radius_m * asin(sqrt(a))


def active_contacts(patient_id: str, db: Session) -> list[EmergencyContact]:
    return (
        db.query(EmergencyContact)
        .filter_by(patient_id=patient_id, active=True)
        .order_by(EmergencyContact.priority)
        .all()
    )


def contact_for_priority(patient_id: str, priority: int, db: Session) -> dict | None:
    contacts = active_contacts(patient_id, db)
    if not contacts:
        return None
    chosen = next(
        (contact for contact in contacts if contact.priority >= priority), contacts[-1]
    )
    return public_contact(chosen)


def public_safety_settings(settings: SafetySettings | None) -> dict:
    if not settings:
        return {
            "safeZoneName": "Home safe zone",
            "safeZoneLatitude": None,
            "safeZoneLongitude": None,
            "safeZoneRadiusM": 250,
            "expectedReturnAt": None,
            "expectedReturnNote": None,
            "lateReturnGraceMinutes": 10,
        }
    return {
        "safeZoneName": settings.safe_zone_name,
        "safeZoneLatitude": settings.safe_zone_latitude,
        "safeZoneLongitude": settings.safe_zone_longitude,
        "safeZoneRadiusM": settings.safe_zone_radius_m,
        "expectedReturnAt": settings.expected_return_at,
        "expectedReturnNote": settings.expected_return_note,
        "lateReturnGraceMinutes": settings.late_return_grace_minutes,
        "updatedAt": settings.updated_at,
    }


def public_location(location: LocationUpdate | None) -> dict | None:
    if not location:
        return None
    age_minutes = minutes_ago(location.captured_at)
    is_online = (
        location.connection_state.lower() == "online" and age_minutes <= 5
        and as_utc(location.captured_at) <= datetime.now(timezone.utc)
    )
    return {
        "id": location.id,
        "patientId": location.patient_id,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "accuracyM": location.accuracy_m,
        "connectionState": "online" if is_online else "offline",
        "capturedAt": location.captured_at,
        "receivedAt": location.received_at,
        "freshness": human_freshness(location.captured_at),
        "label": "Current location" if is_online else "Last known location",
    }


def public_alert(alert: SafetyAlert, db: Session) -> dict:
    return {
        "id": alert.id,
        "patientId": alert.patient_id,
        "type": alert.type,
        "severity": alert.severity,
        "status": alert.status,
        "message": alert.message,
        "createdAt": alert.created_at,
        "acknowledgedAt": alert.acknowledged_at,
        "acknowledgedBy": alert.acknowledged_by,
        "escalatedToPriority": alert.escalated_to_priority,
        "escalatedContact": contact_for_priority(
            alert.patient_id, alert.escalated_to_priority, db
        ),
    }


def public_sos(event: SOSEvent, db: Session) -> dict:
    return {
        "id": event.id,
        "patientId": event.patient_id,
        "message": event.message,
        "status": event.status,
        "createdAt": event.created_at,
        "acknowledgedAt": event.acknowledged_at,
        "acknowledgedBy": event.acknowledged_by,
        "escalatedToPriority": event.escalated_to_priority,
        "escalatedContact": contact_for_priority(
            event.patient_id, event.escalated_to_priority, db
        ),
        "workflowNote": "NeuroX SOS notifies configured caregivers. It does not contact government or emergency services directly.",
    }


def latest_location(patient_id: str, db: Session) -> LocationUpdate | None:
    return (
        db.query(LocationUpdate)
        .filter_by(patient_id=patient_id)
        .order_by(LocationUpdate.captured_at.desc())
        .first()
    )


def open_alert_exists(patient_id: str, alert_type: str, db: Session) -> bool:
    return (
        db.query(SafetyAlert)
        .filter_by(patient_id=patient_id, type=alert_type, status="open")
        .first()
        is not None
    )


def ensure_alert(
    patient_id: str,
    alert_type: str,
    severity: str,
    message: str,
    db: Session,
    location_update_id: str | None = None,
) -> SafetyAlert | None:
    if open_alert_exists(patient_id, alert_type, db):
        return None
    alert = SafetyAlert(
        patient_id=patient_id,
        type=alert_type,
        severity=severity,
        message=message,
        location_update_id=location_update_id,
    )
    db.add(alert)
    return alert


def evaluate_safety(patient_id: str, db: Session) -> None:
    settings = db.get(SafetySettings, patient_id)
    location = latest_location(patient_id, db)
    now_value = datetime.now(timezone.utc)
    if (
        settings
        and settings.location_sharing_enabled
        and location
        and 0 <= minutes_ago(location.captured_at) <= 5
        and as_utc(location.captured_at) <= now_value
        and settings.safe_zone_latitude is not None
        and settings.safe_zone_longitude is not None
    ):
        distance = distance_meters(
            settings.safe_zone_latitude,
            settings.safe_zone_longitude,
            location.latitude,
            location.longitude,
        )
        # A very imprecise fix cannot support a safe-zone conclusion. Surface
        # that limitation to caregivers instead of implying the patient left.
        if location.accuracy_m > max(150, settings.safe_zone_radius_m):
            ensure_alert(
                patient_id,
                "location_accuracy_low",
                "medium",
                (
                    f"Location accuracy is low (+/- {round(location.accuracy_m)} m). "
                    "Safe-zone status cannot be confirmed."
                ),
                db,
                location.id,
            )
        elif distance > settings.safe_zone_radius_m + location.accuracy_m:
            ensure_alert(
                patient_id,
                "safe_zone_exit",
                "high",
                f"Location appears outside {settings.safe_zone_name}. Accuracy +/- {round(location.accuracy_m)} m.",
                db,
                location.id,
            )
    if settings and settings.expected_return_at:
        due_at = as_utc(settings.expected_return_at) + timedelta(
            minutes=settings.late_return_grace_minutes
        )
        if now_value > due_at:
            ensure_alert(
                patient_id,
                "late_return",
                "high",
                "Expected return time has passed and no caregiver acknowledgement is recorded.",
                db,
                location.id if location else None,
            )
    escalation_cutoff = now_value - timedelta(minutes=3)
    for item in (
        db.query(SafetyAlert).filter_by(patient_id=patient_id, status="open").all()
    ):
        if (
            item.escalated_to_priority == 1
            and as_utc(item.created_at) <= escalation_cutoff
        ):
            item.escalated_to_priority = 2
            item.escalated_at = now_value
    for item in (
        db.query(SOSEvent).filter_by(patient_id=patient_id, status="open").all()
    ):
        if (
            item.escalated_to_priority == 1
            and as_utc(item.created_at) <= escalation_cutoff
        ):
            item.escalated_to_priority = 2
            item.escalated_at = now_value
    db.commit()


def evaluate_all_safety(db: Session) -> int:
    """Run deterministic late-return/stale checks without a dashboard visit."""
    patient_ids = [
        item.patient_id for item in db.query(SafetySettings.patient_id).all()
    ]
    for patient_id in patient_ids:
        evaluate_safety(patient_id, db)
    return len(patient_ids)
