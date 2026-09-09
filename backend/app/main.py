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
from app.routers.reports import router as reports_router
from app.routers.notifications import router as notifications_router
from app.routers.safety import router as safety_router
from app.routers.sync import router as sync_router


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(care_router)
app.include_router(activities_router)
app.include_router(reports_router)
app.include_router(notifications_router)
app.include_router(safety_router)
app.include_router(sync_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/language-config")
def language_config():
    return LANGUAGE_CONFIG
