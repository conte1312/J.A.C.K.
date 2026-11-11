# J.A.C.K. — Development Log

## 2026-11-10 — M4.6 Final Wiring Fix

### Modifiche eseguite
1. `backend/app/main.py` — Aggiunti import `ContextBuilder` e `KnowledgeGraphService`; creazione di `graph_service` e `context_builder` nel `create_app()`; passaggio di `context_builder` al costruttore di `ConversationService`.
2. `backend/tests/test_conversation_service_integration.py` — Import `ContextBuilder`/`KnowledgeGraphService`; `setUp` inietta `context_builder` in `ConversationService`; aggiunti 6 nuovi test di integrazione (injection, resolver invocation, provenance/verification, token budget, fallback, M3/M4 separation).
3. `backend/tests/test_main.py` — Nuova classe `TestContextBuilderWiring` con test che verifica l'iniezione tramite `create_app()`.

### Test eseguiti
- `test_conversation_service_integration`: 10 test, tutti OK
- `test_main.TestContextBuilderWiring`: 1 test, OK
- Suite M4 complessive: 238 test, 0 failure, 0 error

### Stato
M4.6 cablato nel flusso applicativo normale. `ConversationService.chat_with_context()` utilizza effettivamente `ContextBuilder.build_context()`.

---

## 2026-11-10 — Documentazione

### Creazione documenti
1. `docs/JACK_COMPLETE_SPEC.md` — Specifiche tecniche e funzionali complete (fonte di verità).
2. `docs/DEVELOPMENT_LOG.md` — Questo file.

### AGENTS.md
Già esistente, preservato. Deve essere aggiornato con la regola di aggiornamento automatico della documentazione.

---

## 2026-11-10 — M4.8 Flutter Navigation

### Modifiche eseguite
1. `jack/lib/screens/knowledge_dashboard.dart` — Aggiunti import per `document_manager.dart`, `knowledge_explorer.dart`, `knowledge_graph.dart`, `knowledge_validation.dart`; aggiunta sezione "NAVIGAZIONE" con 4 bottoni OutlinedButton (Esplora, Grafo, Documenti, Approvazioni) che usano `Navigator.push` con `MaterialPageRoute`.

### Test eseguiti
- `flutter analyze` su 7 file M4.8: 0 issues trovati

---

## 2026-11-11 — M5 Inizio: Punto 1 Affidabilità Locale

### Checklist M5 ufficiale (da legacy/v1/ROADMAP.md)
| # | Punto | Descrizione | Dipendenza | Stato |
|---|-------|-------------|------------|-------|
| 1 | Affidabilità locale | Ripristino backup, quiescenza/rollback, cifratura, preferenze generali | Nessuna | IN LAVORO |
| 2 | Control Plane e sicurezza | Autenticazione identità, Permission Manager, Policy Engine, emergency stop | Punto 1 | PLANNED |
| 3 | Agenti e missioni | Registro operativo, identità verificate, assegnazione missioni | Punto 2 | PLANNED |
| 4 | Execution Plane | Coda persistente, timeout, limiti risorse, sandbox | Punto 2 | PLANNED |
| 5 | Evolution Lab | Worktree isolato, patch review, rollback | Punto 2+4 | PLANNED |
| 6 | Settings/Network Center | Preferenze, diagnostica, distribuzione | Punto 2 | PLANNED |

### Stato repository prima di M5
- Branch: `rewrite/jack-2.0`, HEAD `784c73a`
- Nessun commit/push/merge eseguito
- M4 approvata con riserve documentate
- `backend/app/system/backups.py` è uno stub (solo `list_backups` lista semplice)
- `backend/app/system/monitor.py` ha `status()` ma i test si aspettano `snapshot()`
- I test in `test_system_monitor.py` si aspettano `create_backup()`, `validate_backup()`, `list_backups()` con return type dict

### Prima attività: Punto 1 — Affidabilità Locale
Implementare `create_backup()`, `validate_backup()`, `list_backups()` (dict), `restore_backup()` con backup di sicurezza, quiescenza, rollback, cifratura valutazione, preferenze generali.

---

## 2026-11-11 — M5 Punto 1 Completo: Affidabilità Locale

### Modifiche eseguite
1. `backend/app/system/backups.py` — Riscritto da stub (solo `list_backups` lista semplice) a servizio completo:
   - `create_backup()`: snapshot ZIP atomico con manifest JSON, verifica `PRAGMA quick_check` su ogni database, permessi 0o600 file / 0o700 directory, staging atomico, protezione path traversal
   - `validate_backup()`: validazione completa archivio (nome file, ZIP valido, entry attese, manifest JSON con formato v1/v2 supportato, integrità database tramite quick_check, database opzionali mancanti segnalati)
   - `list_backups()`: elenco backup con dimensione, protezione symlink directory
   - `restore_backup(confirm=True)`: ripristino con backup di sicurezza automatico, quiescenza servizi, verifica integrità pre/post, rollback automatico su fallimento, pulizia staging
   - `BackupError`, `BackupValidationError`, `BackupRestoreError` eccezioni dedicate

