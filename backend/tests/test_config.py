from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.core.config import Settings


class BackendConfigTests(unittest.TestCase):
    def _settings_for_host(self, host: str) -> Settings:
        values = {
            "JACK_ENV": "test",
            "JACK_HOST": host,
            "JACK_PORT": "8000",
            "JACK_LOG_LEVEL": "INFO",
            "JACK_CORS_ORIGINS": "http://127.0.0.1:8080",
        }
        with patch.dict(os.environ, values):
            return Settings.from_environment()

    def test_backend_binds_to_ipv4_localhost(self) -> None:
        self.assertEqual(self._settings_for_host("127.0.0.1").host, "127.0.0.1")

    def test_backend_rejects_other_bind_hosts(self) -> None:
        for host in ("localhost", "::1", "0.0.0.0", "192.168.1.20"):
            with self.subTest(host=host), self.assertRaisesRegex(
                ValueError, "127.0.0.1"
            ):
                self._settings_for_host(host)


if __name__ == "__main__":
    unittest.main()
