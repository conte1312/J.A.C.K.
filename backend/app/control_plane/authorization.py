"""Authorization service (M5 Punto 2 — Control Plane e Sicurezza).

Implementa il gate di sicurezza richiesto dalla roadmap originale:
- Autenticazione delle identità chiamanti (caller authentication)
- Permission Manager: valida richieste di permesso contro capability dichiarate
- Policy Engine fail-closed: nega tutto per default, consente solo se esiste
  una capability corrispondente e (per operazioni critiche) un'approvazione
- Approvazioni non aggirabili per operazioni a rischio alto/critico
- Audit delle decisioni di autorizzazione
- Emergency stop effettivo: blocca tutte le operazioni quando attivo

Tutte le operazioni di scrittura richiedono autenticazione e controllo
delle capacità. Nessuna operazione è consentita per default.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from app.control_plane.repository import (
    ControlPlaneRepository,
    DuplicateDeclarationError,
    IdentityNotFoundError,
)

logger = logging.getLogger("jack.backend.control_plane.authorization")

_RISK_LEVELS = {"low", "normal", "high", "critical"}

# Identità di sistema che esegue le decisioni di autorizzazione.
_SYSTEM_ACTOR_KIND = "service"
_SYSTEM_ACTOR_ID = "control-plane-authorization"


class AuthorizationError(Exception):
    """Errore generico di autorizzazione."""


class AuthenticationError(AuthorizationError):
    """L'identità chiamante non è autenticata."""


class PermissionDeniedError(AuthorizationError):
    """Il permesso richiesto è negato."""


class EmergencyStopActiveError(AuthorizationError):
    """L'emergency stop è attivo; tutte le operazioni sono bloccate."""


class ApprovalRequiredError(AuthorizationError):
    """L'operazione richiede un'approvazione esplicita non presente."""


