# Changelog

## Unreleased — catalogo consultivo di agenti gratuiti

### Aggiunto

- Dieci profili specialistici selezionati dal repository MIT `msitarzewski/agency-agents`, fissati alla revisione `b859c515d813efcfc4755d3471dd9e7686c7706d` con licenza e attribuzione upstream conservate.
- API read-only `GET /api/v1/control-plane/agent-profiles` e `GET /api/v1/control-plane/agent-profiles/{id}` per elencare o consultare i profili.
- Test API che verificano provenienza, accesso ai contenuti, assenza di strumenti/capability, profili disabilitati e rifiuto di profili inesistenti o operazioni di attivazione.

### Limiti

- Il catalogo non è un runtime: non crea identità persistenti, non assegna profili alle missioni e non concede privilegi. Tutti i profili hanno `enabled=false`, `execution_enabled=false`, `tools=[]` e `capabilities=[]`.
- “Gratuito” indica licenza MIT dei profili, non inferenza gratuita. Qualunque futura chiamata AI resta soggetta al Cost Guard e al provider configurato.
- `start.sh` e l'interfaccia Flutter non cambiano; nessuna chiamata a provider o installazione di strumenti esterni è stata eseguita.

## Unreleased — fondamenta Control Plane (development)

### Aggiunto

- Database `control-plane.sqlite3` separato per identità tipizzate, capability dichiarate e audit degli aggiornamenti al registro; incluso nel monitor e nei backup locali.
- API `/api/v1/control-plane` per dichiarare/consultare identità e capability e consultare l’audit. Le capability restano descrittive e non concedono accesso.
- Contratti validabili per richieste di permesso, regole policy, approvazioni ed emergency-stop, non collegati a decisioni o operazioni effettive.
- Documento [docs/control-plane-architecture.md](docs/control-plane-architecture.md) con integrazioni, limiti e prerequisiti per enforcement sicuro.

### Limiti di sicurezza

- Nessuna autenticazione di caller; gli eventi attribuiscono l’operazione al servizio API e non provano l’identità umana/agente.
- Nessun grant, policy applicata, approvazione operativa, emergency stop o esecuzione autonoma. Audit append-only a livello app/trigger SQLite, non antimanomissione contro il proprietario del database.
- Nessuna modifica a Core Protection, permessi filesystem, credenziali, Cost Guard o permessi terminale.
- La validazione read-only accetta anche gli archivi legacy che non contengono ancora `control-plane.sqlite3` e segnala `missing_optional_databases`; i nuovi backup includono tutti e tre i database locali.

### Verifica

- Backend: `cd backend && .venv/bin/python -m pytest -q` — **76 passed, 4 subtests passed**.
- Flutter: `cd jack && flutter analyze --no-pub` — **nessun problema**; `flutter test --no-pub` — **42 test superati**.
- macOS: `cd jack && flutter build macos --no-pub` — **build riuscita** (`jack.app`, 46,9 MB).
- Test specifici includono dichiarazioni duplicate/invalidi, isolamento identità, audit persistente e immutabile, migrazione/non perdita dati, API, monitor e backup.

## Unreleased — preferenza fuso calendario

### Aggiunto

- La Pianificazione carica e salva il fuso orario predefinito del calendario tramite `GET/PUT /api/v1/planning/preferences`; il valore iniziale è `Europe/Rome`.
- Il backend valida il fuso contro il database IANA, applica la preferenza alle query calendario senza parametro esplicito e mantiene il fuso di ogni appuntamento indipendente.
- Migrazione planning v3→v4: aggiunge `planning_settings` e inizializza la preferenza senza modificare i task o gli eventi esistenti.

### Verifica

- Backend: `cd backend && .venv/bin/python -m pytest -q` — **66 passed, 4 subtests passed**.
- Flutter: `cd jack && flutter analyze --no-pub` — **nessun problema**; `flutter test --no-pub` — **42 test superati**.
- macOS: `cd jack && flutter build macos --no-pub` — **build riuscita** (`jack.app`, 46,9 MB).
- Hot restart tramite VM Service riuscito; nessun errore runtime segnalato.

## 2026-11-08 — diagnostica e backup locali (development)

### Aggiunto

