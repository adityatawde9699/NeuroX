from fastapi import APIRouter
from app.services import reminders as service

router = APIRouter(tags=["reminders"])
router.add_api_route(
    "/patients/{patient_id}/reminders", service.reminders, methods=["GET"]
)
router.add_api_route(
    "/reminders", service.create_reminder, methods=["POST"], status_code=201
)
router.add_api_route(
    "/reminders/{reminder_id}", service.update_reminder, methods=["PUT"]
)
router.add_api_route(
    "/reminders/{reminder_id}",
    service.delete_reminder,
    methods=["DELETE"],
    status_code=204,
)
