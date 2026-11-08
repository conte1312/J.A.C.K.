from __future__ import annotations

"""Logica di business del motore di pianificazione di J.A.C.K.

Espone operazioni strutturate e validate. Nessuna scrittura avviene
direttamente dal modello AI: il service è l'unico punto di modifica.
"""

import logging
import calendar
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.planning.models import (
    RecurrenceKind,
    Task,
    TaskPriority,
    TaskStatus,
    _new_id,
    _now,
)
from app.planning.repository import PlanningRepository

logger = logging.getLogger("jack.backend.planning")

MAX_INTERPRETATION_TASKS = 20
AI_PROPOSAL_TTL = timedelta(minutes=10)


class PlanningService:
    def __init__(self, repository: PlanningRepository) -> None:
        self._repository = repository

    # --------------------------------------------------------------- tasks

    def create_task(self, draft: dict[str, Any]) -> dict[str, Any]:
        if not str(draft.get("title", "")).strip():
            raise ValueError("Il titolo del task è obbligatorio.")
        status = str(draft.get("status", TaskStatus.INBOX.value))
        if status not in TaskStatus.values():
            raise ValueError(f"Stato non valido: {status}")
        if status == TaskStatus.COMPLETED.value:
            raise ValueError("Completa il task dopo averne creato le dipendenze.")
        priority = str(draft.get("priority", TaskPriority.NORMAL.value))
        if priority not in TaskPriority.values():
            raise ValueError(f"Priorità non valida: {priority}")
        if draft.get("due_date") and not self._is_valid_date(draft["due_date"]):
            raise ValueError("Data di scadenza non valida.")
        if draft.get("start_date") and not self._is_valid_date(draft["start_date"]):
            raise ValueError("Data di inizio non valida.")
        if (
            draft.get("due_date")
            and draft.get("start_date")
            and draft["due_date"] < draft["start_date"]
        ):
            raise ValueError("La scadenza non può precedere la data di inizio.")
        recurrence_kind = str(
            draft.get("recurrence_kind", RecurrenceKind.NONE.value)
        )
        if recurrence_kind not in {item.value for item in RecurrenceKind}:
            raise ValueError("Ricorrenza task non valida.")
        self._validate_interval(draft.get("recurrence_interval", 1))
        self._validate_project_reference(draft.get("project_id"))
        self._validate_mission_reference(draft.get("mission_id"))
        return self._repository.create_task(draft)

    def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        return self._repository.get_task(task_id)

    def list_tasks(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        if filters.get("status") is not None and filters["status"] not in TaskStatus.values():
            raise ValueError("Stato task non valido.")
        if filters.get("priority") is not None and filters["priority"] not in TaskPriority.values():
            raise ValueError("Priorità task non valida.")
        for field in ("due_before", "due_after"):
            if filters.get(field) is not None and not self._is_valid_date(filters[field]):
                raise ValueError("Filtro data task non valido.")
        if filters.get("sort", "created") not in {"created", "due_date", "priority", "title"}:
            raise ValueError("Ordinamento task non valido.")
        if filters.get("query") is not None and len(filters["query"]) > 200:
            raise ValueError("Testo di ricerca troppo lungo.")
        return self._repository.list_tasks(**filters)

    def update_task(self, task_id: str, patch: dict[str, Any]) -> Optional[dict[str, Any]]:
        if "status" in patch and patch["status"] not in TaskStatus.values():
            raise ValueError(f"Stato non valido: {patch['status']}")
        if "priority" in patch and patch["priority"] not in TaskPriority.values():
            raise ValueError(f"Priorità non valida: {patch['priority']}")
        if patch.get("status") == TaskStatus.COMPLETED.value:
            raise ValueError("Usa l'operazione completa per verificare le dipendenze.")
        if "title" in patch and not str(patch["title"]).strip():
            raise ValueError("Il titolo del task è obbligatorio.")
        if "due_date" in patch and patch["due_date"] is not None and not self._is_valid_date(patch["due_date"]):
            raise ValueError("Data di scadenza non valida.")
        if "start_date" in patch and patch["start_date"] is not None and not self._is_valid_date(patch["start_date"]):
            raise ValueError("Data di inizio non valida.")
        existing = self._repository.get_task(task_id)
        if existing is None:
            return None
        due_date = patch.get("due_date", existing.get("due_date"))
        start_date = patch.get("start_date", existing.get("start_date"))
        if due_date and start_date and due_date < start_date:
            raise ValueError("La scadenza non può precedere la data di inizio.")
        if "recurrence_kind" in patch and patch["recurrence_kind"] not in {
            item.value for item in RecurrenceKind
        }:
            raise ValueError("Ricorrenza task non valida.")
        if "recurrence_interval" in patch:
            self._validate_interval(patch["recurrence_interval"])
        if "project_id" in patch:
            self._validate_project_reference(patch["project_id"])
        if "mission_id" in patch:
            self._validate_mission_reference(patch["mission_id"])
        return self._repository.update_task(task_id, patch)

    def delete_task(self, task_id: str) -> bool:
        return self._repository.delete_task(task_id)

    def complete_task(self, task_id: str) -> dict[str, Any]:
        task = self._repository.complete_task(task_id)
        if task.get("recurrence_kind") != RecurrenceKind.NONE.value:
            self.generate_recurrence_instances()
        return task

    def reopen_task(self, task_id: str) -> Optional[dict[str, Any]]:
        return self._repository.reopen_task(task_id)

    # ----------------------------------------------------------- checklist

    def add_checklist_item(
        self, task_id: str, title: str, position: int = 0
    ) -> dict[str, Any]:
        if not title.strip():
            raise ValueError("Il titolo dell'elemento checklist è obbligatorio.")
        return self._repository.add_checklist_item(task_id, title, position)

    def update_checklist_item(
        self, item_id: str, patch: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        return self._repository.update_checklist_item(item_id, patch)

    def delete_checklist_item(self, item_id: str) -> bool:
        return self._repository.delete_checklist_item(item_id)

    # ---------------------------------------------------------- dependencies

    def add_dependency(
        self, task_id: str, depends_on_task_id: str
    ) -> dict[str, Any]:
        return self._repository.add_dependency(task_id, depends_on_task_id)

    def remove_dependency(self, dependency_id: str) -> bool:
        return self._repository.remove_dependency(dependency_id)

    def list_dependencies_for_task(
        self, task_id: str
    ) -> list[dict[str, Any]]:
        return self._repository.list_dependencies_for_task(task_id)

    def list_dependents_of_task(
        self, task_id: str
    ) -> list[dict[str, Any]]:
        return self._repository.list_dependents_of_task(task_id)

    def can_complete(self, task_id: str) -> tuple[bool, Optional[str]]:
        """Restituisce (può_completare, messaggio_di_blocco)."""
        task = self._repository.get_task(task_id)
        if task is None:
            return False, "Task non trovato."
        if task["status"] == TaskStatus.COMPLETED.value:
            return True, None
        for dep in self._repository.list_dependencies_for_task(task_id):
            prerequisite = self._repository.get_task(dep["depends_on_task_id"])
            if prerequisite is None:
                return False, f"Prerequisito “{dep['depends_on_task_id']}” non trovato."
            if prerequisite["status"] != TaskStatus.COMPLETED.value:
                return (
                    False,
                    f"Impossibile completare: “{prerequisite['title']}” non è ancora completato.",
                )
        return True, None

    # ------------------------------------------------------------- projects

    def create_project(self, draft: dict[str, Any]) -> dict[str, Any]:
        if not str(draft.get("name", "")).strip():
            raise ValueError("Il nome del progetto è obbligatorio.")
        if draft.get("priority", TaskPriority.NORMAL.value) not in TaskPriority.values():
            raise ValueError("Priorità progetto non valida.")
        if draft.get("status", "active") not in {
            "active", "on_hold", "completed", "archived"
        }:
            raise ValueError("Stato progetto non valido.")
        if draft.get("due_date") and not self._is_valid_date(draft["due_date"]):
            raise ValueError("Data di scadenza progetto non valida.")
        if draft.get("start_date") and not self._is_valid_date(draft["start_date"]):
            raise ValueError("Data di inizio progetto non valida.")
        if (
            draft.get("due_date")
            and draft.get("start_date")
            and draft["due_date"] < draft["start_date"]
        ):
            raise ValueError("La scadenza non può precedere la data di inizio.")
        return self._repository.create_project(draft)

    def get_project(self, project_id: str) -> Optional[dict[str, Any]]:
        return self._repository.get_project(project_id)

    def list_projects(
        self, *, include_archived: bool = False, query: Optional[str] = None
    ) -> list[dict[str, Any]]:
        return self._repository.list_projects(
            include_archived=include_archived, query=query
        )

    def update_project(
        self, project_id: str, patch: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        if "name" in patch and not str(patch["name"]).strip():
            raise ValueError("Il nome del progetto è obbligatorio.")
        if "priority" in patch and patch["priority"] not in TaskPriority.values():
            raise ValueError("Priorità progetto non valida.")
        if "status" in patch and patch["status"] not in {
            "active", "on_hold", "completed", "archived"
        }:
            raise ValueError("Stato progetto non valido.")
        if "due_date" in patch and patch["due_date"] is not None and not self._is_valid_date(patch["due_date"]):
            raise ValueError("Data di scadenza progetto non valida.")
        if "start_date" in patch and patch["start_date"] is not None and not self._is_valid_date(patch["start_date"]):
            raise ValueError("Data di inizio progetto non valida.")
        existing = self._repository.get_project(project_id)
        if existing is None:
            return None
        due_date = patch.get("due_date", existing.get("due_date"))
        start_date = patch.get("start_date", existing.get("start_date"))
        if due_date and start_date and due_date < start_date:
            raise ValueError("La scadenza non può precedere la data di inizio.")
        return self._repository.update_project(project_id, patch)

    def archive_project(self, project_id: str) -> Optional[dict[str, Any]]:
        return self._repository.archive_project(project_id)

    def delete_project(self, project_id: str) -> bool:
        return self._repository.delete_project(project_id)

    def create_milestone(
        self, project_id: str, draft: dict[str, Any]
    ) -> dict[str, Any]:
        if not str(draft.get("title", "")).strip():
            raise ValueError("Il titolo della milestone è obbligatorio.")
        if draft.get("due_date") and not self._is_valid_date(draft["due_date"]):
            raise ValueError("Data milestone non valida.")
        return self._repository.create_milestone(project_id, draft)

    def list_milestones(self, project_id: str) -> list[dict[str, Any]]:
        if self._repository.get_project(project_id) is None:
            raise KeyError(f"Progetto {project_id} non trovato.")
        return self._repository.list_milestones(project_id)

    def update_milestone(
        self, milestone_id: str, patch: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        if "title" in patch and not str(patch["title"]).strip():
            raise ValueError("Il titolo della milestone è obbligatorio.")
        if patch.get("due_date") and not self._is_valid_date(patch["due_date"]):
            raise ValueError("Data milestone non valida.")
        if patch.get("completed_at"):
            self._validate_datetime(patch["completed_at"])
        return self._repository.update_milestone(milestone_id, patch)

    def delete_milestone(self, milestone_id: str) -> bool:
        return self._repository.delete_milestone(milestone_id)

    def create_event(self, draft: dict[str, Any]) -> dict[str, Any]:
        if not str(draft.get("title", "")).strip():
            raise ValueError("Il titolo dell'evento è obbligatorio.")
        if draft.get("priority", TaskPriority.NORMAL.value) not in TaskPriority.values():
            raise ValueError("Priorità evento non valida.")
        if draft.get("recurrence_kind", RecurrenceKind.NONE.value) not in {
            item.value for item in RecurrenceKind
        }:
            raise ValueError("Ricorrenza evento non valida.")
        self._validate_interval(draft.get("recurrence_interval", 1))
        timezone_name = str(draft.get("timezone", ""))
        self._validate_timezone(timezone_name)
        starts_at = self._normalize_datetime(draft.get("starts_at", ""), timezone_name)
        ends_at = self._normalize_datetime(draft.get("ends_at", ""), timezone_name)
        if ends_at <= starts_at:
            raise ValueError("La fine dell'evento deve essere successiva all'inizio.")
        recurrence_until = draft.get("recurrence_until")
        if recurrence_until:
            self._validate_date(recurrence_until, "Fine ricorrenza non valida.")
        self._validate_project_reference(draft.get("project_id"))
        return self._repository.create_event(
            {
                **draft,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "timezone": timezone_name,
            }
        )

    def get_event(self, event_id: str) -> Optional[dict[str, Any]]:
        return self._repository.get_event(event_id)

    def list_events(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        if filters.get("timezone"):
            self._validate_timezone(filters["timezone"])
        if filters.get("project_id"):
            self._validate_project_reference(filters["project_id"])
        if filters.get("priority") and filters["priority"] not in TaskPriority.values():
            raise ValueError("Priorità evento non valida.")
        start = self._normalize_datetime(
            filters["starts_at"], filters.get("timezone", "UTC")
        ) if filters.get("starts_at") else None
        end = self._normalize_datetime(
            filters["ends_at"], filters.get("timezone", "UTC")
        ) if filters.get("ends_at") else None
        if start and end and end < start:
            raise ValueError("L'intervallo calendario non è valido.")
        events = self._repository.list_events(
            starts_at=start,
            ends_at=end,
            project_id=filters.get("project_id"),
            priority=filters.get("priority"),
        )
        if not start or not end:
            return events
        return self._expand_event_recurrences(events, start, end)

    def update_event(
        self, event_id: str, patch: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        existing = self._repository.get_event(event_id)
        if existing is None:
            return None
        merged = {**existing, **patch}
        if "title" in patch and not str(patch["title"]).strip():
            raise ValueError("Il titolo dell'evento è obbligatorio.")
        if merged["priority"] not in TaskPriority.values():
            raise ValueError("Priorità evento non valida.")
        if merged["recurrence_kind"] not in {item.value for item in RecurrenceKind}:
            raise ValueError("Ricorrenza evento non valida.")
        self._validate_interval(merged["recurrence_interval"])
        if merged.get("recurrence_until"):
            self._validate_date(
                merged["recurrence_until"], "Fine ricorrenza non valida."
            )
        timezone_name = str(merged["timezone"])
        self._validate_timezone(timezone_name)
        starts_at = self._normalize_datetime(merged["starts_at"], timezone_name)
        ends_at = self._normalize_datetime(merged["ends_at"], timezone_name)
        if ends_at <= starts_at:
            raise ValueError("La fine dell'evento deve essere successiva all'inizio.")
        self._validate_project_reference(merged.get("project_id"))
        normalized_patch = {
            **patch,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "timezone": timezone_name,
        }
        return self._repository.update_event(event_id, normalized_patch)

    def delete_event(self, event_id: str) -> bool:
        return self._repository.delete_event(event_id)

    def get_default_timezone(self) -> str:
        return self._repository.get_default_timezone()

    def set_default_timezone(self, timezone_name: str) -> str:
        self._validate_timezone(timezone_name)
        return self._repository.set_default_timezone(timezone_name)

    # -------------------------------------------------------------- missions

    def create_mission(self, draft: dict[str, Any]) -> dict[str, Any]:
        if not str(draft.get("title", "")).strip():
            raise ValueError("L'obiettivo della missione è obbligatorio.")
        if draft.get("status", "planned") not in {
            "planned", "pending_approval", "approved", "cancelled"
        }:
            raise ValueError("Stato missione non valido per la fase corrente.")
        return self._repository.create_mission(draft)

    def get_mission(self, mission_id: str) -> Optional[dict[str, Any]]:
        return self._repository.get_mission(mission_id)

    def list_missions(self, *, status: Optional[str] = None) -> list[dict[str, Any]]:
        return self._repository.list_missions(status=status)

    def update_mission(
        self, mission_id: str, patch: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        if "title" in patch and not str(patch["title"]).strip():
            raise ValueError("L'obiettivo della missione è obbligatorio.")
        if "status" in patch and patch["status"] not in {
            "planned", "pending_approval", "approved", "cancelled"
        }:
            raise ValueError("Stato missione non valido per la fase corrente.")
        if "assigned_agents" in patch and (
            not isinstance(patch["assigned_agents"], list)
            or any(not isinstance(agent, str) or not agent.strip()
                   for agent in patch["assigned_agents"])
        ):
            raise ValueError("Elenco agenti assegnati non valido.")
        return self._repository.update_mission(mission_id, patch)

    def delete_mission(self, mission_id: str) -> bool:
        return self._repository.delete_mission(mission_id)

    def add_mission_log(self, mission_id: str, message: str) -> dict[str, Any]:
        if self._repository.get_mission(mission_id) is None:
            raise KeyError(f"Missione {mission_id} non trovata.")
        if not message.strip():
            raise ValueError("Il messaggio del log è obbligatorio.")
        return self._repository.add_mission_log(mission_id, message.strip())

    def create_mission_approval(
        self, mission_id: str, description: str
    ) -> dict[str, Any]:
        if self._repository.get_mission(mission_id) is None:
            raise KeyError(f"Missione {mission_id} non trovata.")
        if not description.strip():
            raise ValueError("La descrizione dell'approvazione è obbligatoria.")
        return self._repository.create_mission_approval(
            mission_id, description.strip()
        )

    def update_mission_approval(
        self, approval_id: str, approval_status: str
    ) -> Optional[dict[str, Any]]:
        if approval_status not in {"approved", "rejected", "pending"}:
            raise ValueError("Stato approvazione non valido.")
        return self._repository.update_mission_approval(
            approval_id, approval_status
        )

    # ---------------------------------------------------------- recurrences

    def generate_recurrence_instances(
        self, today: date | None = None
    ) -> list[dict[str, Any]]:
        """Genera le prossime istanze per i task ricorrenti scaduti.

        Viene invocato periodicamente (es. all'avvio o su richiesta) per
        assicurare che ogni task ricorrente abbia un'istanza attiva.
        """
        created: list[dict[str, Any]] = []
        tasks = self._repository.list_tasks()
        current_date = today or date.today()
        today_iso = current_date.isoformat()

        for task in tasks:
            kind = task.get("recurrence_kind")
            if kind == RecurrenceKind.NONE.value:
                continue
            if task.get("status") == TaskStatus.CANCELLED.value:
                continue

            due = task.get("due_date")
            if not due:
                continue

            # Se l'ultima istanza è completata e la scadenza è passata,
            # genera la prossima.
            is_completed = task.get("status") == TaskStatus.COMPLETED.value
            overdue = due < today_iso

            if not is_completed and not overdue:
                continue

            interval = int(task.get("recurrence_interval", 1))
            next_due = self._next_occurrence_after(
                due, kind, interval, current_date
            )
            if not next_due:
                continue

            series_id = task.get("recurrence_series_id") or task["id"]
            if self._repository.has_recurrence_instance(series_id, next_due):
                continue

            draft = {
                "title": task["title"],
                "description": task.get("description", ""),
                "status": TaskStatus.TODO.value,
                "priority": task.get("priority", TaskPriority.NORMAL.value),
                "category": task.get("category", ""),
                "tags": list(task.get("tags") or []),
                "project_id": task.get("project_id"),
                "mission_id": task.get("mission_id"),
                "recurrence_kind": kind,
                "recurrence_interval": interval,
                "recurrence_series_id": series_id,
                "ai_origin": bool(task.get("ai_origin", 0)),
                "responsible_agent": task.get("responsible_agent"),
                "notes": task.get("notes", ""),
                "due_date": next_due,
                "start_date": next_due,
            }
            try:
                created.append(self.create_task(draft))
            except sqlite3.IntegrityError as error:
                if "tasks.recurrence_series_id, tasks.due_date" not in str(error):
                    raise
            except ValueError:
                logger.warning("Impossibile creare istanza ricorrente per %s", task["id"])
        return created

    def _next_occurrence_after(
        self, due: str, kind: str, interval: int, today: date
    ) -> Optional[str]:
        try:
            base = date.fromisoformat(due[:10])
        except ValueError:
            return None

        if kind == RecurrenceKind.DAILY.value:
            elapsed = (today - base).days
            occurrences = max(1, elapsed // interval + 1)
            return (base + timedelta(days=occurrences * interval)).isoformat()
        if kind == RecurrenceKind.WEEKLY.value:
            period_days = interval * 7
            elapsed = (today - base).days
            occurrences = max(1, elapsed // period_days + 1)
            return (base + timedelta(days=occurrences * period_days)).isoformat()

        candidate = self._next_occurrence(due, kind, interval)
        while candidate is not None and candidate <= today.isoformat():
            candidate = self._next_occurrence(candidate, kind, interval)
        return candidate

    def _next_occurrence(
        self, due: str, kind: str, interval: int
    ) -> Optional[str]:
        try:
            base = date.fromisoformat(due[:10])
        except ValueError:
            return None
        if kind == RecurrenceKind.DAILY.value:
            next_date = base + timedelta(days=interval)
        elif kind == RecurrenceKind.WEEKLY.value:
            next_date = base + timedelta(weeks=interval)
        elif kind == RecurrenceKind.MONTHLY.value:
            next_date = self._add_months(base, interval)
        else:
            return None
        return next_date.isoformat()

    @staticmethod
    def _add_months(d: date, months: int) -> date:
        month = d.month - 1 + months
        year = d.year + month // 12
        month = month % 12 + 1
        day = min(d.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    def _expand_event_recurrences(
        self, events: list[dict[str, Any]], start: str, end: str
    ) -> list[dict[str, Any]]:
        range_start = datetime.fromisoformat(start.replace("Z", "+00:00"))
        range_end = datetime.fromisoformat(end.replace("Z", "+00:00"))
        expanded: list[dict[str, Any]] = []
        for event in events:
            if event["recurrence_kind"] == RecurrenceKind.NONE.value:
                expanded.append(event)
                continue
            zone = ZoneInfo(event["timezone"])
            original_start = datetime.fromisoformat(
                event["starts_at"].replace("Z", "+00:00")
            ).astimezone(zone)
            original_end = datetime.fromisoformat(
                event["ends_at"].replace("Z", "+00:00")
            ).astimezone(zone)
            duration = original_end - original_start
            occurrence = original_start
            recurrence_until = (
                date.fromisoformat(event["recurrence_until"])
                if event.get("recurrence_until")
                else None
            )
            step_count = 0
            while occurrence.astimezone(timezone.utc) < range_start:
                occurrence = self._next_event_occurrence(
                    occurrence,
                    event["recurrence_kind"],
                    int(event["recurrence_interval"]),
                )
                step_count += 1
                if step_count > 10000:
                    raise ValueError("Intervallo di ricorrenza evento troppo ampio.")
            while occurrence.astimezone(timezone.utc) < range_end:
                if recurrence_until and occurrence.date() > recurrence_until:
                    break
                occurrence_end = occurrence + duration
                start_utc = occurrence.astimezone(timezone.utc)
                end_utc = occurrence_end.astimezone(timezone.utc)
                if end_utc >= range_start:
                    instance = dict(event)
                    instance["occurrence_starts_at"] = (
                        start_utc.isoformat(timespec="seconds").replace("+00:00", "Z")
                    )
                    instance["occurrence_ends_at"] = (
                        end_utc.isoformat(timespec="seconds").replace("+00:00", "Z")
                    )
                    expanded.append(instance)
                occurrence = self._next_event_occurrence(
                    occurrence,
                    event["recurrence_kind"],
                    int(event["recurrence_interval"]),
                )
                step_count += 1
                if step_count > 10000:
                    raise ValueError("Intervallo di ricorrenza evento troppo ampio.")
        return sorted(
            expanded,
            key=lambda item: (
                item.get("occurrence_starts_at", item["starts_at"]),
                item["title"],
            ),
        )

    @staticmethod
    def _next_event_occurrence(
        occurrence: datetime, kind: str, interval: int
    ) -> datetime:
        if kind == RecurrenceKind.DAILY.value:
            return occurrence + timedelta(days=interval)
        if kind == RecurrenceKind.WEEKLY.value:
            return occurrence + timedelta(weeks=interval)
        if kind == RecurrenceKind.MONTHLY.value:
            next_day = PlanningService._add_months(occurrence.date(), interval)
            return occurrence.replace(
                year=next_day.year, month=next_day.month, day=next_day.day
            )
        return occurrence

    # ----------------------------------------------------------- AI bridge

    def interpret_ai_request(
        self, user_text: str, context: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Interpreta una richiesta in linguaggio naturale e restituisce
        operazioni strutturate da validare e applicare (dopo conferma utente).

        Non modifica il database. Restituisce un'analisi della richiesta e
        una lista di operazioni proposte (`operations`) con parametri pronti
        per essere passati ai metodi del service dopo conferma.
        """
        text = (user_text or "").strip()
        if not text:
            return {
                "understood": False,
                "message": "Non ho ricevuto alcuna richiesta.",
                "operations": [],
            }

        lowered = text.lower()
        operations: list[dict[str, Any]] = []

        # Riconoscimento intenzioni (basato su parole chiave; da estendere
        # con un vero classificatore se necessario, senza chiamate al modello).
        task_prefixes = (
            "crea un'attività",
            "nuova attività",
            "aggiungi task",
            "crea task",
        )
        if any(k in lowered for k in task_prefixes):
            title = self._extract_title(text, prefix_candidates=task_prefixes)
            title = re.split(
                r"\s+(?:con\s+priorità|priorità|entro|per\s+il|scadenza)\b",
                title,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0].strip()
            task_params: dict[str, Any] = {
                "title": title or "Attività",
                "description": "",
                "status": TaskStatus.TODO.value,
                "priority": TaskPriority.NORMAL.value,
                "ai_origin": True,
            }
            due_match = re.search(
                r"\b(?:entro|per il|scadenza(?:\s+al)?)\s+"
                r"(\d{4}-\d{2}-\d{2})\b",
                text,
                re.IGNORECASE,
            )
            if due_match:
                due_date = due_match.group(1)
                self._validate_date(due_date, "Scadenza proposta non valida.")
                task_params["due_date"] = due_date
            priority_match = re.search(
                r"\b(critica|critical|alta|high|normale|normal|bassa|low)\b",
                text,
                re.IGNORECASE,
            )
            if priority_match:
                task_params["priority"] = {
                    "critica": "critical",
                    "critical": "critical",
                    "alta": "high",
                    "high": "high",
                    "normale": "normal",
                    "normal": "normal",
                    "bassa": "low",
                    "low": "low",
                }[priority_match.group(1).lower()]
            operations.append(
                {
                    "op": "create_task",
                    "label": f"Crea l'attività “{title or 'senza titolo'}”.",
                    "params": task_params,
                    "requires_confirmation": True,
                }
            )

        if any(
            k in lowered
            for k in ("crea un progetto", "nuovo progetto")
        ):
            title = self._extract_title(text, prefix_candidates=("crea un progetto", "nuovo progetto"))
            operations.append(
                {
                    "op": "create_project",
                    "label": f"Crea il progetto “{title or 'senza nome'}”.",
                    "params": {
                        "name": title or "Progetto",
                        "description": "",
                        "status": "active",
                        "priority": TaskPriority.NORMAL.value,
                    },
                    "requires_confirmation": True,
                }
            )

        if any(
            k in lowered
            for k in ("mostra le attività in ritardo", "attività in ritardo", "in scadenza")
        ):
            operations.append(
                {
                    "op": "list_overdue",
                    "label": "Mostra le attività in ritardo.",
                    "params": {"overdue_only": True},
                    "requires_confirmation": False,
                }
            )

        if any(
            k in lowered
            for k in ("priorità di oggi", "attività di oggi", "cosa devo fare oggi", "organizza la mia giornata")
        ):
            operations.append(
                {
                    "op": "list_today",
                    "label": "Mostra le attività di oggi.",
                    "params": {"due_after": date.today().isoformat(), "due_before": date.today().isoformat()},
                    "requires_confirmation": False,
                }
            )

        shift_match = re.search(
            r"\b(?:sposta|rinvia|anticipa)\s+(?:la\s+)?scadenza\s+"
            r"(?:di\s+)?(.+?)\s+(?:al|a)\s+(\d{4}-\d{2}-\d{2})\b",
            text,
            re.IGNORECASE,
        )
        if shift_match:
            title = shift_match.group(1).strip(" \t\r\n\"“”")
            due_date = shift_match.group(2)
            self._validate_date(due_date, "Scadenza proposta non valida.")
            matches = self._repository.list_tasks(query=title)
            exact_matches = [
                task
                for task in matches
                if task["title"].casefold() == title.casefold()
                and task["status"] not in {
                    TaskStatus.COMPLETED.value,
                    TaskStatus.CANCELLED.value,
                }
            ]
            if len(exact_matches) != 1:
                return {
                    "understood": False,
                    "message": (
                        "Non ho trovato un'unica attività aperta con quel titolo. "
                        "Verifica il titolo prima di spostare la scadenza."
                    ),
                    "operations": [],
                }
            task = exact_matches[0]
            operations.append(
                {
                    "op": "update_task",
                    "label": (
                        f"Sposta la scadenza di “{task['title']}” al {due_date}."
                    ),
                    "params": {
                        "task_id": task["id"],
                        "due_date": due_date,
                    },
                    "requires_confirmation": True,
                }
            )

        if any(
            k in lowered
            for k in ("suddividi", "scomponi", "obiettivo in attività")
        ):
            _, separator, steps_text = text.partition(":")
            if not separator:
                return {
                    "understood": False,
                    "message": (
                        "Per preparare una suddivisione verificabile, aggiungi "
                        "almeno due passaggi dopo i due punti, separati da "
                        "punto e virgola o da una nuova riga."
                    ),
                    "operations": [],
                }
            steps = [
                step.strip(" \t\r\n.-")
                for step in re.split(r";|\n", steps_text)
                if step.strip(" \t\r\n.-")
            ]
            if len(steps) < 2:
                return {
                    "understood": False,
                    "message": (
                        "La suddivisione richiede almeno due passaggi "
                        "espliciti separati da punto e virgola o da una nuova riga."
                    ),
                    "operations": [],
                }
            if len(steps) > MAX_INTERPRETATION_TASKS:
                return {
                    "understood": False,
                    "message": (
                        f"Puoi proporre al massimo {MAX_INTERPRETATION_TASKS} "
                        "attività per volta."
                    ),
                    "operations": [],
                }
            operations.extend(
                {
                    "op": "create_task",
                    "label": f"Crea l'attività “{step}”.",
                    "params": {
                        "title": step,
                        "status": TaskStatus.TODO.value,
                        "priority": TaskPriority.NORMAL.value,
                        "ai_origin": True,
                    },
                    "requires_confirmation": True,
                }
                for step in steps
            )

        if not operations:
            return {
                "understood": False,
                "message": (
                    "Non ho riconosciuto un'azione di pianificazione. "
                    "Prova con: crea un'attività, crea un progetto, "
                    "mostra le attività in ritardo, quali sono le priorità di oggi."
                ),
                "operations": [],
            }

        proposal_id = self._repository.create_ai_proposal(
            operations,
            expires_at=(
                datetime.now(timezone.utc) + AI_PROPOSAL_TTL
            ).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        )
        return {
            "understood": True,
            "message": f"Ho riconosciuto {len(operations)} operazione{'i' if len(operations) > 1 else ''}.",
            "proposal_id": proposal_id,
            "operations": operations,
        }

    def apply_confirmed_operations(
        self, proposal_id: str, *, confirmed: bool
    ) -> list[dict[str, Any]]:
        """Applica una proposta server-side solo dopo conferma esplicita."""
        if not confirmed:
            raise ValueError("La proposta non è stata confermata.")
        operations = self._repository.consume_ai_proposal(proposal_id)
        if operations is None:
            raise ValueError("Proposta AI inesistente, scaduta o già applicata.")
        if not operations or len(operations) > MAX_INTERPRETATION_TASKS:
            raise ValueError("La proposta contiene un numero non valido di operazioni.")
        supported = {
            "create_task", "create_project", "update_task", "list_overdue",
            "list_today",
        }
        for operation in operations:
            if not isinstance(operation, dict) or operation.get("op") not in supported:
                raise ValueError("La proposta contiene un'operazione non supportata.")
            if not isinstance(operation.get("params", {}), dict):
                raise ValueError("Parametri della proposta non validi.")

        results: list[dict[str, Any]] = []
        for operation in operations:
            op = operation.get("op")
            params = operation.get("params", {})
            if op == "create_task":
                results.append({"op": op, "result": self.create_task(params)})
            elif op == "create_project":
                results.append({"op": op, "result": self.create_project(params)})
            elif op == "update_task":
                task_id = params.get("task_id")
                patch = {key: value for key, value in params.items() if key != "task_id"}
                updated = self.update_task(task_id, patch)
                if updated is None:
                    raise ValueError("L'attività da aggiornare non esiste più.")
                results.append({"op": op, "result": updated})
            elif op == "list_overdue":
                results.append(
                    {"op": op, "result": self.list_tasks({"overdue_only": True})}
                )
            elif op == "list_today":
                today = date.today().isoformat()
                results.append(
                    {
                        "op": op,
                        "result": self.list_tasks(
                            {"due_after": today, "due_before": today}
                        ),
                    }
                )
        return results

    # --------------------------------------------------------------- helpers

    @staticmethod
    def _is_valid_date(value: str) -> bool:
        try:
            date.fromisoformat(str(value))
            return True
        except ValueError:
            return False

    @staticmethod
    def _validate_date(value: str, message: str) -> None:
        if not PlanningService._is_valid_date(value):
            raise ValueError(message)

    @staticmethod
    def _validate_interval(value: Any) -> None:
        if isinstance(value, bool):
            raise ValueError("L'intervallo di ricorrenza deve essere un intero positivo.")
        try:
            interval = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "L'intervallo di ricorrenza deve essere un intero positivo."
            ) from exc
        if interval < 1 or interval > 365:
            raise ValueError("L'intervallo di ricorrenza deve essere tra 1 e 365.")

    def _validate_project_reference(self, project_id: Optional[str]) -> None:
        if project_id is not None and self._repository.get_project(project_id) is None:
            raise ValueError("Il progetto associato non esiste.")

    def _validate_mission_reference(self, mission_id: Optional[str]) -> None:
        if mission_id is not None and self._repository.get_mission(mission_id) is None:
            raise ValueError("La missione associata non esiste.")

    @staticmethod
    def _validate_timezone(value: str) -> None:
        if not value:
            raise ValueError("Il fuso orario è obbligatorio.")
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Fuso orario IANA non valido.") from exc

    @classmethod
    def _validate_datetime(cls, value: str) -> datetime:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Data e ora non valide.")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Data e ora non valide.") from exc
        return parsed

    @classmethod
    def _normalize_datetime(cls, value: str, timezone_name: str) -> str:
        cls._validate_timezone(timezone_name)
        parsed = cls._validate_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name))
        return (
            parsed.astimezone(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )

    @staticmethod
    def _extract_title(text: str, prefix_candidates: tuple[str, ...]) -> str:
        lowered = text.lower()
        for prefix in prefix_candidates:
            if lowered.startswith(prefix):
                remainder = text[len(prefix):].strip()
                remainder = remainder.strip(" :,.-")
                if remainder:
                    return remainder
                break
        # Fallback: usa tutta la frase pulita da verbi comuni.
        cleaned = text
        for verb in ("crea", "nuova", "aggiungi", "attività", "task", "progetto", "un", "una", "il", "lo"):
            cleaned = cleaned.replace(verb, " ")
        cleaned = " ".join(cleaned.split())
        return cleaned or ""
