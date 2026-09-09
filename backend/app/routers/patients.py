from fastapi import APIRouter
from app.services import patients as service

router = APIRouter(tags=["patients"])
router.add_api_route("/patients/me", service.my_patient, methods=["GET"])
router.add_api_route("/patients/{patient_id}", service.patient, methods=["GET"])
router.add_api_route(
    "/caregivers/me/patients", service.assigned_patients, methods=["GET"]
)
router.add_api_route(
    "/patients/{patient_id}/emergency-contacts",
    service.emergency_contacts,
    methods=["GET"],
)
router.add_api_route(
    "/patients/{patient_id}/emergency-contacts",
    service.create_emergency_contact,
    methods=["POST"],
    status_code=201,
)
router.add_api_route(
    "/patients/{patient_id}/emergency-contacts/{contact_id}",
    service.update_emergency_contact,
    methods=["PUT"],
)
