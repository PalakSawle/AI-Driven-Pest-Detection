import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select

from . import models  # noqa: F401  (register tables)
from .config import get_settings
from .db import Base, SessionLocal, engine
from .limiter import limiter
from .models import ModelVersion, User
from .routers import admin, analytics, auth, detections, misc, profile
from .security import hash_password
from .services import detector
from .services.knowledge import seed_reference_data

settings = get_settings()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("agriguard")


def bootstrap():
    if engine.url.get_backend_name() == "sqlite":
        Base.metadata.create_all(engine)  # Postgres uses Alembic migrations (see migrations/)
    meta = detector.model_meta()
    with SessionLocal() as db:
        seed_reference_data(db, meta.get("classes", []))
        if meta and not db.scalar(select(ModelVersion).where(ModelVersion.version == meta.get("version"))):
            for mv in db.scalars(select(ModelVersion)):
                mv.is_active = False
            db.add(ModelVersion(name=meta.get("name", "AgriGuard Pest Detector"), version=meta.get("version", "1.0.0"),
                                architecture=meta.get("architecture", "YOLO"), dataset=meta.get("dataset", ""),
                                classes=meta.get("classes", []), metrics=meta.get("metrics", {}),
                                weights_path=settings.model_path, is_active=True))
        if settings.admin_email and settings.admin_password and not db.scalar(
                select(User).where(User.email == settings.admin_email.lower())):
            db.add(User(email=settings.admin_email.lower(), hashed_password=hash_password(settings.admin_password),
                        full_name="Administrator", role="admin"))
        db.commit()
    if not detector.is_available():
        log.warning("Model weights missing at %s — /api/detections/analyze will return 503 until they are added.",
                    settings.model_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap()
    yield


app = FastAPI(
    title="AgriGuard AI API",
    version="1.0.0",
    description="Smart pest detection & crop protection. YOLO detection on IP102, density & severity scoring, "
                "IPM treatment knowledge base, AI Kisan chatbot, analytics, alerts and weather.",
    lifespan=lifespan,
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def rate_limited(request: Request, exc: RateLimitExceeded):
    return JSONResponse({"detail": f"Too many requests: {exc.detail}. Please wait and try again."}, status_code=429)


@app.exception_handler(Exception)
def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse({"detail": "Internal server error"}, status_code=500)


app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])

for r in (auth.router, profile.router, detections.router, analytics.router, admin.router, misc.alerts,
          misc.treatments, misc.chat, misc.weather_router, misc.files):
    app.include_router(r)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "model_loaded": detector.is_available(), "environment": settings.environment}


@app.get("/", include_in_schema=False)
def root():
    return {"name": "AgriGuard AI API", "docs": "/docs", "health": "/api/health"}
