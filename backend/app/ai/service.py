from __future__ import annotations

import asyncio

from app.ai.catalog import (
    MODEL_BY_ID,
    MODELS,
    PROVIDER_ID,
    PROVIDER_NAME,
)
from app.ai.credentials import (
    CredentialStore,
    CredentialStoreError,
    EnvironmentCredentialError,
)
from app.ai.preferences import (
    AiPreferencesStore,
    ModelAvailabilityError,
    ModelSelectionError,
    PreferencesError,
)
from app.ai.provider import NvidiaNemotronProvider, ProviderRequestError


class AiServiceError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class AiProviderService:
    def __init__(
        self,
        *,
        credentials: CredentialStore | None = None,
        preferences: AiPreferencesStore | None = None,
        provider: NvidiaNemotronProvider | None = None,
    ) -> None:
        self.credentials = credentials or CredentialStore()
        self.preferences = preferences or AiPreferencesStore()
        self.provider = provider or NvidiaNemotronProvider()
        self._verified_models: set[str] = set()

    def get_configuration(self) -> dict[str, object]:
        preferences = self._load_preferences()
        credential = self.credentials.get()
        return {
            "providers": [
                {
                    "id": PROVIDER_ID,
                    "name": PROVIDER_NAME,
                    "configured": credential is not None,
                    "credential_source": credential.source if credential else None,
                    "connection_verified": preferences["selected_model_id"]
                    in self._verified_models,
                    "selected_model_id": preferences["selected_model_id"],
                    "models": [
                        model.to_dict(
                            enabled=model.id in preferences["enabled_model_ids"],
                            selected=model.id == preferences["selected_model_id"],
                        )
                        for model in MODELS
                    ],
                }
            ],
            "selected_provider_id": PROVIDER_ID,
            "selected_model_id": preferences["selected_model_id"],
        }

    def save_credential(self, value: str) -> dict[str, object]:
        try:
            self.credentials.save(value)
        except CredentialStoreError as error:
            raise AiServiceError(
                "credential_storage_failed", str(error), 503
            ) from error
        self._verified_models.clear()
        return self.get_configuration()

    def delete_credential(self) -> dict[str, object]:
        try:
            self.credentials.delete()
        except EnvironmentCredentialError as error:
            raise AiServiceError("environment_credential", str(error), 409) from error
        except CredentialStoreError as error:
            raise AiServiceError(
                "credential_storage_failed", str(error), 503
            ) from error
        self._verified_models.clear()
        return self.get_configuration()

    def select_model(self, model_id: str) -> dict[str, object]:
        try:
            self.preferences.select_model(model_id)
        except ModelSelectionError as error:
            raise AiServiceError("model_selection_failed", str(error), 422) from error
        return self.get_configuration()

    def set_model_enabled(self, model_id: str, enabled: bool) -> dict[str, object]:
        try:
            self.preferences.set_model_enabled(model_id, enabled)
        except ModelAvailabilityError as error:
            raise AiServiceError("model_availability_failed", str(error), 409) from error
        return self.get_configuration()

    async def test_connection(self, model_id: str) -> dict[str, object]:
        self._ensure_enabled_model(model_id)
        credential = self._get_credential()
        await self._provider_chat(
            credential=credential,
            model_id=model_id,
            messages=[{"role": "user", "content": "Reply with OK."}],
            max_tokens=4,
        )
        self._verified_models.add(model_id)
        return self.get_configuration()

    async def chat(
        self,
        *,
        model_id: str,
        messages: list[dict[str, str]],
    ) -> dict[str, str]:
        self._ensure_enabled_model(model_id)
        credential = self._get_credential()
        response = await self._provider_chat(
            credential=credential,
            model_id=model_id,
            messages=messages,
            max_tokens=1024,
        )
        self._verified_models.add(model_id)
        return {
            "provider_id": PROVIDER_ID,
            "model_id": model_id,
            "content": response,
        }

    def _load_preferences(self):
        try:
            return self.preferences.load()
        except PreferencesError as error:
            raise AiServiceError(
                "preferences_unavailable", str(error), 500
            ) from error

    def _ensure_enabled_model(self, model_id: str) -> None:
        if model_id not in MODEL_BY_ID:
            raise AiServiceError("unsupported_model", "Il modello richiesto non è supportato.", 422)
        preferences = self._load_preferences()
        if model_id not in preferences["enabled_model_ids"]:
            raise AiServiceError("model_disabled", "Il modello è disabilitato.", 409)

    def _get_credential(self):
        credential = self.credentials.get()
        if credential is None:
            raise AiServiceError(
                "provider_not_configured",
                "Configura una chiave NVIDIA nell'AI Hub prima di continuare.",
                409,
            )
        return credential

    async def _provider_chat(self, **kwargs: object) -> str:
        try:
            return await asyncio.to_thread(self.provider.chat, **kwargs)
        except ProviderRequestError as error:
            raise AiServiceError(error.code, error.message, error.status_code) from error
