from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.api.schemas.memories import (
    MemoryExclusionWrite,
    MemoryGraphRead,
    MemoryLinkRead,
    MemoryLinkWrite,
    MemoryRead,
    MemoryWrite,
    normalize_category,
)
from app.memory.repository import (
    DuplicateMemoryLinkError,
    MemoryNotFoundError,
    MemoryProposalConflictError,
    MemoryRepository,
)

router = APIRouter(prefix="/memories", tags=["memories", "v2"])


def get_memory_repository(request: Request) -> MemoryRepository:
    return request.app.state.memory_repository


Repository = Annotated[MemoryRepository, Depends(get_memory_repository)]


def _category_filter(category: str | None) -> str | None:
    if category is None:
        return None
    try:
        return normalize_category(category)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid request data",
        ) from error


def _memory_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Memory not found",
    )


def _link_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Memory link not found",
    )


def _link_write_error(error: Exception) -> HTTPException:
    if isinstance(error, DuplicateMemoryLinkError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Equivalent memory link already exists",
        )
    return _memory_not_found()


# ---- V2: Graph ----

@router.get("/graph", response_model=MemoryGraphRead)
def get_memory_graph(
    repository: Repository,
    q: Annotated[str | None, Query(max_length=200)] = None,
    category: Annotated[str | None, Query(max_length=40)] = None,
    excluded: bool | None = None,
) -> dict[str, list[dict[str, object]]]:
    return repository.graph(
        query=q,
        category=_category_filter(category),
        excluded=excluded,
    )


# ---- V2: Links ----

@router.get("/links", response_model=list[MemoryLinkRead])
def list_memory_links(
    repository: Repository,
    memory_id: Annotated[str | None, Query(max_length=120)] = None,
) -> list[dict[str, object]]:
    return repository.list_links(memory_id=memory_id)


@router.post(
    "/links",
    response_model=MemoryLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def create_memory_link(
    payload: MemoryLinkWrite,
    repository: Repository,
) -> dict[str, object]:
    try:
        return repository.create_link(**payload.model_dump())
    except (DuplicateMemoryLinkError, MemoryNotFoundError) as error:
        raise _link_write_error(error) from error


@router.get("/links/{link_id}", response_model=MemoryLinkRead)
def get_memory_link(link_id: str, repository: Repository) -> dict[str, object]:
    link = repository.get_link(link_id)
    if link is None:
        raise _link_not_found()
    return link


@router.put("/links/{link_id}", response_model=MemoryLinkRead)
def update_memory_link(
    link_id: str,
    payload: MemoryLinkWrite,
    repository: Repository,
) -> dict[str, object]:
    try:
        link = repository.update_link(link_id, **payload.model_dump())
    except (DuplicateMemoryLinkError, MemoryNotFoundError) as error:
        raise _link_write_error(error) from error
    if link is None:
        raise _link_not_found()
    return link


@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory_link(link_id: str, repository: Repository) -> Response:
    if not repository.delete_link(link_id):
        raise _link_not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- V2: Memories CRUD with full filters ----

def _memory_not_found_v2() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Memory not found",
    )


@router.get("", response_model=list[MemoryRead])
def list_memories(
    repository: Repository,
    q: Annotated[str | None, Query(max_length=200)] = None,
    category: Annotated[str | None, Query(max_length=40)] = None,
    excluded: bool | None = None,
    provenance: Annotated[str | None, Query(max_length=40)] = None,
    verification: Annotated[str | None, Query(max_length=20)] = None,
    importance_min: Annotated[int | None, Query(ge=1, le=5)] = None,
    importance_max: Annotated[int | None, Query(ge=1, le=5)] = None,
    order_by: Annotated[str | None, Query()] = "updated_at",
    direction: Annotated[str | None, Query()] = "DESC",
    limit: Annotated[int | None, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict[str, object]]:
    valid_order = {"updated_at", "created_at", "importance"}
    order_col = order_by if order_by in valid_order else "updated_at"
    dir_lower = direction.upper() if direction else "DESC"
    if dir_lower not in ("ASC", "DESC"):
        dir_lower = "DESC"
    memories = repository.list(
        query=q,
        category=_category_filter(category),
        excluded=excluded,
    )
    if provenance:
        memories = [memory for memory in memories if memory["source_type"] == provenance]
    if verification:
        memories = [memory for memory in memories if memory["verification"] == verification]
    if importance_min is not None:
        memories = [
            memory for memory in memories
            if int(memory["importance"]) >= importance_min
        ]
    if importance_max is not None:
        memories = [
            memory for memory in memories
            if int(memory["importance"]) <= importance_max
        ]
    memories.sort(
        key=lambda memory: (
            memory[order_col],
            memory["created_at"],
            memory["id"],
        ),
        reverse=dir_lower == "DESC",
    )
    return memories[offset : offset + limit] if limit is not None else memories[offset:]


@router.post("", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
def create_memory(payload: MemoryWrite, repository: Repository) -> dict[str, object]:
    metadata = payload.model_dump(
        mode="json",
        exclude_unset=True,
        exclude={"title", "content", "category"},
    )
    return repository.create(
        title=payload.title,
        content=payload.content,
        category=payload.category.value,
        metadata=metadata,
    )


@router.get("/search", response_model=list[MemoryRead])
def search_memories(
    repository: Repository,
    q: Annotated[str, Query(max_length=200)],
    category: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int | None, Query(ge=1, le=500)] = 50,
) -> list[dict[str, object]]:
    memories = repository.list(query=q, category=_category_filter(category))
    return memories[:limit] if limit is not None else memories


@router.get("/audit", response_model=list[dict[str, object]])
def get_audit_log(
    repository: Repository,
    memory_id: Annotated[str | None, Query(max_length=120)] = None,
    action: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int | None, Query(ge=1, le=500)] = 100,
) -> list[dict[str, object]]:
    return repository.audit_log(memory_id=memory_id, action=action, limit=limit)


