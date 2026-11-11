from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.system.backups import (
    LocalBackupService,
    BackupRestoreError,
)
from app.system.monitor import SystemMonitor
from app.system.security import SecurityPosture
from app.system.timezones import list_timezones

router = APIRouter(prefix="/system", tags=["system"])


def get_system_monitor(request: Request) -> SystemMonitor:
    return request.app.state.system_monitor


Monitor = Annotated[SystemMonitor, Depends(get_system_monitor)]


def get_backup_service(request: Request) -> LocalBackupService:
    return request.app.state.backup_service


BackupService = Annotated[LocalBackupService, Depends(get_backup_service)]


def get_security_posture(request: Request) -> SecurityPosture:
    return request.app.state.security_posture


SecurityStatus = Annotated[SecurityPosture, Depends(get_security_posture)]


@router.get("/monitor")
def read_system_monitor(monitor: Monitor) -> dict[str, object]:
    return monitor.snapshot()


@router.get("/security-status")
def read_security_status(posture: SecurityStatus) -> dict[str, object]:
    return posture.snapshot()


@router.get("/timezones")
def read_timezones() -> dict[str, list[str]]:
    return {"timezones": list_timezones()}


@router.get("/backups")
def list_local_backups(service: BackupService) -> dict[str, object]:
    return service.list_backups()


@router.post("/backups", status_code=status.HTTP_201_CREATED)
def create_local_backup(service: BackupService) -> dict[str, object]:
    return service.create_backup()


@router.post("/backups/{filename}/validate")
def validate_local_backup(
    filename: str, service: BackupService
) -> dict[str, object]:
    try:
        return service.validate_backup(filename)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/backups/{filename}/restore",
    status_code=status.HTTP_200_OK,
)
def restore_local_backup(
    filename: str,
    confirm: bool = False,
    service: BackupService = ...,
) -> dict[str, object]:
    """Ripristina un backup precedente.

    Richiede ``confirm=true`` per eseguire l'operazione distruttiva.
    Prima del ripristino viene creato un backup di sicurezza dello stato
    corrente e, in caso di fallimento, viene tentato il rollback automatico.
    """
    try:
        return service.restore_backup(filename, confirm=confirm)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except BackupRestoreError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
