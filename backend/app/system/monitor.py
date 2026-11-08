from __future__ import annotations

import os
import resource
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SystemMonitor:
    """Collects read-only backend, SQLite, and local-disk diagnostics."""

    def __init__(self, database_paths: dict[str, str | Path]) -> None:
        self._database_paths: dict[str, Path] = {}
        seen: set[Path] = set()
        for label, raw_path in database_paths.items():
            path = Path(raw_path).expanduser().resolve()
            if path not in seen:
                self._database_paths[label] = path
                seen.add(path)
        if not self._database_paths:
            raise ValueError("At least one database path is required.")

    def snapshot(self) -> dict[str, Any]:
        databases = [
            self._inspect_database(label, path)
            for label, path in self._database_paths.items()
        ]
        disk_path = next(iter(self._database_paths.values())).parent
        disk = shutil.disk_usage(disk_path)
        usage = resource.getrusage(resource.RUSAGE_SELF)
        peak_memory = int(usage.ru_maxrss)
        if sys.platform != "darwin":
            peak_memory *= 1024
        return {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "backend": {
                "status": "ok",
                "pid": os.getpid(),
                "cpu_user_seconds": round(usage.ru_utime, 3),
                "cpu_system_seconds": round(usage.ru_stime, 3),
                "peak_memory_bytes": peak_memory,
            },
            "disk": {
                "total_bytes": disk.total,
                "free_bytes": disk.free,
                "used_bytes": disk.used,
            },
            "databases": databases,
        }

    @staticmethod
    def _inspect_database(label: str, path: Path) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": label,
            "status": "missing",
            "size_bytes": None,
            "schema_version": None,
            "integrity": None,
        }
        try:
            result["size_bytes"] = path.stat().st_size
        except FileNotFoundError:
            return result
        except OSError as error:
            result.update(status="error", error=str(error))
            return result

        try:
            with sqlite3.connect(
                f"{path.as_uri()}?mode=ro",
                uri=True,
                timeout=1,
            ) as connection:
                check = connection.execute("PRAGMA quick_check").fetchone()
                version = connection.execute("PRAGMA user_version").fetchone()
            integrity_ok = check is not None and check[0] == "ok"
            result.update(
                status="ok" if integrity_ok else "error",
                integrity=integrity_ok,
                schema_version=int(version[0]) if version is not None else None,
            )
            if not integrity_ok:
                result["error"] = "SQLite quick_check reported an integrity problem."
        except sqlite3.Error as error:
            result.update(status="error", error=str(error))
        return result
