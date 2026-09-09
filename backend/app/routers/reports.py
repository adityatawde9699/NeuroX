from fastapi import APIRouter
from app.services import reports as service

router = APIRouter(tags=["reports"])

router.add_api_route(
    "/patients/{patient_id}/performance", service.performance, methods=["GET"]
)
router.add_api_route(
    "/patients/{patient_id}/reports/activity", service.activity_report, methods=["GET"]
)
