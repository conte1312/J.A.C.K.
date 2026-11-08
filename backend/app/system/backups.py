from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import stat
import tempfile
import uuid
import zipfile
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_BACKUP_NAME = re.compile(r"^jack-backup-\d{8}T\d{6}Z-[0-9a-f]{12}\.zip$")


class LocalBackupService:
    """Creates private, consistent SQLite snapshots without modifying sources."""

    def __init__(
        self,
        database_paths: dict[str, str | Path],
        backup_directory: str | Path,
    ) -> None:
        if not database_paths:
            raise ValueError("At least one database path is required.")
        self._database_paths = {
            name: Path(path).expanduser().resolve()
            for name, path in database_paths.items()
        }
        filenames = [path.name for path in self._database_paths.values()]
        if len(filenames) != len(set(filenames)):
            raise ValueError("Database filenames must be unique in a backup.")
        self.backup_directory = Path(backup_directory).expanduser()

    def list_backups(self) -> dict[str, Any]:
        directory = self._ensure_backup_directory()
        backups = []
        for path in directory.iterdir():
            if path.is_symlink() or not path.is_file() or not _BACKUP_NAME.fullmatch(path.name):
                continue
            stat_result = path.stat()
            backups.append(
                {
                    "filename": path.name,
                    "created_at": datetime.fromtimestamp(
                        stat_result.st_mtime, timezone.utc
                    ).isoformat(),
                    "size_bytes": stat_result.st_size,
                }
            )
        backups.sort(key=lambda backup: backup["created_at"], reverse=True)
        return {"directory": str(directory.resolve()), "backups": backups}

    def create_backup(self) -> dict[str, Any]:
        directory = self._ensure_backup_directory()
        created_at = datetime.now(timezone.utc)
        timestamp = created_at.strftime("%Y%m%dT%H%M%SZ")
        filename = f"jack-backup-{timestamp}-{uuid.uuid4().hex[:12]}.zip"
        final_path = directory / filename

        with tempfile.TemporaryDirectory(
            prefix=".jack-backup-stage-", dir=directory
        ) as staging_name:
            staging = Path(staging_name)
            manifest_databases = []
            for name, source_path in self._database_paths.items():
                if not source_path.is_file():
                    raise FileNotFoundError(
                        f"Required local database is missing: {name}."
                    )
                snapshot_path = staging / source_path.name
                with sqlite3.connect(
                    f"{source_path.as_uri()}?mode=ro",
                    uri=True,
                    timeout=5,
                ) as source, sqlite3.connect(snapshot_path) as snapshot:
                    source.backup(snapshot)
                    check = snapshot.execute("PRAGMA quick_check").fetchone()
                    version = snapshot.execute("PRAGMA user_version").fetchone()
                    if check is None or check[0] != "ok":
                        raise sqlite3.DatabaseError(
                            f"SQLite integrity check failed for {name}."
                        )
                snapshot_path.chmod(0o600)
                manifest_databases.append(
                    {
                        "name": name,
                        "filename": source_path.name,
                        "schema_version": int(version[0]) if version else None,
                    }
                )

            manifest = {
                "format_version": 1,
                "created_at": created_at.isoformat(),
                "databases": manifest_databases,
            }
            temporary_zip = directory / f".{filename}.{uuid.uuid4().hex}.tmp"
            try:
                with zipfile.ZipFile(
                    temporary_zip,
                    mode="w",
                    compression=zipfile.ZIP_DEFLATED,
                    compresslevel=6,
                ) as archive:
                    archive.writestr(
                        "manifest.json",
                        json.dumps(manifest, ensure_ascii=False, indent=2),
                    )
                    for entry in manifest_databases:
                        archive.write(
                            staging / entry["filename"],
                            arcname=entry["filename"],
                        )
                temporary_zip.chmod(0o600)
                os.replace(temporary_zip, final_path)
            finally:
                temporary_zip.unlink(missing_ok=True)

        return {
            "filename": filename,
            "created_at": created_at.isoformat(),
            "size_bytes": final_path.stat().st_size,
            "directory": str(directory.resolve()),
        }

    def validate_backup(self, filename: str) -> dict[str, Any]:
        if not _BACKUP_NAME.fullmatch(filename):
            raise ValueError("Invalid local backup filename.")
        directory = self._ensure_backup_directory()
        backup_path = directory / filename
        if backup_path.is_symlink():
            raise ValueError("Backup archive must not be a symbolic link.")
        if not backup_path.is_file():
            raise FileNotFoundError("Local backup archive was not found.")

        expected_files = {
            database_path.name: name
            for name, database_path in self._database_paths.items()
        }
        with tempfile.TemporaryDirectory(prefix="jack-backup-validate-") as workdir:
            staging = Path(workdir)
            try:
                with zipfile.ZipFile(backup_path) as archive:
                    entries = archive.infolist()
                    entry_names = [entry.filename for entry in entries]
                    expected_entries = {"manifest.json", *expected_files}
                    if len(entry_names) != len(set(entry_names)) or set(
                        entry_names
                    ) != expected_entries:
                        raise ValueError("Backup archive entries do not match.")
                    for entry in entries:
                        mode = entry.external_attr >> 16
                        if entry.is_dir() or stat.S_ISLNK(mode):
                            raise ValueError(
                                "Backup archive contains an unsafe entry."
                            )
                        if entry.flag_bits & 0x1:
                            raise ValueError(
                                "Encrypted backup archives are not supported."
                            )
                        if entry.compress_type not in (
                            zipfile.ZIP_STORED,
                            zipfile.ZIP_DEFLATED,
                        ):
                            raise ValueError(
                                "Backup archive compression is not supported."
                            )
                    manifest_info = archive.getinfo("manifest.json")
                    if manifest_info.file_size > 1_000_000:
                        raise ValueError("Backup manifest is too large.")
                    manifest = json.loads(archive.read("manifest.json"))
                    if (
                        not isinstance(manifest, dict)
                        or manifest.get("format_version") != 1
                        or not isinstance(manifest.get("databases"), list)
                    ):
                        raise ValueError("Backup manifest is invalid.")

                    manifest_by_name: dict[str, dict[str, Any]] = {}
                    for item in manifest["databases"]:
                        if not isinstance(item, dict):
                            raise ValueError("Backup manifest is invalid.")
                        name = item.get("name")
                        stored_filename = item.get("filename")
                        if (
                            not isinstance(name, str)
                            or not isinstance(stored_filename, str)
                            or name not in self._database_paths
                            or stored_filename
                            != self._database_paths[name].name
                            or name in manifest_by_name
                        ):
                            raise ValueError("Backup manifest databases do not match.")
                        manifest_by_name[name] = item
                    if set(manifest_by_name) != set(self._database_paths):
                        raise ValueError("Backup manifest databases do not match.")

                    databases = []
                    for stored_filename, name in expected_files.items():
                        entry = archive.getinfo(stored_filename)
                        reserve_bytes = 10 * 1024 * 1024
                        if entry.file_size > max(
                            0, shutil.disk_usage(staging).free - reserve_bytes
                        ):
                            raise ValueError(
                                "Insufficient local disk space to validate backup."
                            )
                        snapshot_path = staging / stored_filename
                        copied = 0
                        with archive.open(entry) as source, snapshot_path.open(
                            "xb"
                        ) as destination:
                            while chunk := source.read(1024 * 1024):
                                copied += len(chunk)
                                if copied > entry.file_size:
                                    raise ValueError(
                                        "Backup database size does not match."
                                    )
                                destination.write(chunk)
                        if copied != entry.file_size:
                            raise ValueError("Backup database size does not match.")
                        with sqlite3.connect(
                            f"{snapshot_path.as_uri()}?mode=ro",
                            uri=True,
                            timeout=5,
                        ) as connection:
                            check = connection.execute("PRAGMA quick_check").fetchone()
                            version = connection.execute(
                                "PRAGMA user_version"
                            ).fetchone()
                        schema_version = int(version[0]) if version else None
                        declared_version = manifest_by_name[name].get(
                            "schema_version"
                        )
                        if (
                            check is None
                            or check[0] != "ok"
                            or declared_version != schema_version
                        ):
                            raise ValueError(
                                f"Backup database integrity check failed for {name}."
                            )
                        databases.append(
                            {
                                "name": name,
                                "filename": stored_filename,
                                "schema_version": schema_version,
                                "integrity": True,
                            }
                        )
            except (
                zipfile.BadZipFile,
                json.JSONDecodeError,
                KeyError,
                sqlite3.DatabaseError,
                EOFError,
                zlib.error,
                NotImplementedError,
                RuntimeError,
            ) as error:
                raise ValueError("Backup archive is invalid or corrupted.") from error

        return {
            "filename": filename,
            "valid": True,
            "databases": databases,
        }

    def _ensure_backup_directory(self) -> Path:
        directory = self.backup_directory
        if directory.is_symlink():
            raise OSError("Backup directory must not be a symbolic link.")
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not directory.is_dir():
            raise NotADirectoryError("Backup path is not a directory.")
        directory.chmod(0o700)
        return directory
