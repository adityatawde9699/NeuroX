from fastapi import APIRouter
from app.services import activities as service

router = APIRouter(tags=["activities"])

router.add_api_route("/activities", service.activities, methods=["GET"])
router.add_api_route(
    "/activities/{activity_id}/start",
    service.start_activity,
    methods=["POST"],
    status_code=201,
)
router.add_api_route(
    "/activities/{activity_id}/complete", service.complete_activity, methods=["POST"]
)
router.add_api_route(
    "/patients/{patient_id}/activity-sessions",
    service.activity_history,
    methods=["GET"],
)