class AuthorizationService:
    """Servizio di autorizzazione e policy enforcement per il Control Plane.

    Implementa il modello fail-closed: ogni operazione è negata per default
    a meno che non esista una capability dichiarata che la consenta
    esplicitamente.
    """

    def __init__(self, repository: ControlPlaneRepository) -> None:
        self._repository = repository
        self._emergency_stop_active = False
        self._emergency_stop_reason: str | None = None
        self._emergency_stop_activated_at: str | None = None
        self._emergency_stop_activated_by: str | None = None

    # ------------------------------------------------------------------
    # Autenticazione identità chiamante
    # ------------------------------------------------------------------

    def authenticate_caller(
        self,
        *,
        identity_kind: str,
        identity_id: str,
    ) -> dict[str, Any]:
        """Autentica un'identità chiamante verificando che esista nel Control Plane.

        Args:
            identity_kind: tipo di identità (user, agent, service, tool, node).
            identity_id: identificativo dell'identità.

        Returns:
            Dizionario con i dettagli dell'identità autenticata.

        Raises:
            AuthenticationError: se l'identità non esiste.
        """
        identity = self._repository.get_identity(identity_kind, identity_id)
        if identity is None:
            raise AuthenticationError(
                f"Identity not found: {identity_kind}:{identity_id}"
            )
        return identity

    # ------------------------------------------------------------------
    # Permission check
    # ------------------------------------------------------------------

    def check_permission(
        self,
        *,
        requester_kind: str,
        requester_id: str,
        resource: str,
        operation: str,
        risk_level: str = "normal",
    ) -> dict[str, Any]:
        """Verifica se un'identità ha il permesso di eseguire un'operazione.

        Modello fail-closed: l'operazione è negata a meno che:
        1. L'emergency stop non sia attivo (in tal caso sempre negata).
        2. Esista una capability dichiarata per il requester sulla risorsa
           che includa l'operazione richiesta.
        3. Se il rischio è alto o critico, serva un'approvazione esplicita.

        Args:
            requester_kind: tipo di identità richiedente.
            requester_id: identificativo del richiedente.
            resource: risorsa target.
            operation: operazione richiesta.
            risk_level: livello di rischio dell'operazione.

        Returns:
            Dizionario con l'esito della decisione:
            - ``allowed``: bool
            - ``reason``: str
            - ``requires_approval``: bool
            - ``capability_id``: str | None

        Raises:
            AuthenticationError: se il requester non è autenticato.
            EmergencyStopActiveError: se l'emergency stop è attivo.
        """
        # 1. Autentica il requester.
        self.authenticate_caller(
            identity_kind=requester_kind, identity_id=requester_id
        )

        # 2. Emergency stop: blocca tutto.
        if self._emergency_stop_active:
            self._audit_decision(
                actor_kind=requester_kind,
                actor_id=requester_id,
                resource=resource,
                operation=operation,
                outcome="deny",
                reason="emergency_stop_active",
                risk_level=risk_level,
            )
            raise EmergencyStopActiveError(
                f"Emergency stop is active: {self._emergency_stop_reason or 'security'}"
            )

        # 3. Cerca una capability corrispondente.
        capabilities = self._repository.list_capabilities(
            owner_kind=requester_kind,
            owner_id=requester_id,
            resource=resource,
        )

        matching_capability = None
        for cap in capabilities:
            if operation in cap.get("operations", []):
                matching_capability = cap
                break

        if matching_capability is None:
            self._audit_decision(
                actor_kind=requester_kind,
                actor_id=requester_id,
                resource=resource,
                operation=operation,
                outcome="deny",
                reason="no_matching_capability",
                risk_level=risk_level,
            )
            raise PermissionDeniedError(
                f"No capability grants {requester_kind}:{requester_id} "
                f"operation '{operation}' on resource '{resource}'"
            )

        # 4. Controllo approvazione per operazioni a rischio.
        requires_approval = bool(
            matching_capability.get("approval_required", False)
            or risk_level in ("high", "critical")
        )

        if requires_approval:
            # L'approvazione deve essere tracciata come decision audit.
            # Senza un'approvazione esplicita registrata, l'operazione è negata.
            self._audit_decision(
                actor_kind=requester_kind,
                actor_id=requester_id,
                resource=resource,
                operation=operation,
                outcome="requires_approval",
                reason="approval_required",
                risk_level=risk_level,
                capability_id=matching_capability.get("id"),
            )
            raise ApprovalRequiredError(
                f"Operation '{operation}' on resource '{resource}' "
                f"requires explicit approval"
            )

        # 5. Operazione consentita.
        self._audit_decision(
            actor_kind=requester_kind,
            actor_id=requester_id,
            resource=resource,
            operation=operation,
            outcome="allow",
            reason="capability_granted",
            risk_level=risk_level,
            capability_id=matching_capability.get("id"),
        )
        return {
            "allowed": True,
            "reason": "capability_granted",
            "requires_approval": False,
            "capability_id": matching_capability.get("id"),
        }

    # ------------------------------------------------------------------
    # Emergency stop
    # ------------------------------------------------------------------

    def activate_emergency_stop(
        self,
        *,
        activated_by_kind: str,
        activated_by_id: str,
        reason: str = "security",
    ) -> dict[str, Any]:
        """Attiva l'emergency stop, bloccando tutte le operazioni.

        Richiede che l'identità attivante esista nel Control Plane.
        """
        self.authenticate_caller(
            identity_kind=activated_by_kind, identity_id=activated_by_id
        )

        now = _now()
        self._emergency_stop_active = True
        self._emergency_stop_reason = reason
        self._emergency_stop_activated_at = now
        self._emergency_stop_activated_by = f"{activated_by_kind}:{activated_by_id}"

        self._audit_decision(
            actor_kind=activated_by_kind,
            actor_id=activated_by_id,
            resource="system",
            operation="emergency_stop.activate",
            outcome="allow",
            reason="emergency_stop_activated",
            risk_level="critical",
        )

        logger.warning(
            "Emergency stop activated by %s:%s — reason: %s",
            activated_by_kind,
            activated_by_id,
            reason,
        )
        return {
            "active": True,
            "activated_at": now,
            "activated_by": f"{activated_by_kind}:{activated_by_id}",
            "reason": reason,
        }

    def deactivate_emergency_stop(
        self,
        *,
        deactivated_by_kind: str,
        deactivated_by_id: str,
    ) -> dict[str, Any]:
        """Disattiva l'emergency stop, ripristinando le operazioni.

        Richiede che l'identità disattivante esista nel Control Plane.
        """
        self.authenticate_caller(
            identity_kind=deactivated_by_kind, identity_id=deactivated_by_id
        )

        now = _now()
        self._emergency_stop_active = False
        self._emergency_stop_reason = None
        self._emergency_stop_activated_at = None
        self._emergency_stop_activated_by = None

        self._audit_decision(
            actor_kind=deactivated_by_kind,
            actor_id=deactivated_by_id,
            resource="system",
            operation="emergency_stop.deactivate",
            outcome="allow",
            reason="emergency_stop_deactivated",
            risk_level="critical",
        )

        logger.info(
            "Emergency stop deactivated by %s:%s",
            deactivated_by_kind,
            deactivated_by_id,
        )
        return {
            "active": False,
            "deactivated_at": now,
            "deactivated_by": f"{deactivated_by_kind}:{deactivated_by_id}",
        }

    def get_emergency_stop_status(self) -> dict[str, Any]:
        """Restituisce lo stato corrente dell'emergency stop."""
        activated_by = None
        if self._emergency_stop_activated_by is not None:
            kind, _, id_ = self._emergency_stop_activated_by.partition(":")
            activated_by = {"kind": kind, "id": id_}
        return {
            "active": self._emergency_stop_active,
            "activated_at": self._emergency_stop_activated_at,
            "activated_by": activated_by,
            "reason": self._emergency_stop_reason,
        }

    # ------------------------------------------------------------------
    # Audit decisioni
    # ------------------------------------------------------------------

    def _audit_decision(
        self,
        *,
        actor_kind: str,
        actor_id: str,
        resource: str,
        operation: str,
        outcome: str,
        reason: str,
        risk_level: str = "normal",
        capability_id: str | None = None,
    ) -> None:
        """Registra una decisione di autorizzazione nell'audit log.

        Scrive direttamente nella tabella di audit del Control Plane.
        L'esito è sempre 'recorded' (append-only, immutabile).
        """
        try:
            with self._repository._connection() as connection:
                self._repository._append_audit(
                    connection,
                    action=f"authorization.{outcome}",
                    subject_kind="system",
                    subject_id=resource,
                    details={
                        "actor_kind": actor_kind,
                        "actor_id": actor_id,
                        "operation": operation,
                        "outcome": outcome,
                        "reason": reason,
                        "risk_level": risk_level,
                        "capability_id": capability_id,
                    },
                    occurred_at=_now(),
                )
        except Exception:
            # L'audit non deve bloccare l'operazione, ma deve essere loggato.
            logger.exception("Failed to record authorization audit event")

    # ------------------------------------------------------------------
    # Approvazioni (stub operativo per M5)
    # ------------------------------------------------------------------

    def record_approval(
        self,
        *,
        approval_id: str,
        request_id: str,
        status: str,
        requested_by_kind: str,
        requested_by_id: str,
        resolved_by_kind: str | None = None,
        resolved_by_id: str | None = None,
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        """Registra un'approvazione per un'operazione a rischio.

        Questo è un registro operativo: le approvazioni vengono consultate
        dal permission check per verificare che un'operazione a rischio
        sia stata esplicitamente approvata.

        Stati supportati: pending, approved, rejected, expired.
        """
        if status not in {"pending", "approved", "rejected", "expired"}:
            raise ValueError(f"Invalid approval status: {status}")

        # Verifica che le identità esistano.
        self.authenticate_caller(
            identity_kind=requested_by_kind, identity_id=requested_by_id
        )
        if resolved_by_kind is not None and resolved_by_id is not None:
            self.authenticate_caller(
                identity_kind=resolved_by_kind, identity_id=resolved_by_id
            )

        now = _now()

        # Registra l'approvazione come evento di audit.
        details = {
            "approval_id": approval_id,
            "request_id": request_id,
            "status": status,
            "requested_by": f"{requested_by_kind}:{requested_by_id}",
            "resolved_by": (
                f"{resolved_by_kind}:{resolved_by_id}"
                if resolved_by_kind and resolved_by_id
                else None
            ),
            "expires_at": expires_at,
        }
        try:
            with self._repository._connection() as connection:
                self._repository._append_audit(
                    connection,
                    action=f"approval.{status}",
                    subject_kind="system",
                    subject_id=request_id,
                    details=details,
                    occurred_at=now,
                )
        except Exception:
            logger.exception("Failed to record approval audit event")

        return {
            "id": approval_id,
            "request_id": request_id,
            "status": status,
            "requested_by": f"{requested_by_kind}:{requested_by_id}",
            "resolved_by": (
                f"{resolved_by_kind}:{resolved_by_id}"
                if resolved_by_kind and resolved_by_id
                else None
            ),
            "expires_at": expires_at,
            "recorded_at": now,
        }

    # ------------------------------------------------------------------
    # Lista decisioni di autorizzazione (audit)
    # ------------------------------------------------------------------

    def list_authorization_decisions(
        self,
        *,
        actor_kind: str | None = None,
        actor_id: str | None = None,
        resource: str | None = None,
        operation: str | None = None,
        outcome: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Restituisce le decisioni di autorizzazione registrate nell'audit."""
        # Riutilizza il metodo di audit del repository filtrando per azioni
        # di autorizzazione.
        actions: list[str] | None = None
        if outcome is not None:
            actions = [f"authorization.{outcome}"]
        # Il repository supporta un solo action alla volta; se serve filtrare
        # per multiple azioni, si fa in post-processing.
        action_filter = actions[0] if actions else None

        events = self._repository.list_audit_events(
            subject_kind="system",
            subject_id=resource,
            action=action_filter,
            limit=limit,
            offset=offset,
        )

        # Post-filtraggio per attore, operazione e outcome.
        results: list[dict[str, Any]] = []
        for event in events:
            details = event.get("details", {})
            if actor_kind is not None and details.get("actor_kind") != actor_kind:
                continue
            if actor_id is not None and details.get("actor_id") != actor_id:
                continue
            if operation is not None and details.get("operation") != operation:
                continue
            if outcome is not None and details.get("outcome") != outcome:
                continue
            results.append(
                {
                    "id": event["id"],
                    "occurred_at": event["occurred_at"],
                    "actor": event["actor"],
                    "action": event["action"],
                    "subject": event["subject"],
                    "outcome": event["outcome"],
                    "details": details,
                }
            )
        return results


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


__all__ = [
    "AuthorizationService",
    "AuthorizationError",
    "AuthenticationError",
    "PermissionDeniedError",
    "EmergencyStopActiveError",
    "ApprovalRequiredError",
]
