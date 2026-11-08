from __future__ import annotations

import json
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.ai.base_provider import (
    ProviderInfo,
    ProviderModel,
    ProviderRequestError,
    BaseAiProvider,
)

NVIDIA_CHAT_COMPLETIONS_URL = (
    "https://integrate.api.nvidia.com/v1/chat/completions"
)

NVIDIA_MODELS = (
    ProviderModel(
        id="nvidia/nemotron-3.5-lightning-30b-a3b",
        name="Nemotron 3.5 Lightning 30B A3B",
        description="Modello Nemotron orientato a chat, coding e ragionamento.",
        is_free=True,
        context_window=16384,
        max_output_tokens=1024,
    ),
    ProviderModel(
        id="nvidia/nemotron-3.5-bolt-e4b",
        name="Nemotron 3.5 Bolt E4B",
        description="Modello Nemotron compatto per conversazioni e uso generale.",
        is_free=True,
        context_window=16384,
        max_output_tokens=1024,
    ),
)


class NvidiaNemotronProvider(BaseAiProvider):
    """Adapter per NVIDIA Nemotron (endpoint integrate.api.nvidia.com)."""

    def __init__(self, *, timeout: float = 35.0, transport=None) -> None:
        self._timeout = timeout
        self._transport = transport or self._post_json

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            id="nvidia",
            name="NVIDIA Nemotron",
            provider_type="online",
            base_url=NVIDIA_CHAT_COMPLETIONS_URL,
            requires_credential=True,
            is_free_tier_available=True,
            models=NVIDIA_MODELS,
        )

    async def chat(
        self,
        *,
        credential_value: str | None,
        model_id: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.6,
    ) -> str:
        if not credential_value:
            raise ProviderRequestError(
                "provider_not_configured",
                "Configura una chiave NVIDIA nell'AI Hub prima di continuare.",
                409,
            )
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        response = await self._transport(credential_value, payload)
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderRequestError(
                "invalid_provider_response",
                "NVIDIA ha restituito una risposta non leggibile.",
                502,
            ) from error
        if not isinstance(content, str) or not content.strip():
            raise ProviderRequestError(
                "empty_provider_response",
                "NVIDIA ha restituito una risposta vuota.",
                502,
            )
        return content.strip()

    async def test_connection(
        self,
        *,
        credential_value: str | None,
        model_id: str,
    ) -> bool:
        if not credential_value:
            raise ProviderRequestError(
                "provider_not_configured",
                "Configura una chiave NVIDIA nell'AI Hub prima di continuare.",
                409,
            )
        await self._transport(
            credential_value,
            {
                "model": model_id,
                "messages": [{"role": "user", "content": "Reply with OK."}],
                "temperature": 0.6,
                "max_tokens": 4,
                "stream": False,
            },
        )
        return True

    def is_model_free(self, model_id: str) -> bool:
        return any(m.id == model_id and m.is_free for m in NVIDIA_MODELS)

    def get_available_models(self) -> list[ProviderModel]:
        return list(NVIDIA_MODELS)

    async def _post_json(
        self,
        credential_value: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        request = Request(
            NVIDIA_CHAT_COMPLETIONS_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {credential_value}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise _provider_error_for_status(error.code) from None
        except (TimeoutError, socket.timeout):
            raise ProviderRequestError(
                "provider_timeout",
                "NVIDIA non ha risposto entro il tempo previsto.",
                504,
            ) from None
        except URLError:
            raise ProviderRequestError(
                "provider_unreachable",
                "Non è stato possibile raggiungere il servizio NVIDIA.",
                502,
            ) from None
        except (UnicodeDecodeError, json.JSONDecodeError, OSError):
            raise ProviderRequestError(
                "provider_unavailable",
                "Il servizio NVIDIA ha restituito una risposta non valida.",
                502,
            ) from None
        if not isinstance(decoded, dict):
            raise ProviderRequestError(
                "invalid_provider_response",
                "NVIDIA ha restituito una risposta non leggibile.",
                502,
            )
        return decoded


def _provider_error_for_status(status_code: int) -> ProviderRequestError:
    if status_code in (401, 403):
        return ProviderRequestError(
            "provider_authentication_failed",
            "NVIDIA non ha accettato la chiave API. Verifica la configurazione.",
            401,
        )
    if status_code == 429:
        return ProviderRequestError(
            "provider_rate_limited",
            "NVIDIA ha applicato un limite temporaneo. Attendi e riprova.",
            429,
        )
    if status_code in (400, 404, 422):
        return ProviderRequestError(
            "provider_request_rejected",
            "NVIDIA ha rifiutato la richiesta o il modello non è disponibile.",
            502,
        )
    if status_code >= 500:
        return ProviderRequestError(
            "provider_unavailable",
            "Il servizio NVIDIA non è al momento disponibile.",
            502,
        )
    return ProviderRequestError(
        "provider_request_failed",
        "La richiesta a NVIDIA non è stata completata.",
        502,
    )
