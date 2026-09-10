"""FastAPI composition root; domain logic lives in routers and services."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ORIGINS
from app.catalog import LANGUAGE_CONFIG
from app.seed import _seed_database
from app.routers.authentication import router as auth_router
from app.routers.care import router as care_router
from app.routers.activities import router as activities_router
from app.routers.administration import preferences_router
from app.routers.administration import router as administration_router
from app.routers.reports import router as reports_router
from app.routers.notifications import router as notifications_router
from app.routers.safety import router as safety_router
from app.routers.sync import router as sync_router
from app.routers.privacy import router as privacy_router
from app.routers.system import router as system_router
from app.api_v1 import router as api_v1_router
from app.http import configure_http
from app.observability import configure_logging, configure_observability, configure_otel


@asynccontextmanager
async def lifespan(_: FastAPI):
    _seed_database()
    yield


app = FastAPI(
    title="NeuroX API",
    version="0.3.0",
    description="Supportive engagement APIs — not clinical diagnosis.",
    lifespan=lifespan,
)
configure_logging()
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
configure_http(app)
configure_observability(app)
app.include_router(auth_router)
app.include_router(administration_router)
app.include_router(preferences_router)
app.include_router(care_router)
app.include_router(activities_router)
app.include_router(reports_router)
app.include_router(notifications_router)
app.include_router(safety_router)
app.include_router(sync_router)
app.include_router(privacy_router)
app.include_router(system_router)
app.include_router(api_v1_router)
configure_otel(app)


@app.get("/language-config")
def language_config():
    return LANGUAGE_CONFIG