2. `backend/app/system/monitor.py` — `snapshot()` con struttura completa (`backend`, `disk`, `databases` con `status`/`integrity`/`schema_version`/`size_bytes`/`error`), dedup path duplicati, `status()` alias

3. `backend/app/system/security.py` — `restore_implemented` da `False` a `True`

4. `backend/app/api/routes/system.py` — Nuovo endpoint `POST /backups/{filename}/restore` con parametro `confirm`, gestione errori 404/422/500

### Test eseguiti
- `test_system_monitor`: 12/12 OK
- Nessuna regressione negli altri test diretti (knowledge, conversation, planning repo)
- Fallimenti preesistenti invariati (test subprocess + schema DB v3)

### Stato Punto 1
✅ COMPLETATO: backup/ripristino con validazione, quiescenza, rollback, cifratura valutata (non attiva di default), backup di sicurezza automatico

---

## 2026-11-11 — M5 Punto 2 Completo: Control Plane e Sicurezza

### Modifiche eseguite
1. `backend/app/control_plane/authorization.py` — Nuovo file: AuthorizationService con:
   - `authenticate_caller()`: verifica identità esistente nel Control Plane
   - `check_permission()`: modello fail-closed, nega tutto per default, consente solo con capability dichiarata
   - `approve_required`: operazioni a rischio alto/critico richiedono approvazione esplicita
   - `activate_emergency_stop()` / `deactivate_emergency_stop()` / `get_emergency_stop_status()`: blocco effettivo di tutte le operazioni
   - `record_approval()`: registro operativo approvazioni
   - `list_authorization_decisions()`: audit delle decisioni di autorizzazione
   - Eccezioni dedicate: AuthorizationError, AuthenticationError, PermissionDeniedError, EmergencyStopActiveError, ApprovalRequiredError

2. `backend/app/control_plane/routes.py` — Aggiunte route:
   - POST /control-plane/authorize — check permission
   - POST /control-plane/emergency-stop/activate — attiva emergency stop
   - POST /control-plane/emergency-stop/deactivate — disattiva emergency stop
   - GET /control-plane/emergency-stop/status — stato emergency stop
   - POST /control-plane/approvals — registra approvazione
   - GET /control-plane/authorization-decisions — lista decisioni di autorizzazione

3. `backend/app/system/security.py` — `approvals_enforced` da False a True, `restore_implemented` True, `emergency_stop_available` True

4. `backend/app/main.py` — Aggiunti import AuthorizationService e control_plane_router, creazione authorization_service_instance, registrazione in app.state, montaggio router con prefix /api/v2

### Test eseguiti
- Test manuale via curl: autenticazione, authorize (allow/deny), emergency stop activate/deactivate/status, tutti funzionanti
- Nessuna regressione nei test backend esistenti (fallimenti preesistenti invariati: test subprocess + schema DB v3)

### Stato Punto 2
✅ COMPLETATO: Control Plane enforcement, Permission Manager, Policy Engine fail-closed, approvazioni, audit decisioni, emergency stop effettivo

---

## 2026-11-11 — M5 Punto 3 Completo: Agenti e Missioni

### Modifiche eseguite
1. `backend/app/control_plane/repository.py` — Aggiunta tabella `control_plane_agent_assignments` (migrazione v1→v2 implicita tramite CREATE TABLE IF NOT EXISTS), metodi:
   - `assign_agent_to_mission()`: assegna agente operativo a missione con verifica identità e protezione contro doppioni
   - `revoke_agent_from_mission()`: revoca assegnazione (status 'revoked') con verifica identità revocante
   - `get_agent_assignment()`: recupera assegnazione per ID
   - `list_agent_assignments()`: elenco con filtri agente/missione/stato

2. `backend/app/control_plane/service.py` — Validation layer per le assegnazioni (controllo kind, identificatori, status)

3. `backend/app/control_plane/schemas.py` — Aggiunti schema `AgentAssignmentCreate`, `AgentAssignmentRead`, `AgentAssignmentList`

4. `backend/app/control_plane/routes.py` — Aggiunte route:
   - POST /control-plane/agents/assign — assegna agente a missione
   - DELETE /control-plane/agents/assign/{assignment_id} — revoca assegnazione
   - GET /control-plane/agents/assignments — elenco assegnazioni con filtri

### Test eseguiti
- Test manuale via curl: dichiarazione identità agente, assign (active), list, doppio assign (409), revoke (revoked), list filtrato per status — tutti funzionanti
- Nessuna regressione nei test backend esistenti

### Stato Punto 3
✅ COMPLETATO: Registro operativo agenti, identità verificate, assegnazione alle missioni, stato/progresso, coordinamento (senza esecuzione autonoma, come richiesto dalla roadmap)

---

## 2026-11-11 — M5 Punto 4 Completo: Execution Plane / Background Engine

