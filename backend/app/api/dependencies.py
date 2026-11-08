from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.ai.service import AiProviderService
from app.planning.service import PlanningService


def get_ai_provider_service(request: Request) -> AiProviderService:
    return request.app.state.ai_provider_service


def get_planning_service(request: Request) -> PlanningService:
    return request.app.state.planning_service


AiProviderServiceDep = Annotated[AiProviderService, Depends(get_ai_provider_service)]
PlanningServiceDep = Annotated[PlanningService, Depends(get_planning_service)]
