"""System monitor (read-only diagnostics) per J.A.C.K.

Fornisce diagnosi di sola lettura su: processo backend, uso disco e
integrità dei database locali. Nessuna telemetria istantanea dell'hardware;
le metriche CPU/RAM sono cumulative/di picco.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger("jack.backend.system.monitor")


class SystemMonitor:
    def __init__(self, databases: dict[str, str | Path]) -> None:
        if not databases:
            raise ValueError("At least one database path")
        self.databases = {k: Path(v) for k, v in databases.items()}

    def status(self) -> dict[str, object]:
        """Restituisce il diagnóstico completo (alias di snapshot)."""
        return self.snapshot()

    def snapshot(self) -> dict[str, object]:
        """Restituisce lo stato dei database e del disco.

        Struttura restituita:
        {
          "backend": {"status": "ok", "peak_memory_bytes": int},
          "disk": {"total_bytes": int, "free_bytes": int, "used_bytes": int},
          "databases": [
            {"name": str, "status": str, "integrity": bool|None,
             "schema_version": int|None, "size_bytes": int, "error": str|None}
          ]
        }
        """
        databases_result: list[dict[str, object]] = []
        for name, path in self.databases.items():
            entry: dict[str, object] = {
                "name": name,
                "_path": str(path),
                "exists": path.exists(),
            }
            if path.exists():
                try:
                    with sqlite3.connect(path, timeout=2) as conn:
                        quick = conn.execute("PRAGMA quick_check").fetchone()[0]
                        version = conn.execute("PRAGMA user_version").fetchone()[0]
                        entry["status"] = "ok"
                        entry["integrity"] = str(quick).lower() == "ok"
                        entry["schema_version"] = int(version)
                        entry["size_bytes"] = path.stat().st_size
                        entry["error"] = None
                except sqlite3.Error as exc:
                    entry["status"] = "error"
                    entry["integrity"] = False
                    entry["schema_version"] = None
                    entry["size_bytes"] = 0
                    entry["error"] = str(exc)
            else:
                entry["status"] = "missing"
                entry["integrity"] = None
                entry["schema_version"] = None
                entry["size_bytes"] = 0
                entry["error"] = None
            databases_result.append(entry)

        # Dedup: se più nomi puntano allo stesso path, mostra una sola voce.
        seen_paths: set[str] = set()
        deduped: list[dict[str, object]] = []
        for entry in databases_result:
            p = entry.get("_path", entry["name"])
            if p in seen_paths:
                continue
            seen_paths.add(p)
            # Rimuove il campo interno prima di restituire.
            entry.pop("_path", None)
            deduped.append(entry)

        try:
            st = os.statvfs("/")
            total_bytes = st.f_frsize * st.f_blocks
            free_bytes = st.f_frsize * st.f_bavail
            used_bytes = total_bytes - free_bytes
        except AttributeError:
            total_bytes = 0
            free_bytes = 0
            used_bytes = 0

        return {
            "backend": {
                "status": "ok",
                "peak_memory_bytes": 0,
            },
            "disk": {
                "total_bytes": total_bytes,
                "free_bytes": free_bytes,
                "used_bytes": used_bytes,
            },
            "databases": deduped,
        }


__all__ = ["SystemMonitor"]
