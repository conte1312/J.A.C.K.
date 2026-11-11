"""M4 Knowledge API routes (FastAPI).

Espone KnowledgeRepository tramite endpoint REST sotto /api/v2/knowledge.
Tutte le operazioni delegano al repository esistente; nessuna logica di
persistenza è duplicata qui.
"""

from __future__ import annotations

import ipaddress
import os
import socket
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.api.schemas.knowledge import (
    AuditRead,
    ContextBuildRequest,
    ContextItemRead,
    ContextPackageRead,
    ContextResolutionPlanRead,
    DatabaseIntegrityRead,
    DuplicateItemRead,
    DocumentChunkRead,
    DocumentImportRequest,
    DocumentImportResponse,
    DocumentReprocessRequest,
    DocumentSourceRead,
    DomainRead,
    DomainWrite,
    EmbeddingConsistencyRead,
    GraphContradictionRead,
    GraphConsistencyItemRead,
    GraphDuplicateRead,
    GraphExtractionApplyRequest,
    GraphExtractionApplyResponse,
    GraphExtractionRequest,
    GraphExtractionResponse,
    GraphLinkRead,
    GraphNodeRead,
    GraphRelatedItem,
    GraphTraversalRead,
    BrokenProvenanceRead,
    HybridSearchRequest,
    HybridSearchResultItem,
    HybridSearchResponse,
    ItemFilter,
    ItemRead,
    ItemUpdate,
    ItemWrite,
    KnowledgeHealth,
    LinkRead,
    LinkWrite,
    LearningPolicyDecisionRead,
    MaintenanceReportRead,
    MaintenanceRunRead,
    OrphanItemRead,
    ProposalRead,
    ProposalWrite,
    SearchStatusResponse,
    SourceEvaluationRead,
    StaleItemRead,
    VerificationTransitionRead,
    VersionHistoryRead,
)
from app.knowledge.repository import (
    DuplicateMemoryLinkError,
    KnowledgeNotFoundError,
    KnowledgeProposalConflictError,
    KnowledgeRepository,
    default_knowledge_database_path,
)
from app.knowledge.context_builder import ContextBuilder
from app.knowledge.context_resolver import ContextualResolver
from app.knowledge.document_service import DocumentService
from app.knowledge.document_parser import (
    DocumentParseError,
    DocumentSecurityError,
)
from app.knowledge.embeddings import LocalEmbeddingProvider
from app.knowledge.graph_extractor import KnowledgeGraphExtractor
from app.knowledge.graph_service import KnowledgeGraphService
from app.knowledge.hybrid_search import HybridSearchEngine
from app.knowledge.maintenance_service import MaintenanceService
from app.knowledge.m3_interface import MemoryReadInterface
from app.knowledge.repository import (
    DuplicateMemoryLinkError,
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
from app.knowledge.vector_store import VectorStore
from app.ai.service import AiProviderService

router = APIRouter(prefix="/knowledge", tags=["knowledge", "v2"])


def get_knowledge_repository(request: Request) -> KnowledgeRepository:
    return request.app.state.knowledge_repository


def get_document_service(
    request: Request,
) -> DocumentService:
    repository = request.app.state.knowledge_repository
    return DocumentService(repository=repository)


def get_vector_store(request: Request) -> VectorStore:
    return request.app.state.vector_store


def get_embedding_provider(request: Request) -> LocalEmbeddingProvider:
    return request.app.state.embedding_provider


def get_hybrid_search_engine(
    request: Request,
) -> HybridSearchEngine:
    repository = request.app.state.knowledge_repository
    vector_store = request.app.state.vector_store
    embedding_provider = request.app.state.embedding_provider
    return HybridSearchEngine(
        repository=repository,
        vector_store=vector_store,
        embedding_provider=embedding_provider,
    )


def get_graph_service(request: Request) -> KnowledgeGraphService:
    repository = request.app.state.knowledge_repository
    return KnowledgeGraphService(repository=repository)


Repository = Annotated[KnowledgeRepository, Depends(get_knowledge_repository)]
DocumentServiceDep = Annotated[
    DocumentService, Depends(get_document_service)
]
VectorStoreDep = Annotated[VectorStore, Depends(get_vector_store)]
EmbeddingProviderDep = Annotated[
    LocalEmbeddingProvider, Depends(get_embedding_provider)
]
HybridSearchDep = Annotated[
    HybridSearchEngine, Depends(get_hybrid_search_engine)
]
GraphServiceDep = Annotated[
    KnowledgeGraphService, Depends(get_graph_service)
]


def get_graph_extractor(request: Request) -> KnowledgeGraphExtractor:
    ai_provider_service = request.app.state.ai_provider_service
    return KnowledgeGraphExtractor(ai_provider_service=ai_provider_service)


GraphExtractorDep = Annotated[
    KnowledgeGraphExtractor, Depends(get_graph_extractor)
]


def get_context_builder(
    request: Request,
) -> ContextBuilder:
    repository = request.app.state.knowledge_repository
    graph_service = request.app.state.graph_service if hasattr(
        request.app.state, "graph_service"
    ) else None
    return ContextBuilder(
        repository=repository,
        graph_service=graph_service,
    )


ContextBuilderDep = Annotated[
    ContextBuilder, Depends(get_context_builder)
]


def get_maintenance_service(
    request: Request,
) -> MaintenanceService:
    repository = request.app.state.knowledge_repository
    return MaintenanceService(repository=repository)


def get_validation_service(
    request: Request,
) -> ValidationService:
    repository = request.app.state.knowledge_repository
    graph_service = request.app.state.graph_service if hasattr(
        request.app.state, "graph_service"
    ) else None
    return ValidationService(
        repository=repository,
        graph_service=graph_service,
    )


MaintenanceServiceDep = Annotated[
    MaintenanceService, Depends(get_maintenance_service)
]
ValidationServiceDep = Annotated[
    ValidationService, Depends(get_validation_service)
]


def _item_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Knowledge item not found",
    )


