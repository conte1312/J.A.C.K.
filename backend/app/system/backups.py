"""Local backup service (M5 Punto 1 — Affidabilità Locale).

Fornisce:
- Creazione di snapshot ZIP atomici con manifest JSON e verifica integrità SQLite.
- Validazione completa degli archivi: path traversal, manifest, schema versioni,
  integrità dei database, database opzionali, protezione da archivi malevoli.
- Ripristino controllato con backup di sicurezza automatico, quiescenza servizi,
  rollback automatico e verifica finale dei database.
- Protezione contro path traversal, archivi corrotti, entry unsafe, file non ZIP.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from typing import Any

logger = logging.getLogger("jack.backend.system.backups")

# Versioni del formato di archivio supportate.
SUPPORTED_FORMAT_VERSIONS = (1, 2)
ARCHIVE_FORMAT_VERSION = 2

# Prefisso per directory di staging atomico.
STAGING_PREFIX = ".jack-backup-stage-"

# Prefisso per file di backup.
BACKUP_PREFIX = "jack-backup-"

# Permessi: directory 0o700, file 0o600 (solo proprietario).
BACKUP_DIR_MODE = 0o700
BACKUP_FILE_MODE = 0o600

# Nomi di entry non ammessi nell'archivio (path traversal).
FORBIDDEN_ENTRY_PREFIXES = ("..", "/")


class BackupError(Exception):
    """Errore generico del servizio backup."""


class BackupValidationError(BackupError):
    """Errore di validazione di un archivio backup."""


class BackupRestoreError(BackupError):
    """Errore durante il ripristino di un backup."""


class LocalBackupService:
    """Servizio di backup locale per database SQLite di J.A.C.K.

    Tutti gli archivi sono ZIP con:
    - ``manifest.json``: metadati (formato, timestamp, database, versioni schema)
    - uno file per database, con nome corrispondente al nome fisico originale
    """

    def __init__(
        self,
        databases: dict[str, str | Path],
        backup_dir: str | Path,
        optional_database_names: frozenset[str] | None = None,
    ) -> None:
        self.databases = {k: Path(v) for k, v in databases.items()}
        self.backup_dir = Path(backup_dir)
        self.optional = optional_database_names or frozenset()

        # Valida unicità dei nomi file di database.
        filenames = [p.name for p in self.databases.values()]
        if len(filenames) != len(set(filenames)):
            raise ValueError("Database filenames must be unique")

    # ------------------------------------------------------------------
    # Creazione backup
    # ------------------------------------------------------------------

    def create_backup(self) -> dict[str, object]:
        """Crea un backup ZIP atomico di tutti i database configurati.

        Ogni database deve esistere e passare ``PRAGMA quick_check``.
        L'archivio viene scritto in una directory di staging temporanea e
        spostato in modo atomico solo se tutte le verifiche superano.

        Returns:
            Dizionario con ``filename`` (nome del file ZIP creato).

        Raises:
            FileNotFoundError: se un database configurato non esiste.
            sqlite3.DatabaseError: se un database non passa l'integrità.
            BackupError: per altri errori durante la creazione.
        """
        self._ensure_backup_dir()

        # Verifica che tutti i database esistano e siano integri prima di iniziare.
        for name, path in self.databases.items():
            if not path.exists():
                raise FileNotFoundError(
                    f"Database '{name}' not found at {path}"
                )
            self._verify_database_integrity(path)

        # Nome del file di backup: timestamp UTC + identificativo breve.
        from datetime import datetime, timezone

        stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        short_id = hashlib.sha256(
            os.urandom(16)
        ).hexdigest()[:12]
        filename = f"{BACKUP_PREFIX}{stamp}-{short_id}.zip"

        # Directory di staging atomica all'interno di backup_dir.
        staging_dir = self.backup_dir / f"{STAGING_PREFIX}{short_id}"
        staging_dir.mkdir(mode=BACKUP_DIR_MODE, exist_ok=False)

        try:
            archive_path = staging_dir / filename
            databases_meta: list[dict[str, object]] = []

            with zipfile.ZipFile(
                archive_path, "w", zipfile.ZIP_DEFLATED
            ) as archive:
                for name, path in self.databases.items():
                    version = self._read_schema_version(path)
                    databases_meta.append(
                        {
                            "name": name,
                            "filename": path.name,
                            "schema_version": version,
                        }
                    )
                    archive.write(path, arcname=path.name)

                manifest = {
                    "format_version": ARCHIVE_FORMAT_VERSION,
                    "created_at": f"{stamp}",
                    "databases": databases_meta,
                }
                archive.writestr(
                    "manifest.json", json.dumps(manifest, indent=2)
                )

            # Imposta permessi 0o600 sul file ZIP.
            archive_path.chmod(BACKUP_FILE_MODE)

            # Spostamento atomico dallo staging alla directory finale.
            final_path = self.backup_dir / filename
            os.replace(archive_path, final_path)

            logger.info(
                "Backup creato: %s (%d database)", filename, len(databases_meta)
            )
            return {"filename": filename}
        except Exception:
            # Pulizia staging in caso di errore.
            self._cleanup_staging(staging_dir)
            raise
        finally:
            # Assicura che la directory di staging venga rimossa anche se vuota.
            try:
                staging_dir.rmdir()
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Validazione backup
    # ------------------------------------------------------------------

    def validate_backup(self, filename: str) -> dict[str, object]:
        """Valida un archivio backup esistente.

        Esegue controlli di:
        - nome file valido (no path traversal)
        - esistenza del file
        - archivio ZIP valido
        - entry attese (nessuna path traversal, nessun file extra)
        - manifest JSON valido con formato supportato
        - integrità di ogni database tramite ``PRAGMA quick_check``
        - versione schema leggibile
        - database opzionali mancanti segnalati ma non bloccanti

        Args:
            filename: nome del file ZIP nella backup directory.

        Returns:
            Dizionario con:
            - ``valid``: bool
            - ``missing_optional_databases``: lista di nomi opzionali assenti
            - ``databases``: lista di dict con ``name``, ``integrity``, ``schema_version``

        Raises:
            FileNotFoundError: se il file non esiste.
            ValueError: se il filename è invalido o l'archivio è corrotto.
        """
        self._validate_filename(filename)

        archive_path = self.backup_dir / filename
        if not archive_path.exists():
            raise FileNotFoundError(f"Backup not found: {filename}")

        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                # Controllo entry: nessuna path traversal, nessun file extra.
                names = archive.namelist()
                expected = {"manifest.json"}
                expected.update(p.name for p in self.databases.values())

                for name in names:
                    if any(name.startswith(p) for p in FORBIDDEN_ENTRY_PREFIXES):
                        raise ValueError(
                            "entries do not match manifest"
                        )
                    if name not in expected:
                        raise ValueError(
                            "entries do not match manifest"
                        )

                # Leggi e valida manifest.
                try:
                    manifest_raw = archive.read("manifest.json")
                    manifest = json.loads(manifest_raw)
                except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                    raise ValueError(
                        "invalid or corrupted manifest"
                    ) from exc

                if not isinstance(manifest, dict):
                    raise ValueError("Invalid manifest structure")
                if manifest.get("format_version") not in SUPPORTED_FORMAT_VERSIONS:
                    raise ValueError(
                        f"Unsupported format version: {manifest.get('format_version')}"
                    )

                manifest_dbs = manifest.get("databases", [])
                if not isinstance(manifest_dbs, list):
                    raise ValueError("Invalid manifest databases")

                # Estrai database in una directory temporanea per integrità.
                with tempfile.TemporaryDirectory(
                    prefix="jack-backup-validate-"
                ) as tmp_dir:
                    tmp_path = Path(tmp_dir)

                    for entry in manifest_dbs:
                        db_name = entry.get("name")
                        db_filename = entry.get("filename")
                        if not db_name or not db_filename:
                            raise ValueError(
                                "Invalid manifest database entry"
                            )

                        # Estrai il database nel temp dir.
                        db_data = archive.read(db_filename)
                        staged_db = tmp_path / db_filename
                        staged_db.write_bytes(db_data)

                        # Verifica integrità SQLite.
                        try:
                            with sqlite3.connect(str(staged_db)) as conn:
                                quick = conn.execute(
                                    "PRAGMA quick_check"
                                ).fetchone()[0]
                                version = conn.execute(
                                    "PRAGMA user_version"
                                ).fetchone()[0]
                        except sqlite3.DatabaseError as exc:
                            raise ValueError(
                                f"invalid or corrupted database: {db_name}"
                            ) from exc

                        if str(quick).lower() != "ok":
                            raise ValueError(
                                f"Database integrity check failed: {db_name}"
                            )

                # Determina database opzionali mancanti.
                present_filenames = {
                    entry.get("filename") for entry in manifest_dbs
                }
                missing_optional: list[str] = []
                for name, path in self.databases.items():
                    if name in self.optional and path.name not in present_filenames:
                        missing_optional.append(name)

                # Costruisci lista database per il risultato.
                databases_result: list[dict[str, object]] = []
                for entry in manifest_dbs:
                    databases_result.append(
                        {
                            "name": entry.get("name", ""),
                            "integrity": True,
                            "schema_version": int(entry.get("schema_version", 0)),
                        }
                    )

                return {
                    "valid": True,
                    "missing_optional_databases": missing_optional,
                    "databases": databases_result,
                }

        except zipfile.BadZipFile as exc:
            raise ValueError(
                "invalid or corrupted archive"
            ) from exc

    # ------------------------------------------------------------------
    # Ripristino backup (M5 Punto 1)
    # ------------------------------------------------------------------

    def restore_backup(
        self,
        filename: str,
        *,
        confirm: bool = False,
        quiesce_services: bool = True,
    ) -> dict[str, object]:
        """Ripristina un backup con verifica, backup di sicurezza e rollback.

        Il flusso è:
        1. Verifica che ``filename`` sia valido e che l'archivio esista.
        2. Se ``confirm`` è False, solleva errore (operazione richiede conferma).
        3. Crea un backup di sicurezza dello stato corrente prima del ripristino.
        4. Quiescenza servizi (se richiesta) — segna i database come non disponibili.
        5. Estrai l'archivio in una directory di staging.
        6. Verifica integrità di ogni database estratto.
        7. Sostituisci i database correnti con quelli estratti.
        8. Verifica finale dei database ripristinati.
        9. In caso di errore in qualsiasi fase, rollback allo stato precedente.

        Args:
            filename: nome del file ZIP da ripristinare.
            confirm: deve essere True per eseguire il ripristino.
            quiesce_services: se True, segnala che i servizi sono messi in pausa.

        Returns:
            Dizionario con esito dell'operazione.

        Raises:
            ValueError: se confirm è False o filename invalido.
            FileNotFoundError: se il backup non esiste.
            BackupRestoreError: se il ripristino fallisce (con rollback tentato).
        """
        if not confirm:
            raise ValueError(
                "Restore requires explicit confirmation (confirm=True)"
            )

        self._validate_filename(filename)
        archive_path = self.backup_dir / filename
        if not archive_path.exists():
            raise FileNotFoundError(f"Backup not found: {filename}")

        # Valida l'archivio prima di qualsiasi modifica.
        validation = self.validate_backup(filename)
        if not validation["valid"]:
            raise BackupRestoreError(
                "Cannot restore invalid backup archive"
            )

        # Fase 1: backup di sicurezza dello stato corrente.
        safety_backup = self._create_safety_backup()

        # Fase 2: quiescenza servizi (se richiesta).
        if quiesce_services:
            self._quiesce_services()

        # Fase 3: estrai in staging.
        staging_dir = self.backup_dir / f"{STAGING_PREFIX}restore-{os.urandom(8).hex()}"
        staging_dir.mkdir(mode=BACKUP_DIR_MODE, exist_ok=False)

        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                archive.extractall(staging_dir)

            # Leggi manifest dallo staging.
            manifest_path = staging_dir / "manifest.json"
            if not manifest_path.exists():
                raise BackupRestoreError("Missing manifest in backup archive")

            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            # Fase 4: verifica integrità di ogni database estratto.
            for entry in manifest.get("databases", []):
                db_filename = entry.get("filename")
                if not db_filename:
                    continue
                staged_db = staging_dir / db_filename
                if not staged_db.exists():
                    raise BackupRestoreError(
                        f"Missing database in archive: {db_filename}"
                    )
                self._verify_database_integrity(staged_db)

            # Fase 5: sostituisci i database correnti.
            restored_files: list[Path] = []
            original_backups: dict[str, Path] = {}

            try:
                for entry in manifest.get("databases", []):
                    db_filename = entry.get("filename")
                    if not db_filename:
                        continue
                    staged_db = staging_dir / db_filename

                    # Trova il nome logico del database dal filename.
                    logical_name = None
                    for name, path in self.databases.items():
                        if path.name == db_filename:
                            logical_name = name
                            break
                    if logical_name is None:
                        continue

                    current_path = self.databases[logical_name]

                    # Backup di sicurezza del file corrente prima di sovrascrivere.
                    safety_path = current_path.with_suffix(
                        current_path.suffix + ".jack-safety"
                    )
                    if current_path.exists():
                        shutil.copy2(current_path, safety_path)
                        original_backups[logical_name] = safety_path

                    # Sostituzione atomica.
                    os.replace(staged_db, current_path)
                    restored_files.append(current_path)

                # Fase 6: verifica finale dei database ripristinati.
                for logical_name in list(original_backups.keys()):
                    current_path = self.databases[logical_name]
                    self._verify_database_integrity(current_path)

                logger.info(
                    "Backup ripristinato: %s (%d database)",
                    filename,
                    len(restored_files),
                )

                return {
                    "restored": True,
                    "filename": filename,
                    "databases_restored": len(restored_files),
                    "safety_backup": safety_backup,
                }

            except Exception as exc:
                # Rollback: ripristina i file originali dai backup di sicurezza.
                logger.error("Restore failed, rolling back: %s", exc)
                for logical_name, safety_path in original_backups.items():
                    current_path = self.databases[logical_name]
                    try:
                        if safety_path.exists():
                            shutil.copy2(safety_path, current_path)
                            # Pulisci file di sicurezza.
                            safety_path.unlink()
                    except OSError:
                        logger.exception(
                            "Rollback failed for %s", logical_name
                        )
                raise BackupRestoreError(
                    f"Restore failed and rollback attempted: {exc}"
                ) from exc
            finally:
                # Pulisci backup di sicurezza temporanei.
                for safety_path in original_backups.values():
                    try:
                        if safety_path.exists():
                            safety_path.unlink()
                    except OSError:
                        pass
                # Pulisci directory di staging.
                self._cleanup_staging(staging_dir)

        except Exception:
            self._cleanup_staging(staging_dir)
            raise

    # ------------------------------------------------------------------
    # List backup
    # ------------------------------------------------------------------

    def list_backups(self) -> dict[str, object]:
        """Elenca i backup disponibili nella directory di backup.

        Returns:
            Dizionario con:
            - ``backups``: lista di dict con ``filename`` e ``size_bytes``
            - ``directory``: path assoluto della directory di backup

        Raises:
            OSError: se la directory è un symlink (protezione).
        """
        # Protezione: se la directory di backup è un symlink, rifiuta.
        if self.backup_dir.is_symlink():
            raise OSError("symbolic link directory not allowed")

        self._ensure_backup_dir()

        backups: list[dict[str, object]] = []
        for path in sorted(self.backup_dir.glob("*.zip")):
            if path.is_file():
                backups.append(
                    {
                        "filename": path.name,
                        "size_bytes": path.stat().st_size,
                    }
                )

        return {
            "backups": backups,
            "directory": str(self.backup_dir.resolve()),
        }

    # ------------------------------------------------------------------
    # Helpers interni
    # ------------------------------------------------------------------

    def _ensure_backup_dir(self) -> None:
        """Crea la directory di backup se non esiste, con permessi 0o700."""
        if self.backup_dir.is_symlink():
            raise OSError("symbolic link directory not allowed")
        self.backup_dir.mkdir(mode=BACKUP_DIR_MODE, exist_ok=True)

    def _validate_filename(self, filename: str) -> None:
        """Valida che il nome file sia sicuro (no path traversal)."""
        if not filename or ".." in filename or filename.startswith("/"):
            raise ValueError("Invalid local backup filename")
        if Path(filename).name != filename:
            raise ValueError("Invalid local backup filename")

    def _verify_database_integrity(self, path: Path) -> None:
        """Verifica che un file SQLite sia un database valido e integro."""
        if not path.exists():
            raise FileNotFoundError(f"Database not found: {path}")
        try:
            with sqlite3.connect(str(path), timeout=2) as conn:
                quick = conn.execute("PRAGMA quick_check").fetchone()[0]
                if str(quick).lower() != "ok":
                    raise sqlite3.DatabaseError(
                        f"file is not a database"
                    )
        except sqlite3.DatabaseError as exc:
            raise sqlite3.DatabaseError(
                f"file is not a database: {path}"
            ) from exc

    def _read_schema_version(self, path: Path) -> int:
        """Legge la versione schema (PRAGMA user_version) di un database."""
        with sqlite3.connect(str(path), timeout=2) as conn:
            return int(conn.execute("PRAGMA user_version").fetchone()[0])

    def _create_safety_backup(self) -> dict[str, object]:
        """Crea un backup di sicurezza prima di un'operazione distruttiva.

        Usa lo stesso meccanismo di create_backup ma con un nome distinto.
        """
        return self.create_backup()

    def _quiesce_services(self) -> None:
        """Segna i servizi come messi in pausa per il ripristino.

        Questa è una hook che può essere estesa per notificare i servizi
        in esecuzione di sospendere le operazioni sui database.
        """
        logger.info("Servizi messi in quiescenza per ripristino backup")

    def _cleanup_staging(self, staging_dir: Path) -> None:
        """Rimuove una directory di staging e tutto il suo contenuto."""
        try:
            shutil.rmtree(staging_dir, ignore_errors=True)
        except OSError:
            pass


__all__ = [
    "LocalBackupService",
    "BackupError",
    "BackupValidationError",
    "BackupRestoreError",
    "ARCHIVE_FORMAT_VERSION",
]
