from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.ai.routes import ai_router, chat_router
from app.api.dependencies import AiProviderServiceDep, get_ai_provider_service
from app.api.routes.info import router as info_router
from app.api.routes.memories import router as memories_router
from app.api.routes.system import router as system_router
from app.planning.routes import router as planning_router
from app.conversations.routes import router as conversations_router

api_router = APIRouter()
api_router.include_router(info_router)
api_router.include_router(system_router)
api_router.include_router(memories_router)
api_router.include_router(planning_router)
api_router.include_router(ai_router)
api_router.include_router(conversations_router)

__all__ = [
    "api_router",
    "AiProviderServiceDep",
    "get_ai_provider_service",
]
