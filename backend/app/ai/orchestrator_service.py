from __future__ import annotations

from app.ai.base_provider import ProviderRequestError
from app.ai.credential_manager import CredentialManager
from app.ai.cost_guard import CostGuard
from app.ai.multi_preferences import AiMultiPreferencesStore
from app.ai.provider_registry import registry
from app.ai.router_service import AiRouter, AiRouterConfig


class AiOrchestratorService:
    """Servizio orchestratore multi-provider per J.A.C.K.

    Coordina:
    - CostGuard (protezione contro costi involontari)
    - CredentialManager (credenziali per provider nel Keychain)
    - AiMultiPreferencesStore (preferenze provider/modello/ordine)
    - AiRouter (routing intelligente con failover controllato)
    """

    def __init__(
        self,
        *,
        credentials: CredentialManager | None = None,
        preferences: AiMultiPreferencesStore | None = None,
        router: AiRouter | None = None,
        cost_guard: CostGuard | None = None,
    ) -> None:
        self._registry = registry
        self._credentials = credentials or CredentialManager()
        self._preferences = preferences or AiMultiPreferencesStore()
        self._cost_guard = cost_guard or CostGuard(self._registry)
        self._router = router or AiRouter(
            cost_guard=self._cost_guard,
        )

    def get_configuration(self) -> dict[str, object]:
        """Restituisce la configurazione completa di tutti i provider."""
        providers = []
        for provider_id in self._registry.list_providers():
            provider = self._registry.get_provider(provider_id)
            if provider is None:
                continue
            credential = self._credentials.get_credential(provider_id)
            prefs = self._preferences.load()
            is_selected_provider = prefs["selected_provider_id"] == provider_id
            is_selected_model = (
                prefs["selected_model_id"]
                and any(m.id == prefs["selected_model_id"] for m in provider.get_available_models())
            )
            router_states = self._router.get_provider_states()
            state = router_states.get(provider_id)
            providers.append({
                "id": provider_id,
                "name": provider.info.name,
                "provider_type": provider.info.provider_type,
                "base_url": provider.info.base_url,
                "requires_credential": provider.info.requires_credential,
                "is_free_tier_available": provider.info.is_free_tier_available,
                "configured": credential is not None,
                "credential_source": credential.source if credential else None,
                "available": state.available if state else False,
                "last_error": state.last_error if state else None,
                "quota_exhausted": state.quota_exhausted if state else False,
                "selected_provider": is_selected_provider,
                "models": [
                    {
                        "id": m.id,
                        "name": m.name,
                        "description": m.description,
                        "is_free": m.is_free,
                        "context_window": m.context_window,
                        "max_output_tokens": m.max_output_tokens,
                        "enabled": m.id in prefs.get("enabled_providers", []),
                        "selected": m.id == prefs.get("selected_model_id") and is_selected_provider,
                        "availability_note": (
                            "Piano gratuito disponibile" if m.is_free else "Non disponibile gratuitamente"
                        ),
                    }
                    for m in provider.get_available_models()
                ],
            })
        return {
            "providers": providers,
            "selected_provider_id": prefs["selected_provider_id"],
            "selected_model_id": prefs["selected_model_id"],
            "provider_order": prefs["provider_order"],
            "enabled_providers": prefs["enabled_providers"],
        }

    def save_provider_credential(self, provider_id: str, value: str) -> dict[str, object]:
        """Salva la credenziale per un provider."""
        try:
            self._credentials.save_credential(provider_id, value)
        except Exception as error:
            raise ProviderRequestError(
                "credential_storage_failed", str(error), 503
            ) from error
        self._router.mark_provider_available(provider_id)
        return self.get_configuration()

    def remove_provider_credential(self, provider_id: str) -> dict[str, object]:
        """Rimuove la credenziale per un provider."""
        try:
            self._credentials.delete_credential(provider_id)
        except Exception as error:
            raise ProviderRequestError(
                "credential_storage_failed", str(error), 503
            ) from error
        self._router.mark_provider_unavailable(
            provider_id, "Credenziale rimossa", quota_exhausted=False
        )
        return self.get_configuration()

    def test_provider_connection(
        self, provider_id: str, model_id: str
    ) -> dict[str, object]:
        """Testa la connessione per un provider e modello."""
        import asyncio

        try:
            result = asyncio.run(
                self._router.route_test_connection(
                    provider_id=provider_id,
                    model_id=model_id,
                )
            )
        except ProviderRequestError as error:
            raise ProviderRequestError(
                error.code, error.message, error.status_code
            ) from error
        return self.get_configuration()

    def set_provider_order(self, order: list[str]) -> dict[str, object]:
        """Imposta l'ordine dei provider per il routing."""
        self._router.set_provider_order(order)
        self._preferences.set_provider_order(order)
        return self.get_configuration()

    def set_provider_enabled(self, provider_id: str, enabled: bool) -> dict[str, object]:
        """Abilita o disabilita un provider."""
        self._router.set_provider_enabled(provider_id, enabled)
        self._preferences.set_provider_enabled(provider_id, enabled)
        return self.get_configuration()

    def select_provider_and_model(
        self, provider_id: str, model_id: str | None = None
    ) -> dict[str, object]:
        """Seleziona provider e modello per la chat."""
        self._preferences.select_provider_and_model(provider_id, model_id)
        self._router.mark_provider_available(provider_id)
        return self.get_configuration()

    async def send_chat(
        self,
        *,
        model_id: str | None,
        messages: list[dict[str, str]],
    ) -> dict[str, str]:
        """Invia una richiesta chat attraverso il router multi-provider.

        Il router gestisce l'ordine, il failover, la protezione costi
        e la selezione del modello gratuito.
        """
        try:
            return await self._router.route_chat(
                model_id=model_id,
                messages=messages,
            )
        except ProviderRequestError as error:
            raise ProviderRequestError(
                error.code, error.message, error.status_code
            ) from error
