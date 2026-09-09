"""HTTP bindings for native and browser authentication."""

from fastapi import APIRouter, Depends
from app.schemas import AuthResponse
from app.services import authentication as service

router = APIRouter(tags=["authentication"])
router.add_api_route(
    "/auth/register",
    service.register,
    methods=["POST"],
    response_model=AuthResponse,
    status_code=201,
)
router.add_api_route(
    "/auth/login", service.login, methods=["POST"], response_model=AuthResponse
)
router.add_api_route(
    "/auth/google", service.google_login, methods=["POST"], response_model=AuthResponse
)
router.add_api_route(
    "/auth/refresh", service.refresh, methods=["POST"], response_model=AuthResponse
)
router.add_api_route("/auth/logout", service.logout, methods=["POST"])
router.add_api_route("/auth/me", service.me, methods=["GET"])
router.add_api_route("/auth/me", service.update_current_user, methods=["PUT"])
router.add_api_route(
    "/auth/me/password", service.update_current_password, methods=["PUT"]
)
router.add_api_route(
    "/auth/browser/login",
    service.browser_login,
    methods=["POST"],
    dependencies=[Depends(service.browser_origin)],
)
router.add_api_route(
    "/auth/browser/register",
    service.browser_register,
    methods=["POST"],
    dependencies=[Depends(service.browser_origin)],
)
router.add_api_route(
    "/auth/browser/google",
    service.browser_google,
    methods=["POST"],
    dependencies=[Depends(service.browser_origin)],
)
router.add_api_route(
    "/auth/browser/refresh",
    service.browser_refresh,
    methods=["POST"],
    dependencies=[Depends(service.browser_origin)],
)
router.add_api_route(
    "/auth/browser/logout",
    service.browser_logout,
    methods=["POST"],
    dependencies=[Depends(service.browser_origin)],
)
