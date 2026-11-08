from __future__ import annotations

from dataclasses import dataclass, field

from app.ai.base_provider import BaseAiProvider, ProviderRequestError
from app.ai.cost_guard import CostGuard
from app.ai.provider_registry import DEFAULT_PROVIDER_ORDER, registry


@dataclass
class ProviderState:
    """Stato runtime di un provider."""

    id: str
    available: bool = False
    last_error: str | None = None
    quota_exhausted: bool = False


@dataclass
class AiRouterConfig:
    """Configurazione del router AI."""

    provider_order: list[str] = field(default_factory=lambda: list(DEFAULT_PROVIDER_ORDER))
    enabled_providers: list[str] = field(
        default_factory=lambda: ["google", "groq", "openrouter", "ollama", "nvidia"]
    )
    max_retries_per_provider: int = 1
    failover_enabled: bool = True


class AiRouter:
    """Router intelligente per la selezione del provider AI.

    Ordine predefinito: Gemini -> Groq -> OpenRouter -> Ollama -> NVIDIA Nemotron.
    L'utente può modificare l'ordine e abilitare/disabilitare i provider.

    Il router:
    - Verifica la disponibilità del provider.
    - Controlla che il modello sia gratuito (CostGuard).
    - Passa a un altro provider solo se autorizzato e disponibile.
    - Non ripete richieste che potrebbero consumare inutilmente la quota.
    - Non effettua mai fallback verso modelli a pagamento.
    """

    def __init__(
        self,
        config: AiRouterConfig | None = None,
        cost_guard: CostGuard | None = None,
    ) -> None:
        self._registry = registry
        self._cost_guard = cost_guard or CostGuard(self._registry)
        self._config = config or AiRouterConfig()
        self._states: dict[str, ProviderState] = {
            pid: ProviderState(id=pid) for pid in self._config.enabled_providers
        }

    def get_config(self) -> AiRouterConfig:
        return self._config

    def set_provider_order(self, order: list[str]) -> None:
        for pid in order:
            if not self._registry.is_registered(pid):
                raise ProviderRequestError(
                    "unknown_provider",
                    f"Il provider '{pid}' non è registrato.",
                    404,
                )
        self._config.provider_order = list(order)

    def set_provider_enabled(self, provider_id: str, enabled: bool) -> None:
        if not self._registry.is_registered(provider_id):
            raise ProviderRequestError(
                "unknown_provider",
                f"Il provider '{provider_id}' non è registrato.",
                404,
            )
        if enabled and provider_id not in self._config.enabled_providers:
            self._config.enabled_providers.append(provider_id)
            self._states[provider_id] = ProviderState(id=provider_id)
        elif not enabled:
            self._config.enabled_providers = [
                p for p in self._config.enabled_providers if p != provider_id
            ]
            self._states.pop(provider_id, None)

    def get_provider_states(self) -> dict[str, ProviderState]:
        return dict(self._states)

    def get_selected_provider_and_model(
        self, model_id: str | None = None
    ) -> tuple[str, str]:
        """Restituisce (provider_id, model_id) per il modello richiesto.

        Se model_id è None, usa il primo modello gratuito del primo provider
        disponibile nell'ordine configurato.
        """
        for provider_id in self._config.provider_order:
            if provider_id not in self._config.enabled_providers:
                continue
            provider = self._registry.get_provider(provider_id)
            if provider is None:
                continue
            state = self._states.get(provider_id)
            if state is not None and state.quota_exhausted:
                continue
            if not state.available:
                continue
            if model_id is None:
                for model in provider.get_available_models():
                    if model.is_free:
                        return provider_id, model.id
            else:
                if provider.is_model_free(model_id):
                    return provider_id, model_id
        raise ProviderRequestError(
            "no_provider_available",
            "Nessun provider gratuito disponibile per il modello richiesto. "
            "Configura almeno un provider gratuito nell'AI Hub.",
            409,
        )

    def mark_provider_available(self, provider_id: str) -> None:
        if provider_id in self._states:
            self._states[provider_id].available = True
            self._states[provider_id].last_error = None
            self._states[provider_id].quota_exhausted = False

    def mark_provider_unavailable(
        self, provider_id: str, error: str, quota_exhausted: bool = False
    ) -> None:
        if provider_id in self._states:
            self._states[provider_id].available = False
            self._states[provider_id].last_error = error
            if quota_exhausted:
                self._states[provider_id].quota_exhausted = True

    async def route_chat(
        self,
        *,
        model_id: str | None,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.6,
    ) -> dict[str, str]:
        """Esegue una richiesta chat passando attraverso i provider in ordine.

        Restituisce {"provider_id", "model_id", "content"}.
        Solleva ProviderRequestError se nessun provider riesce a rispondere.
        """
        last_error: str | None = None
        attempted: list[str] = []

        for provider_id in self._config.provider_order:
            if provider_id not in self._config.enabled_providers:
                continue
            provider = self._registry.get_provider(provider_id)
            if provider is None:
                continue
            state = self._states.get(provider_id)
            if state is not None and state.quota_exhausted:
                continue

            # Determina il modello effettivo da usare per questo provider.
            effective_model_id = model_id
            if effective_model_id is None:
                free_models = [
                    m for m in provider.get_available_models() if m.is_free
                ]
                if not free_models:
                    continue
                effective_model_id = free_models[0].id

            # Verifica che il modello sia gratuito (CostGuard).
            try:
                self._cost_guard.assert_model_is_free(
                    provider_id, effective_model_id
                )
            except ProviderRequestError as error:
                self.mark_provider_unavailable(
                    provider_id, error.message, quota_exhausted=False
                )
                continue

            credential = self._get_credential(provider_id)
            attempted.append(provider_id)

            try:
                content = await provider.chat(
                    credential_value=credential.value if credential else None,
                    model_id=effective_model_id,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                self.mark_provider_available(provider_id)
                return {
                    "provider_id": provider_id,
                    "model_id": effective_model_id,
                    "content": content,
                }
            except ProviderRequestError as error:
                last_error = error.message
                quota_exhausted = error.status_code == 429
                self.mark_provider_unavailable(
                    provider_id, error.message, quota_exhausted=quota_exhausted
                )
                continue

        attempted_str = ", ".join(attempted) if attempted else "nessuno"
        raise ProviderRequestError(
            "all_providers_unavailable",
            (
                f"Nessun provider disponibile per completare la richiesta. "
                f"Provider tentati: {attempted_str}. Ultimo errore: {last_error or 'sconosciuto'}"
            ),
            503,
        )

    async def route_test_connection(
        self,
        *,
        provider_id: str,
        model_id: str,
    ) -> bool:
        """Testa la connessione per un provider e modello specifici."""
        provider = self._registry.get_provider(provider_id)
        if provider is None:
            raise ProviderRequestError(
                "unknown_provider",
                f"Il provider '{provider_id}' non è registrato.",
                404,
            )
        self._cost_guard.assert_model_is_free(provider_id, model_id)
        credential = self._get_credential(provider_id)
        try:
            result = await provider.test_connection(
                credential_value=credential.value if credential else None,
                model_id=model_id,
            )
            self.mark_provider_available(provider_id)
            return result
        except ProviderRequestError as error:
            self.mark_provider_unavailable(
                provider_id, error.message, quota_exhausted=(error.status_code == 429)
            )
            raise

    def _get_credential(self, provider_id: str):
        from app.ai.credential_manager import CredentialManager

        manager = CredentialManager()
        return manager.get_credential(provider_id)
