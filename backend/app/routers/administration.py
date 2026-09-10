from fastapi import APIRouter

from app.services import administration as service
from app.services import caregiver_settings

router = APIRouter(tags=["administration"])
router.add_api_route("/admin/audit-events", service.audit_events, methods=["GET"])
router.add_api_route(
    "/admin/privacy-requests", service.privacy_requests, methods=["GET"]
)
router.add_api_route(
    "/admin/privacy-requests/{request_id}",
    service.review_privacy_request,
    methods=["PUT"],
)
router.add_api_route("/admin/assignments", service.create_assignment, methods=["POST"])
router.add_api_route(
    "/admin/assignments/{caregiver_id}/{patient_id}",
    service.revoke_assignment,
    methods=["DELETE"],
)


preferences_router = APIRouter(tags=["caregiver-settings"])
preferences_router.add_api_route(
    "/caregivers/me/preferences", caregiver_settings.get_settings, methods=["GET"]
)
preferences_router.add_api_route(
    "/caregivers/me/preferences", caregiver_settings.update_settings, methods=["PUT"]
)