@router.post("/proposals", status_code=status.HTTP_201_CREATED)
def create_memory_proposal(
    payload: MemoryWrite,
    repository: Repository,
) -> dict[str, object]:
    return repository.create_proposal(
        title=payload.title,
        content=payload.content,
        category=payload.category.value,
        metadata=payload.model_dump(
            mode="json",
            exclude_unset=True,
            exclude={"title", "content", "category"},
        ),
    )


@router.get("/proposals")
def list_memory_proposals(
    repository: Repository,
    proposal_status: Annotated[
        str | None, Query(alias="status", pattern="^(pending|approved|rejected|expired)$")
    ] = None,
) -> list[dict[str, object]]:
    return repository.list_proposals(status=proposal_status)


@router.get("/proposals/{proposal_id}")
def get_memory_proposal(
    proposal_id: str,
    repository: Repository,
) -> dict[str, object]:
    proposal = repository.get_proposal(proposal_id)
    if proposal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory proposal not found",
        )
    return proposal


@router.post("/proposals/{proposal_id}/approve", response_model=MemoryRead)
def approve_memory_proposal(
    proposal_id: str,
    repository: Repository,
) -> dict[str, object]:
    try:
        memory = repository.approve_proposal(proposal_id)
    except MemoryProposalConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Memory proposal cannot be approved: {error}",
        ) from error
    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory proposal not found",
        )
    return memory


@router.post("/proposals/{proposal_id}/reject")
def reject_memory_proposal(
    proposal_id: str,
    repository: Repository,
) -> dict[str, object]:
    try:
        proposal = repository.reject_proposal(proposal_id)
    except MemoryProposalConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Memory proposal cannot be rejected: {error}",
        ) from error
    if proposal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory proposal not found",
        )
    return proposal


@router.get("/{memory_id}", response_model=MemoryRead)
def get_memory(memory_id: str, repository: Repository) -> dict[str, object]:
    memory = repository.get(memory_id)
    if memory is None:
        raise _memory_not_found_v2()
    return memory


@router.put("/{memory_id}", response_model=MemoryRead)
def update_memory(
    memory_id: str,
    payload: MemoryWrite,
    repository: Repository,
) -> dict[str, object]:
    metadata = payload.model_dump(
        mode="json",
        exclude_unset=True,
        exclude={"title", "content", "category"},
    )
    memory = repository.update(
        memory_id,
        title=payload.title,
        content=payload.content,
        category=payload.category.value,
        metadata=metadata,
    )
    if memory is None:
        raise _memory_not_found_v2()
    return memory


@router.put("/{memory_id}/exclusion", response_model=MemoryRead)
def set_memory_exclusion(
    memory_id: str,
    payload: MemoryExclusionWrite,
    repository: Repository,
) -> dict[str, object]:
    memory = repository.set_excluded(memory_id, payload.excluded)
    if memory is None:
        raise _memory_not_found_v2()
    return memory


@router.put("/{memory_id}/last-used", response_model=MemoryRead)
def mark_memory_used(
    memory_id: str,
    repository: Repository,
) -> dict[str, object]:
    memory = repository.mark_used(memory_id)
    if memory is None:
        raise _memory_not_found_v2()
    return memory


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(memory_id: str, repository: Repository) -> Response:
    if not repository.delete(memory_id):
        raise _memory_not_found_v2()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- V2: Filters ----

@router.get("/filter/category", response_model=list[MemoryRead])
def filter_memories_by_category(
    repository: Repository,
    category: Annotated[str, Query(max_length=40)],
    excluded: bool | None = None,
) -> list[dict[str, object]]:
    return repository.list(
        category=_category_filter(category),
        excluded=excluded,
    )


@router.get("/filter/verification", response_model=list[MemoryRead])
def filter_memories_by_verification(
    repository: Repository,
    verification: Annotated[str, Query(max_length=20)],
    category: Annotated[str | None, Query(max_length=40)] = None,
) -> list[dict[str, object]]:
    if verification not in {"verified", "to_verify", "inferred"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid request data",
        )
    memories = repository.list(category=_category_filter(category))
    return [
        memory for memory in memories if memory["verification"] == verification
    ]


@router.get("/filter/tag", response_model=list[MemoryRead])
def filter_memories_by_tag(
    repository: Repository,
    tag: Annotated[str, Query(max_length=64)],
    category: Annotated[str | None, Query(max_length=40)] = None,
) -> list[dict[str, object]]:
    memories = repository.list(category=_category_filter(category))
    normalized_tag = tag.casefold()
    return [
        memory
        for memory in memories
        if any(str(memory_tag).casefold() == normalized_tag for memory_tag in memory["tags"])
    ]


# ---- V2: Import/Export ----

@router.post("/import", response_model=list[MemoryRead])
def import_memories(
    repository: Repository,
    memories: list[MemoryWrite],
) -> list[dict[str, object]]:
    """Import multiple memories at once."""
    results: list[dict[str, object]] = []
    for payload in memories:
        try:
            created = repository.create(
                title=payload.title,
                content=payload.content,
                category=payload.category.value,
                metadata=payload.model_dump(
                    mode="json",
                    exclude_unset=True,
                    exclude={"title", "content", "category"},
                ),
            )
            results.append(created)
        except Exception as error:
            # Log but continue with others
            logger = __import__("logging").getLogger("jack.backend")
            logger.warning(f"Failed to import memory: {error}")
    return results