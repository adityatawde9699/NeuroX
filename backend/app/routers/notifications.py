from fastapi import APIRouter
from app.services import notifications as service

router = APIRouter(tags=["notifications"])

router.add_api_route(
    "/patients/{patient_id}/alerts", service.alert_history, methods=["GET"]
)
