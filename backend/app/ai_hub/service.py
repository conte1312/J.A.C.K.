"""AI Hub service stub (M1 foundation).

Provider registration, model selection, routing, fallback, timeout and error
management. Credentials are never stored here in plaintext; they are handled
by the credential store (Keychain on macOS, environment fallback).

A provider is considered connected only after a real verification call.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("jack.backend.ai_hub")


@dataclass(frozen=True)
class ProviderConfig:
    id: str
    name: str
    kind: str  # "local" | "cloud"
    models: tuple[str, ...]
    enabled: bool = False
    timeout_seconds: float = 30.0
    fallback: bool = True


@dataclass
class ProviderState:
    config: ProviderConfig
    connected: bool = False
    last_error: str | None = None
    last_verified_at: str | None = None


class AiHubService:
    """Registry of AI providers with routing and fallback support."""

    def __init__(self) -> None:
        self._providers: dict[str, ProviderState] = {}
        self._default_timeout = 30.0

    def register_provider(self, config: ProviderConfig) -> None:
        """Register a provider. It is not connected until verified."""
        self._providers[config.id] = ProviderState(config=config)
        logger.info("Provider registered: %s (%s)", config.id, config.kind)

    def list_providers(self) -> list[dict[str, Any]]:
        return [
            {
                "id": state.config.id,
                "name": state.config.name,
                "kind": state.config.kind,
                "enabled": state.config.enabled,
                "connected": state.connected,
                "models": list(state.config.models),
                "timeout_seconds": state.config.timeout_seconds,
                "fallback": state.config.fallback,
                "last_error": state.last_error,
                "last_verified_at": state.last_verified_at,
            }
            for state in self._providers.values()
        ]

    def get_provider(self, provider_id: str) -> ProviderState | None:
        return self._providers.get(provider_id)

    def set_enabled(self, provider_id: str, enabled: bool) -> bool:
        state = self._providers.get(provider_id)
        if state is None:
            return False
        # Replace with a new dataclass instance since ProviderConfig is frozen.
        current = state.config
        self._providers[provider_id] = ProviderState(
            config=ProviderConfig(
                id=current.id,
                name=current.name,
                kind=current.kind,
                models=current.models,
                enabled=enabled,
                timeout_seconds=current.timeout_seconds,
                fallback=current.fallback,
            ),
            connected=state.connected,
            last_error=state.last_error,
            last_verified_at=state.last_verified_at,
        )
        return True

    def set_connected(
        self,
        provider_id: str,
        connected: bool,
        *,
        last_error: str | None = None,
        last_verified_at: str | None = None,
    ) -> bool:
        state = self._providers.get(provider_id)
        if state is None:
            return False
        current = state.config
        self._providers[provider_id] = ProviderState(
            config=ProviderConfig(
                id=current.id,
                name=current.name,
                kind=current.kind,
                models=current.models,
                enabled=current.enabled,
                timeout_seconds=current.timeout_seconds,
                fallback=current.fallback,
            ),
            connected=connected,
            last_error=last_error,
            last_verified_at=last_verified_at,
        )
        return True

    def select_provider(self, preferred: str | None = None) -> ProviderState | None:
        """Select the best available provider, honoring fallback order."""
        candidates = [
            s for s in self._providers.values() if s.config.enabled and s.connected
        ]
        if not candidates:
            return None
        if preferred:
            for s in candidates:
                if s.config.id == preferred:
                    return s
        # Deterministic fallback: first enabled+connected in registration order.
        return candidates[0]

    def credentials_configured(self, provider_id: str) -> bool:
        """Whether credentials exist for a provider (delegated to credential store).

        This stub returns False until the credential store is wired.
        """
        return False