- Nuova API read-only `GET /api/v1/system/monitor` per stato del processo backend, CPU cumulativa, memoria massima, spazio disco e `PRAGMA quick_check` sui database locali.
- La sezione Impostazioni mostra stato, dimensione e versione schema dei database senza esporre i percorsi locali; errori e database mancanti sono distinti.
- Endpoint `GET/POST /api/v1/system/backups` per elencare e creare snapshot SQLite coerenti in archivio ZIP; verifica d’integrità prima della pubblicazione atomica.
- Endpoint `POST /api/v1/system/backups/{filename}/validate` per verificare in sola lettura struttura, manifest e integrità SQLite degli archivi, senza estrarli nelle directory dell’app o modificare i database attivi.
- La sezione Impostazioni consente di consultare, creare e verificare backup locali dopo conferma, avvisando che gli archivi non sono cifrati.
- Endpoint `GET /api/v1/system/security-status` e scheda Settings che dichiarano bind loopback, assenza di esecuzione autonoma, approvazioni non applicate, backup non cifrati e ripristino assente. La vista è informativa, non un motore di autorizzazione.
- Generazione automatica delle ricorrenze task all’avvio e ogni ora; i task arretrati saltano alla prossima occorrenza futura, con vincolo SQLite univoco per evitare duplicati anche in scansioni concorrenti.
- Migrazione planning v2→v3 con identificatore di serie delle ricorrenze, senza eliminare o riscrivere i task esistenti.
- Endpoint `GET /api/v1/system/timezones` con il catalogo IANA disponibile nel runtime; calendario e form appuntamenti consentono ricerca di qualsiasi zona supportata.
- I test API usano database temporanei isolati anche per conversazioni e memoria; test backend per backup incompleti, contenuto, integrità, manifest/entry ZIP non validi, nomi duplicati e rifiuto di directory symlink.

### Limiti

- La diagnostica non controlla hardware e non misura percentuali CPU istantanee.
- Il backup è locale e non cifrato. È disponibile solo la validazione read-only; non è implementato il ripristino, che richiede quiescenza dei database, snapshot di sicurezza e rollback verificabile.
- Agenti eseguibili, Security Center e Background Engine non sono ancora implementati; la roadmap li ordina dietro policy di sicurezza e approvazioni.

### Verifica worktree

- Backend: `cd backend && .venv/bin/python -m pytest -q` — **63 passed, 4 subtests passed**.
- Flutter: `cd jack && flutter analyze --no-pub` — **nessun problema**.
- Flutter: `cd jack && flutter test --no-pub` — **41 test superati**.
- macOS: `cd jack && flutter build macos --no-pub` — **build riuscita** (`jack.app`, 46,9 MB); verificato hot restart.

## V1.2 — Fase 2: Pianificazione (development, 2026-11-08)

Implementazione pubblicata sul branch di sviluppo `development`; nessun tag di release creato.

### Aggiunto

- Task Engine persistente: CRUD, stato/priorità, date, tag/categoria, checklist, dipendenze, filtri, ordinamento e generazione della ricorrenza successiva.
- Project Engine: CRUD, archiviazione, milestone e avanzamento calcolato dai task associati.
- Calendar Engine: viste giorno/settimana/mese, appuntamenti distinti dalle scadenze, filtri, fuso orario e ricorrenze.
- Gestione UI delle missioni pianificate: stato, piano, task collegati, log e approvazioni. Nessuna esecuzione autonoma.
- Proposte di pianificazione strutturate nel backend e nel flusso conversazionale: operazioni validate server-side e applicate solo dopo conferma. L’interpretazione è deterministica e non invia prompt ai provider.
- Migrazione planning da schema v1 a v2, mantenendo i record missione, e indici per stato, scadenze e associazioni.

### API

Prefisso `/api/v1/planning`:

- `/tasks`, `/tasks/{id}`, `/tasks/{id}/complete`, `/tasks/{id}/reopen`, `/tasks/{id}/can-complete`
- `/tasks/{id}/checklist`, `/checklist/{id}`, `/tasks/{id}/dependencies`, `/dependencies/{id}`, `/recurrences/generate`
- `/projects`, `/projects/{id}`, `/projects/{id}/archive`, `/projects/{id}/milestones`, `/milestones/{id}`
- `/calendar`, `/calendar/events`, `/calendar/events/{id}`
- `/missions`, `/missions/{id}`, `/missions/{id}/logs`, `/missions/{id}/approvals`, `/mission-approvals/{id}`
- `/ai/interpret`, `/ai/apply`

Il database planning separato usa `PRAGMA user_version=2` e le tabelle `tasks`, `projects`, `checklist_items`, `task_dependencies`, `missions`, `project_milestones`, `calendar_events`, `planning_ai_proposals`, `mission_logs` e `mission_approvals`.

### Verifica

- Backend: `cd backend && .venv/bin/python -m pytest` — **43 passed**.
- Flutter: `cd jack && flutter analyze --no-pub` — **nessun problema**.
- Flutter: `cd jack && flutter test --no-pub` — **37 test superati**.
- macOS: `cd jack && flutter build macos --no-pub` — **build riuscita** (`jack.app`, 46,5 MB).

La build segnala che `flutter_secure_storage_macos` non supporta Swift Package Manager; l’avviso non impedisce la build.

### Limiti noti

- Nessuno scheduler in background o notifiche locali macOS; la ricorrenza viene generata tramite endpoint esplicito.
- L’interpretazione delle richieste è rule-based; la suddivisione di un obiettivo richiede passaggi espliciti, non generati dal modello.
- Il selettore del fuso orario ora carica il catalogo IANA dal backend; la versione V1.2 storica riportava il limite dei preset che è stato superato in questo ciclo.
- La Fase 3 e l’esecuzione autonoma degli agenti non sono iniziate.
