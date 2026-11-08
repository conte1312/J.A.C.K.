from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from app.ai.catalog import DEFAULT_MODEL_ID, MODEL_BY_ID, MODELS


class PreferencesError(Exception):
    pass


class ModelSelectionError(PreferencesError):
    pass


class ModelAvailabilityError(PreferencesError):
    pass


class AiPreferencesStore:
    """Small local JSON store for model selection and enablement only."""

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
                selected = data["selected_model_id"]
                enabled = data["enabled_model_ids"]
                if (
                    data.get("schema_version") != 1
                    or selected not in MODEL_BY_ID
                    or not isinstance(enabled, list)
                    or not enabled
                    or any(item not in MODEL_BY_ID for item in enabled)
                    or selected not in enabled
                ):
                    raise ValueError("Invalid AI settings structure")
                return {
                    "selected_model_id": selected,
                    "enabled_model_ids": list(dict.fromkeys(enabled)),
                }
            except (OSError, ValueError, TypeError, KeyError) as error:
                raise PreferencesError(
                    "La configurazione locale dei modelli AI non è leggibile."
                ) from error

    def select_model(self, model_id: str) -> dict[str, Any]:
        if model_id not in MODEL_BY_ID:
            raise ModelSelectionError("Il modello selezionato non è supportato.")
        with self._lock:
            data = self.load()
            if model_id not in data["enabled_model_ids"]:
                raise ModelSelectionError("Abilita il modello prima di selezionarlo.")
            data["selected_model_id"] = model_id
            self._save(data)
            return data

    def set_model_enabled(self, model_id: str, enabled: bool) -> dict[str, Any]:
        if model_id not in MODEL_BY_ID:
            raise ModelAvailabilityError("Il modello richiesto non è supportato.")
        with self._lock:
            data = self.load()
            enabled_ids = set(data["enabled_model_ids"])
            if enabled:
                enabled_ids.add(model_id)
            else:
                if data["selected_model_id"] == model_id:
                    raise ModelAvailabilityError(
                        "Seleziona un altro modello prima di disabilitare quello attivo."
                    )
                enabled_ids.discard(model_id)
                if not enabled_ids:
                    raise ModelAvailabilityError(
                        "Mantieni almeno un modello abilitato."
                    )
            data["enabled_model_ids"] = [model.id for model in MODELS if model.id in enabled_ids]
            self._save(data)
            return data

    def _save(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        payload = {
            "schema_version": 1,
            "selected_model_id": data["selected_model_id"],
            "enabled_model_ids": data["enabled_model_ids"],
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
                "Non è stato possibile salvare la configurazione locale dei modelli."
            ) from error

    @staticmethod
    def _defaults() -> dict[str, Any]:
        return {
            "selected_model_id": DEFAULT_MODEL_ID,
            "enabled_model_ids": [model.id for model in MODELS],
        }
