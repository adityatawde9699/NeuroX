from fastapi import APIRouter
from app.services import sync as service

router = APIRouter(tags=["sync"])

router.add_api_route("/sync/events", service.sync, methods=["POST"])