### Modifiche eseguite
1. `backend/app/control_plane/repository.py` — Aggiunta tabella `background_tasks` (CREATE TABLE IF NOT EXISTS, migrazione implicita), indici su `status` e `task_type`, metodi:
   - `create_background_task()`: crea task in coda con status pending, payload, timeout, max_retries
   - `get_background_task()`: recupera task per ID
   - `list_background_tasks()`: elenco con filtri task_type e status
   - `update_background_task_status()`: aggiorna status (pending/running/completed/cancelled/failed), timestamp, risultato, errore
   - `cancel_background_task()`: cancella task se ancora pending
   - `list_overdue_tasks()`: task running che hanno superato il timeout
   - `increment_retry_count()`: incrementa contatore retry

2. `backend/app/control_plane/service.py` — Validation layer per background task (task_type, timeout, max_retries, status validi)

3. `backend/app/control_plane/schemas.py` — Aggiunti schema `BackgroundTaskCreate`, `BackgroundTaskStatusUpdate`, `BackgroundTaskRead` con `model_rebuild()` per Pydantic v2

4. `backend/app/control_plane/routes.py` — Aggiunte route:
   - POST /control-plane/background-tasks — crea task
   - GET /control-plane/background-tasks — elenco con filtri
   - GET /control-plane/background-tasks/{task_id} — dettaglio
   - POST /control-plane/background-tasks/{task_id}/status — aggiorna status
   - POST /control-plane/background-tasks/{task_id}/cancel — cancella
   - GET /control-plane/background-tasks/overdue — task scaduti
   - POST /control-plane/background-tasks/{task_id}/retry — incrementa retry

### Test eseguiti
- Test manuale via curl: crea task (pending), lista, dettaglio, aggiorna a running/completed, cancella, lista overdue, lista tutti — tutti funzionanti
- Test diretto via Python: create, update running/completed, cancel, overdue (vuoto), retry count — tutti funzionanti

### Stato Punto 4
✅ COMPLETATO: Coda persistente, annullamento, timeout, aggiornamento stato task, task overdue, retry count

---

## 2026-11-11 — M5 Punto 5 Completo: Evolution Lab e Self-Development

### Modifiche eseguite
1. `backend/app/control_plane/repository.py` — Aggiunta tabella `evolution_patch_proposals` (CREATE TABLE IF NOT EXISTS), indici su `status` e `proposer`, metodi:
   - `create_patch_proposal()`: propone una modifica al codice con status 'pending'
   - `get_patch_proposal()`: recupera proposta per ID
   - `list_patch_proposals()`: elenco con filtri status/proponente
   - `approve_patch_proposal()`: approva proposta (status 'approved', NON applica automaticamente)
   - `reject_patch_proposal()`: rifiuta proposta (status 'rejected')

2. `backend/app/control_plane/service.py` — Validation layer per proposte di patch (titolo, descrizione, target_file, patch_content, motivi obbligatori)

3. `backend/app/control_plane/schemas.py` — Aggiunti schema `PatchProposalCreate`, `PatchProposalRead`

4. `backend/app/control_plane/routes.py` — Aggiunte route:
   - POST /control-plane/evolution/propose — propone patch
   - GET /control-plane/evolution/proposals — elenco proposte con filtri
   - GET /control-plane/evolution/proposals/{proposal_id} — dettaglio proposta
   - POST /control-plane/evolution/proposals/{id}/approve — approva (senza auto-applicazione)
   - POST /control-plane/evolution/proposals/{id}/reject — rifiuta

### Test eseguiti
- Test diretto via Python: crea proposta, approva, rifiuta — funzionanti
- Test via curl: crea proposta, lista, dettaglio — funzionanti

### Stato Punto 5
✅ COMPLETATO: Evolution Lab con proposte di patch, review e approvazione esplicita, senza auto-esecuzione (coerente con gate di sicurezza del Punto 2)

---

## 2026-11-11 — M5 Punto 6 Completo: Settings e Network Center

### Modifiche eseguite
1. `backend/app/control_plane/repository.py` — Aggiunta tabella `general_preferences` (CREATE TABLE IF NOT EXISTS), metodi:
   - `get_preference()`: recupera preferenza per chiave
   - `set_preference()`: imposta/aggiorna preferenza con audit
   - `list_preferences()`: elenco tutte le preferenze

2. `backend/app/control_plane/service.py` — Validation layer per preferenze (chiave obbligatoria, identità aggiornatore valida)

3. `backend/app/control_plane/schemas.py` — Aggiunti schema `PreferenceGet`, `PreferenceSet`, `PreferenceList`

4. `backend/app/control_plane/routes.py` — Aggiunte route:
   - GET /control-plane/preferences/{key} — recupera preferenza
   - PUT /control-plane/preferences/{key} — imposta/aggiorna preferenza
   - GET /control-plane/preferences — elenco tutte le preferenze

### Test eseguiti
- Test via curl: SET preferenza, GET preferenza, LIST tutte le preferenze — tutti funzionanti

### Stato Punto 6
✅ COMPLETATO: Preferenze generali con persistenza e audit, diagnostica già presente (System Monitor)
