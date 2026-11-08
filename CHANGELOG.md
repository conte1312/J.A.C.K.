# Changelog

## Unreleased — diagnostica e backup locali

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

## V1.2 — Fase 2: Pianificazione (worktree, 2026-11-08)

Implementazione locale non rilasciata: nessun tag, commit o push creato.

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
