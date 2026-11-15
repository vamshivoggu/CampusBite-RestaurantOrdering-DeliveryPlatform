"""CampusBite FastAPI application entry point."""
import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import SessionLocal, init_db
from .middleware import RequestLoggingMiddleware
from .routers import ai, auth, delivery, orders, owner, restaurants
from .schemas import MetaOut
from .services.reminders import reminder_loop

logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
logger = logging.getLogger("campusbite")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.seed_demo_data:
        from .seed import seed_demo_data

        with SessionLocal() as db:
            seed_demo_data(db)
    if settings.jwt_secret_key.startswith("dev-only") and settings.environment == "production":
        logger.warning("JWT_SECRET_KEY is using the insecure default - set it in your environment!")
    if not settings.ai_enabled:
        logger.info("OPENAI_API_KEY not set - AI insights endpoint will return 503")

    stop = asyncio.Event()
    task = asyncio.create_task(reminder_loop(stop)) if settings.enable_reminder_scheduler else None
    yield
    stop.set()
    if task:
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="REST API for CampusBite – restaurant ordering & delivery. "
                "Use **Authorize** with a demo account (e.g. customer@campusbite.dev / Password@123).",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time", "Retry-After"],
)

API_PREFIX = "/api"
for r in (auth.router, restaurants.router, orders.router, owner.router, delivery.router, ai.router):
    app.include_router(r, prefix=API_PREFIX)


@app.get("/api/health", tags=["Meta"])
def health():
    return {"status": "ok"}


@app.get("/api/meta", response_model=MetaOut, tags=["Meta"])
def meta():
    return MetaOut(app_name=settings.app_name, currency=settings.currency, delivery_fee=settings.delivery_fee,
                   ai_enabled=settings.ai_enabled, reminder_threshold_minutes=settings.reminder_threshold_minutes)


@app.get("/", include_in_schema=False)
def root():
    return {"name": settings.app_name, "docs": "/docs", "health": "/api/health"}
