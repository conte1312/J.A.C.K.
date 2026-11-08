from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.control_plane.agent_catalog import (
    AgentProfileNotFoundError,
    get_agent_profile,
    list_agent_profiles,
)
from app.control_plane.repository import (
    DuplicateDeclarationError,
    IdentityNotFoundError,
)
from app.control_plane.schemas import (
    AgentProfileDetailRead,
    AgentProfileRead,
    AuditEventRead,
    CapabilityDeclaration,
    CapabilityRead,
    IdentityDeclaration,
    IdentityKindValue,
    IdentityRead,
)
from app.control_plane.service import ControlPlaneService

router = APIRouter(prefix="/control-plane", tags=["control-plane"])


def get_control_plane_service(request: Request) -> ControlPlaneService:
    return request.app.state.control_plane_service


Service = Annotated[ControlPlaneService, Depends(get_control_plane_service)]


@router.get("/agent-profiles", response_model=list[AgentProfileRead])
def list_declared_agent_profiles() -> list[dict[str, object]]:
    return list_agent_profiles()


@router.get(
    "/agent-profiles/{profile_id}",
    response_model=AgentProfileDetailRead,
)
def read_agent_profile(profile_id: str) -> dict[str, object]:
    try:
        return get_agent_profile(profile_id)
    except AgentProfileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Agent profile not found.") from error


@router.get("/identities", response_model=list[IdentityRead])
def list_identities(
    service: Service,
    kind: IdentityKindValue | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, object]]:
    return service.list_identities(kind=kind, limit=limit, offset=offset)


@router.post(
    "/identities",
    response_model=IdentityRead,
    status_code=status.HTTP_201_CREATED,
)
def declare_identity(
    payload: IdentityDeclaration, service: Service
) -> dict[str, object]:
    try:
        return service.declare_identity(payload.model_dump())
    except DuplicateDeclarationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/capabilities", response_model=list[CapabilityRead])
def list_capabilities(
    service: Service,
    owner_kind: IdentityKindValue | None = None,
    owner_id: str | None = Query(default=None, min_length=2, max_length=128),
    resource: str | None = Query(default=None, min_length=1, max_length=256),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, object]]:
    return service.list_capabilities(
        owner_kind=owner_kind,
        owner_id=owner_id,
        resource=resource,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/capabilities",
    response_model=CapabilityRead,
    status_code=status.HTTP_201_CREATED,
)
def declare_capability(
    payload: CapabilityDeclaration, service: Service
) -> dict[str, object]:
    try:
        return service.declare_capability(payload.model_dump())
    except IdentityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DuplicateDeclarationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/audit-events", response_model=list[AuditEventRead])
def list_audit_events(
    service: Service,
    subject_kind: IdentityKindValue | None = None,
    subject_id: str | None = Query(default=None, min_length=2, max_length=128),
    action: str | None = Query(default=None, min_length=2, max_length=128),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, object]]:
    return service.list_audit_events(
        subject_kind=subject_kind,
        subject_id=subject_id,
        action=action,
        limit=limit,
        offset=offset,
    )
