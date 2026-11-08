from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from app.ai.provider_registry import DEFAULT_PROVIDER_ORDER


class PreferencesError(Exception):
    pass


class ModelSelectionError(PreferencesError):
    pass


class ModelAvailabilityError(PreferencesError):
    pass


class AiMultiPreferencesStore:
    """Store per le preferenze multi-provider di J.A.C.K.

    Gestisce:
    - provider selezionato e modello selezionato
    - ordine dei provider per il routing
    - provider abilitati/disabilitati
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or self.default_path()
        self._lock = threading.RLock()

    @staticmethod
    def default_path() -> Path:
        override = os.getenv("JACK_AI_SETTINGS_PATH")
        if override:
            return Path(override).expanduser()
        if os.name == "darwin":
            return (
                Path.home()
                / "Library"
                / "Application Support"
                / "J.A.C.K."
                / "ai_provider_settings.json"
            )
        return Path.home() / ".config" / "J.A.C.K." / "ai_provider_settings.json"

    def load(self) -> dict[str, Any]:
        with self._lock:
            if not self._path.exists():
                return self._defaults()
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                schema_version = data.get("schema_version")
                if schema_version == 1:
                    # Migrazione dal formato legacy (solo NVIDIA).
                    selected_model = data.get("selected_model_id")
                    enabled_models = data.get("enabled_model_ids", [])
                    provider_order = list(DEFAULT_PROVIDER_ORDER)
                    # Se il modello legacy è un modello NVIDIA, seleziona NVIDIA.
                    selected_provider = "nvidia" if any(
                        isinstance(m, str) and m.startswith("nvidia/")
                        for m in enabled_models
                    ) else DEFAULT_PROVIDER_ORDER[0]
                    if selected_model and isinstance(selected_model, str) and selected_model.startswith("nvidia/"):
                        selected_provider = "nvidia"
                    # Il vecchio store teneva abilitate i singoli modelli; nel nuovo
                    # store abilita il provider che li contiene.
                    enabled_providers = ["nvidia"] if any(
                        isinstance(m, str) and m.startswith("nvidia/")
                        for m in enabled_models
                    ) else [DEFAULT_PROVIDER_ORDER[0]]
                    return {
                        "selected_provider_id": selected_provider,
                        "selected_model_id": selected_model,
                        "provider_order": provider_order,
                        "enabled_providers": list(dict.fromkeys(enabled_providers)),
                    }
                selected_provider = data.get("selected_provider_id")
                selected_model = data.get("selected_model_id")
                provider_order = data.get("provider_order", DEFAULT_PROVIDER_ORDER)
                enabled_providers = data.get("enabled_providers", list(DEFAULT_PROVIDER_ORDER))
                if not isinstance(provider_order, list) or not provider_order:
                    raise ValueError("Invalid provider_order structure")
                if not isinstance(enabled_providers, list) or not enabled_providers:
                    raise ValueError("Invalid enabled_providers structure")
                return {
                    "selected_provider_id": selected_provider,
                    "selected_model_id": selected_model,
                    "provider_order": list(dict.fromkeys(provider_order)),
                    "enabled_providers": list(dict.fromkeys(enabled_providers)),
                }
            except (OSError, ValueError, TypeError, KeyError) as error:
                raise PreferencesError(
                    "La configurazione multi-provider AI non è leggibile."
                ) from error

    def select_provider_and_model(
        self, provider_id: str, model_id: str | None = None
    ) -> dict[str, Any]:
        if model_id is not None and not model_id:
            model_id = None
        with self._lock:
            data = self.load()
            if provider_id not in data["enabled_providers"]:
                raise ModelSelectionError(
                    "Abilita il provider prima di selezionarlo."
                )
            data["selected_provider_id"] = provider_id
            if model_id is not None:
                data["selected_model_id"] = model_id
            self._save(data)
            return data

    def set_provider_order(self, order: list[str]) -> dict[str, Any]:
        with self._lock:
            data = self.load()
            data["provider_order"] = list(dict.fromkeys(order))
            self._save(data)
            return data

    def set_provider_enabled(self, provider_id: str, enabled: bool) -> dict[str, Any]:
        with self._lock:
            data = self.load()
            enabled_ids = set(data["enabled_providers"])
            if enabled:
                enabled_ids.add(provider_id)
            else:
                if data["selected_provider_id"] == provider_id:
                    raise ModelAvailabilityError(
                        "Seleziona un altro provider prima di disabilitare quello attivo."
                    )
                enabled_ids.discard(provider_id)
                if not enabled_ids:
                    raise ModelAvailabilityError(
                        "Mantieni almeno un provider abilitato."
                    )
            data["enabled_providers"] = list(enabled_ids)
            self._save(data)
            return data

    def _save(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        payload = {
            "schema_version": 2,
            "selected_provider_id": data.get("selected_provider_id"),
            "selected_model_id": data.get("selected_model_id"),
            "provider_order": data.get("provider_order", DEFAULT_PROVIDER_ORDER),
            "enabled_providers": data.get("enabled_providers", list(DEFAULT_PROVIDER_ORDER)),
        }
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                0o600,
            )
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, self._path)
            if os.name != "nt":
                os.chmod(self._path, 0o600)
        except OSError as error:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise PreferencesError(
                "Non è stato possibile salvare la configurazione multi-provider AI."
            ) from error

    @staticmethod
    def _defaults() -> dict[str, Any]:
        return {
            "selected_provider_id": DEFAULT_PROVIDER_ORDER[0],
            "selected_model_id": None,
            "provider_order": list(DEFAULT_PROVIDER_ORDER),
            "enabled_providers": list(DEFAULT_PROVIDER_ORDER),
        }
