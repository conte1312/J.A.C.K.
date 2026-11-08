from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.ai.base_provider import ProviderRequestError
from app.ai.orchestrator_service import AiOrchestratorService
from app.ai.schemas import (
    ChatInput,
    ConnectionTestInput,
    CredentialInput,
    ModelEnabledInput,
    ModelSelectionInput,
    ProviderCredentialInput,
    ProviderEnableInput,
    ProviderOrderInput,
)
from app.ai.router_service import AiRouter

router = APIRouter()
ai_router = APIRouter(prefix="/ai", tags=["ai-provider"])
chat_router = APIRouter(tags=["chat"])


def _orchestrator(request: Request) -> AiOrchestratorService:
    return request.app.state.ai_orchestrator_service


def _router(request: Request) -> AiRouter:
    return request.app.state.ai_router


Orchestrator = Annotated[AiOrchestratorService, Depends(_orchestrator)]
RouterDep = Annotated[AiRouter, Depends(_router)]


def _raise_http(error) -> None:
    if isinstance(error, ProviderRequestError):
        raise HTTPException(
            status_code=error.status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"code": "internal_error", "message": str(error)},
    ) from error


# ---------------------------------------------------------------------------
# Configurazione provider (multi-provider)
# ---------------------------------------------------------------------------


@ai_router.get("/providers")
async def get_providers(orchestrator: Orchestrator) -> dict[str, object]:
    try:
        return orchestrator.get_configuration()
    except Exception as error:  # noqa: BLE001 - gestito come errore generico
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "configuration_error", "message": str(error)},
        ) from error


@ai_router.put("/providers/{provider_id}/credentials")
async def save_provider_credential(
    provider_id: str,
    payload: ProviderCredentialInput,
    orchestrator: Orchestrator,
) -> dict[str, object]:
    try:
        return orchestrator.save_provider_credential(
            provider_id, payload.api_key.get_secret_value()
        )
    except Exception as error:  # noqa: BLE001
        _raise_http(error)


@ai_router.delete("/providers/{provider_id}/credentials")
async def delete_provider_credential(
    provider_id: str,
    orchestrator: Orchestrator,
) -> dict[str, object]:
    try:
        return orchestrator.remove_provider_credential(provider_id)
    except Exception as error:  # noqa: BLE001
        _raise_http(error)


@ai_router.post("/providers/{provider_id}/test")
async def test_provider_connection(
    provider_id: str,
    payload: ConnectionTestInput,
    orchestrator: Orchestrator,
) -> dict[str, object]:
    try:
        return orchestrator.test_provider_connection(
            provider_id, payload.model_id
        )
    except Exception as error:  # noqa: BLE001
        _raise_http(error)


@ai_router.put("/provider-order")
async def set_provider_order(
    payload: ProviderOrderInput,
    orchestrator: Orchestrator,
) -> dict[str, object]:
    try:
        return orchestrator.set_provider_order(payload.provider_order)
    except Exception as error:  # noqa: BLE001
        _raise_http(error)


@ai_router.put("/providers/{provider_id}/enabled")
async def set_provider_enabled(
    provider_id: str,
    payload: ProviderEnableInput,
    orchestrator: Orchestrator,
) -> dict[str, object]:
    try:
        return orchestrator.set_provider_enabled(provider_id, payload.enabled)
    except Exception as error:  # noqa: BLE001
        _raise_http(error)


# ---------------------------------------------------------------------------
# Selezione provider + modello
# ---------------------------------------------------------------------------


@ai_router.put("/selection")
async def select_provider_and_model(
    payload: ModelSelectionInput,
    orchestrator: Orchestrator,
) -> dict[str, object]:
    """Seleziona provider e modello.

    Il payload accetta model_id; il provider viene dedotto dal router
    o può essere specificato estendendo lo schema in futuro.
    """
    try:
        # Il payload attuale contiene solo model_id; il provider viene
        # risolto dal router in base all'ordine configurato.
        return orchestrator.select_provider_and_model(
            provider_id="", model_id=payload.model_id
        )
    except Exception as error:  # noqa: BLE001
        _raise_http(error)


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


@chat_router.post("/chat")
async def create_chat_completion(
    payload: ChatInput,
    orchestrator: Orchestrator,
) -> dict[str, str]:
    try:
        return await orchestrator.send_chat(
            model_id=payload.model_id,
            messages=[turn.model_dump() for turn in payload.messages],
        )
    except Exception as error:  # noqa: BLE001
        _raise_http(error)


# Manteniamo le vecchie route NVIDIA-specific come alias per retro-compatibilità
@ai_router.put("/providers/nvidia/credentials")
async def save_nvidia_credential(
    payload: CredentialInput,
    orchestrator: Orchestrator,
) -> dict[str, object]:
    return await save_provider_credential(
        "nvidia",
        ProviderCredentialInput(
            provider_id="nvidia",
            api_key=payload.api_key,
        ),
        orchestrator,
    )


@ai_router.delete("/providers/nvidia/credentials")
async def delete_nvidia_credential(
    orchestrator: Orchestrator,
) -> dict[str, object]:
    return await delete_provider_credential("nvidia", orchestrator)


@ai_router.post("/providers/nvidia/test")
async def test_nvidia_connection(
    payload: ConnectionTestInput,
    orchestrator: Orchestrator,
) -> dict[str, object]:
    return await test_provider_connection(
        "nvidia", payload, orchestrator
    )


@ai_router.put("/models/{model_id}/enabled")
async def set_model_enabled(
    model_id: str,
    payload: ModelEnabledInput,
    orchestrator: Orchestrator,
) -> dict[str, object]:
    """Alias retro-compatibile: abilita/disabilita un modello."""
    # Il nuovo modello usa provider-enabled. Per retro-compat, abilita
    # il provider che contiene il modello.
    providers = orchestrator.get_configuration().get("providers", [])
    target_provider = None
    for p in providers:
        for m in p.get("models", []):
            if m["id"] == model_id:
                target_provider = p["id"]
                break
        if target_provider:
            break
    if target_provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "model_not_found", "message": "Modello non trovato."},
        )
    return await set_provider_enabled(
        target_provider, ProviderEnableInput(provider_id=target_provider, enabled=payload.enabled), orchestrator
    )
