from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.planning.repository import PlanningRepository
from app.planning.service import PlanningService


class PlanningEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            prefix="jack-planning-test-"
        )
        self.database_path = Path(self.temporary_directory.name) / "tasks.sqlite3"
        self.repository = PlanningRepository(self.database_path)
        self.repository.initialize()
        self.service = PlanningService(self.repository)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_new_database_initializes_and_data_persists_after_reopen(self) -> None:
        project = self.service.create_project({"name": "Progetto persistente"})
        task = self.service.create_task(
            {
                "title": "Attività persistente",
                "project_id": project["id"],
                "tags": ["fase-2"],
            }
        )

        reopened = PlanningRepository(self.database_path)
        reopened.initialize()
        self.assertEqual(reopened.get_task(task["id"])["title"], "Attività persistente")
        self.assertEqual(reopened.get_project(project["id"])["task_ids"], [task["id"]])
        with sqlite3.connect(self.database_path) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)

    def test_version_one_database_migrates_without_losing_missions(self) -> None:
        legacy_database_path = (
            Path(self.temporary_directory.name) / "legacy-tasks.sqlite3"
        )
        with sqlite3.connect(legacy_database_path) as connection:
            connection.execute(
                """
                CREATE TABLE missions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    plan TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'planned',
                    progress_percent INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    notes TEXT NOT NULL DEFAULT ''
                )
                """
            )
            connection.execute(
                """
                INSERT INTO missions (id, title, created_at)
                VALUES ('legacy-mission', 'Missione legacy', '2026-01-01T00:00:00Z')
                """
            )
            connection.execute("PRAGMA user_version = 1")

        PlanningRepository(legacy_database_path).initialize()
        with sqlite3.connect(legacy_database_path) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)
            self.assertEqual(
                connection.execute(
                    "SELECT title FROM missions WHERE id = 'legacy-mission'"
                ).fetchone()[0],
                "Missione legacy",
            )
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(missions)")
            }
        self.assertIn("assigned_agents", columns)
        self.assertIn("results", columns)
        self.assertEqual(
            PlanningRepository(legacy_database_path).get_mission("legacy-mission")[
                "assigned_agents"
            ],
            [],
        )

    def test_dependencies_block_completion_and_reject_cycles(self) -> None:
        prerequisite = self.service.create_task({"title": "Prerequisito"})
        task = self.service.create_task({"title": "Task dipendente"})
        dependency = self.service.add_dependency(
            task["id"], prerequisite["id"]
        )

        allowed, _ = self.service.can_complete(task["id"])
        self.assertFalse(allowed)
        with self.assertRaises(ValueError):
            self.service.complete_task(task["id"])
        self.service.complete_task(prerequisite["id"])
        self.service.complete_task(task["id"])
        self.assertEqual(self.service.get_task(task["id"])["status"], "completed")
        with self.assertRaises(ValueError):
            self.service.add_dependency(prerequisite["id"], task["id"])
        self.assertTrue(self.service.remove_dependency(dependency["id"]))

    def test_project_milestones_and_progress_use_actual_tasks(self) -> None:
        project = self.service.create_project({"name": "Milestone"})
        milestone = self.service.create_milestone(
            project["id"],
            {"title": "Prima consegna", "due_date": "2026-11-12"},
        )
        first = self.service.create_task(
            {"title": "Completata", "project_id": project["id"]}
        )
        cancelled = self.service.create_task(
            {"title": "Annullata", "project_id": project["id"]}
        )
        self.service.update_task(
            cancelled["id"],
            {"status": "cancelled"},
        )
        self.service.complete_task(first["id"])

        details = self.service.get_project(project["id"])
        self.assertEqual(details["completion_percent"], 100)
        self.assertEqual(details["completed_task_count"], 1)
        self.assertEqual(details["open_task_count"], 0)
        self.assertEqual(details["milestones"][0]["id"], milestone["id"])
        self.service.update_milestone(milestone["id"], {"completed_at": "2026-11-08T10:00:00Z"})
        self.assertTrue(self.service.delete_milestone(milestone["id"]))

    def test_task_recurrence_generates_one_next_instance(self) -> None:
        task = self.service.create_task(
            {
                "title": "Ricorrente",
                "due_date": "2026-11-08",
                "recurrence_kind": "monthly",
            }
        )
        self.service.complete_task(task["id"])

        instances = self.service.list_tasks({"query": "Ricorrente"})
        self.assertEqual(len(instances), 2)
        next_task = next(item for item in instances if item["id"] != task["id"])
        self.assertEqual(next_task["due_date"], "2026-12-08")
        self.assertEqual(self.service.generate_recurrence_instances(), [])

    def test_overdue_recurrence_catches_up_to_one_future_instance(self) -> None:
        task = self.service.create_task(
            {
                "title": "Attività giornaliera",
                "due_date": "2026-10-01",
                "recurrence_kind": "daily",
            }
        )

        created = self.service.generate_recurrence_instances(date(2026, 11, 8))

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["due_date"], "2026-11-09")
        self.assertEqual(created[0]["recurrence_series_id"], task["id"])
        self.assertEqual(
            self.service.generate_recurrence_instances(date(2026, 11, 8)),
            [],
        )

    def test_same_title_recurring_tasks_keep_independent_series(self) -> None:
        first = self.service.create_task(
            {
                "title": "Promemoria",
                "due_date": "2026-11-07",
                "recurrence_kind": "weekly",
            }
        )
        second = self.service.create_task(
            {
                "title": "Promemoria",
                "due_date": "2026-11-07",
                "recurrence_kind": "weekly",
            }
        )

        created = self.service.generate_recurrence_instances(date(2026, 11, 8))

        self.assertEqual(len(created), 2)
        self.assertEqual(
            {task["recurrence_series_id"] for task in created},
            {first["id"], second["id"]},
        )

    def test_concurrent_recurrence_scans_create_only_one_instance(self) -> None:
        self.service.create_task(
            {
                "title": "Scansione concorrente",
                "due_date": "2026-11-07",
                "recurrence_kind": "daily",
            }
        )

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda _: self.service.generate_recurrence_instances(
                        date(2026, 11, 8)
                    ),
                    range(2),
                )
            )

        self.assertEqual(sum(len(result) for result in results), 1)

    def test_version_two_migration_assigns_series_to_existing_recurring_tasks(
        self,
    ) -> None:
        legacy_path = Path(self.temporary_directory.name) / "v2-tasks.sqlite3"
        repository = PlanningRepository(legacy_path)
        repository.initialize()
        legacy_service = PlanningService(repository)
        task = legacy_service.create_task(
            {
                "title": "Ricorrenza esistente",
                "due_date": "2026-11-08",
                "recurrence_kind": "daily",
            }
        )
        with sqlite3.connect(legacy_path) as connection:
            connection.execute("DROP INDEX uq_tasks_recurrence_series_due")
            connection.execute("ALTER TABLE tasks DROP COLUMN recurrence_series_id")
            connection.execute("PRAGMA user_version = 2")

        repository.initialize()

        with sqlite3.connect(legacy_path) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 3)
            self.assertEqual(
                connection.execute(
                    "SELECT recurrence_series_id FROM tasks WHERE id = ?",
                    (task["id"],),
                ).fetchone()[0],
                task["id"],
            )

    def test_calendar_events_keep_timezone_and_expand_recurrence(self) -> None:
        event = self.service.create_event(
            {
                "title": "Stand-up",
                "starts_at": "2026-11-02T09:00:00",
                "ends_at": "2026-11-02T09:30:00",
                "timezone": "Europe/Rome",
                "recurrence_kind": "weekly",
            }
        )
        self.assertEqual(event["starts_at"], "2026-11-02T08:00:00Z")
        items = self.service.list_events(
            {
                "starts_at": "2026-11-01T23:00:00Z",
                "ends_at": "2026-11-16T23:00:00Z",
                "timezone": "Europe/Rome",
            }
        )
        self.assertEqual(len(items), 3)
        self.assertTrue(
            all(item["occurrence_starts_at"].endswith("Z") for item in items)
        )
        with self.assertRaises(ValueError):
            self.service.create_event(
                {
                    "title": "Invalid timezone",
                    "starts_at": "2026-11-02T09:00:00",
                    "ends_at": "2026-11-02T10:00:00",
                    "timezone": "Mars/Olympus",
                }
            )

    def test_ai_proposal_requires_server_side_confirmation_and_is_single_use(self) -> None:
        proposal = self.service.interpret_ai_request("Crea un'attività Preparare la demo")
        self.assertTrue(proposal["understood"])
        self.assertTrue(proposal["proposal_id"])
        self.assertEqual(self.service.list_tasks({}), [])
        with self.assertRaises(ValueError):
            self.service.apply_confirmed_operations(
                proposal["proposal_id"], confirmed=False
            )
        results = self.service.apply_confirmed_operations(
            proposal["proposal_id"], confirmed=True
        )
        self.assertEqual(results[0]["result"]["title"], "Preparare la demo")
        with self.assertRaises(ValueError):
            self.service.apply_confirmed_operations(
                proposal["proposal_id"], confirmed=True
            )

    def test_ai_proposals_create_breakdown_and_shift_due_date_only_after_confirm(self) -> None:
        create = self.service.interpret_ai_request(
            "Crea un'attività Preparare la demo con priorità alta entro 2026-11-20"
        )
        self.assertEqual(create["operations"][0]["params"]["title"], "Preparare la demo")
        self.assertEqual(create["operations"][0]["params"]["priority"], "high")
        self.assertEqual(create["operations"][0]["params"]["due_date"], "2026-11-20")
        self.assertEqual(self.service.list_tasks({}), [])
        self.service.apply_confirmed_operations(create["proposal_id"], confirmed=True)

        task = self.service.list_tasks({"query": "Preparare la demo"})[0]
        shift = self.service.interpret_ai_request(
            "Sposta la scadenza di Preparare la demo al 2026-11-23"
        )
        self.assertEqual(shift["operations"][0]["op"], "update_task")
        self.assertEqual(task["due_date"], "2026-11-20")
        self.service.apply_confirmed_operations(shift["proposal_id"], confirmed=True)
        self.assertEqual(
            self.service.get_task(task["id"])["due_date"], "2026-11-23"
        )

        breakdown = self.service.interpret_ai_request(
            "Suddividi lancio versione: Preparare i test; Aggiornare la guida"
        )
        self.assertTrue(breakdown["understood"])
        self.assertEqual(len(breakdown["operations"]), 2)
        self.assertEqual(self.service.list_tasks({"query": "Aggiornare"}), [])
        results = self.service.apply_confirmed_operations(
            breakdown["proposal_id"], confirmed=True
        )
        self.assertEqual([item["result"]["title"] for item in results], [
            "Preparare i test",
            "Aggiornare la guida",
        ])

    def test_ai_breakdown_requires_explicit_steps_and_rejects_bad_deadline(self) -> None:
        proposal = self.service.interpret_ai_request("Suddividi questo obiettivo")
        self.assertFalse(proposal["understood"])
        self.assertEqual(proposal["operations"], [])
        with self.assertRaises(ValueError):
            self.service.interpret_ai_request(
                "Crea un'attività Demo entro 2026-02-30"
            )

    def test_task_filters_sorting_and_date_order_validation(self) -> None:
        project = self.service.create_project({"name": "Filtri"})
        first = self.service.create_task(
            {
                "title": "Alpha",
                "priority": "high",
                "category": "release",
                "tags": ["v1"],
                "project_id": project["id"],
                "start_date": "2026-11-01",
                "due_date": "2026-11-10",
            }
        )
        second = self.service.create_task(
            {
                "title": "Beta",
                "priority": "low",
                "project_id": project["id"],
                "due_date": "2026-11-12",
            }
        )
        self.assertEqual(
            [task["id"] for task in self.service.list_tasks({"tag": "v1"})],
            [first["id"]],
        )
        self.assertEqual(
            [task["title"] for task in self.service.list_tasks({"sort": "priority"})],
            ["Alpha", "Beta"],
        )
        self.assertEqual(
            [task["title"] for task in self.service.list_tasks({"due_after": "2026-11-11"})],
            ["Beta"],
        )
        with self.assertRaises(ValueError):
            self.service.create_task(
                {
                    "title": "Date incoerenti",
                    "start_date": "2026-11-20",
                    "due_date": "2026-11-19",
                }
            )
        with self.assertRaises(ValueError):
            self.service.update_task(
                second["id"], {"start_date": "2026-11-13"}
            )

    def test_project_dates_archive_and_milestone_crud(self) -> None:
        project = self.service.create_project(
            {
                "name": "Pianificazione",
                "start_date": "2026-11-01",
                "due_date": "2026-11-30",
            }
        )
        milestone = self.service.create_milestone(
            project["id"],
            {
                "title": "Prima versione",
                "description": "Consegna",
                "due_date": "2026-11-15",
            },
        )
        updated = self.service.update_milestone(
            milestone["id"], {"title": "Versione candidata"}
        )
        self.assertEqual(updated["title"], "Versione candidata")
        self.assertTrue(self.service.delete_milestone(milestone["id"]))
        archived = self.service.archive_project(project["id"])
        self.assertEqual(archived["status"], "archived")
        self.assertEqual(self.service.list_projects(), [])
        self.assertEqual(
            self.service.list_projects(include_archived=True)[0]["id"], project["id"]
        )
        with self.assertRaises(ValueError):
            self.service.update_project(
                project["id"], {"start_date": "2026-12-01"}
            )

    def test_planned_mission_tracks_tasks_logs_and_approvals(self) -> None:
        mission = self.service.create_mission(
            {
                "title": "Preparare la V2",
                "plan": "Pianificare le attività senza eseguirle autonomamente.",
                "assigned_agents": ["planner"],
            }
        )
        task = self.service.create_task(
            {"title": "Verificare il piano", "mission_id": mission["id"]}
        )
        self.service.complete_task(task["id"])
        log = self.service.add_mission_log(mission["id"], "Attività completata.")
        approval = self.service.create_mission_approval(
            mission["id"], "Approvare la prossima fase"
        )
        resolved = self.service.update_mission_approval(
            approval["id"], "approved"
        )
        current = self.service.get_mission(mission["id"])

        self.assertEqual(current["task_ids"], [task["id"]])
        self.assertEqual(current["progress_percent"], 100)
        self.assertEqual(current["logs"][0]["id"], log["id"])
        self.assertEqual(resolved["status"], "approved")

    def test_invalid_completion_and_calendar_inputs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.service.create_task({"title": "Scadenza errata", "due_date": "2026-02-30"})
        with self.assertRaises(ValueError):
            self.service.create_task({"title": "Titolo completato", "status": "completed"})
        with self.assertRaises(ValueError):
            self.service.create_event(
                {
                    "title": "Durata negativa",
                    "starts_at": "2026-11-08T12:00:00Z",
                    "ends_at": "2026-11-08T11:00:00Z",
                    "timezone": "UTC",
                }
            )


if __name__ == "__main__":
    unittest.main()
