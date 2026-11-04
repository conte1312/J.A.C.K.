from __future__ import annotations

import json
import os
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BACKEND_DIR = Path(__file__).resolve().parents[1]


class MemoryApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            prefix="jack-memory-api-test-"
        )
        self.database_path = Path(self.temporary_directory.name) / "memories.sqlite3"
        self.port = _free_local_port()
        self.server: subprocess.Popen[bytes] | None = None
        self._start_server()

    def tearDown(self) -> None:
        self._stop_server()
        self.temporary_directory.cleanup()

    def test_health_and_info_stay_available(self) -> None:
        health_status, health = self._request("GET", "/health")
        info_status, info = self._request("GET", "/api/v1/info")

        self.assertEqual(health_status, 200)
        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["app"], "J.A.C.K.")
        self.assertEqual(health["version"], "0.1.0")
        self.assertEqual(info_status, 200)
        self.assertIn("memories", info["modules"])

    def test_database_starts_empty_and_crud_works(self) -> None:
        status_code, empty = self._request("GET", "/api/v1/memories")
        self.assertEqual(status_code, 200)
        self.assertEqual(empty, [])
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(self.database_path.stat().st_mode), 0o600)

        status_code, created = self._request(
            "POST",
            "/api/v1/memories",
            {
                "title": "Preferenza riunioni",
                "content": "Preferisco pianificare le riunioni al mattino.",
                "category": "preferenze",
            },
        )
        self.assertEqual(status_code, 201)
        self.assertTrue(created["id"])
        self.assertEqual(created["title"], "Preferenza riunioni")
        self.assertEqual(created["category"], "preferences")
        self.assertEqual(created["source_type"], "saved")
        self.assertEqual(created["source"], "user_entry")
        self.assertEqual(created["verification"], "to_verify")
        self.assertEqual(created["tags"], [])
        self.assertEqual(created["importance"], 3)
        self.assertFalse(created["excluded"])
        self.assertIsNone(created["last_used"])
        self.assertTrue(created["created_at"].endswith("Z"))
        self.assertEqual(created["created_at"], created["updated_at"])

        status_code, detail = self._request(
            "GET", f"/api/v1/memories/{created['id']}"
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(detail["content"], created["content"])

        time.sleep(0.01)
        status_code, updated = self._request(
            "PUT",
            f"/api/v1/memories/{created['id']}",
            {
                "title": "Preferenza aggiornata",
                "content": "Preferisco le riunioni brevi al mattino.",
                "category": "note",
            },
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(updated["title"], "Preferenza aggiornata")
        self.assertEqual(updated["category"], "other")
        self.assertGreater(updated["updated_at"], created["updated_at"])

        status_code, _ = self._request(
            "DELETE", f"/api/v1/memories/{created['id']}"
        )
        self.assertEqual(status_code, 204)
        status_code, missing = self._request(
            "GET", f"/api/v1/memories/{created['id']}"
        )
        self.assertEqual(status_code, 404)
        self.assertEqual(missing["detail"], "Memory not found")

    def test_search_and_category_filters(self) -> None:
        entries = [
            ("Riunione prodotto", "Luca e Giulia preparano le metriche.", "lavoro"),
            ("Progetto Atlas", "Giulia coordina l'implementazione.", "progetti"),
            ("Nota cucina", "Ricetta per la cena del venerdì.", "note"),
        ]
        for title, content, category in entries:
            status_code, _ = self._request(
                "POST",
                "/api/v1/memories",
                {"title": title, "content": content, "category": category},
            )
            self.assertEqual(status_code, 201)

        status_code, search_results = self._request(
            "GET", "/api/v1/memories?q=GIULIA"
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(len(search_results), 2)

        status_code, category_results = self._request(
            "GET", "/api/v1/memories?category=lavoro"
        )
        self.assertEqual(status_code, 200)
        self.assertEqual([item["title"] for item in category_results], ["Riunione prodotto"])
        self.assertEqual(category_results[0]["category"], "work")

        status_code, combined_results = self._request(
            "GET", "/api/v1/memories?q=giulia&category=progetti"
        )
        self.assertEqual(status_code, 200)
        self.assertEqual([item["title"] for item in combined_results], ["Progetto Atlas"])

    def test_memory_metadata_validation_and_explicit_updates(self) -> None:
        status_code, created = self._request(
            "POST",
            "/api/v1/memories",
            {
                "title": "Typed memory",
                "content": "Neutral metadata test content.",
                "category": "technical",
                "source_type": "retrieved",
                "source": "manual test fixture",
                "verification": "verified",
                "tags": ["local", " test "],
                "importance": 5,
                "excluded": True,
                "conversation_id": "conversation-test",
            },
        )
        self.assertEqual(status_code, 201)
        self.assertEqual(created["tags"], ["local", "test"])
        self.assertEqual(created["source_type"], "retrieved")
        self.assertEqual(created["verification"], "verified")
        self.assertEqual(created["importance"], 5)
        self.assertTrue(created["excluded"])
        self.assertEqual(created["conversation_id"], "conversation-test")

        status_code, updated = self._request(
            "PUT",
            f"/api/v1/memories/{created['id']}",
            {
                "title": "Renamed memory",
                "content": "The optional metadata remains intact.",
                "category": "technical",
            },
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(updated["source_type"], "retrieved")
        self.assertEqual(updated["tags"], ["local", "test"])
        self.assertEqual(updated["importance"], 5)
        self.assertTrue(updated["excluded"])

        for payload in (
            {"importance": 0},
            {"importance": 6},
            {"source_type": "automatic"},
            {"verification": "certain"},
            {"tags": [""]},
        ):
            invalid = {
                "title": "Invalid metadata",
                "content": "No private data in errors.",
                "category": "other",
                **payload,
            }
            status_code, body = self._request("POST", "/api/v1/memories", invalid)
            self.assertEqual(status_code, 422)
            self.assertEqual(body["detail"], "Invalid request data")

    def test_exclusion_last_used_and_graph_filters(self) -> None:
        _, first = self._request(
            "POST",
            "/api/v1/memories",
            {"title": "First graph node", "content": "One", "category": "work"},
        )
        _, second = self._request(
            "POST",
            "/api/v1/memories",
            {
                "title": "Second graph node",
                "content": "Two",
                "category": "projects",
            },
        )
        status_code, used = self._request(
            "PUT",
            f"/api/v1/memories/{first['id']}/last-used",
        )
        self.assertEqual(status_code, 200)
        status_code, exclusion_update = self._request(
            "PUT",
            f"/api/v1/memories/{second['id']}/exclusion",
            {"excluded": True},
        )
        self.assertEqual(status_code, 200)
        self.assertTrue(used["last_used"])
        self.assertTrue(exclusion_update["excluded"])

        status_code, excluded = self._request(
            "GET", "/api/v1/memories?excluded=true"
        )
        self.assertEqual(status_code, 200)
        self.assertEqual([memory["id"] for memory in excluded], [second["id"]])

        status_code, included = self._request(
            "PUT",
            f"/api/v1/memories/{second['id']}/exclusion",
            {"excluded": False},
        )
        self.assertEqual(status_code, 200)
        self.assertFalse(included["excluded"])
        status_code, graph = self._request("GET", "/api/v1/memories/graph?category=work")
        self.assertEqual(status_code, 200)
        self.assertEqual([node["id"] for node in graph["nodes"]], [first["id"]])
        self.assertEqual(graph["edges"], [])

    def test_memory_link_crud_validation_duplicate_and_cascade(self) -> None:
        _, first = self._request(
            "POST",
            "/api/v1/memories",
            {"title": "Node A", "content": "A", "category": "identity"},
        )
        _, second = self._request(
            "POST",
            "/api/v1/memories",
            {"title": "Node B", "content": "B", "category": "people"},
        )
        payload = {
            "from_id": first["id"],
            "to_id": second["id"],
            "relation": "È collegato",
            "strength": 2,
        }
        status_code, link = self._request("POST", "/api/v1/memories/links", payload)
        self.assertEqual(status_code, 201)
        self.assertEqual(link["strength"], 2)
        status_code, link_detail = self._request(
            "GET", f"/api/v1/memories/links/{link['id']}"
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(link_detail["id"], link["id"])

        duplicate = {
            **payload,
            "from_id": second["id"],
            "to_id": first["id"],
            "relation": "è COLLEGATO ",
        }
        status_code, conflict = self._request(
            "POST", "/api/v1/memories/links", duplicate
        )
        self.assertEqual(status_code, 409)
        self.assertEqual(conflict["detail"], "Equivalent memory link already exists")

        for invalid in (
            {**payload, "from_id": first["id"], "to_id": first["id"]},
            {**payload, "strength": 0},
            {**payload, "strength": 4},
        ):
            status_code, body = self._request(
                "POST", "/api/v1/memories/links", invalid
            )
            self.assertEqual(status_code, 422)
            self.assertEqual(body["detail"], "Invalid request data")

        status_code, missing_memory = self._request(
            "POST",
            "/api/v1/memories/links",
            {**payload, "to_id": "not-a-memory"},
        )
        self.assertEqual(status_code, 404)
        self.assertEqual(missing_memory["detail"], "Memory not found")

        status_code, filtered = self._request(
            "GET", f"/api/v1/memories/links?memory_id={first['id']}"
        )
        self.assertEqual(status_code, 200)
        self.assertEqual([item["id"] for item in filtered], [link["id"]])

        status_code, graph = self._request("GET", "/api/v1/memories/graph")
        self.assertEqual(status_code, 200)
        self.assertEqual(len(graph["nodes"]), 2)
        self.assertEqual(graph["edges"][0]["id"], link["id"])

        status_code, updated = self._request(
            "PUT",
            f"/api/v1/memories/links/{link['id']}",
            {**payload, "relation": "depends on", "strength": 3},
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(updated["relation"], "depends on")
        self.assertEqual(updated["strength"], 3)

        status_code, _ = self._request(
            "DELETE", f"/api/v1/memories/{first['id']}"
        )
        self.assertEqual(status_code, 204)
        status_code, remaining_links = self._request("GET", "/api/v1/memories/links")
        self.assertEqual(status_code, 200)
        self.assertEqual(remaining_links, [])

        status_code, _ = self._request(
            "DELETE", f"/api/v1/memories/links/{link['id']}"
        )
        self.assertEqual(status_code, 404)

    def test_validation_errors_do_not_echo_memory_content(self) -> None:
        private_text = "private-memory-content-that-must-not-be-echoed"
        status_code, invalid_title = self._request(
            "POST",
            "/api/v1/memories",
            {"title": "  ", "content": private_text, "category": "note"},
        )
        self.assertEqual(status_code, 422)
        self.assertNotIn(private_text, json.dumps(invalid_title))
        self.assertEqual(invalid_title["detail"], "Invalid request data")

        status_code, invalid_category = self._request(
            "POST",
            "/api/v1/memories",
            {"title": "Titolo", "content": "Testo", "category": "cloud"},
        )
        self.assertEqual(status_code, 422)
        self.assertNotIn("cloud", json.dumps(invalid_category))

        status_code, too_long_query = self._request(
            "GET", f"/api/v1/memories?q={'x' * 201}"
        )
        self.assertEqual(status_code, 422)
        self.assertEqual(too_long_query["detail"], "Invalid request data")

    def test_missing_update_and_delete_return_not_found(self) -> None:
        status_code, _ = self._request(
            "PUT",
            "/api/v1/memories/missing-id",
            {"title": "Titolo", "content": "Testo", "category": "note"},
        )
        self.assertEqual(status_code, 404)

        status_code, _ = self._request("DELETE", "/api/v1/memories/missing-id")
        self.assertEqual(status_code, 404)

    def test_memory_survives_backend_restart(self) -> None:
        status_code, created = self._request(
            "POST",
            "/api/v1/memories",
            {
                "title": "Persistenza locale",
                "content": "Questo ricordo resta nel database SQLite.",
                "category": "progetti",
            },
        )
        self.assertEqual(status_code, 201)

        self._stop_server()
        self._start_server()

        status_code, restored = self._request(
            "GET", f"/api/v1/memories/{created['id']}"
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(restored["title"], "Persistenza locale")
        self.assertEqual(restored["content"], created["content"])

    def _start_server(self) -> None:
        environment = os.environ.copy()
        environment.update(
            {
                "JACK_ENV": "production",
                "JACK_HOST": "127.0.0.1",
                "JACK_PORT": str(self.port),
                "JACK_MEMORY_DB_PATH": str(self.database_path),
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
                self.fail("Backend test server exited during startup.")
            try:
                status_code, _ = self._request("GET", "/health", timeout=0.25)
                if status_code == 200:
                    return
            except (URLError, TimeoutError, ConnectionError):
                time.sleep(0.05)
        self.fail("Backend test server did not become ready.")

    def _stop_server(self) -> None:
        if self.server is None:
            return
        self.server.terminate()
        try:
            self.server.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.server.kill()
            self.server.wait(timeout=3)
        self.server = None

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
        decoded = json.loads(raw_body) if raw_body else None
        return response.status, decoded


def _free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


if __name__ == "__main__":
    unittest.main()
