from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.memory.repository import MemoryRepository, default_memory_database_path

configure_logging()
logger = logging.getLogger("jack.backend")


def create_app(
    memory_repository: MemoryRepository | None = None,
) -> FastAPI:
    repository = memory_repository or MemoryRepository(default_memory_database_path())

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        repository.initialize()
        logger.info(
            "Starting %s v%s on %s:%s",
            settings.app_name,
            __version__,
            settings.host,
            settings.port,
        )
        yield
        logger.info("Stopping %s", settings.app_name)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    if settings.environment == "development" and settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Accept", "Content-Type"],
            max_age=300,
        )

    app.state.memory_repository = repository
    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        started_at = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "%s %s -> %s (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.error(
            "Unhandled error for %s %s",
            request.method,
            request.url.path,
            exc_info=(type(error), error, error.__traceback__),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        logger.info("Rejected request with %s validation issue(s)", len(error.errors()))
        return JSONResponse(
            status_code=422,
            content={"detail": "Invalid request data"},
        )

    return app


app = create_app()

