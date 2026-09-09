from fastapi import APIRouter
from app.services import privacy as service

router = APIRouter(tags=["privacy"])
router.add_api_route("/patients/me/privacy", service.privacy_status, methods=["GET"])
router.add_api_route(
    "/patients/me/privacy/consents", service.set_consent, methods=["PUT"]
)
router.add_api_route(
    "/patients/me/privacy/location-sharing",
    service.set_location_sharing,
    methods=["PUT"],
)
router.add_api_route("/patients/me/caregivers", service.caregivers, methods=["GET"])
router.add_api_route(
    "/patients/me/caregivers/{caregiver_id}",
    service.revoke_caregiver,
    methods=["DELETE"],
)
router.add_api_route(
    "/patients/me/privacy/export", service.export_data, methods=["GET"]
)
router.add_api_route(
    "/patients/me/privacy/deletion-request",
    service.request_deletion,
    methods=["POST"],
    status_code=202,
)
