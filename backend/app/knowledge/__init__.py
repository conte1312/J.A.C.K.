"""Knowledge Engine package (M4).

Persistent, versioned, relation-aware local knowledge store for J.A.C.K.
"""

from app.knowledge.chunking import DocumentChunker
from app.knowledge.document_parser import (
    DocumentParseError,
    DocumentSecurityError,
    ParsedDocument,
    parse_document,
)
from app.knowledge.document_service import DocumentImportResult, DocumentService
from app.knowledge.embeddings import (
    EmbeddingResult,
    EmbeddingProvider,
    LocalEmbeddingProvider,
    cosine_similarity,
)
from app.knowledge.context_builder import (
    ContextBuilder,
    ContextItem,
    ContextPackage,
)
from app.knowledge.context_resolver import (
    ContextualResolver,
    ResolutionPlan,
    ResolvedContext,
)
from app.knowledge.graph_extractor import (
    ExtractedEntity,
    ExtractedRelation,
    ExtractionResult,
    KnowledgeGraphExtractor,
    extract_graph_from_text,
)
from app.knowledge.graph_service import (
    GraphNode,
    GraphLink,
    GraphTraversalResult,
    KnowledgeGraphService,
)
from app.knowledge.hybrid_search import HybridSearchEngine
from app.knowledge.m3_interface import MemoryReadInterface
from app.knowledge.maintenance_service import (
    MaintenanceReport,
    DuplicateItemReport,
    StaleItemReport,
    OrphanItemReport,
    BrokenProvenanceReport,
    MaintenanceService,
)
from app.knowledge.repository import (
    KnowledgeNotFoundError,
    KnowledgeProposalConflictError,
    KnowledgeRepository,
    default_knowledge_database_path,
)
from app.knowledge.validation_service import (
    LEVEL_A,
    LEVEL_B,
    LEVEL_C,
    LearningPolicyDecision,
    SourceEvaluation,
    VerificationDecision,
    ValidationService,
)
from app.knowledge.vector_store import EmbeddingRecord, VectorStore

__all__ = [
    "KnowledgeRepository",
    "KnowledgeNotFoundError",
    "KnowledgeProposalConflictError",
    "default_knowledge_database_path",
    "DocumentService",
    "DocumentImportResult",
    "DocumentChunker",
    "ParsedDocument",
    "parse_document",
    "DocumentParseError",
    "DocumentSecurityError",
    "EmbeddingResult",
    "EmbeddingProvider",
    "LocalEmbeddingProvider",
    "cosine_similarity",
    "HybridSearchEngine",
    "VectorStore",
    "EmbeddingRecord",
    "GraphNode",
    "GraphLink",
    "GraphTraversalResult",
    "KnowledgeGraphService",
    "ExtractedEntity",
    "ExtractedRelation",
    "ExtractionResult",
    "KnowledgeGraphExtractor",
    "extract_graph_from_text",
    "ContextBuilder",
    "ContextItem",
    "ContextPackage",
    "ContextualResolver",
    "ResolutionPlan",
    "ResolvedContext",
    "MemoryReadInterface",
    "MaintenanceReport",
    "DuplicateItemReport",
    "StaleItemReport",
    "OrphanItemReport",
    "BrokenProvenanceReport",
    "MaintenanceService",
    "LEVEL_A",
    "LEVEL_B",
    "LEVEL_C",
    "LearningPolicyDecision",
    "SourceEvaluation",
    "VerificationDecision",
    "ValidationService",
]
