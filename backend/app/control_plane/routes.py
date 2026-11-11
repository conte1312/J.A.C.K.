from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.control_plane.agent_catalog import (
    AgentProfileNotFoundError,
    get_agent_profile,
    list_agent_profiles,
)
from app.control_plane.authorization import (
    ApprovalRequiredError,
    AuthorizationService,
    AuthenticationError,
    EmergencyStopActiveError,
    PermissionDeniedError,
)
from app.control_plane.repository import (
    DuplicateDeclarationError,
    IdentityNotFoundError,
)
from app.control_plane.schemas import (
    AgentAssignmentCreate,
    AgentAssignmentRead,
    AgentProfileDetailRead,
    AgentProfileRead,
    ApprovalRecordContract,
    AuditEventRead,
    AuthorizationDecisionContract,
    BackgroundTaskCreate,
    BackgroundTaskRead,
    BackgroundTaskStatusUpdate,
    CapabilityDeclaration,
    CapabilityRead,
    EmergencyStopStatusContract,
    IdentityDeclaration,
    IdentityKindValue,
    IdentityRead,
    PatchProposalCreate,
    PatchProposalRead,
    PermissionRequestContract,
    PreferenceGet,
    PreferenceList,
    PreferenceSet,
)
from app.control_plane.service import ControlPlaneService

router = APIRouter(prefix="/control-plane", tags=["control-plane"])


def get_control_plane_service(request: Request) -> ControlPlaneService:
    return request.app.state.control_plane_service


def get_authorization_service(request: Request) -> AuthorizationService:
    return request.app.state.authorization_service


Service = Annotated[ControlPlaneService, Depends(get_control_plane_service)]
Authorization = Annotated[
    AuthorizationService, Depends(get_authorization_service)
]


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


# ---------------------------------------------------------------------------
# Authorization (M5 Punto 2 — Control Plane e Sicurezza)
# ---------------------------------------------------------------------------


@router.post(
    "/authorize",
    response_model=dict[str, Any],
)
def authorize_operation(
    payload: PermissionRequestContract,
    authz: Authorization,
) -> dict[str, Any]:
    """Verifica se un'identità ha il permesso di eseguire un'operazione.

    Modello fail-closed: l'operazione è negata per default a meno che non
    esista una capability dichiarata che la consenta esplicitamente.
    """
    try:
        return authz.check_permission(
            requester_kind=payload.requester.kind,
            requester_id=payload.requester.id,
            resource=payload.resource,
            operation=payload.operation,
            risk_level=payload.risk_level,
        )
    except AuthenticationError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    except EmergencyStopActiveError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except PermissionDeniedError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ApprovalRequiredError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.post(
    "/emergency-stop/activate",
    response_model=EmergencyStopStatusContract,
)
def activate_emergency_stop(
    activated_by_kind: str = Query(..., min_length=1, max_length=32),
    activated_by_id: str = Query(..., min_length=2, max_length=128),
    reason: str = Query(default="security", min_length=1, max_length=2000),
    authz: Authorization = ...,
) -> dict[str, Any]:
    """Attiva l'emergency stop, bloccando tutte le operazioni."""
    try:
        result = authz.activate_emergency_stop(
            activated_by_kind=activated_by_kind,
            activated_by_id=activated_by_id,
            reason=reason,
        )
        return {
            "active": result["active"],
            "activated_at": result["activated_at"],
            "activated_by": {
                "kind": activated_by_kind,
                "id": activated_by_id,
            },
            "reason": result["reason"],
        }
    except AuthenticationError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error


