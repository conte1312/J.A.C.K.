from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BACKEND_DIR = Path(__file__).resolve().parents[1]


class ConversationsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            prefix="jack-conversations-api-test-"
        )
        self.database_path = Path(self.temporary_directory.name) / "test.sqlite3"
        self.port = _free_local_port()
        self.server: subprocess.Popen[bytes] | None = None
        self._start_server()

    def tearDown(self) -> None:
        self._stop_server()
        self.temporary_directory.cleanup()

    def _start_server(self) -> None:
        environment = os.environ.copy()
        environment.update(
            {
                "JACK_ENV": "production",
                "JACK_HOST": "127.0.0.1",
                "JACK_PORT": str(self.port),
                "JACK_LOG_LEVEL": "warning",
                "JACK_MEMORY_DB_PATH": str(self.database_path),
                "JACK_CONTROL_PLANE_DB_PATH": str(
                    Path(self.temporary_directory.name) / "control-plane.sqlite3"
                ),
                "JACK_AI_SETTINGS_PATH": str(
                    Path(self.temporary_directory.name) / "ai_settings.json"
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

    def _create_conversation(self, title: str = "Test") -> str:
        status_code, conversation = self._request(
            "POST",
            "/api/v1/conversations",
            {"title": title, "provider_id": "nvidia", "model_id": "nvidia/nemotron-3.5-lightning-30b-a3b"},
        )
        self.assertEqual(status_code, 201)
        self.assertEqual(conversation["title"], title)
        return conversation["id"]

    def test_health_and_conversations_start_empty(self) -> None:
        status_code, health = self._request("GET", "/health")
        self.assertEqual(status_code, 200)
        self.assertEqual(health["status"], "ok")

        status_code, conversations = self._request(
            "GET", "/api/v1/conversations"
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(conversations, [])

    def test_create_list_get_rename_and_delete_conversation(self) -> None:
        conversation_id = self._create_conversation("Progetto Atlas")

        status_code, conversations = self._request(
            "GET", "/api/v1/conversations"
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(len(conversations), 1)
        self.assertEqual(conversations[0]["id"], conversation_id)
        self.assertEqual(conversations[0]["title"], "Progetto Atlas")
        self.assertEqual(conversations[0]["provider_id"], "nvidia")
        self.assertEqual(
            conversations[0]["model_id"],
            "nvidia/nemotron-3.5-lightning-30b-a3b",
        )
        self.assertEqual(conversations[0]["message_count"], 0)

        status_code, detail = self._request(
            "GET", f"/api/v1/conversations/{conversation_id}"
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(detail["conversation"]["id"], conversation_id)
        self.assertEqual(detail["messages"], [])

        status_code, updated = self._request(
            "PUT",
            f"/api/v1/conversations/{conversation_id}/title",
            {"title": "Atlas Rinominata"},
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(updated["title"], "Atlas Rinominata")

        status_code, _ = self._request(
            "DELETE", f"/api/v1/conversations/{conversation_id}"
        )
        self.assertEqual(status_code, 204)

        status_code, conversations = self._request("GET", "/api/v1/conversations")
        self.assertEqual(status_code, 200)
        self.assertEqual(conversations, [])

    def test_add_and_retrieve_messages(self) -> None:
        conversation_id = self._create_conversation("Chat")

        status_code, message = self._request(
            "POST",
            f"/api/v1/conversations/{conversation_id}/messages",
            {"role": "user", "content": "Ciao Nemotron"},
        )
        self.assertEqual(status_code, 201)
        self.assertEqual(message["role"], "user")
        self.assertEqual(message["content"], "Ciao Nemotron")

        status_code, detail = self._request(
            "GET", f"/api/v1/conversations/{conversation_id}"
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(detail["conversation"]["message_count"], 1)
        self.assertEqual(len(detail["messages"]), 1)
        self.assertEqual(detail["messages"][0]["content"], "Ciao Nemotron")

    def test_missing_conversation_returns_404(self) -> None:
        status_code, _ = self._request("GET", "/api/v1/conversations/inesistente")
        self.assertEqual(status_code, 404)

        status_code, _ = self._request(
            "DELETE", "/api/v1/conversations/inesistente"
        )
        self.assertEqual(status_code, 404)

    def test_chat_without_nvidia_key_returns_error(self) -> None:
        conversation_id = self._create_conversation("Chat")
        status_code, body = self._request(
            "POST",
            f"/api/v1/conversations/{conversation_id}/chat",
            {
                "model_id": "nvidia/nemotron-3.5-lightning-30b-a3b",
                "messages": [{"role": "user", "content": "Ciao"}],
            },
        )
        # Senza una API key NVIDIA valida configurata, il provider rifiuta la richiesta.
        self.assertIn(status_code, (401, 409, 422))
        self.assertIsInstance(body, dict)


def _free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


if __name__ == "__main__":
    unittest.main()
