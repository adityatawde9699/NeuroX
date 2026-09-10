from datetime import datetime, timezone

from fastapi import Depends
from sqlalchemy.orm import Session

from app.access import caregiver_only
from app.audit import record
from app.database import get_db
from app.models import CaregiverSettings, User
from app.schemas import CaregiverSettingsUpdate


def _public(settings: CaregiverSettings) -> dict:
    return {
        "available": settings.available,
        "notifySos": settings.notify_sos,
        "notifySafetyAlerts": settings.notify_safety_alerts,
        "notifyReminders": settings.notify_reminders,
        "updatedAt": settings.updated_at,
    }


def get_settings(user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
    settings = db.get(CaregiverSettings, user.id)
    if not settings:
        settings = CaregiverSettings(caregiver_id=user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return _public(settings)


def update_settings(
    request: CaregiverSettingsUpdate,
    user: User = Depends(caregiver_only),
    db: Session = Depends(get_db),
):
    settings = db.get(CaregiverSettings, user.id)
    if not settings:
        settings = CaregiverSettings(caregiver_id=user.id)
        db.add(settings)
    changed = sorted(request.model_dump(exclude_unset=True))
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    settings.updated_at = datetime.now(timezone.utc)
    record(
        db,
        actor_id=user.id,
        action="caregiver.preferences_updated",
        target_id=user.id,
        metadata={"fields": changed},
    )
    db.commit()
    db.refresh(settings)
    return _public(settings)