@router.post(
    "/emergency-stop/deactivate",
    response_model=EmergencyStopStatusContract,
)
def deactivate_emergency_stop(
    deactivated_by_kind: str = Query(..., min_length=1, max_length=32),
    deactivated_by_id: str = Query(..., min_length=2, max_length=128),
    authz: Authorization = ...,
) -> dict[str, Any]:
    """Disattiva l'emergency stop, ripristinando le operazioni."""
    try:
        result = authz.deactivate_emergency_stop(
            deactivated_by_kind=deactivated_by_kind,
            deactivated_by_id=deactivated_by_id,
        )
        return {
            "active": result["active"],
            "activated_at": result["deactivated_at"],
            "activated_by": {
                "kind": deactivated_by_kind,
                "id": deactivated_by_id,
            },
            "reason": None,
        }
    except AuthenticationError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error


@router.get(
    "/emergency-stop/status",
    response_model=EmergencyStopStatusContract,
)
def read_emergency_stop_status(
    authz: Authorization = ...,
) -> dict[str, Any]:
    """Restituisce lo stato corrente dell'emergency stop."""
    return authz.get_emergency_stop_status()


@router.post(
    "/approvals",
    response_model=ApprovalRecordContract,
    status_code=status.HTTP_201_CREATED,
)
def record_approval(
    payload: ApprovalRecordContract,
    authz: Authorization = ...,
) -> dict[str, Any]:
    """Registra un'approvazione per un'operazione a rischio.

    Le approvazioni vengono consultate dal permission check per verificare
    che un'operazione a rischio sia stata esplicitamente approvata.
    """
    try:
        return authz.record_approval(
            approval_id=payload.id,
            request_id=payload.request_id,
            status=payload.status,
            requested_by_kind=payload.requested_by.kind,
            requested_by_id=payload.requested_by.id,
            resolved_by_kind=(
                payload.resolved_by.kind if payload.resolved_by else None
            ),
            resolved_by_id=(
                payload.resolved_by.id if payload.resolved_by else None
            ),
            expires_at=payload.expires_at,
        )
    except AuthenticationError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get(
    "/authorization-decisions",
    response_model=list[AuditEventRead],
)
def list_authorization_decisions(
    authz: Authorization = ...,
    actor_kind: IdentityKindValue | None = None,
    actor_id: str | None = Query(default=None, min_length=2, max_length=128),
    resource: str | None = Query(default=None, min_length=1, max_length=256),
    operation: str | None = Query(default=None, min_length=1, max_length=128),
    outcome: str | None = Query(default=None, min_length=1, max_length=32),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    """Restituisce le decisioni di autorizzazione registrate nell'audit."""
    return authz.list_authorization_decisions(
        actor_kind=actor_kind,
        actor_id=actor_id,
        resource=resource,
        operation=operation,
        outcome=outcome,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Agent-to-mission assignments (M5 Punto 3)
# ---------------------------------------------------------------------------

@router.post(
    "/agents/assign",
    response_model=AgentAssignmentRead,
    status_code=status.HTTP_201_CREATED,
)
def assign_agent(
    payload: AgentAssignmentCreate,
    service: Service,
) -> dict[str, Any]:
    """Assegna un agente operativo a una missione.

    Richiede che sia l'agente che l'assegnatario esistano come identità
    dichiarate nel Control Plane.
    """
    try:
        return service.assign_agent_to_mission(
            agent_kind=payload.agent_kind,
            agent_id=payload.agent_id,
            mission_id=payload.mission_id,
            assigned_by_kind=payload.assigned_by_kind,
            assigned_by_id=payload.assigned_by_id,
        )
    except IdentityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DuplicateDeclarationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete(
    "/agents/assign/{assignment_id}",
    response_model=AgentAssignmentRead,
)
def revoke_agent_assignment(
    assignment_id: str,
    revoked_by_kind: str = Query(..., min_length=1, max_length=32),
    revoked_by_id: str = Query(..., min_length=2, max_length=128),
    service: Service = ...,
) -> dict[str, Any]:
    """Revoca un'assegnazione agente-missione (imposta status 'revoked')."""
    try:
        result = service.revoke_agent_from_mission(
            assignment_id=assignment_id,
            revoked_by_kind=revoked_by_kind,
            revoked_by_id=revoked_by_id,
        )
        if result is None:
            raise HTTPException(
                status_code=404, detail="Assignment not found."
            )
        return result
    except IdentityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get(
    "/agents/assignments",
    response_model=list[AgentAssignmentRead],
)
def list_agent_assignments(
    service: Service,
    agent_kind: IdentityKindValue | None = None,
    agent_id: str | None = Query(default=None, min_length=2, max_length=128),
    mission_id: str | None = Query(default=None, min_length=2, max_length=128),
    status: str | None = Query(
        default=None, min_length=1, max_length=16, pattern="^(active|revoked)$"
    ),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    """Elenca le assegnazioni agente-missione con filtri opzionali."""
    return service.list_agent_assignments(
        agent_kind=agent_kind,
        agent_id=agent_id,
        mission_id=mission_id,
        status=status,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Background tasks (M5 Punto 4 — Execution Plane)
# ---------------------------------------------------------------------------

@router.post(
    "/background-tasks",
    response_model=BackgroundTaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_background_task(
    payload: BackgroundTaskCreate,
    service: Service,
) -> dict[str, Any]:
    """Crea un task in background in coda persistente.

    Il task viene inserito con status 'pending' e può essere eseguito
    da un worker esterno.
    """
    try:
        return service.create_background_task(
            task_type=payload.task_type,
            payload=payload.payload,
            timeout_seconds=payload.timeout_seconds,
            max_retries=payload.max_retries,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get(
    "/background-tasks",
    response_model=list[BackgroundTaskRead],
)
def list_background_tasks(
    service: Service,
    task_type: str | None = Query(default=None, min_length=1, max_length=128),
    status: str | None = Query(
        default=None,
        min_length=1,
        max_length=16,
        pattern="^(pending|running|completed|cancelled|failed)$",
    ),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    """Elenca task in background con filtri opzionali."""
    return service.list_background_tasks(
        task_type=task_type,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/background-tasks/{task_id}",
    response_model=BackgroundTaskRead,
)
def get_background_task(
    task_id: str,
    service: Service,
) -> dict[str, Any]:
    """Restituisce un task in background per ID."""
    try:
        result = service.get_background_task(task_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return result


@router.post(
    "/background-tasks/{task_id}/status",
    response_model=BackgroundTaskRead,
)
def update_background_task_status(
    task_id: str,
    payload: BackgroundTaskStatusUpdate,
    service: Service,
) -> dict[str, Any]:
    """Aggiorna lo status di un task in background."""
    try:
        result = service.update_background_task_status(
            task_id=task_id,
            status=payload.status,
            result=payload.result,
            error=payload.error,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return result


@router.post(
    "/background-tasks/{task_id}/cancel",
    response_model=BackgroundTaskRead,
)
def cancel_background_task(
    task_id: str,
    service: Service,
) -> dict[str, Any]:
    """Cancella un task in background se è ancora pending."""
    try:
        result = service.cancel_background_task(task_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return result


@router.get(
    "/background-tasks/overdue",
    response_model=list[BackgroundTaskRead],
)
def list_overdue_background_tasks(
    service: Service,
) -> list[dict[str, Any]]:
    """Restituisce task 'running' che hanno superato il timeout."""
    return service.list_overdue_tasks()


@router.post(
    "/background-tasks/{task_id}/retry",
    response_model=BackgroundTaskRead,
)
def increment_background_task_retry(
    task_id: str,
    service: Service,
) -> dict[str, Any]:
    """Incrementa il contatore di retry di un task."""
    try:
        result = service.increment_retry_count(task_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return result


# ---------------------------------------------------------------------------
# Evolution Lab patch proposals (M5 Punto 5)
# ---------------------------------------------------------------------------

@router.post(
    "/evolution/propose",
    response_model=PatchProposalRead,
    status_code=status.HTTP_201_CREATED,
)
def propose_patch(
    payload: PatchProposalCreate,
    service: Service,
) -> dict[str, Any]:
    """Propone una modifica al codice (patch) per revisione.

    La proposta NON viene applicata automaticamente. Richiede
    approvazione esplicita tramite POST /evolution/proposals/{id}/approve.
    """
    try:
        return service.create_patch_proposal(
            title=payload.title,
            description=payload.description,
            target_file=payload.target_file,
            patch_content=payload.patch_content,
            proposed_by_kind=payload.proposed_by_kind,
            proposed_by_id=payload.proposed_by_id,
        )
    except IdentityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get(
    "/evolution/proposals",
    response_model=list[PatchProposalRead],
)
def list_patch_proposals(
    service: Service,
    status: str | None = Query(
        default=None,
        min_length=1,
        max_length=16,
        pattern="^(pending|approved|rejected)$",
    ),
    proposed_by_kind: IdentityKindValue | None = None,
    proposed_by_id: str | None = Query(default=None, min_length=2, max_length=128),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    """Elenca le proposte di patch con filtri opzionali."""
    return service.list_patch_proposals(
        status=status,
        proposed_by_kind=proposed_by_kind,
        proposed_by_id=proposed_by_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/evolution/proposals/{proposal_id}",
    response_model=PatchProposalRead,
)
def get_patch_proposal(
    proposal_id: str,
    service: Service,
) -> dict[str, Any]:
    """Restituisce una proposta di patch per ID."""
    try:
        result = service.get_patch_proposal(proposal_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    return result


@router.post(
    "/evolution/proposals/{proposal_id}/approve",
    response_model=PatchProposalRead,
)
def approve_patch_proposal(
    proposal_id: str,
    reviewed_by_kind: str = Query(..., min_length=1, max_length=32),
    reviewed_by_id: str = Query(..., min_length=2, max_length=128),
    approval_reason: str = Query(..., min_length=1, max_length=2000),
    service: Service = ...,
) -> dict[str, Any]:
    """Approva una proposta di patch.

    L'approvazione NON applica il patch automaticamente. Registra
    solo la decisione di approvazione.
    """
    try:
        return service.approve_patch_proposal(
            proposal_id=proposal_id,
            reviewed_by_kind=reviewed_by_kind,
            reviewed_by_id=reviewed_by_id,
            approval_reason=approval_reason,
        )
    except IdentityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/evolution/proposals/{proposal_id}/reject",
    response_model=PatchProposalRead,
)
def reject_patch_proposal(
    proposal_id: str,
    reviewed_by_kind: str = Query(..., min_length=1, max_length=32),
    reviewed_by_id: str = Query(..., min_length=2, max_length=128),
    rejection_reason: str = Query(..., min_length=1, max_length=2000),
    service: Service = ...,
) -> dict[str, Any]:
    """Rifiuta una proposta di patch."""
    try:
        return service.reject_patch_proposal(
            proposal_id=proposal_id,
            reviewed_by_kind=reviewed_by_kind,
            reviewed_by_id=reviewed_by_id,
            rejection_reason=rejection_reason,
        )
    except IdentityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


# ---------------------------------------------------------------------------
# General preferences (M5 Punto 6 — Settings e Network Center)
# ---------------------------------------------------------------------------

@router.get(
    "/preferences/{key}",
    response_model=PreferenceGet,
)
def get_preference(
    key: str,
    service: Service,
) -> dict[str, Any]:
    """Restituisce una preferenza generale per chiave."""
    try:
        result = service.get_preference(key)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Preference not found.")
    return result


@router.put(
    "/preferences/{key}",
    response_model=PreferenceGet,
)
def set_preference(
    key: str,
    payload: PreferenceSet,
    service: Service,
) -> dict[str, Any]:
    """Imposta o aggiorna una preferenza generale."""
    try:
        return service.set_preference(
            key=key,
            value=payload.value,
            updated_by_kind="service",
            updated_by_id="control-plane-api",
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get(
    "/preferences",
    response_model=list[PreferenceGet],
)
def list_preferences(
    service: Service,
) -> list[dict[str, Any]]:
    """Elenca tutte le preferenze generali."""
    return service.list_preferences()
