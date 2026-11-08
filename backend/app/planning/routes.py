from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.api.dependencies import get_planning_service
from app.planning.models import TaskPriority, TaskStatus
from app.planning.schemas import (
    AiApplyRequest,
    AiInterpretRequest,
    EventCreate,
    EventUpdate,
    MilestoneCreate,
    MilestoneUpdate,
    MissionApprovalCreate,
    MissionApprovalUpdate,
    MissionCreate,
    MissionLogCreate,
    MissionUpdate,
    ProjectCreate,
    ProjectUpdate,
    TaskCreate,
    TaskUpdate,
)
from app.planning.service import PlanningService

router = APIRouter(prefix="/planning", tags=["planning"])

Service = Annotated[PlanningService, Depends(get_planning_service)]


# ------------------------------------------------------------------ tasks

@router.get("/tasks")
def list_tasks(
    service: Service,
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    mission_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    overdue_only: bool = Query(False),
    due_before: Optional[str] = Query(None),
    due_after: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    sort: str = Query("created", pattern="^(created|due_date|priority|title)$"),
    descending: bool = Query(False),
    limit: Optional[int] = Query(None, ge=1),
    offset: Optional[int] = Query(None, ge=0),
):
    filters: dict[str, object] = {}
    if status is not None:
        if status not in TaskStatus.values():
            raise HTTPException(status_code=422, detail=f"Stato non valido: {status}")
        filters["status"] = status
    if priority is not None:
        if priority not in TaskPriority.values():
            raise HTTPException(status_code=422, detail=f"Priorità non valida: {priority}")
        filters["priority"] = priority
    if project_id is not None:
        filters["project_id"] = project_id
    if mission_id is not None:
        filters["mission_id"] = mission_id
    if category is not None:
        filters["category"] = category
    filters["overdue_only"] = overdue_only
    if due_before is not None:
        filters["due_before"] = due_before
    if due_after is not None:
        filters["due_after"] = due_after
    if query is not None:
        filters["query"] = query
    if tag is not None:
        filters["tag"] = tag
    filters["sort"] = sort
    filters["descending"] = descending
    if limit is not None:
        filters["limit"] = limit
    if offset is not None:
        filters["offset"] = offset
    try:
        return service.list_tasks(filters)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, service: Service):
    try:
        return service.create_task(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/tasks/{task_id}")
def get_task(task_id: str, service: Service):
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task non trovato.")
    return task


@router.put("/tasks/{task_id}")
def update_task(task_id: str, payload: TaskUpdate, service: Service):
    try:
        updated = service.update_task(task_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Task non trovato.")
    return updated


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, service: Service):
    if not service.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task non trovato.")


@router.post("/tasks/{task_id}/complete")
def complete_task(task_id: str, service: Service):
    try:
        return service.complete_task(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Task non trovato.")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/reopen")
def reopen_task(task_id: str, service: Service):
    task = service.reopen_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task non trovato.")
    return task


@router.get("/tasks/{task_id}/can-complete")
def can_complete(task_id: str, service: Service):
    allowed, message = service.can_complete(task_id)
    if message is None and not allowed:
        raise HTTPException(status_code=404, detail="Task non trovato.")
    return {"allowed": allowed, "message": message}


# ------------------------------------------------------------ checklist

@router.post("/tasks/{task_id}/checklist", status_code=status.HTTP_201_CREATED)
def add_checklist_item(task_id: str, payload: dict, service: Service):
    title = payload.get("title")
    position = int(payload.get("position", 0))
    try:
        return service.add_checklist_item(task_id, title, position)
    except KeyError:
        raise HTTPException(status_code=404, detail="Task non trovato.")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/checklist/{item_id}")
def update_checklist_item(item_id: str, payload: dict, service: Service):
    updated = service.update_checklist_item(item_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="Elemento checklist non trovato.")
    return updated


@router.delete("/checklist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_checklist_item(item_id: str, service: Service):
    if not service.delete_checklist_item(item_id):
        raise HTTPException(status_code=404, detail="Elemento checklist non trovato.")


# -------------------------------------------------------- dependencies

@router.get("/tasks/{task_id}/dependencies")
def list_dependencies(task_id: str, service: Service):
    return service.list_dependencies_for_task(task_id)


@router.get("/tasks/{task_id}/dependents")
def list_dependents(task_id: str, service: Service):
    return service.list_dependents_of_task(task_id)


@router.post("/tasks/{task_id}/dependencies", status_code=status.HTTP_201_CREATED)
def add_dependency(task_id: str, payload: dict, service: Service):
    depends_on = payload.get("depends_on_task_id")
    if not depends_on:
        raise HTTPException(status_code=422, detail="depends_on_task_id obbligatorio.")
    try:
        return service.add_dependency(task_id, depends_on)
    except KeyError:
        raise HTTPException(status_code=404, detail="Task non trovato.")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/dependencies/{dependency_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_dependency(dependency_id: str, service: Service):
    if not service.remove_dependency(dependency_id):
        raise HTTPException(status_code=404, detail="Dipendenza non trovata.")


# ---------------------------------------------------------- recurrences

@router.post("/recurrences/generate")
def generate_recurrences(service: Service):
    created = service.generate_recurrence_instances()
    return {"created": created, "count": len(created)}


# ----------------------------------------------------------------- projects

@router.get("/projects")
def list_projects(
    service: Service,
    include_archived: bool = Query(False),
    query: Optional[str] = Query(None),
):
    return service.list_projects(include_archived=include_archived, query=query)


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, service: Service):
    try:
        return service.create_project(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/projects/{project_id}")
def get_project(project_id: str, service: Service):
    project = service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Progetto non trovato.")
    return project


@router.put("/projects/{project_id}")
def update_project(project_id: str, payload: ProjectUpdate, service: Service):
    try:
        updated = service.update_project(
            project_id, payload.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Progetto non trovato.")
    return updated


@router.post("/projects/{project_id}/archive")
def archive_project(project_id: str, service: Service):
    archived = service.archive_project(project_id)
    if archived is None:
        raise HTTPException(status_code=404, detail="Progetto non trovato.")
    return archived


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, service: Service):
    if not service.delete_project(project_id):
        raise HTTPException(status_code=404, detail="Progetto non trovato.")


# ----------------------------------------------------------- project milestones

@router.get("/projects/{project_id}/milestones")
def list_milestones(project_id: str, service: Service):
    try:
        return service.list_milestones(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Progetto non trovato.") from exc


@router.post(
    "/projects/{project_id}/milestones",
    status_code=status.HTTP_201_CREATED,
)
def create_milestone(
    project_id: str, payload: MilestoneCreate, service: Service
):
    try:
        return service.create_milestone(project_id, payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Progetto non trovato.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/milestones/{milestone_id}")
def update_milestone(
    milestone_id: str, payload: MilestoneUpdate, service: Service
):
    try:
        milestone = service.update_milestone(
            milestone_id, payload.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone non trovata.")
    return milestone


@router.delete("/milestones/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_milestone(milestone_id: str, service: Service):
    if not service.delete_milestone(milestone_id):
        raise HTTPException(status_code=404, detail="Milestone non trovata.")


# ------------------------------------------------------------------- calendar

@router.get("/calendar")
def get_calendar(
    service: Service,
    from_date: date = Query(...),
    to_date: date = Query(...),
    timezone_name: str = Query("UTC", alias="timezone"),
    project_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
):
    if to_date < from_date:
        raise HTTPException(status_code=422, detail="Intervallo calendario non valido.")
    try:
        service._validate_timezone(timezone_name)
        zone = ZoneInfo(timezone_name)
        start = datetime.combine(from_date, time.min, tzinfo=zone).isoformat()
        end = datetime.combine(
            to_date + timedelta(days=1), time.min, tzinfo=zone
        ).isoformat()
        tasks = service.list_tasks(
            {
                "due_after": from_date.isoformat(),
                "due_before": to_date.isoformat(),
                "project_id": project_id,
                "priority": priority,
                "sort": "due_date",
            }
        )
        events = service.list_events(
            {
                "starts_at": start,
                "ends_at": end,
                "timezone": timezone_name,
                "project_id": project_id,
                "priority": priority,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"tasks": tasks, "events": events, "timezone": timezone_name}


@router.get("/calendar/events")
def list_events(
    service: Service,
    starts_at: Optional[str] = Query(None),
    ends_at: Optional[str] = Query(None),
    timezone_name: str = Query("UTC", alias="timezone"),
    project_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
):
    try:
        return service.list_events(
            {
                "starts_at": starts_at,
                "ends_at": ends_at,
                "timezone": timezone_name,
                "project_id": project_id,
                "priority": priority,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/calendar/events", status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, service: Service):
    try:
        return service.create_event(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/calendar/events/{event_id}")
def get_event(event_id: str, service: Service):
    event = service.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Evento non trovato.")
    return event


@router.put("/calendar/events/{event_id}")
def update_event(event_id: str, payload: EventUpdate, service: Service):
    try:
        event = service.update_event(
            event_id, payload.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=404, detail="Evento non trovato.")
    return event


@router.delete("/calendar/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: str, service: Service):
    if not service.delete_event(event_id):
        raise HTTPException(status_code=404, detail="Evento non trovato.")


# ------------------------------------------------------------------ missions

@router.get("/missions")
def list_missions(service: Service, status: Optional[str] = Query(None)):
    return service.list_missions(status=status)


@router.post("/missions", status_code=status.HTTP_201_CREATED)
def create_mission(payload: MissionCreate, service: Service):
    try:
        return service.create_mission(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/missions/{mission_id}")
def get_mission(mission_id: str, service: Service):
    mission = service.get_mission(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Missione non trovata.")
    return mission


@router.put("/missions/{mission_id}")
def update_mission(mission_id: str, payload: MissionUpdate, service: Service):
    try:
        updated = service.update_mission(
            mission_id, payload.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Missione non trovata.")
    return updated


@router.delete("/missions/{mission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mission(mission_id: str, service: Service):
    if not service.delete_mission(mission_id):
        raise HTTPException(status_code=404, detail="Missione non trovata.")


@router.post(
    "/missions/{mission_id}/logs", status_code=status.HTTP_201_CREATED
)
def add_mission_log(
    mission_id: str, payload: MissionLogCreate, service: Service
):
    try:
        return service.add_mission_log(mission_id, payload.message)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Missione non trovata.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/missions/{mission_id}/approvals", status_code=status.HTTP_201_CREATED
)
def create_mission_approval(
    mission_id: str, payload: MissionApprovalCreate, service: Service
):
    try:
        return service.create_mission_approval(mission_id, payload.description)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Missione non trovata.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/mission-approvals/{approval_id}")
def update_mission_approval(
    approval_id: str, payload: MissionApprovalUpdate, service: Service
):
    try:
        approval = service.update_mission_approval(approval_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if approval is None:
        raise HTTPException(status_code=404, detail="Approvazione non trovata.")
    return approval


# ------------------------------------------------------------ AI bridge

@router.post("/ai/interpret")
def ai_interpret(payload: AiInterpretRequest, service: Service):
    return service.interpret_ai_request(payload.text)


@router.post("/ai/apply")
def ai_apply(payload: AiApplyRequest, service: Service):
    try:
        return service.apply_confirmed_operations(
            payload.proposal_id, confirmed=payload.confirmed
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