def _domain_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Knowledge domain not found",
    )


def _link_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Knowledge link not found",
    )


def _proposal_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Knowledge proposal not found",
    )


def _link_write_error(error: Exception) -> HTTPException:
    if isinstance(error, DuplicateMemoryLinkError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Equivalent knowledge link already exists",
        )
    return _item_not_found()


# =====================================================================
# Health
# =====================================================================

@router.get("/health", response_model=KnowledgeHealth)
def knowledge_health(
    repository: Repository,
) -> dict[str, object]:
    return {
        "status": "ok",
        "schema_version": repository.current_version(),
    }


# =====================================================================
# Domains
# =====================================================================

@router.get("/domains", response_model=list[DomainRead])
def list_domains(
    repository: Repository,
    parent_domain_id: Annotated[str | None, Query(max_length=120)] = None,
) -> list[dict[str, object]]:
    return repository.list_domains(parent_domain_id=parent_domain_id)


@router.post(
    "/domains",
    response_model=DomainRead,
    status_code=status.HTTP_201_CREATED,
)
def create_domain(
    payload: DomainWrite,
    repository: Repository,
) -> dict[str, object]:
    try:
        return repository.create_domain(
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            parent_domain_id=payload.parent_domain_id,
        )
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Domain slug already exists or invalid parent domain",
        ) from error


@router.get("/domains/{domain_id}", response_model=DomainRead)
def get_domain(domain_id: str, repository: Repository) -> dict[str, object]:
    domain = repository.get_domain(domain_id)
    if domain is None:
        raise _domain_not_found()
    return domain


@router.put("/domains/{domain_id}", response_model=DomainRead)
def update_domain(
    domain_id: str,
    payload: DomainWrite,
    repository: Repository,
) -> dict[str, object]:
    domain = repository.get_domain(domain_id)
    if domain is None:
        raise _domain_not_found()
    try:
        return repository.update_domain(
            domain_id,
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            parent_domain_id=payload.parent_domain_id,
        )
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Domain slug already exists",
        ) from error


@router.delete("/domains/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_domain(domain_id: str, repository: Repository) -> Response:
    if not repository.delete_domain(domain_id):
        raise _domain_not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =====================================================================
# Items
# =====================================================================

@router.get("/items", response_model=list[ItemRead])
def list_items(
    repository: Repository,
    domain_id: Annotated[str | None, Query(max_length=120)] = None,
    knowledge_type: Annotated[str | None, Query()] = None,
    source_type: Annotated[str | None, Query()] = None,
    verification_status: Annotated[str | None, Query()] = None,
    item_state: Annotated[str | None, Query()] = None,
    is_current: Annotated[bool | None, Query()] = None,
    tags: Annotated[str | None, Query(max_length=200)] = None,
    importance_min: Annotated[int | None, Query(ge=1, le=5)] = None,
    importance_max: Annotated[int | None, Query(ge=1, le=5)] = None,
    excluded: Annotated[bool | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict[str, object]]:
    items = repository.list_items(
        domain_id=domain_id,
        knowledge_type=knowledge_type,
        source_type=source_type,
        verification_status=verification_status,
        item_state=item_state,
        is_current=is_current,
        query=q,
        limit=limit,
        offset=offset,
    )
    # Filtri post-repository non supportati nativamente dal repository.
    result = items
    if tags:
        wanted = {t.strip().casefold() for t in tags.split(",") if t.strip()}
        result = [
            item
            for item in result
            if wanted.intersection({str(t).casefold() for t in item.get("tags", [])})
        ]
    if importance_min is not None:
        result = [item for item in result if int(item["importance"]) >= importance_min]
    if importance_max is not None:
        result = [item for item in result if int(item["importance"]) <= importance_max]
    if excluded is not None:
        result = [item for item in result if bool(item["excluded"]) == excluded]
    return result


@router.post(
    "/items",
    response_model=ItemRead,
    status_code=status.HTTP_201_CREATED,
)
def create_item(payload: ItemWrite, repository: Repository) -> dict[str, object]:
    try:
        return repository.create_item(
            title=payload.title,
            content=payload.content,
            domain_id=payload.domain_id,
            knowledge_type=(
                payload.knowledge_type.value if payload.knowledge_type else "concept"
            ),
            source_type=(
                payload.source_type.value if payload.source_type else "system"
            ),
            source_id=payload.source_id,
            source_title=payload.source_title,
            source_url=payload.source_url,
            confidence_score=(
                payload.confidence_score
                if payload.confidence_score is not None
                else 1.0
            ),
            verification_status=(
                payload.verification_status.value
                if payload.verification_status
                else "unverified"
            ),
            item_state=(
                payload.item_state.value if payload.item_state else "draft"
            ),
            tags=payload.tags,
            importance=(
                payload.importance if payload.importance is not None else 3
            ),
            excluded=payload.excluded if payload.excluded is not None else False,
            conversation_id=payload.conversation_id,
            last_used=(
                payload.last_used.isoformat()
                if payload.last_used is not None
                else None
            ),
        )
    except KnowledgeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid request data",
        ) from error


@router.get("/items/search", response_model=list[ItemRead])
def search_items(
    repository: Repository,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    domain_id: Annotated[str | None, Query(max_length=120)] = None,
    knowledge_type: Annotated[str | None, Query()] = None,
    verification_status: Annotated[str | None, Query()] = None,
    item_state: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[dict[str, object]]:
    if not q or not q.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid search query",
        )
    try:
        return repository.search_items(
            query=q,
            domain_id=domain_id,
            knowledge_type=knowledge_type,
            verification_status=verification_status,
            item_state=item_state,
            limit=limit,
        )
    except Exception as error:
        # Invalid FTS expression -> 422
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid search query",
        ) from error


