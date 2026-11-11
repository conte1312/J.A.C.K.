"""Knowledge Graph extraction for J.A.C.K. M4.5.

Usa il provider AI esistente (app.ai.service.AiProviderService) per estrarre
entità e relazioni da testo libero. Le entità vengono mappate su knowledge_items
e le relazioni su knowledge_links.

Tutte le entità/relazioni estratte sono marcate come candidate (process_state='pending',
verification_status='unverified', item_state='draft') e richiedono approvazione
esplicita prima di essere pubblicate come conoscenza verificata.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.ai.service import AiProviderService, AiServiceError

logger = logging.getLogger("jack.backend.knowledge")

# Relation types allowed in the knowledge graph (matches knowledge_links CHECK).
RELATION_TYPES = (
    "related",
    "prerequisite",
    "contradicts",
    "supports",
    "updates",
    "instance_of",
    "part_of",
    "causes",
    "influences",
)

# Knowledge item types allowed.
KNOWLEDGE_TYPES = (
    "concept",
    "fact",
    "procedure",
    "definition",
    "theorem",
    "formula",
    "reference",
)

# Maximum number of entities/relationships to extract per document to avoid
# unbounded growth.
MAX_ENTITIES = 20
MAX_RELATIONS = 30


@dataclass
class ExtractedEntity:
    id: str
    title: str
    description: str
    knowledge_type: str
    confidence: float
    source_span: str | None = None  # Original text span, for provenance


@dataclass
class ExtractedRelation:
    from_title: str
    to_title: str
    relation_type: str
    strength: int
    description: str
    confidence: float


@dataclass
class ExtractionResult:
    entities: list[ExtractedEntity] = field(default_factory=list)
    relations: list[ExtractedRelation] = field(default_factory=list)


class KnowledgeGraphExtractor:
    """Extracts entities and relations from text using an AI provider.

    All extracted items are returned as candidates; the caller is responsible
    for creating knowledge_items and knowledge_links through the repository,
    typically via an approval flow.
    """

    def __init__(
        self,
        ai_provider_service: AiProviderService,
    ) -> None:
        self.ai_provider_service = ai_provider_service

    def extract(
        self,
        text: str,
        *,
        max_entities: int = MAX_ENTITIES,
        max_relations: int = MAX_RELATIONS,
    ) -> ExtractionResult:
        """Extract entities and relations from text.

        Returns an ExtractionResult with candidate entities and relations.
        The caller must insert them into the repository via create_item /
        create_link, typically through an approval flow.
        """
        if not text or not text.strip():
            return ExtractionResult()

        prompt = self._build_extraction_prompt(text, max_entities, max_relations)

        try:
            credential = self.ai_provider_service.credentials.get()
        except Exception:
            logger.warning("No AI credential available for graph extraction.")
            return ExtractionResult()

        try:
            raw = self.ai_provider_service._provider_chat(  # type: ignore[attr-defined]
                credential=credential,
                model_id=self.ai_provider_service.preferences.selected_model_id,  # type: ignore[attr-defined]
                messages=[
                    {
                        "role": "system",
                        "content": "You are a knowledge graph extraction assistant. "
                        "Extract entities and relations from text and return ONLY valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1024,
            )
        except Exception as error:
            logger.warning("Graph extraction failed: %s", error)
            return ExtractionResult()

        return self._parse_extraction_response(raw)

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def _build_extraction_prompt(
        self,
        text: str,
        max_entities: int,
        max_relations: int,
    ) -> str:
        relation_types = ", ".join(RELATION_TYPES)
        knowledge_types = ", ".join(KNOWLEDGE_TYPES)
        return f"""You are a knowledge graph extraction assistant. Extract entities and relations from the text below.

Return ONLY a valid JSON object with this exact schema:
{{
  "entities": [
    {{
      "title": "short entity name",
      "description": "brief description",
      "knowledge_type": "concept | fact | procedure | definition | theorem | formula | reference",
      "confidence": 0.0 to 1.0
    }}
  ],
  "relations": [
    {{
      "from_title": "exact entity title from entities list",
      "to_title": "exact entity title from entities list",
      "relation_type": "related | prerequisite | contradicts | supports | updates | instance_of | part_of | causes | influences",
      "strength": 1 | 2 | 3,
      "description": "brief description of the relationship",
      "confidence": 0.0 to 1.0
    }}
  ]
}}

Rules:
- Only extract entities that are clearly mentioned in the text.
- relation_type must be one of: {relation_types}
- knowledge_type must be one of: {knowledge_types}
- strength must be 1 (weak), 2 (moderate), or 3 (strong)
- confidence must be 0.0 to 1.0
- Do not invent entities not present in the text.
- Do not create relations between entities that are not both in the entities list.
- Max {max_entities} entities, {max_relations} relations.
- Return ONLY valid JSON, no markdown, no extra text.

Text to analyze:
---
{text[:3000]}
---
"""

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_extraction_response(self, raw: str) -> ExtractionResult:
        result = ExtractionResult()

        # Try to extract JSON from the response (may be wrapped in markdown).
        json_text = raw.strip()
        if json_text.startswith("```"):
            # Remove markdown code fences.
            lines = json_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            json_text = "\n".join(lines).strip()

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as error:
            logger.warning("Failed to parse extraction JSON: %s", error)
            return result

        if not isinstance(data, dict):
            logger.warning("Extraction result is not a JSON object.")
            return result

        # Parse entities.
        entities_raw = data.get("entities", [])
        if not isinstance(entities_raw, list):
            entities_raw = []
        for item in entities_raw:
            if not isinstance(item, dict):
                continue
            result.entities.append(
                ExtractedEntity(
                    id=str(item.get("title", "")),
                    title=str(item.get("title", "")),
                    description=str(item.get("description", "")),
                    knowledge_type=str(item.get("knowledge_type", "concept")),
                    confidence=float(item.get("confidence", 0.5)),
                )
            )

        # Parse relations.
        relations_raw = data.get("relations", [])
        if not isinstance(relations_raw, list):
            relations_raw = []
        for item in relations_raw:
            if not isinstance(item, dict):
                continue
            result.relations.append(
                ExtractedRelation(
                    from_title=str(item.get("from_title", "")),
                    to_title=str(item.get("to_title", "")),
                    relation_type=str(item.get("relation_type", "related")),
                    strength=int(item.get("strength", 1)),
                    description=str(item.get("description", "")),
                    confidence=float(item.get("confidence", 0.5)),
                )
            )

        return result


def extract_graph_from_text(
    ai_provider_service: AiProviderService,
    text: str,
    *,
    max_entities: int = MAX_ENTITIES,
    max_relations: int = MAX_RELATIONS,
) -> ExtractionResult:
    """Convenience function to extract a knowledge graph from text."""
    extractor = KnowledgeGraphExtractor(ai_provider_service)
    return extractor.extract(
        text, max_entities=max_entities, max_relations=max_relations
    )