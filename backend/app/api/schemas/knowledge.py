"""Pydantic schemi per l'API M4 Knowledge Engine.

Convenzioni coerenti con backend/app/api/schemas/memories.py:
- ConfigDict(extra="forbid", str_strip_whitespace=True) sui modelli di input.
- ConfigDict(extra="forbid") sui modelli di output.
- Enum basati su str per i valori vincolati dal repository.
- Campi opzionali esclusi dal modello di input quando None.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---- Enum (allineati ai vincoli CHECK del repository M4) ----

class KnowledgeType(str, Enum):
    concept = "concept"
    fact = "fact"
    procedure = "procedure"
    definition = "definition"
    theorem = "theorem"
    formula = "formula"
    reference = "reference"


class SourceType(str, Enum):
    document = "document"
    conversation = "conversation"
    import_ = "import"
    system = "system"
    autonomous = "autonomous"


class ItemState(str, Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class VerificationStatus(str, Enum):
    unverified = "unverified"
    provisional = "provisional"
    verified = "verified"
    inferred = "inferred"
    contradicted = "contradicted"


class ProcessState(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"
    published = "published"


class RelationType(str, Enum):
    related = "related"
    prerequisite = "prerequisite"
    contradicts = "contradicts"
    supports = "supports"
    updates = "updates"
    instance_of = "instance_of"
    part_of = "part_of"
    causes = "causes"
    influences = "influences"


# ---- Domains ----

class DomainWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    parent_domain_id: str | None = Field(default=None, max_length=120)


class DomainRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    slug: str
    description: str | None
    parent_domain_id: str | None
    created_at: datetime
    updated_at: datetime


# ---- Items ----

class ItemWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=20_000)
    domain_id: str = Field(min_length=1, max_length=120)
    knowledge_type: KnowledgeType | None = None
    source_type: SourceType | None = None
    source_id: str | None = Field(default=None, max_length=120)
    source_title: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=500)
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    verification_status: VerificationStatus | None = None
    item_state: ItemState | None = None
    tags: list[str] | None = Field(default=None, max_length=30)
    importance: int | None = Field(default=None, ge=1, le=5)
    excluded: bool | None = None
    conversation_id: str | None = Field(default=None, max_length=120)
    last_used: datetime | None = None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        for tag in value:
            tag = tag.strip()
            if not tag or len(tag) > 64:
                raise ValueError("Invalid tag")
            normalized.append(tag)
        return normalized

    @model_validator(mode="after")
    def reject_null_non_nullable_metadata(self) -> ItemWrite:
        for field_name in (
            "knowledge_type",
            "source_type",
            "verification_status",
            "item_state",
            "tags",
            "importance",
            "excluded",
        ):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"Invalid {field_name}")
        return self


class ItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=160)
    content: str | None = Field(default=None, min_length=1, max_length=20_000)
    summary: str | None = Field(default=None, max_length=1000)
    knowledge_type: KnowledgeType | None = None
    source_type: SourceType | None = None
    source_id: str | None = Field(default=None, max_length=120)
    source_title: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=500)
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    verification_status: VerificationStatus | None = None
    item_state: ItemState | None = None
    verification_reason: str | None = Field(default=None, max_length=500)
    expires_at: datetime | None = None


class ItemRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    domain_id: str
    title: str
    content: str
    summary: str | None
    knowledge_type: KnowledgeType
    source_type: SourceType
    source_id: str | None
    source_title: str | None
    source_url: str | None
    confidence_score: float
    verification_status: VerificationStatus
    item_state: ItemState
    version: int
    is_current: bool
    acquired_at: datetime
    verified_at: datetime | None
    verification_reason: str | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    tags: list[str]
    importance: int
    excluded: bool
    conversation_id: str | None
    last_used: datetime | None


class ItemFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain_id: str | None = Field(default=None, max_length=120)
    knowledge_type: KnowledgeType | None = None
    source_type: SourceType | None = None
    verification_status: VerificationStatus | None = None
    item_state: ItemState | None = None
    is_current: bool | None = None
    tags: str | None = Field(default=None, max_length=200)
    importance_min: int | None = Field(default=None, ge=1, le=5)
    importance_max: int | None = Field(default=None, ge=1, le=5)
    excluded: bool | None = None
    q: str | None = Field(default=None, max_length=200)
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


# ---- Relations ----

class LinkWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    from_id: str = Field(min_length=1, max_length=120)
    to_id: str = Field(min_length=1, max_length=120)
    relation_type: RelationType
    strength: int = Field(default=1, ge=1, le=3)
    description: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def reject_self_link(self) -> LinkWrite:
        if self.from_id == self.to_id:
            raise ValueError("Self-links are not allowed")
        return self


class LinkRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    from_id: str
    to_id: str
    relation_type: RelationType
    relation_key: str
    strength: int
    description: str | None
    created_at: datetime


# ---- Proposals ----

class ProposalWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=20_000)
    domain_id: str = Field(min_length=1, max_length=120)
    knowledge_type: KnowledgeType | None = None
    source_type: SourceType | None = None
    source_id: str | None = Field(default=None, max_length=120)
    source_title: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=500)
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    verification_status: VerificationStatus | None = None
    tags: list[str] | None = Field(default=None, max_length=30)
    importance: int | None = Field(default=None, ge=1, le=5)
    excluded: bool | None = None
    conversation_id: str | None = Field(default=None, max_length=120)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        for tag in value:
            tag = tag.strip()
            if not tag or len(tag) > 64:
                raise ValueError("Invalid tag")
            normalized.append(tag)
        return normalized


class ProposalRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    content: str
    domain_id: str
    knowledge_type: KnowledgeType
    source_type: SourceType
    source_id: str | None
    source_title: str | None
    source_url: str | None
    confidence_score: float
    verification_status: VerificationStatus
    tags: list[str]
    importance: int
    excluded: bool
    conversation_id: str | None
    process_state: ProcessState
    created_at: datetime
    expires_at: datetime
    resolved_at: datetime | None
    published_item_id: str | None


# ---- Audit ----

class AuditRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    item_id: str | None
    proposal_id: str | None
    action: str
    occurred_at: datetime
    details_json: str | None


# ---- Health ----

class KnowledgeHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    schema_version: int


# ---- Documents (M4.3) ----

class DocumentImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    domain_id: str | None = Field(default=None, max_length=120)
    skip_duplicate: bool = Field(default=True)


class DocumentImportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    document_title: str
    document_type: str
    chunks_created: int
    items_created: int
    content_hash: str
    status: str


class DocumentSourceRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    document_type: str
    file_path: str | None
    created_at: datetime
    updated_at: datetime
    content_hash: str | None
    page_count: int | None


class DocumentChunkRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source_id: str
    item_id: str | None
    chunk_index: int
    content: str
    page_number: int | None
    section_title: str | None
    char_start: int | None
    char_end: int | None
    embedding_id: str | None
    created_at: datetime


class DocumentReprocessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    skip_duplicate: bool = Field(default=False)


# ---- Semantic Search (M4.4) ----

class HybridSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=500)
    domain_id: str | None = Field(default=None, max_length=120)
    knowledge_type: str | None = Field(default=None, max_length=40)
    verification_status: str | None = Field(default=None, max_length=40)
    item_state: str | None = Field(default="published", max_length=40)
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    min_similarity: float = Field(default=0.1, ge=0.0, le=1.0)


class HybridSearchResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    content: str
    domain_id: str
    knowledge_type: str
    source_type: str
    verification_status: str
    item_state: str
    tags: list[str]
    importance: int
    score: float
    ft_score: float | None
    semantic_score: float | None
    match_reasons: list[str]


class HybridSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    results: list[HybridSearchResultItem]
    total: int
    offset: int
    limit: int


class SearchStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    embedding_provider: str
    embedding_version: str
    embedding_dimensions: int
    stored_embeddings: int
    fts5_available: bool


# ---- Knowledge Graph (M4.5) ----

class GraphLinkRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    from_id: str
    to_id: str
    relation_type: str
    relation_key: str
    strength: int
    description: str | None
    created_at: str


class GraphNodeRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    item_id: str
    title: str
    content_preview: str | None
    links_out: list[GraphLinkRead]
    links_in: list[GraphLinkRead]


class GraphTraversalRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_item_id: str
    nodes: list[GraphNodeRead]
    edges: list[GraphLinkRead]
    max_depth_reached: int


class GraphRelatedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    title: str
    content_preview: str | None
    link: dict[str, object]


class GraphContradictionRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    link_id: str
    from_id: str
    from_title: str
    to_id: str
    to_title: str
    strength: int
    description: str | None
    created_at: str


class GraphDuplicateRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_id: str
    to_id: str
    relation_type: str
    strength: int
    links: list[dict[str, object]]


# ---- Validation & Maintenance (M4.7) ----

class DuplicateItemRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    title: str
    content_hash: str
    duplicate_count: int
    item_ids: list[str]


class StaleItemRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    title: str
    updated_at: str
    days_since_update: int


class OrphanItemRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    title: str
    reason: str


class BrokenProvenanceRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    title: str
    source_id: str | None
    reason: str


class EmbeddingConsistencyRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_published_items: int
    items_with_embeddings: int
    missing_embeddings: int
    consistency_ratio: float


class GraphConsistencyItemRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    link_id: str
    from_id: str
    to_id: str
    relation_type: str
    issue: str


class DatabaseIntegrityRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    integrity_check: str
    passed: bool
    database: str


class MaintenanceReportRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    duplicate_items: list[DuplicateItemRead]
    stale_items: list[StaleItemRead]
    orphan_items: list[OrphanItemRead]
    broken_provenance: list[BrokenProvenanceRead]
    embedding_consistency: EmbeddingConsistencyRead
    graph_consistency: list[GraphConsistencyItemRead]
    database_integrity: DatabaseIntegrityRead
    generated_at: str


class MaintenanceRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    stale_days: int = Field(default=180, ge=1, le=3650)


class MaintenanceRunRead(MaintenanceReportRead):
    model_config = ConfigDict(extra="forbid")


class SourceEvaluationRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    source_title: str
    authority_score: float | None
    reliability: float
    corroboration_count: int
    contradiction_count: int
    overall_trust: float


class LearningPolicyDecisionRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str
    action: str
    reason: str


class EvaluatePolicyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str
    content_sensitivity: str = Field(default="general", max_length=20)
    source_trust: float | None = Field(default=None, ge=0.0, le=1.0)


class VerificationTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    item_id: str
    current_state: str
    target_state: str
    state_type: str = Field(max_length=40)


class VerificationTransitionRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    current_state: str
    target_state: str
    state_type: str
    allowed: bool


# ---- Graph Extraction (M4.5) ----

class GraphExtractionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=10000)
    max_entities: int = Field(default=20, ge=1, le=100)
    max_relations: int = Field(default=30, ge=1, le=100)


class ExtractedEntityRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    description: str
    knowledge_type: str
    confidence: float


class ExtractedRelationRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_title: str
    to_title: str
    relation_type: str
    strength: int
    description: str
    confidence: float


class GraphExtractionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entities: list[ExtractedEntityRead]
    relations: list[ExtractedRelationRead]


class ExtractedItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=20000)
    domain_id: str = Field(min_length=1, max_length=120)
    knowledge_type: str = Field(default="concept", max_length=40)
    source_type: str = Field(default="document", max_length=40)
    tags: list[str] = Field(default_factory=list)
    importance: int = Field(default=3, ge=1, le=5)
    verification_status: str = Field(default="unverified", max_length=40)


class ExtractedLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    from_title: str = Field(min_length=1, max_length=160)
    to_title: str = Field(min_length=1, max_length=160)
    relation_type: str = Field(default="related", max_length=40)
    strength: int = Field(default=1, ge=1, le=3)
    description: str | None = Field(default=None, max_length=500)


class GraphExtractionApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    items: list[ExtractedItemCreate] = Field(default_factory=list)
    links: list[ExtractedLinkCreate] = Field(default_factory=list)


class GraphExtractionApplyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items_created: int
    links_created: int
    item_ids: list[str]
    link_ids: list[str]


class VersionHistoryRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    version: int
    content: str
    summary: str
    change_reason: str
    created_at: str
    created_by: str


# ---- Context Builder (M4.6) ----

class ContextBuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=1000)
    conversation_context: str | None = Field(default=None, max_length=5000)
    domain_id: str | None = Field(default=None, max_length=120)
    max_items: int = Field(default=10, ge=1, le=50)
    target_model_context: int | None = Field(default=None, ge=512, le=200000)
    include_personal: bool = Field(default=False)


class ContextItemRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    title: str
    content: str
    source_type: str
    source_id: str | None
    domain_id: str
    verification_status: str
    item_state: str
    confidence: float
    is_personal: bool
    source_provenance: dict[str, object] | None
    tokens_estimated: int


class ContextPackageRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    items: list[ContextItemRead]
    total_items: int
    total_tokens_estimated: int
    token_budget: int
    verification_summary: dict[str, int]
    sources: list[dict[str, object]]
    graph_links: list[dict[str, object]]
    uncertainty_notes: list[str]
    generated_at: str
    context_version: str


class ContextResolutionPlanRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    key_terms: list[str]
    relevant_domains: list[str]
    relevant_item_types: list[str]
    suggested_verification: list[str]
    include_graph: bool
    max_items: int
    max_chunks: int
    reason: str