@router.get("/items/{item_id}", response_model=ItemRead)
def get_item(item_id: str, repository: Repository) -> dict[str, object]:
    item = repository.get_item(item_id)
    if item is None:
        raise _item_not_found()
    return item


@router.put("/items/{item_id}", response_model=ItemRead)
def update_item(
    item_id: str,
    payload: ItemUpdate,
    repository: Repository,
) -> dict[str, object]:
    update_kwargs: dict[str, object] = {}
    if payload.title is not None:
        update_kwargs["title"] = payload.title
    if payload.content is not None:
        update_kwargs["content"] = payload.content
    if payload.summary is not None:
        update_kwargs["summary"] = payload.summary
    if payload.knowledge_type is not None:
        update_kwargs["knowledge_type"] = payload.knowledge_type.value
    if payload.source_type is not None:
        update_kwargs["source_type"] = payload.source_type.value
    if payload.source_id is not None:
        update_kwargs["source_id"] = payload.source_id
    if payload.source_title is not None:
        update_kwargs["source_title"] = payload.source_title
    if payload.source_url is not None:
        update_kwargs["source_url"] = payload.source_url
    if payload.confidence_score is not None:
        update_kwargs["confidence_score"] = payload.confidence_score
    if payload.verification_status is not None:
        update_kwargs["verification_status"] = payload.verification_status.value
    if payload.item_state is not None:
        update_kwargs["item_state"] = payload.item_state.value
    if payload.verification_reason is not None:
        update_kwargs["verification_reason"] = payload.verification_reason
    if payload.expires_at is not None:
        update_kwargs["expires_at"] = payload.expires_at.isoformat()

    try:
        item = repository.update_item(item_id, **update_kwargs)
    except KnowledgeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid request data",
        ) from error

    if item is None:
        raise _item_not_found()
    return item


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_item(item_id: str, repository: Repository) -> Response:
    """Soft-delete (archive) an item. No physical deletion via public API."""
    if not repository.delete_item(item_id):
        raise _item_not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =====================================================================
# Relations
# =====================================================================

@router.get("/links", response_model=list[LinkRead])
def list_links(
    repository: Repository,
    item_id: Annotated[str | None, Query(max_length=120)] = None,
    relation_type: Annotated[str | None, Query()] = None,
) -> list[dict[str, object]]:
    return repository.list_links(item_id=item_id, relation_type=relation_type)


@router.post(
    "/links",
    response_model=LinkRead,
    status_code=status.HTTP_201_CREATED,
)
def create_link(payload: LinkWrite, repository: Repository) -> dict[str, object]:
    try:
        return repository.create_link(
            from_id=payload.from_id,
            to_id=payload.to_id,
            relation_type=payload.relation_type.value,
            strength=payload.strength,
            description=payload.description,
        )
    except (DuplicateMemoryLinkError, KnowledgeNotFoundError) as error:
        raise _link_write_error(error) from error


@router.get("/links/{link_id}", response_model=LinkRead)
def get_link(link_id: str, repository: Repository) -> dict[str, object]:
    link = repository.get_link(link_id)
    if link is None:
        raise _link_not_found()
    return link


@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(link_id: str, repository: Repository) -> Response:
    if not repository.delete_link(link_id):
        raise _link_not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =====================================================================
# Proposals
# =====================================================================

@router.get("/proposals", response_model=list[ProposalRead])
def list_proposals(
    repository: Repository,
    process_state: Annotated[str | None, Query()] = None,
) -> list[dict[str, object]]:
    return repository.list_proposals(process_state=process_state)


@router.post(
    "/proposals",
    response_model=ProposalRead,
    status_code=status.HTTP_201_CREATED,
)
def create_proposal(
    payload: ProposalWrite,
    repository: Repository,
) -> dict[str, object]:
    try:
        return repository.create_proposal(
            title=payload.title,
            content=payload.content,
            domain_id=payload.domain_id,
            knowledge_type=(
                payload.knowledge_type.value if payload.knowledge_type else "concept"
            ),
            source_type=(
                payload.source_type.value if payload.source_type else "autonomous"
            ),
            source_id=payload.source_id,
            source_title=payload.source_title,
            source_url=payload.source_url,
            confidence_score=(
                payload.confidence_score
                if payload.confidence_score is not None
                else 1.0
            ),
            verification_status=(
                payload.verification_status.value
                if payload.verification_status
                else "unverified"
            ),
            tags=payload.tags,
            importance=(
                payload.importance if payload.importance is not None else 3
            ),
            excluded=payload.excluded if payload.excluded is not None else False,
            conversation_id=payload.conversation_id,
        )
    except KnowledgeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid request data",
        ) from error


