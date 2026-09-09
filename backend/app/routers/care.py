"""Care API composition; patient routes precede parameterized routes."""

from fastapi import APIRouter
from app.routers.patients import router as patients_router
from app.routers.reminders import router as reminders_router

router = APIRouter()
router.include_router(patients_router)
router.include_router(reminders_router)
