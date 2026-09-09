from fastapi import APIRouter
from app.services import safety as service

router = APIRouter(tags=["safety"])

router.add_api_route(
    "/patients/{patient_id}/location-updates", service.location_history, methods=["GET"]
)
router.add_api_route("/patients/{patient_id}/safety", service.safety, methods=["GET"])
router.add_api_route(
    "/patients/{patient_id}/safety/settings",
    service.update_safety_settings,
    methods=["PUT"],
)
router.add_api_route(
    "/patients/{patient_id}/location-updates",
    service.create_location_update,
    methods=["POST"],
    status_code=201,
)
router.add_api_route(
    "/patients/{patient_id}/sos-events",
    service.create_sos_event,
    methods=["POST"],
    status_code=201,
)
router.add_api_route(
    "/patients/{patient_id}/sos-events/{event_id}/acknowledge",
    service.acknowledge_sos_event,
    methods=["POST"],
)
router.add_api_route(
    "/patients/{patient_id}/safety-alerts/{alert_id}/acknowledge",
    service.acknowledge_safety_alert,
    methods=["POST"],
)
