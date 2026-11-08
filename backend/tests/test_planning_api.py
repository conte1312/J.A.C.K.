from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
import zipfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BACKEND_DIR = Path(__file__).resolve().parents[1]


class PlanningApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            prefix="jack-planning-api-test-"
        )
        self.database_path = Path(self.temporary_directory.name) / "tasks.sqlite3"
        self.port = _free_local_port()
        self.server: subprocess.Popen[bytes] | None = None
        self._start_server()

    def tearDown(self) -> None:
        if self.server is not None:
            self.server.terminate()
            try:
                self.server.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.server.kill()
                self.server.wait(timeout=3)
        self.temporary_directory.cleanup()

    def _start_server(self) -> None:
        environment = os.environ.copy()
        environment.update(
            {
                "JACK_ENV": "production",
                "JACK_HOST": "127.0.0.1",
                "JACK_PORT": str(self.port),
                "JACK_LOG_LEVEL": "warning",
                "JACK_MEMORY_DB_PATH": str(
                    Path(self.temporary_directory.name) / "memories.sqlite3"
                ),
                "JACK_PLANNING_DB_PATH": str(self.database_path),
                "JACK_CONTROL_PLANE_DB_PATH": str(
                    Path(self.temporary_directory.name) / "control-plane.sqlite3"
                ),
            }
        )
        self.server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
                "--log-level",
                "warning",
            ],
            cwd=BACKEND_DIR,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if self.server.poll() is not None:
                self.fail("Planning API test server exited during startup.")
            try:
                code, _ = self._request("GET", "/health", timeout=0.25)
                if code == 200:
                    return
            except (URLError, TimeoutError, ConnectionError):
                time.sleep(0.05)
        self.fail("Planning API test server did not become ready.")

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
        *,
        timeout: float = 3,
    ) -> tuple[int, object]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=body,
            method=method,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        try:
            response = urlopen(request, timeout=timeout)
        except HTTPError as error:
            response = error
        raw_body = response.read().decode("utf-8")
        return response.status, json.loads(raw_body) if raw_body else None

    def test_task_crud_checklist_dependencies_filters_and_completion(self) -> None:
        code, prerequisite = self._request(
            "POST",
            "/api/v1/planning/tasks",
            {
                "title": "Preparare specifica",
                "status": "todo",
                "priority": "high",
                "start_date": "2026-11-01",
                "due_date": "2026-11-10",
                "category": "release",
                "tags": ["v1.2"],
            },
        )
        self.assertEqual(code, 201)
        code, task = self._request(
            "POST",
            "/api/v1/planning/tasks",
            {"title": "Avviare implementazione", "status": "todo"},
        )
        self.assertEqual(code, 201)
        task_id = task["id"]
        prerequisite_id = prerequisite["id"]

        code, item = self._request(
            "POST",
            f"/api/v1/planning/tasks/{task_id}/checklist",
            {"title": "Aggiungere test"},
        )
        self.assertEqual(code, 201)
        self.assertEqual(item["title"], "Aggiungere test")
        code, dependency = self._request(
            "POST",
            f"/api/v1/planning/tasks/{task_id}/dependencies",
            {"depends_on_task_id": prerequisite_id},
        )
        self.assertEqual(code, 201)
        code, can_complete = self._request(
            "GET", f"/api/v1/planning/tasks/{task_id}/can-complete"
        )
        self.assertEqual(code, 200)
        self.assertFalse(can_complete["allowed"])
        code, _ = self._request(
            "POST", f"/api/v1/planning/tasks/{task_id}/complete", {}
        )
        self.assertEqual(code, 409)

        code, filtered = self._request(
            "GET", "/api/v1/planning/tasks?priority=high&tag=v1.2&sort=title"
        )
        self.assertEqual(code, 200)
        self.assertEqual([row["id"] for row in filtered], [prerequisite_id])
        code, updated_item = self._request(
            "PUT", f"/api/v1/planning/checklist/{item['id']}", {"is_done": True}
        )
        self.assertEqual(code, 200)
        self.assertTrue(updated_item["is_done"])

        self._request("POST", f"/api/v1/planning/tasks/{prerequisite_id}/complete", {})
        code, completed = self._request(
            "POST", f"/api/v1/planning/tasks/{task_id}/complete", {}
        )
        self.assertEqual(code, 200)
        self.assertIsNotNone(completed["completed_at"])
        self.assertEqual(
            self._request("DELETE", f"/api/v1/planning/dependencies/{dependency['id']}")[0],
            204,
        )
        self.assertEqual(self._request("DELETE", f"/api/v1/planning/tasks/{task_id}")[0], 204)
        self.assertEqual(self._request("GET", f"/api/v1/planning/tasks/{task_id}")[0], 404)

    def test_system_monitor_api_reports_backend_and_local_databases(self) -> None:
        code, snapshot = self._request("GET", "/api/v1/system/monitor")

        self.assertEqual(code, 200)
        self.assertEqual(snapshot["backend"]["status"], "ok")
        self.assertGreater(snapshot["disk"]["total_bytes"], 0)
        self.assertEqual(
            [database["name"] for database in snapshot["databases"]],
            ["Memoria e conversazioni", "Pianificazione", "Control Plane"],
        )
        self.assertTrue(
            all(database["integrity"] for database in snapshot["databases"])
        )
        self.assertNotIn(str(self.database_path.parent), json.dumps(snapshot))

    def test_system_backup_api_creates_a_listed_archive(self) -> None:
        code, created = self._request("POST", "/api/v1/system/backups", {})

        self.assertEqual(code, 201)
        self.assertGreater(created["size_bytes"], 0)
        self.assertEqual(
            created["directory"],
            str((self.database_path.parent / "backups").resolve()),
        )
        backup_path = Path(created["directory"]) / created["filename"]
        with zipfile.ZipFile(backup_path) as archive:
            self.assertEqual(
                set(archive.namelist()),
                {
                    "manifest.json",
                    "memories.sqlite3",
                    "tasks.sqlite3",
                    "control-plane.sqlite3",
                },
            )
            manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(
                {database["name"] for database in manifest["databases"]},
                {"Memoria e conversazioni", "Pianificazione", "Control Plane"},
            )
            for filename in (
                "memories.sqlite3",
                "tasks.sqlite3",
                "control-plane.sqlite3",
            ):
                with tempfile.NamedTemporaryFile(
                    suffix=".sqlite3", dir=self.temporary_directory.name
                ) as extracted:
                    extracted.write(archive.read(filename))
                    extracted.flush()
                    with sqlite3.connect(extracted.name) as connection:
                        self.assertEqual(
                            connection.execute("PRAGMA quick_check").fetchone()[0],
                            "ok",
                        )
        code, validation = self._request(
            "POST",
            f"/api/v1/system/backups/{created['filename']}/validate",
        )
        self.assertEqual(code, 200)
        self.assertTrue(validation["valid"])
        self.assertEqual(
            {database["name"] for database in validation["databases"]},
            {"Memoria e conversazioni", "Pianificazione", "Control Plane"},
        )
        self.assertEqual(validation["missing_optional_databases"], [])
        self.assertTrue(
            all(database["integrity"] for database in validation["databases"])
        )
        code, backups = self._request("GET", "/api/v1/system/backups")
        self.assertEqual(code, 200)
        self.assertEqual(backups["backups"][0]["filename"], created["filename"])

    def test_security_status_reports_current_limits_without_granting_capabilities(
        self,
    ) -> None:
        code, status = self._request("GET", "/api/v1/system/security-status")

        self.assertEqual(code, 200)
        self.assertEqual(status["api_bind_host"], "127.0.0.1")
        self.assertEqual(status["api_scope"], "loopback")
        self.assertEqual(status["autonomous_execution"], "not_available")
        self.assertEqual(status["external_action_approval"], "not_enforced")
        self.assertEqual(status["backup_encryption"], "not_encrypted")
        self.assertEqual(status["restore"], "not_available")
        self.assertTrue(status["informational_only"])

    def test_timezone_catalog_contains_valid_iana_zones(self) -> None:
        code, result = self._request("GET", "/api/v1/system/timezones")

        self.assertEqual(code, 200)
        timezones = result["timezones"]
        self.assertIn("Europe/Rome", timezones)
        self.assertIn("America/New_York", timezones)
        self.assertIn("Asia/Tokyo", timezones)
        self.assertIn("UTC", timezones)
        self.assertEqual(timezones, sorted(set(timezones)))

    def test_project_milestones_and_progress_are_based_on_tasks(self) -> None:
        code, project = self._request(
            "POST",
            "/api/v1/planning/projects",
            {
                "name": "Progetto API",
                "goal": "Rilasciare una versione",
                "start_date": "2026-11-01",
                "due_date": "2026-11-30",
            },
        )
        self.assertEqual(code, 201)
        project_id = project["id"]
        _, task = self._request(
            "POST",
            "/api/v1/planning/tasks",
            {"title": "Attività progetto", "project_id": project_id},
        )
        _, milestone = self._request(
            "POST",
            f"/api/v1/planning/projects/{project_id}/milestones",
            {"title": "Beta", "due_date": "2026-11-15"},
        )
        self.assertEqual(milestone["title"], "Beta")
        self._request(
            "PUT",
            f"/api/v1/planning/milestones/{milestone['id']}",
            {"completed_at": "2026-11-08T10:00:00Z"},
        )
        _, current = self._request("GET", f"/api/v1/planning/projects/{project_id}")
        self.assertEqual(current["open_task_count"], 1)
        self.assertEqual(current["completion_percent"], 0)
        self._request("POST", f"/api/v1/planning/tasks/{task['id']}/complete", {})
        _, current = self._request("GET", f"/api/v1/planning/projects/{project_id}")
        self.assertEqual(current["completed_task_count"], 1)
        self.assertEqual(current["completion_percent"], 100)
        self.assertEqual(
            self._request("POST", f"/api/v1/planning/projects/{project_id}/archive", {})[0],
            200,
        )
        self.assertEqual(
            self._request("GET", "/api/v1/planning/projects?include_archived=false")[1],
            [],
        )
        self.assertEqual(self._request("DELETE", f"/api/v1/planning/projects/{project_id}")[0], 204)

    def test_calendar_timezone_event_recurrence_and_filters(self) -> None:
        code, event = self._request(
            "POST",
            "/api/v1/planning/calendar/events",
            {
                "title": "Riunione",
                "starts_at": "2026-11-02T09:00:00",
                "ends_at": "2026-11-02T09:30:00",
                "timezone": "Europe/Rome",
                "priority": "high",
                "recurrence_kind": "weekly",
                "recurrence_interval": 1,
                "recurrence_until": "2026-11-16",
            },
        )
        self.assertEqual(code, 201)
        self.assertEqual(event["starts_at"], "2026-11-02T08:00:00Z")
        self.assertEqual(event["timezone"], "Europe/Rome")
        code, calendar = self._request(
            "GET",
            "/api/v1/planning/calendar?from_date=2026-11-01&to_date=2026-11-30"
            "&timezone=Europe%2FRome&priority=high",
        )
        self.assertEqual(code, 200)
        self.assertEqual(len(calendar["events"]), 3)
        self.assertEqual(calendar["timezone"], "Europe/Rome")
        self.assertEqual(calendar["tasks"], [])
        self.assertEqual(
            self._request("DELETE", f"/api/v1/planning/calendar/events/{event['id']}")[0],
            204,
        )
        code, _ = self._request(
            "POST",
            "/api/v1/planning/calendar/events",
            {
                "title": "Fuso invalido",
                "starts_at": "2026-11-02T09:00:00",
                "ends_at": "2026-11-02T10:00:00",
                "timezone": "Mars/Olympus",
            },
        )
        self.assertEqual(code, 422)

    def test_calendar_timezone_preference_is_validated_and_persistent(self) -> None:
        code, preferences = self._request("GET", "/api/v1/planning/preferences")
        self.assertEqual(code, 200)
        self.assertEqual(preferences["timezone"], "Europe/Rome")

        code, preferences = self._request(
            "PUT",
            "/api/v1/planning/preferences",
            {"timezone": "America/New_York"},
        )
        self.assertEqual(code, 200)
        self.assertEqual(preferences["timezone"], "America/New_York")

        code, calendar = self._request(
            "GET",
            "/api/v1/planning/calendar?from_date=2026-11-01&to_date=2026-11-01",
        )
        self.assertEqual(code, 200)
        self.assertEqual(calendar["timezone"], "America/New_York")

        code, _ = self._request(
            "PUT",
            "/api/v1/planning/preferences",
            {"timezone": "Mars/Olympus"},
        )
        self.assertEqual(code, 422)
        code, preferences = self._request("GET", "/api/v1/planning/preferences")
        self.assertEqual(code, 200)
        self.assertEqual(preferences["timezone"], "America/New_York")

    def test_control_plane_declared_identities_capabilities_and_audit_api(self) -> None:
        identity_path = "/api/v1/control-plane/identities"
        capability_path = "/api/v1/control-plane/capabilities"
        audit_path = "/api/v1/control-plane/audit-events"

        code, identity = self._request(
            "POST",
            identity_path,
            {"kind": "agent", "id": "planner", "display_name": "Planner agent"},
        )
        self.assertEqual(code, 201)
        self.assertEqual(identity["kind"], "agent")
        self.assertEqual(
            self._request("GET", identity_path + "?kind=agent")[1][0]["id"],
            "planner",
        )
        self.assertEqual(
            self._request(
                "POST",
                identity_path,
                {"kind": "agent", "id": "planner", "display_name": "Duplicate"},
            )[0],
            409,
        )

        capability = {
            "id": "read-planning-tasks",
            "owner": {"kind": "agent", "id": "planner"},
            "description": "A declaration, not an access grant.",
            "resource": "planning.tasks",
            "operations": ["read"],
            "scope": {"project_id": "project-1"},
            "risk_level": "normal",
            "approval_required": False,
        }
        code, registered = self._request(
            "POST", capability_path, capability
        )
        self.assertEqual(code, 201)
        self.assertEqual(registered["owner"]["kind"], "agent")
        self.assertNotIn("granted", registered)
        self.assertEqual(
            self._request(
                "GET",
                capability_path + "?owner_kind=agent&resource=planning.tasks",
            )[1][0]["id"],
            "read-planning-tasks",
        )
        self.assertEqual(
            self._request(
                "POST",
                capability_path,
                {**capability, "owner": {"kind": "tool", "id": "planner"}},
            )[0],
            404,
        )
        self.assertEqual(
            self._request(
                "POST",
                capability_path,
                {**capability, "risk_level": "critical", "approval_required": False},
            )[0],
            422,
        )

        code, events = self._request("GET", audit_path + "?subject_id=planner")
        self.assertEqual(code, 200)
        self.assertEqual(
            {event["action"] for event in events},
            {"identity.declared", "capability.declared"},
        )
        self.assertTrue(
            all(
                event["actor"] == {"kind": "service", "id": "control-plane-api"}
                for event in events
            )
        )

    def test_curated_agent_profiles_are_read_only_and_have_no_capabilities(self) -> None:
        catalog_path = "/api/v1/control-plane/agent-profiles"
        code, profiles = self._request("GET", catalog_path)

        self.assertEqual(code, 200)
        self.assertEqual(len(profiles), 10)
        self.assertEqual(
            {profile["id"] for profile in profiles},
            {
                "software-architect",
                "backend-architect",
                "desktop-app-engineer",
                "ai-engineer",
                "multi-agent-systems-architect",
                "minimal-change-engineer",
                "code-reviewer",
                "privacy-engineer",
                "test-automation-engineer",
                "project-shepherd",
            },
        )
        self.assertTrue(
            all(
                profile["enabled"] is False
                and profile["execution_enabled"] is False
                and profile["capabilities"] == []
                and profile["tools"] == []
                and profile["source_license"] == "MIT"
                for profile in profiles
            )
        )

        code, profile = self._request(
            "GET", f"{catalog_path}/multi-agent-systems-architect"
        )
        self.assertEqual(code, 200)
        self.assertEqual(profile["source_repository"], "msitarzewski/agency-agents")
        self.assertEqual(
            profile["source_revision"], "b859c515d813efcfc4755d3471dd9e7686c7706d"
        )
        self.assertTrue(profile["profile_markdown"].startswith("---\n"))
        self.assertEqual(profile["capabilities"], [])
        self.assertEqual(profile["tools"], [])
        self.assertEqual(
            self._request("GET", f"{catalog_path}/not-a-profile")[0], 404
        )
        self.assertEqual(
            self._request(
                "POST",
                f"{catalog_path}/multi-agent-systems-architect",
                {},
            )[0],
            405,
        )

    def test_ai_proposals_require_confirmation_and_support_structured_breakdown(self) -> None:
        code, proposal = self._request(
            "POST",
            "/api/v1/planning/ai/interpret",
            {
                "text": "Suddividi lancio versione: Scrivere test; Preparare guida",
            },
        )
        self.assertEqual(code, 200)
        self.assertEqual(len(proposal["operations"]), 2)
        self.assertEqual(self._request("GET", "/api/v1/planning/tasks")[1], [])
        code, _ = self._request(
            "POST",
            "/api/v1/planning/ai/apply",
            {"proposal_id": proposal["proposal_id"], "confirmed": False},
        )
        self.assertEqual(code, 409)
        code, results = self._request(
            "POST",
            "/api/v1/planning/ai/apply",
            {"proposal_id": proposal["proposal_id"], "confirmed": True},
        )
        self.assertEqual(code, 200)
        self.assertEqual(
            [result["result"]["title"] for result in results],
            ["Scrivere test", "Preparare guida"],
        )
        code, _ = self._request(
            "POST",
            "/api/v1/planning/ai/apply",
            {"proposal_id": proposal["proposal_id"], "confirmed": True},
        )
        self.assertEqual(code, 409)
        code, unsupported = self._request(
            "POST",
            "/api/v1/planning/ai/interpret",
            {"text": "Suddividi un obiettivo senza elencare i passaggi"},
        )
        self.assertEqual(code, 200)
        self.assertFalse(unsupported["understood"])

    def test_missions_crud_linked_tasks_logs_and_approval(self) -> None:
        code, mission = self._request(
            "POST",
            "/api/v1/planning/missions",
            {
                "title": "Piano V2",
                "plan": "Elencare le attività prima dell'esecuzione.",
                "assigned_agents": ["planner"],
            },
        )
        self.assertEqual(code, 201)
        mission_id = mission["id"]
        _, task = self._request(
            "POST",
            "/api/v1/planning/tasks",
            {"title": "Attività missione", "mission_id": mission_id},
        )
        _, log = self._request(
            "POST",
            f"/api/v1/planning/missions/{mission_id}/logs",
            {"message": "Piano creato"},
        )
        _, approval = self._request(
            "POST",
            f"/api/v1/planning/missions/{mission_id}/approvals",
            {"description": "Autorizzare la fase successiva"},
        )
        _, approval = self._request(
            "PUT",
            f"/api/v1/planning/mission-approvals/{approval['id']}",
            {"status": "approved"},
        )
        _, current = self._request("GET", f"/api/v1/planning/missions/{mission_id}")
        self.assertEqual(current["task_ids"], [task["id"]])
        self.assertEqual(current["logs"][0]["id"], log["id"])
        self.assertEqual(current["approvals"][0]["status"], "approved")
        self.assertEqual(self._request("DELETE", f"/api/v1/planning/missions/{mission_id}")[0], 204)


def _free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


if __name__ == "__main__":
    unittest.main()
