from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.ai.service import AiProviderService


def get_ai_provider_service(request: Request) -> AiProviderService:
    return request.app.state.ai_provider_service


AiProviderServiceDep = Annotated[AiProviderService, Depends(get_ai_provider_service)]
