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

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Modelli disponibili nel piano gratuito di Gemini (al 2026).
# Verificare periodicamente su https://ai.google.dev/pricing.
GEMINI_MODELS = (
    ProviderModel(
        id="gemini-1.5-flash",
        name="Gemini 1.5 Flash",
        description="Modello Google Gemini veloce ed efficiente (piano gratuito).",
        is_free=True,
        context_window=1048576,
        max_output_tokens=8192,
    ),
    ProviderModel(
        id="gemini-1.5-flash-8b",
        name="Gemini 1.5 Flash 8B",
        description="Modello Google Gemini compatto (piano gratuito).",
        is_free=True,
        context_window=1048576,
        max_output_tokens=8192,
    ),
    ProviderModel(
        id="gemini-1.5-pro",
        name="Gemini 1.5 Pro",
        description="Modello Google Gemini avanzato (piano gratuito con limiti).",
        is_free=True,
        context_window=1048576,
        max_output_tokens=8192,
    ),
)


class GeminiProvider(BaseAiProvider):
    """Adapter per Google Gemini API (piano gratuito)."""

    def __init__(self, *, timeout: float = 60.0, transport=None) -> None:
        self._timeout = timeout
        self._transport = transport or self._post_json

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            id="google",
            name="Google Gemini",
            provider_type="online",
            base_url=GEMINI_API_BASE,
            requires_credential=True,
            is_free_tier_available=True,
            models=GEMINI_MODELS,
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
                "Configura una chiave API Google Gemini nell'AI Hub prima di continuare.",
                409,
            )
        if not self.is_model_free(model_id):
            raise ProviderRequestError(
                "model_not_free",
                f"Il modello {model_id} non è disponibile nel piano gratuito di Gemini.",
                409,
            )
        gemini_messages = self._convert_messages(messages)
        payload = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        response = await self._transport(credential_value, model_id, payload)
        try:
            candidates = response["candidates"]
            if not candidates:
                raise ProviderRequestError(
                    "empty_provider_response",
                    "Gemini ha restituito una risposta vuota.",
                    502,
                )
            content = candidates[0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderRequestError(
                "invalid_provider_response",
                "Gemini ha restituito una risposta non leggibile.",
                502,
            ) from error
        if not isinstance(content, str) or not content.strip():
            raise ProviderRequestError(
                "empty_provider_response",
                "Gemini ha restituito una risposta vuota.",
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
                "Configura una chiave API Google Gemini nell'AI Hub prima di continuare.",
                409,
            )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": "Reply with OK."}]}],
            "generationConfig": {"temperature": 0.6, "maxOutputTokens": 4},
        }
        await self._transport(credential_value, model_id, payload)
        return True

    def is_model_free(self, model_id: str) -> bool:
        return any(m.id == model_id and m.is_free for m in GEMINI_MODELS)

    def get_available_models(self) -> list[ProviderModel]:
        return list(GEMINI_MODELS)

    def _convert_messages(
        self, messages: list[dict[str, str]]
    ) -> list[dict[str, Any]]:
        converted = []
        for message in messages:
            role = message.get("role", "user")
            # Gemini usa solo "user" e "model"; "system" viene mappato a "user".
            gemini_role = "model" if role == "assistant" else "user"
            converted.append(
                {"role": gemini_role, "parts": [{"text": message.get("content", "")}]}
            )
        return converted

    async def _post_json(
        self,
        credential_value: str,
        model_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        url = f"{GEMINI_API_BASE}/models/{model_id}:generateContent?key={credential_value}"
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
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
                "Gemini non ha risposto entro il tempo previsto.",
                504,
            ) from None
        except URLError:
            raise ProviderRequestError(
                "provider_unreachable",
                "Non è stato possibile raggiungere il servizio Gemini.",
                502,
            ) from None
        except (UnicodeDecodeError, json.JSONDecodeError, OSError):
            raise ProviderRequestError(
                "provider_unavailable",
                "Il servizio Gemini ha restituito una risposta non valida.",
                502,
            ) from None
        if not isinstance(decoded, dict):
            raise ProviderRequestError(
                "invalid_provider_response",
                "Gemini ha restituito una risposta non leggibile.",
                502,
            )
        return decoded


def _provider_error_for_status(status_code: int) -> ProviderRequestError:
    if status_code in (401, 403):
        return ProviderRequestError(
            "provider_authentication_failed",
            "Gemini non ha accettato la chiave API. Verifica la configurazione.",
            401,
        )
    if status_code == 429:
        return ProviderRequestError(
            "provider_rate_limited",
            "Gemini ha applicato un limite temporaneo. Attendi e riprova.",
            429,
        )
    if status_code in (400, 404, 422):
        return ProviderRequestError(
            "provider_request_rejected",
            "Gemini ha rifiutato la richiesta o il modello non è disponibile.",
            502,
        )
    if status_code >= 500:
        return ProviderRequestError(
            "provider_unavailable",
            "Il servizio Gemini non è al momento disponibile.",
            502,
        )
    return ProviderRequestError(
        "provider_request_failed",
        "La richiesta a Gemini non è stata completata.",
        502,
    )
