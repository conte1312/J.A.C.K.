from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.control_plane.repository import (
    ControlPlaneRepository,
    default_control_plane_database_path,
)
from app.control_plane.service import ControlPlaneService
from app.ai.credential_manager import CredentialManager
from app.ai.cost_guard import CostGuard
from app.ai.multi_preferences import AiMultiPreferencesStore
from app.ai.orchestrator_service import AiOrchestratorService
from app.ai.router_service import AiRouter
from app.ai.routes import ai_router, chat_router
from app.ai.service import AiProviderService
from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.conversations.repository import ConversationRepository
from app.conversations.service import ConversationService
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.memory.repository import (
    MemoryRepository,
    default_memory_database_path,
)
from app.planning.repository import (
    PlanningRepository,
    default_planning_database_path,
)
from app.planning.service import PlanningService
from app.planning.scheduler import run_recurrence_scheduler
from app.system.backups import LocalBackupService
from app.system.monitor import SystemMonitor
from app.system.security import SecurityPosture

configure_logging()
logger = logging.getLogger("jack.backend")


def create_app(
    memory_repository: MemoryRepository | None = None,
    ai_provider_service: AiProviderService | None = None,
    conversation_repository: ConversationRepository | None = None,
    conversation_service: ConversationService | None = None,
    planning_repository: PlanningRepository | None = None,
    planning_service: PlanningService | None = None,
    control_plane_repository: ControlPlaneRepository | None = None,
    control_plane_service: ControlPlaneService | None = None,
) -> FastAPI:
    repository = memory_repository or MemoryRepository(default_memory_database_path())
    provider_service = ai_provider_service or AiProviderService()
    conversation_store = conversation_repository or ConversationRepository(
        default_memory_database_path()
    )
    conversation_service_instance = conversation_service or ConversationService(
        conversation_repository=conversation_store,
        memory_repository=repository,
        ai_provider_service=provider_service,
    )

    planning_repo = planning_repository or PlanningRepository(
        default_planning_database_path()
    )
    planning_service_instance = planning_service or PlanningService(
        repository=planning_repo
    )
    control_plane_repo = control_plane_repository or ControlPlaneRepository(
        default_control_plane_database_path()
    )
    control_plane_service_instance = control_plane_service or ControlPlaneService(
        control_plane_repo
    )
    # Nuovo sistema multi-provider
    from app.ai.provider_registry import registry as _provider_registry

    credential_manager = CredentialManager()
    preferences_store = AiMultiPreferencesStore()
    cost_guard = CostGuard(_provider_registry)
    ai_router_instance = AiRouter(cost_guard=cost_guard)
    orchestrator_service = AiOrchestratorService(
        credentials=credential_manager,
        preferences=preferences_store,
        router=ai_router_instance,
        cost_guard=cost_guard,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        repository.initialize()
        conversation_store.initialize()
        planning_repo.initialize()
        control_plane_repo.initialize()
        recurrence_scheduler = asyncio.create_task(
            run_recurrence_scheduler(planning_service_instance)
        )
        logger.info(
            "Starting %s v%s on %s:%s",
            settings.app_name,
            __version__,
            settings.host,
            settings.port,
        )
        try:
            yield
        finally:
            recurrence_scheduler.cancel()
            try:
                await recurrence_scheduler
            except asyncio.CancelledError:
                pass
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
    app.state.ai_provider_service = provider_service
    app.state.conversation_repository = conversation_store
    app.state.conversation_service = conversation_service_instance
    app.state.planning_repository = planning_repo
    app.state.planning_service = planning_service_instance
    app.state.control_plane_repository = control_plane_repo
    app.state.control_plane_service = control_plane_service_instance
    app.state.system_monitor = SystemMonitor(
        {
            "Memoria e conversazioni": repository.database_path,
            "Pianificazione": planning_repo.database_path,
            "Control Plane": control_plane_repo.database_path,
        }
    )
    app.state.backup_service = LocalBackupService(
        {
            "Memoria e conversazioni": repository.database_path,
            "Pianificazione": planning_repo.database_path,
            "Control Plane": control_plane_repo.database_path,
        },
        repository.database_path.parent / "backups",
        optional_database_names={"Control Plane"},
    )
    app.state.security_posture = SecurityPosture(settings)
    app.state.ai_router = ai_router_instance
    app.state.ai_orchestrator_service = orchestrator_service
    app.state.cost_guard = cost_guard
    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(chat_router)

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