@router.get("/proposals/{proposal_id}", response_model=ProposalRead)
def get_proposal(proposal_id: str, repository: Repository) -> dict[str, object]:
    proposal = repository.get_proposal(proposal_id)
    if proposal is None:
        raise _proposal_not_found()
    return proposal


@router.post("/proposals/{proposal_id}/approve", response_model=ProposalRead)
def approve_proposal(
    proposal_id: str,
    repository: Repository,
) -> dict[str, object]:
    try:
        item = repository.approve_proposal(proposal_id)
    except KnowledgeProposalConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Knowledge proposal cannot be approved: {error}",
        ) from error
    if item is None:
        raise _proposal_not_found()
    return item


@router.post("/proposals/{proposal_id}/reject", response_model=ProposalRead)
def reject_proposal(
    proposal_id: str,
    repository: Repository,
) -> dict[str, object]:
    try:
        proposal = repository.reject_proposal(proposal_id)
    except KnowledgeProposalConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Knowledge proposal cannot be rejected: {error}",
        ) from error
    if proposal is None:
        raise _proposal_not_found()
    return proposal


# =====================================================================
# Audit log
# =====================================================================

@router.get("/audit", response_model=list[AuditRead])
def get_audit_log(
    repository: Repository,
    item_id: Annotated[str | None, Query(max_length=120)] = None,
    proposal_id: Annotated[str | None, Query(max_length=120)] = None,
    action: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[dict[str, object]]:
    return repository.audit_log(
        item_id=item_id,
        proposal_id=proposal_id,
        action=action,
        limit=limit,
    )


# =====================================================================
# Documents (M4.3)
# =====================================================================

@router.post(
    "/documents/import",
    response_model=DocumentImportResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_document(
    payload: DocumentImportRequest,
    service: DocumentServiceDep,
) -> dict[str, object]:
    # Note: file_path is expected to be passed via a temporary upload
    # mechanism. For M4.3, the client provides an absolute local path.
    # In a production scenario this would be a multipart upload.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Use /documents/import/file with a local path parameter",
    )


@router.post(
    "/documents/import/file",
    response_model=DocumentImportResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_document_file(
    file_path: Annotated[str, Query(max_length=500)],
    domain_id: Annotated[str | None, Query(max_length=120)] = None,
    skip_duplicate: Annotated[bool, Query()] = True,
    service: DocumentServiceDep = ...,
) -> dict[str, object]:
    try:
        result = service.import_document(
            file_path=file_path,
            domain_id=domain_id,
            skip_duplicate=skip_duplicate,
        )
    except DocumentSecurityError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except DocumentParseError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except KnowledgeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    return {
        "source_id": result.source_id,
        "document_title": result.document_title,
        "document_type": result.document_type,
        "chunks_created": result.chunks_created,
        "items_created": result.items_created,
        "content_hash": result.content_hash,
        "status": result.status,
    }


@router.get("/documents", response_model=list[DocumentSourceRead])
def list_documents(
    service: DocumentServiceDep,
) -> list[dict[str, object]]:
    return service.list_sources()


@router.get("/documents/{source_id}", response_model=DocumentSourceRead)
def get_document(
    source_id: str,
    service: DocumentServiceDep,
) -> dict[str, object]:
    source = service.get_source(source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document source not found",
        )
    return source


@router.get(
    "/documents/{source_id}/chunks",
    response_model=list[DocumentChunkRead],
)
def get_document_chunks(
    source_id: str,
    service: DocumentServiceDep,
) -> list[dict[str, object]]:
    source = service.get_source(source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document source not found",
        )
    return service.list_chunks(source_id)


@router.post(
    "/documents/{source_id}/reprocess",
    response_model=DocumentImportResponse,
)
def reprocess_document(
    source_id: str,
    payload: DocumentReprocessRequest,
    service: DocumentServiceDep,
) -> dict[str, object]:
    source = service.get_source(source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document source not found",
        )
    file_path = str(source.get("file_path") or "")
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No file path available for reprocessing",
        )
    try:
        result = service.import_document(
            file_path=file_path,
            domain_id=None,
            skip_duplicate=payload.skip_duplicate,
        )
    except DocumentSecurityError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except DocumentParseError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    return {
        "source_id": result.source_id,
        "document_title": result.document_title,
        "document_type": result.document_type,
        "chunks_created": result.chunks_created,
        "items_created": result.items_created,
        "content_hash": result.content_hash,
        "status": result.status,
    }


@router.delete("/documents/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    source_id: str,
    service: DocumentServiceDep,
) -> Response:
    if not service.delete_source(source_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document source not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =====================================================================
# Semantic Search (M4.4)
# =====================================================================

@router.post(
    "/search/hybrid",
    response_model=HybridSearchResponse,
)
def hybrid_search(
    payload: HybridSearchRequest,
    engine: HybridSearchDep,
) -> dict[str, object]:
    results = engine.search(
        query=payload.query,
        domain_id=payload.domain_id,
        knowledge_type=payload.knowledge_type,
        verification_status=payload.verification_status,
        item_state=payload.item_state,
        limit=payload.limit,
        offset=payload.offset,
        min_similarity=payload.min_similarity,
    )
    items = [
        HybridSearchResultItem(
            id=str(r.item["id"]),
            title=str(r.item["title"]),
            content=str(r.item["content"]),
            domain_id=str(r.item["domain_id"]),
            knowledge_type=str(r.item["knowledge_type"]),
            source_type=str(r.item["source_type"]),
            verification_status=str(r.item["verification_status"]),
            item_state=str(r.item["item_state"]),
            tags=list(r.item.get("tags", [])),
            importance=int(r.item.get("importance", 3)),
            score=r.score,
            ft_score=r.ft_score,
            semantic_score=r.semantic_score,
            match_reasons=list(r.match_reasons),
        )
        for r in results
    ]
    return {
        "query": payload.query,
        "results": items,
        "total": len(items),
        "offset": payload.offset,
        "limit": payload.limit,
    }


@router.post(
    "/search/semantic",
    response_model=HybridSearchResponse,
)
def semantic_search(
    payload: HybridSearchRequest,
    engine: HybridSearchDep,
) -> dict[str, object]:
    # Semantic-only: use only vector similarity, no FTS5
    results = engine.search(
        query=payload.query,
        domain_id=payload.domain_id,
        knowledge_type=payload.knowledge_type,
        verification_status=payload.verification_status,
        item_state=payload.item_state,
        limit=payload.limit,
        offset=payload.offset,
        min_similarity=payload.min_similarity,
    )
    # Override ft_score to None for pure semantic
    items = [
        HybridSearchResultItem(
            id=str(r.item["id"]),
            title=str(r.item["title"]),
            content=str(r.item["content"]),
            domain_id=str(r.item["domain_id"]),
            knowledge_type=str(r.item["knowledge_type"]),
            source_type=str(r.item["source_type"]),
            verification_status=str(r.item["verification_status"]),
            item_state=str(r.item["item_state"]),
            tags=list(r.item.get("tags", [])),
            importance=int(r.item.get("importance", 3)),
            score=r.semantic_score if r.semantic_score is not None else 0.0,
            ft_score=None,
            semantic_score=r.semantic_score,
            match_reasons=["semantic"] if r.semantic_score and r.semantic_score > 0 else [],
        )
        for r in results
    ]
    return {
        "query": payload.query,
        "results": items,
        "total": len(items),
        "offset": payload.offset,
        "limit": payload.limit,
    }


@router.get(
    "/search/status",
    response_model=SearchStatusResponse,
)
def search_status(
    engine: HybridSearchDep,
) -> dict[str, object]:
    return engine.get_search_status()


# =====================================================================
# Knowledge Graph (M4.5)
# =====================================================================

@router.get(
    "/graph/{item_id}",
    response_model=GraphTraversalRead,
)
def get_graph(
    item_id: str,
    depth: Annotated[int, Query(ge=1, le=5)] = 2,
    service: GraphServiceDep = ...,
) -> dict[str, object]:
    try:
        result = service.get_subgraph(item_id=item_id, depth=depth)
    except KnowledgeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    return {
        "start_item_id": result.start_item_id,
        "nodes": [
            {
                "id": n.id,
                "item_id": n.id,
                "title": str(n.item.get("title", "")),
                "content_preview": (
                    str(n.item.get("content", ""))[:200]
                    if n.item.get("content")
                    else None
                ),
                "links_out": [
                    {
                        "id": l.id,
                        "from_id": l.from_id,
                        "to_id": l.to_id,
                        "relation_type": l.relation_type,
                        "relation_key": l.relation_key,
                        "strength": l.strength,
                        "description": l.description,
                        "created_at": l.created_at,
                    }
                    for l in n.links_out
                ],
                "links_in": [
                    {
                        "id": l.id,
                        "from_id": l.from_id,
                        "to_id": l.to_id,
                        "relation_type": l.relation_type,
                        "relation_key": l.relation_key,
                        "strength": l.strength,
                        "description": l.description,
                        "created_at": l.created_at,
                    }
                    for l in n.links_in
                ],
            }
            for n in result.nodes.values()
        ],
        "edges": [
            {
                "id": e.id,
                "from_id": e.from_id,
                "to_id": e.to_id,
                "relation_type": e.relation_type,
                "relation_key": e.relation_key,
                "strength": e.strength,
                "description": e.description,
                "created_at": e.created_at,
            }
            for e in result.edges
        ],
        "max_depth_reached": result.max_depth_reached,
    }


@router.get(
    "/graph/{item_id}/neighbors",
    response_model=GraphTraversalRead,
)
def get_graph_neighbors(
    item_id: str,
    depth: Annotated[int, Query(ge=1, le=5)] = 1,
    relation_type: Annotated[str | None, Query()] = None,
    service: GraphServiceDep = ...,
) -> dict[str, object]:
    try:
        result = service.get_neighbors(
            item_id=item_id,
            depth=depth,
            relation_type=relation_type,
        )
    except KnowledgeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    return {
        "start_item_id": result.start_item_id,
        "nodes": [
            {
                "id": n.id,
                "item_id": n.id,
                "title": str(n.item.get("title", "")),
                "content_preview": (
                    str(n.item.get("content", ""))[:200]
                    if n.item.get("content")
                    else None
                ),
                "links_out": [],
                "links_in": [],
            }
            for n in result.nodes.values()
        ],
        "edges": [
            {
                "id": e.id,
                "from_id": e.from_id,
                "to_id": e.to_id,
                "relation_type": e.relation_type,
                "relation_key": e.relation_key,
                "strength": e.strength,
                "description": e.description,
                "created_at": e.created_at,
            }
            for e in result.edges
        ],
        "max_depth_reached": result.max_depth_reached,
    }


@router.get(
    "/graph/{item_id}/related",
    response_model=list[GraphRelatedItem],
)
def get_graph_related(
    item_id: str,
    relation_type: Annotated[str | None, Query()] = None,
    min_strength: Annotated[int, Query(ge=1, le=3)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    service: GraphServiceDep = ...,
) -> list[dict[str, object]]:
    try:
        related = service.get_related(
            item_id=item_id,
            relation_types=[relation_type] if relation_type else None,
            min_strength=min_strength,
            limit=limit,
        )
    except KnowledgeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    return [
        {
            "item_id": str(r["item"]["id"]),
            "title": str(r["item"].get("title", "")),
            "content_preview": (
                str(r["item"].get("content", ""))[:200]
                if r["item"].get("content")
                else None
            ),
            "link": r["link"],
        }
        for r in related
    ]


@router.get(
    "/graph/{item_id}/contradictions",
    response_model=list[GraphContradictionRead],
)
def get_graph_contradictions(
    item_id: str,
    service: GraphServiceDep = ...,
) -> list[dict[str, object]]:
    try:
        return service.find_contradictions(item_id=item_id)
    except KnowledgeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


@router.get(
    "/graph/{item_id}/duplicates",
    response_model=list[GraphDuplicateRead],
)
def get_graph_duplicates(
    item_id: str,
    service: GraphServiceDep = ...,
) -> list[dict[str, object]]:
    try:
        return service.find_duplicate_relationships(item_id=item_id)
    except KnowledgeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


# =====================================================================
# Context Builder (M4.6)
# =====================================================================

@router.post(
    "/context/resolve",
    response_model=ContextResolutionPlanRead,
)
def resolve_context(
    payload: ContextBuildRequest,
    builder: ContextBuilderDep,
) -> dict[str, object]:
    plan = builder.resolver.resolve(
        query=payload.query,
        conversation_context=payload.conversation_context,
        domain_id=payload.domain_id,
        max_items=payload.max_items,
    )
    return {
        "query": plan.query,
        "key_terms": plan.key_terms,
        "relevant_domains": plan.relevant_domains,
        "relevant_item_types": plan.relevant_item_types,
        "suggested_verification": plan.suggested_verification,
        "include_graph": plan.include_graph,
        "max_items": plan.max_items,
        "max_chunks": plan.max_chunks,
        "reason": plan.reason,
    }


@router.post(
    "/context/build",
    response_model=ContextPackageRead,
)
def build_context(
    payload: ContextBuildRequest,
    builder: ContextBuilderDep,
) -> dict[str, object]:
    package = builder.build_context(
        query=payload.query,
        conversation_context=payload.conversation_context,
        domain_id=payload.domain_id,
        max_items=payload.max_items,
        target_model_context=payload.target_model_context,
        include_personal=payload.include_personal,
    )
    return {
        "query": package.query,
        "items": [
            {
                "item_id": it.item_id,
                "title": it.title,
                "content": it.content,
                "source_type": it.source_type,
                "source_id": it.source_id,
                "domain_id": it.domain_id,
                "verification_status": it.verification_status,
                "item_state": it.item_state,
                "confidence": it.confidence,
                "is_personal": it.is_personal,
                "source_provenance": it.source_provenance,
                "tokens_estimated": it.tokens_estimated,
            }
            for it in package.items
        ],
        "total_items": package.total_items,
        "total_tokens_estimated": package.total_tokens_estimated,
        "token_budget": package.token_budget,
        "verification_summary": package.verification_summary,
        "sources": package.sources,
        "graph_links": package.graph_links,
        "uncertainty_notes": package.uncertainty_notes,
        "generated_at": package.generated_at,
        "context_version": package.context_version,
    }


# =====================================================================
# Validation & Maintenance (M4.7)
# =====================================================================

@router.post(
    "/maintenance/run",
    response_model=MaintenanceRunRead,
)
def run_maintenance(
    payload: MaintenanceRunRequest,
    service: MaintenanceServiceDep,
) -> dict[str, object]:
    report = service.run_full_maintenance(stale_days=payload.stale_days)
    return {
        "duplicate_items": [
            {
                "item_id": d.item_id,
                "title": d.title,
                "content_hash": d.content_hash,
                "duplicate_count": d.duplicate_count,
                "item_ids": d.item_ids,
            }
            for d in report.duplicate_items
        ],
        "stale_items": [
            {
                "item_id": s.item_id,
                "title": s.title,
                "updated_at": s.updated_at,
                "days_since_update": s.days_since_update,
            }
            for s in report.stale_items
        ],
        "orphan_items": [
            {
                "item_id": o.item_id,
                "title": o.title,
                "reason": o.reason,
            }
            for o in report.orphan_items
        ],
        "broken_provenance": [
            {
                "item_id": b.item_id,
                "title": b.title,
                "source_id": b.source_id,
                "reason": b.reason,
            }
            for b in report.broken_provenance
        ],
        "embedding_consistency": report.embedding_consistency,
        "graph_consistency": report.graph_consistency,
        "database_integrity": report.database_integrity,
        "generated_at": report.generated_at,
    }


@router.get(
    "/maintenance/duplicates",
    response_model=list[DuplicateItemRead],
)
def get_duplicates(
    service: MaintenanceServiceDep,
) -> list[dict[str, object]]:
    return service.find_duplicate_items()


@router.get(
    "/maintenance/stale",
    response_model=list[StaleItemRead],
)
def get_stale(
    stale_days: Annotated[int, Query(ge=1, le=3650)] = 180,
    service: MaintenanceServiceDep = ...,
) -> list[dict[str, object]]:
    return service.find_stale_items(stale_days=stale_days)


@router.get(
    "/maintenance/orphans",
    response_model=list[OrphanItemRead],
)
def get_orphans(
    service: MaintenanceServiceDep,
) -> list[dict[str, object]]:
    return service.find_orphan_items()


@router.get(
    "/maintenance/broken-provenance",
    response_model=list[BrokenProvenanceRead],
)
def get_broken_provenance(
    service: MaintenanceServiceDep,
) -> list[dict[str, object]]:
    return service.find_broken_provenance()


@router.get(
    "/maintenance/embedding-consistency",
    response_model=EmbeddingConsistencyRead,
)
def get_embedding_consistency(
    service: MaintenanceServiceDep,
) -> dict[str, Any]:
    return service.check_embedding_consistency()


@router.get(
    "/maintenance/graph-consistency",
    response_model=list[GraphConsistencyItemRead],
)
def get_graph_consistency(
    service: MaintenanceServiceDep,
) -> list[dict[str, Any]]:
    return service.check_graph_consistency()


@router.get(
    "/maintenance/database-integrity",
    response_model=DatabaseIntegrityRead,
)
def get_database_integrity(
    service: MaintenanceServiceDep,
) -> dict[str, Any]:
    return service.check_database_integrity()


@router.post(
    "/validation/evaluate-source",
    response_model=SourceEvaluationRead,
)
def evaluate_source(
    source_id: Annotated[str, Query(max_length=120)],
    service: ValidationServiceDep,
) -> dict[str, Any]:
    result = service.evaluate_source(source_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    return {
        "source_id": result.source_id,
        "source_title": result.source_title,
        "authority_score": result.authority_score,
        "reliability": result.reliability,
        "corroboration_count": result.corroboration_count,
        "contradiction_count": result.contradiction_count,
        "overall_trust": result.overall_trust,
    }


@router.post(
    "/validation/evaluate-policy",
    response_model=LearningPolicyDecisionRead,
)
def evaluate_policy(
    payload: EvaluatePolicyRequest,
    service: ValidationServiceDep,
) -> dict[str, str]:
    decision = service.evaluate_learning_policy(
        source_id=payload.source_id,
        content_sensitivity=payload.content_sensitivity,
        source_trust=payload.source_trust,
    )
    return {
        "level": decision.level,
        "action": decision.action,
        "reason": decision.reason,
    }


@router.post(
    "/validation/validate-transition",
    response_model=VerificationTransitionRead,
)
def validate_transition(
    payload: VerificationTransitionRequest,
    service: ValidationServiceDep,
) -> dict[str, Any]:
    allowed = service.validate_transition(
        current_state=payload.current_state,
        target_state=payload.target_state,
        state_type=payload.state_type,
    )
    return {
        "item_id": payload.item_id,
        "current_state": payload.current_state,
        "target_state": payload.target_state,
        "state_type": payload.state_type,
        "allowed": allowed,
    }


@router.get(
    "/validation/versions/{item_id}",
    response_model=list[VersionHistoryRead],
)
def get_versions(
    item_id: str,
    service: ValidationServiceDep,
) -> list[dict[str, Any]]:
    return service.get_version_history(item_id)


@router.get(
    "/validation/contradictions",
    response_model=list[GraphContradictionRead],
)
def get_contradictions(
    item_id: Annotated[str | None, Query(max_length=120)] = None,
    service: ValidationServiceDep = ...,
) -> list[dict[str, Any]]:
    return service.find_contradictions(item_id=item_id)


# =====================================================================
# Document Import from URL (M4.3)
# =====================================================================

def _is_private_or_local(host: str) -> bool:
    """Return True if the host is a private/localhost address (SSRF protection)."""
    try:
        import ipaddress

        # Try to parse as IP address directly
        try:
            ip = ipaddress.ip_address(host)
            return ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast
        except ValueError:
            pass

        # Resolve hostname to IP addresses
        import socket

        infos = socket.getaddrinfo(host, None)
        for info in infos:
            family = info[0]
            sockaddr = info[4]
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
                if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast:
                    return True
            except ValueError:
                continue
        return False
    except Exception:
        # If we can't resolve, treat as unsafe
        return True


@router.post(
    "/documents/import/url",
    response_model=DocumentImportResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_document_from_url(
    url: Annotated[str, Query(min_length=1, max_length=2000)],
    domain_id: Annotated[str | None, Query(max_length=120)] = None,
    skip_duplicate: Annotated[bool, Query()] = True,
    service: DocumentServiceDep = ...,
) -> dict[str, object]:
    """Import a document from a URL.

    Security measures:
    - Blocks localhost and private IP addresses (SSRF protection)
    - Resolves DNS and checks all resolved addresses
    - Limits download size and timeout
    - Validates content type
    - Does not execute page scripts
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="URL non valida",
        )

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solo URL http:// e https:// sono supportate",
        )

    host = parsed.hostname or ""
    if not host:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="URL senza host valido",
        )

    if _is_private_or_local(host):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accesso a indirizzi locali o privati non consentito (SSRF protection)",
        )

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "J.A.C.K. Knowledge Importer/1.0",
                "Accept": "text/html, application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, text/plain, text/markdown",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            # Check content type
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
            allowed_types = {
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "text/plain",
                "text/markdown",
                "text/html",
                "application/xhtml+xml",
            }
            if content_type and content_type not in allowed_types:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Tipo contenuto non supportato: {content_type}",
                )

            # Read with size limit
            max_size = 50 * 1024 * 1024  # 50 MB
            content = response.read(max_size + 1)
            if len(content) > max_size:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Documento troppo grande (massimo 50 MB)",
                )

    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Impossibile scaricare il documento: {error.reason}",
        )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Errore durante il download: {error}",
        )

    # Save to temporary file and import
    import tempfile

    with tempfile.NamedTemporaryFile(
        suffix=os.path.splitext(parsed.path)[1] or ".html", delete=False
    ) as tmp_file:
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    try:
        result = service.import_document(
            file_path=tmp_file_path,
            domain_id=domain_id,
            skip_duplicate=skip_duplicate,
        )
        return {
            "source_id": result.source_id,
            "document_title": result.document_title,
            "document_type": result.document_type,
            "chunks_created": result.chunks_created,
            "items_created": result.items_created,
            "content_hash": result.content_hash,
            "status": result.status,
        }
    finally:
        try:
            os.unlink(tmp_file_path)
        except OSError:
            pass


# =====================================================================
# Graph Extraction (M4.5)
# =====================================================================

@router.post(
    "/knowledge-graph/extract",
    response_model=GraphExtractionResponse,
)
def extract_knowledge_graph(
    payload: GraphExtractionRequest,
    extractor: GraphExtractorDep,
) -> dict[str, object]:
    """Estrae entità e relazioni da un testo usando il provider AI.

    Il risultato è una proposta: entità e relazioni vengono restituite come
    candidati. L'utente deve poi approvarle tramite gli endpoint
    /knowledge/items e /knowledge/links per crearle effettivamente.
    """
    result = extractor.extract(
        payload.text,
        max_entities=payload.max_entities,
        max_relations=payload.max_relations,
    )
    return {
        "entities": [
            {
                "id": e.title,
                "title": e.title,
                "description": e.description,
                "knowledge_type": e.knowledge_type,
                "confidence": e.confidence,
            }
            for e in result.entities
        ],
        "relations": [
            {
                "from_title": r.from_title,
                "to_title": r.to_title,
                "relation_type": r.relation_type,
                "strength": r.strength,
                "description": r.description,
                "confidence": r.confidence,
            }
            for r in result.relations
        ],
    }


@router.post(
    "/knowledge-graph/apply",
    response_model=GraphExtractionApplyResponse,
)
def apply_graph_extraction(
    payload: GraphExtractionApplyRequest,
    repository: Repository,
) -> dict[str, object]:
    """Applica entità e relazioni estratte come conoscenza reale.

    Crea knowledge_items per ogni entità e knowledge_links per ogni relazione.
    Gli item vengono creati come draft con verification_status='unverified'
    e richiedono approvazione esplicita prima di essere pubblicati.
    """
    created_item_ids: list[str] = []
    created_link_ids: list[str] = []
    title_to_id: dict[str, str] = {}

    # Create items first
    for item_payload in payload.items:
        created = repository.create_item(
            title=item_payload.title,
            content=item_payload.content,
            domain_id=item_payload.domain_id,
            knowledge_type=item_payload.knowledge_type,
            source_type=item_payload.source_type,
            tags=[],
            importance=item_payload.importance,
            excluded=False,
            verification_status=item_payload.verification_status,
            item_state="draft",
        )
        created_item_ids.append(created["id"])
        title_to_id[item_payload.title] = created["id"]

    # Create links
    created_link_ids_list: list[str] = []
    for link_payload in payload.links:
        from_id = title_to_id.get(link_payload.from_title)
        to_id = title_to_id.get(link_payload.to_title)
        if not from_id or not to_id:
            continue  # Skip links where either endpoint doesn't exist
        try:
            created_link = repository.create_link(
                from_id=from_id,
                to_id=to_id,
                relation_type=link_payload.relation_type,
                strength=link_payload.strength,
                description=link_payload.description,
            )
            created_link_ids_list.append(created_link["id"])
        except DuplicateMemoryLinkError:
            continue  # Skip duplicates
        except KnowledgeNotFoundError:
            continue  # Skip if items don't exist

    return {
        "items_created": len(created_item_ids),
        "links_created": len(created_link_ids_list),
        "item_ids": created_item_ids,
        "link_ids": created_link_ids_list,
    }
