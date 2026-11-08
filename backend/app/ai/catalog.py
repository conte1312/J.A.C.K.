from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelDefinition:
    id: str
    name: str
    description: str

    def to_dict(self, *, enabled: bool, selected: bool) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "enabled": enabled,
            "selected": selected,
            "availability_note": "Endpoint NVIDIA ospitato; accesso e limiti dipendono dai termini correnti del servizio.",
        }


PROVIDER_ID = "nvidia"
PROVIDER_NAME = "NVIDIA Nemotron"
NVIDIA_CHAT_COMPLETIONS_URL = (
    "https://integrate.api.nvidia.com/v1/chat/completions"
)

MODELS = (
    ModelDefinition(
        id="nvidia/nemotron-3.5-lightning-30b-a3b",
        name="Nemotron 3.5 Lightning 30B A3B",
        description="Modello Nemotron orientato a chat, coding e ragionamento.",
    ),
    ModelDefinition(
        id="nvidia/nemotron-3.5-bolt-e4b",
        name="Nemotron 3.5 Bolt E4B",
        description="Modello Nemotron compatto per conversazioni e uso generale.",
    ),
)
MODEL_BY_ID = {model.id: model for model in MODELS}
DEFAULT_MODEL_ID = MODELS[0].id
