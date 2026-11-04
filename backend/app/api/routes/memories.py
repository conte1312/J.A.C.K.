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
    MemoryRepository,
)

router = APIRouter(prefix="/memories", tags=["memories"])


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


@router.get("", response_model=list[MemoryRead])
def list_memories(
    repository: Repository,
    q: Annotated[str | None, Query(max_length=200)] = None,
    category: Annotated[str | None, Query(max_length=40)] = None,
    excluded: bool | None = None,
) -> list[dict[str, object]]:
    return repository.list(
        query=q,
        category=_category_filter(category),
        excluded=excluded,
    )


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


@router.get("/{memory_id}", response_model=MemoryRead)
def get_memory(memory_id: str, repository: Repository) -> dict[str, object]:
    memory = repository.get(memory_id)
    if memory is None:
        raise _memory_not_found()
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
        raise _memory_not_found()
    return memory


@router.put("/{memory_id}/exclusion", response_model=MemoryRead)
def set_memory_exclusion(
    memory_id: str,
    payload: MemoryExclusionWrite,
    repository: Repository,
) -> dict[str, object]:
    memory = repository.set_excluded(memory_id, payload.excluded)
    if memory is None:
        raise _memory_not_found()
    return memory


@router.put("/{memory_id}/last-used", response_model=MemoryRead)
def mark_memory_used(
    memory_id: str,
    repository: Repository,
) -> dict[str, object]:
    memory = repository.mark_used(memory_id)
    if memory is None:
        raise _memory_not_found()
    return memory


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(memory_id: str, repository: Repository) -> Response:
    if not repository.delete(memory_id):
        raise _memory_not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
