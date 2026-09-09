from datetime import datetime, timezone
from fastapi import Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    Reminder,
    SyncEvent,
    User,
)
from app.schemas import (
    ActivityCompletion,
    LocationUpdateCreate,
    ReminderUpdate,
    SafetySettingsUpdate,
    SOSEventCreate,
    SyncEventRequest,
)
from app.services.authentication import current_user
from app.access import can_access_patient

from app.services.safety_state import as_utc, latest_location
from app.services.activities import complete_activity
from app.services.reminders import update_reminder
from app.services.safety import (
    create_location_update,
    create_sos_event,
    update_safety_settings,
)


def apply_sync_event(event: SyncEventRequest, user: User, db: Session) -> dict:
    if not can_access_patient(user, event.patient_id, db):
        raise HTTPException(
            status_code=403, detail="You are not assigned to this patient."
        )

    if event.event_type == "activity_completion":
        payload = ActivityCompletion.model_validate(event.payload)
        if payload.event_id != event.event_id:
            raise HTTPException(
                status_code=422, detail="Activity event IDs must match."
            )
        if payload.user_id != user.id or payload.user_id != event.patient_id:
            raise HTTPException(
                status_code=403,
                detail="Activity user does not match the event patient.",
            )
        result = complete_activity(payload.activity_id, payload, user, db)
    elif event.event_type == "reminder_update":
        reminder_id = event.payload.get("reminder_id")
        if not isinstance(reminder_id, str):
            raise HTTPException(status_code=422, detail="reminder_id is required.")
        payload = ReminderUpdate.model_validate(event.payload.get("changes", {}))
        reminder = db.get(Reminder, reminder_id)
        if not reminder or reminder.patient_id != event.patient_id:
            raise HTTPException(
                status_code=404, detail="Reminder not found for this patient."
            )
        result = update_reminder(reminder_id, payload, user, db)
    elif event.event_type == "location_update":
        payload = LocationUpdateCreate.model_validate(event.payload)
        latest = latest_location(event.patient_id, db)
        if latest and as_utc(payload.captured_at) <= as_utc(latest.captured_at):
            raise HTTPException(
                status_code=409,
                detail="Location update is older than the latest stored location.",
            )
        result = create_location_update(event.patient_id, payload, user, db)
    elif event.event_type == "safety_settings_update":
        payload = SafetySettingsUpdate.model_validate(event.payload)
        result = update_safety_settings(event.patient_id, payload, user, db)
    elif event.event_type == "sos_event":
        payload = SOSEventCreate.model_validate(event.payload)
        result = create_sos_event(event.patient_id, payload, user, db)
    else:
        raise HTTPException(
            status_code=422, detail=f"Unsupported sync event type: {event.event_type}"
        )
    return {"event_id": event.event_id, "status": "accepted", "result": result}


def sync(
    events: list[SyncEventRequest],
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    results = []
    for event in events:
        # Re-check access on retries as assignments may have been revoked.
        if not can_access_patient(user, event.patient_id, db):
            results.append(
                {
                    "event_id": event.event_id,
                    "status": "rejected",
                    "detail": "You are not assigned to this patient.",
                }
            )
            continue
        existing = db.get(SyncEvent, event.event_id)
        if existing:
            if (
                existing.user_id != user.id
                or existing.patient_id != event.patient_id
                or existing.event_type != event.event_type
                or existing.payload != event.payload
            ):
                results.append(
                    {
                        "event_id": event.event_id,
                        "status": "conflict",
                        "detail": "Event ID is already associated with different event data.",
                    }
                )
                continue
            if existing.status != "accepted":
                results.append(
                    {
                        "event_id": event.event_id,
                        "status": existing.status,
                        "detail": existing.result.get(
                            "detail", "Event was not accepted."
                        ),
                    }
                )
            else:
                results.append(
                    {
                        "event_id": event.event_id,
                        "status": "duplicate",
                        "result": existing.result,
                    }
                )
            continue
        try:
            processed = apply_sync_event(event, user, db)
            record = SyncEvent(
                event_id=event.event_id,
                user_id=user.id,
                patient_id=event.patient_id,
                event_type=event.event_type,
                payload=event.payload,
                status="accepted",
                result=jsonable_encoder(processed["result"]),
            )
            db.add(record)
            db.commit()
            results.append(processed)
        except (HTTPException, ValidationError) as exc:
            db.rollback()
            detail = (
                exc.detail
                if isinstance(exc, HTTPException)
                else "Invalid sync event payload."
            )
            status_text = (
                "conflict"
                if isinstance(exc, HTTPException) and exc.status_code == 409
                else "rejected"
            )
            record = SyncEvent(
                event_id=event.event_id,
                user_id=user.id,
                patient_id=event.patient_id,
                event_type=event.event_type,
                payload=event.payload,
                status=status_text,
                result={"detail": detail},
            )
            db.add(record)
            db.commit()
            results.append(
                {"event_id": event.event_id, "status": status_text, "detail": detail}
            )
    return {"results": results, "syncedAt": datetime.now(timezone.utc)}
