from fastapi import Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    SafetyAlert,
    SOSEvent,
    User,
)
from app.access import patient_access

from app.services.safety_state import public_alert, public_sos


def alert_history(
    patient_id: str,
    alert_status: str = Query(
        default="open", alias="status", pattern="^(open|acknowledged|all)$"
    ),
    severity: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    _: User = Depends(patient_access),
    db: Session = Depends(get_db),
):
    alert_query = db.query(SafetyAlert).filter(SafetyAlert.patient_id == patient_id)
    sos_query = db.query(SOSEvent).filter(SOSEvent.patient_id == patient_id)
    if alert_status != "all":
        alert_query = alert_query.filter(SafetyAlert.status == alert_status)
        sos_query = sos_query.filter(SOSEvent.status == alert_status)
    if severity:
        alert_query = alert_query.filter(SafetyAlert.severity == severity)
    alerts = [
        {**public_alert(item, db), "kind": "safety_alert"}
        for item in alert_query.order_by(SafetyAlert.created_at.desc())
        .limit(limit)
        .all()
    ]
    alerts.extend(
        {**public_sos(item, db), "kind": "sos"}
        for item in sos_query.order_by(SOSEvent.created_at.desc()).limit(limit).all()
    )
    return sorted(alerts, key=lambda item: item["createdAt"], reverse=True)[:limit]
