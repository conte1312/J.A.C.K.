"""Backend startup tests for J.A.C.K. 2.0.

Avvia il server FastAPI su una porta libera (pattern già usato dai test V1)
e verifica che l'applicazione costruisca, si leghi a loopback e risponda
alle health check. Nessun servizio esterno, nessun segreto, nessuna rete.
"""

from __future__ import annotations

import socket
import threading
import unittest

import uvicorn

from app.main import app


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestBackendStartup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        config = uvicorn.Config(
            app, host="127.0.0.1", port=cls.port, log_level="error"
        )
        cls.server = uvicorn.Server(config)
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()
        # Attendi che il server sia pronto.
        import time
        import urllib.request

        url = f"http://127.0.0.1:{cls.port}/health"
        for _ in range(50):
            try:
                with urllib.request.urlopen(url, timeout=1) as _r:
                    return
            except Exception:
                time.sleep(0.1)
        raise RuntimeError("Il server di test non si è avviato.")

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True

    def _get(self, path: str):
        import urllib.request
        import json

        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}{path}", timeout=2
        ) as response:
            return response.status, json.loads(response.read().decode())

    def test_health_endpoint(self):
        status, data = self._get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")

    def test_api_v1_health(self):
        status, data = self._get("/api/v1/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["api"], "v1")

    def test_api_v2_health(self):
        status, data = self._get("/api/v2/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["api"], "v2")
        self.assertEqual(data["version"], "2.0.0")

    def test_api_v2_info(self):
        status, data = self._get("/api/v2/info")
        self.assertEqual(status, 200)
        self.assertEqual(data["api"], "v2")
        self.assertEqual(data["version"], "2.0.0")
        self.assertEqual(data["bind"], "127.0.0.1")

    def test_bind_is_loopback(self):
        self.assertEqual(self.server.config.host, "127.0.0.1")

    def test_app_version(self):
        from app import __version__
        self.assertEqual(__version__, "2.0.0")


class TestContextBuilderWiring(unittest.TestCase):
    """Verifica che ContextBuilder sia iniettato nel ConversationService
    durante il normale avvio applicativo tramite create_app()."""

    def test_context_builder_injected_in_conversation_service(self):
        import tempfile
        from pathlib import Path

        from app.main import create_app
        from app.memory.repository import MemoryRepository
        from app.conversations.repository import ConversationRepository
        from app.knowledge.repository import KnowledgeRepository
        from app.knowledge.context_builder import ContextBuilder

        temp_dir = tempfile.TemporaryDirectory(prefix="jack-wiring-test-")

        mem_db_path = Path(temp_dir.name) / "memory.sqlite3"
        kb_db_path = Path(temp_dir.name) / "knowledge.sqlite3"
        conv_db_path = Path(temp_dir.name) / "conversations.sqlite3"

        mem_repo = MemoryRepository(mem_db_path)
        mem_repo.initialize()
        kb_repo = KnowledgeRepository(kb_db_path)
        kb_repo.initialize()
        conv_repo = ConversationRepository(conv_db_path)
        conv_repo.initialize()

        try:
            app = create_app(
                memory_repository=mem_repo,
                knowledge_repository=kb_repo,
                conversation_repository=conv_repo,
            )

            self.assertIsNotNone(app.state.conversation_service)
            self.assertIsNotNone(app.state.conversation_service.context_builder)
            self.assertIsInstance(
                app.state.conversation_service.context_builder, ContextBuilder
            )
        finally:
            temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
