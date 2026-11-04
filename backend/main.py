"""
GeoSentinel FastAPI application entry point.

Phase 1: foundation API, health checks, registry, PostGIS connectivity.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.router import api_router
from backend.shared.config import get_settings
from backend.shared.exceptions import GeoSentinelError, ValidationError
from backend.shared.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    settings = get_settings()
    configure_logging(settings.log_level, settings.app_env)
    logger.info(
        "application_starting",
        app=settings.app_name,
        env=settings.app_env,
        max_aois=settings.max_aois,
    )
    yield
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Application factory for tests and uvicorn."""
    settings = get_settings()
    configure_logging(settings.log_level, settings.app_env)

    app = FastAPI(
        title=settings.app_name,
        description="Geospatial intelligence and OSINT fusion platform",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
    )

    origins = list(set(settings.cors_origin_list + [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ]))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.exception_handler(ValidationError)
    async def validation_handler(_request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.message})

    @app.exception_handler(GeoSentinelError)
    async def app_error_handler(_request: Request, exc: GeoSentinelError) -> JSONResponse:
        logger.error("application_error", message=exc.message)
        return JSONResponse(status_code=500, content={"detail": "An internal error occurred"})

    @app.exception_handler(Exception)
    async def unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", error_type=type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "An internal error occurred"})

    app.include_router(api_router, prefix=settings.api_prefix)
    if settings.api_prefix != "/api":
        app.include_router(api_router, prefix="/api")

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "version": "0.1.0",
            "api": settings.api_prefix,
            "status": "operational",
        }

    return app


app = create_app()
