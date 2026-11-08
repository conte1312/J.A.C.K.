# J.A.C.K. — Stato e roadmap

**Aggiornato:** 8 novembre 2026
**Branch di sviluppo:** `development`; Control Plane foundation verificato e pronto per commit/pubblicazione. `main` non modificato.
**Stack verificato:** Flutter 3.47.9 / Dart 3.13.7, FastAPI, SQLite, macOS.

Questo documento descrive lo stato effettivo del repository, incluse le modifiche locali non committate. “Implementato” indica che il relativo codice è presente; è indicato separatamente quando non esiste ancora una verifica end-to-end.

## Stato delle aree

| Area | Stato | Evidenza e limiti |
|---|---|---|
| Conversazioni e chat | Implementata | Conversazioni e messaggi persistenti in SQLite; il frontend usa l’endpoint conversazionale. La chat non mostra risposte simulate quando il backend non è disponibile. |
| AI Hub e provider | Implementata | Gestione provider, credenziali, modelli e routing tramite backend. Il Cost Guard limita le richieste ai modelli ammessi. Nessuna chiamata a provider è stata eseguita durante questa verifica. |
| Memoria locale | Implementata | CRUD, ricerca, collegamenti e recupero di contesto sono serviti dal backend locale. Le credenziali non sono salvate nel database memoria. |
| Knowledge Core | Implementato | Grafo alimentato dai dati locali, aggiornato dopo le modifiche alla memoria; stato vuoto informativo senza fallback dimostrativi in produzione. |
| Pianificazione — backend | Implementata su `development` | CRUD e filtri task/progetti, checklist, dipendenze, ricorrenze, milestone, calendario/eventi, proposte AI validate, missioni e preferenza timezone persistono in SQLite separato. Le ricorrenze vengono verificate all’avvio e ogni ora; test unitari e API HTTP dedicati passano. |
| Pianificazione — frontend | Implementata su `development` | La voce esistente della sidebar apre dashboard giornaliera, calendario giorno/settimana/mese, attività, progetti e missioni. Il fuso predefinito è caricato e salvato tramite backend; i fusi specifici degli appuntamenti restano modificabili. |
| Missioni | Gestione pianificata implementata | UI per pianificare/modificare/eliminare missioni, collegamento dal task, progresso calcolato, log e approvazioni. L’esecuzione autonoma degli agenti resta esclusa. |
| Moduli / agenti / evoluzione | Non implementati come motore generale | “Moduli” oggi apre l’AI Hub; non esiste ancora un framework general-purpose per moduli, agenti o auto-modifica. |
| Impostazioni | Parziale | La sezione contiene il Monitor locale, la creazione/elenco backup e una vista informativa di sicurezza. La preferenza timezone è disponibile in Pianificazione; ripristino e motore di enforcement delle policy restano da realizzare. |
| Monitoraggio | Base, read-only | `/api/v1/system/monitor` controlla processo backend, uso disco e integrità dei database memoria/conversazioni, Planning e Control Plane; metriche CPU/RAM sono cumulative/di picco, non telemetria istantanea dell’hardware. |
| Backup locali | Creazione, elenco e validazione read-only | `/api/v1/system/backups` crea snapshot SQLite coerenti in ZIP dei database memoria/conversazioni, Planning e Control Plane; `POST /api/v1/system/backups/{filename}/validate` verifica manifest e integrità SQLite senza ripristinare né alterare i database attivi. La validazione supporta snapshot legacy privi del solo database Control Plane. Gli archivi non sono cifrati; il ripristino non è implementato. |
| Stato sicurezza | Informativo, non enforcement | `/api/v1/system/security-status` e Impostazioni descrivono bind loopback, assenza di esecuzione autonoma, approvazioni non applicate, backup non cifrati e ripristino assente. Non è un Security Center né un motore di policy. |
| Fusi orari calendario | Preferenza persistente | `GET /api/v1/system/timezones` espone le zone del runtime Python. `GET/PUT /api/v1/planning/preferences` legge e salva il fuso predefinito validato come IANA; calendario e form appuntamenti lo riutilizzano, mantenendo selezione per singolo evento. |
| Control Plane | Fondamenta dichiarative, non enforcement | Registro persistente di identità tipizzate e capability dichiarate, audit append-only per tali registrazioni e API di consultazione sotto `/api/v1/control-plane`. Nessun grant, policy applicata, approvazione operativa, emergency stop o esecuzione agente è attivo. |
| Scheduler e notifiche | Scheduler ricorrenze attivo | Il backend materializza le ricorrenze task all’avvio e ogni ora; notifiche locali macOS non presenti. |
| Sincronizzazione / rete | Solo backend locale e provider AI configurati | Backend vincolato a loopback. Non è implementata sincronizzazione cloud o multi-dispositivo. |
| Packaging e distribuzione | Pianificati | La build macOS locale funziona; firma, notarizzazione e distribuzione non sono state completate. |

## Pianificazione V1.2 — Fase 2 implementata

### Backend

- Router sotto `/api/v1/planning`: CRUD e filtri task/progetti; completamento e riapertura task; checklist; dipendenze e verifica di completabilità; ricorrenze; milestone; calendario ed eventi; missioni/log/approvazioni; interpretazione e applicazione di proposte AI.
- Le dipendenze rifiutano i cicli e impediscono il completamento finché i prerequisiti non sono completati.
- L’avanzamento progetto è calcolato dai task effettivi. Le attività annullate non gonfiano il denominatore.
- Scadenze task ed eventi di calendario sono entità distinte. Gli eventi conservano il fuso orario e le ricorrenze si espandono nel periodo richiesto. `GET /api/v1/system/timezones` fornisce il catalogo IANA per calendario e appuntamenti.
- Database separato `tasks.sqlite3` accanto ai dati locali J.A.C.K.; `PRAGMA user_version` è alla versione 4. La migrazione v3→v4 aggiunge la preferenza timezone senza alterare task/eventi preesistenti; v2→v3 assegna identificatori di serie alle ricorrenze legacy e aggiunge unicità per istanza/data.
- Tabelle: `tasks`, `projects`, `checklist_items`, `task_dependencies`, `missions`, `project_milestones`, `calendar_events`, `planning_settings`, `planning_ai_proposals`, `mission_logs`, `mission_approvals`.
- Il bootstrap FastAPI inizializza il repository planning indipendentemente da quello della memoria.
- Un processo asincrono nel lifespan controlla subito le ricorrenze e poi ogni ora. Le istanze arretrate saltano direttamente alla prossima data futura; un indice univoco impedisce duplicati anche con scansioni concorrenti.

### Frontend

- La navigazione esistente è mantenuta; `JackHomePage` apre `PlanningScreen` tramite `PlanningApiService`.
- Dashboard “Oggi”, calendario giorno/settimana/mese, elenco task, progetti e missioni hanno stati vuoti espliciti e non usano dati demo.
- Ricerca, filtri task per stato/priorità/progetto, ordinamento ascendente/descendente e navigazione temporale; gli appuntamenti supportano filtro progetto/priorità e ricorrenze con fuso orario.
- I form task espongono date inizio/scadenza, priorità, stato, progetto, missione, categoria, tag, agente responsabile, note, checklist/ricorrenza. I dettagli consentono checklist e gestione dipendenze; le operazioni rifiutate dal backend mostrano errori.
- I progetti espongono stato, priorità, obiettivo, date e note; milestone sono creabili, modificabili, completabili ed eliminabili. Avanzamento e conteggi vengono dai task effettivi.
- Le missioni pianificate sono visibili e gestibili, con task collegati tramite il campo missione del task, log, approvazioni e stato. Non viene avviata alcuna esecuzione autonoma.
- Scadenze task e appuntamenti restano entità distinte.

### Ponte AI e missioni

- L’API planning produce proposte persistenti a scadenza e monouso. Le modifiche passano da validazione backend e conferma esplicita; il modello non accede al database.
- La conversazione controlla localmente i messaggi con intenti di pianificazione e propone le operazioni supportate: creazione task/progetti, spostamento scadenze, elenco attività di oggi/in ritardo e breakdown con passaggi espliciti. Le richieste non comprese proseguono nel normale flusso chat.
- L’interpretazione è rule-based e non invia prompt ai provider. Il breakdown non inventa passaggi: richiede elementi espliciti separati da righe o `;`. “Organizza la giornata” mostra le attività di oggi; non esegue un riordino o una pianificazione automatica.
- La sezione Pianificazione mantiene anche il pulsante “Chiedi a J.A.C.K.” e la conferma riepilogativa.
- Le missioni restano pianificate: non avviano agenti e non eseguono azioni autonome.

## Fondamenta Control Plane

- Aggiunto database locale indipendente `control-plane.sqlite3` (schema v1) e integrazione nel bootstrap, monitor e backup esistenti.
- Identità dichiarate distinguono utente, agente, servizio, strumento e nodo. Le capability dichiarano proprietario, risorsa, operazioni, scope, rischio e requisito di approvazione; non costituiscono grant o privilegi.
- Le registrazioni di identità/capability producono audit nella stessa transazione. Trigger SQLite impediscono update/delete degli eventi, senza promettere protezione antimanomissione dal proprietario locale del database.
- Nuovi backup includono il database Control Plane. La validazione read-only continua ad accettare gli archivi precedenti senza tale database e segnala i database opzionali mancanti.
- L’API espone dichiarazioni e lettura audit; non espone append manuale dell’audit.
- I contratti per richiesta permesso, regole policy, approvazioni ed emergency-stop sono solo modelli validabili e non sono esposti come funzioni operative.
- Non esiste autenticazione caller: l’attore audit indica il servizio backend, non prova l’identità dell’utente che ha invocato la rotta.
- Disegno, confini futuri e prerequisiti per enforcement documentati in [docs/control-plane-architecture.md](docs/control-plane-architecture.md).

## Evidenze di verifica

Eseguite sul worktree corrente, senza richieste a provider AI:

- Backend: `.venv/bin/python -m pytest -q` — **76 test superati, 4 subtests superati**. Include API HTTP e unit test per CRUD, persistenza/riapertura, migrazioni planning v1/v2/v3, preferenze timezone, dipendenze, progressi progetto, milestone, ricorrenze/fusi orari e scheduler, proposte AI con conferma, missioni, monitor, backup, stato sicurezza e Control Plane.
- Backend Control Plane: test di dichiarazioni tipizzate, persistenza, isolamento, trigger audit immutabili, validazione schema e mantenimento compatibilità degli archivi precedenti.
- Flutter: `flutter analyze --no-pub` — **nessun problema**.
- Flutter: `flutter test --no-pub` — **42 test superati**, inclusi navigazione, stati vuoti, creazione UI di task/progetto/missione, persistenza della preferenza timezone, monitor locale e flusso di verifica backup.
- macOS: `flutter build macos --no-pub` — **build completata** (`jack.app`, 46,9 MB).
- La build segnala che `flutter_secure_storage_macos` non supporta Swift Package Manager; non ha impedito la build. La migrazione/adozione SPM resta da verificare.
- Hot restart eseguito tramite VM Service dopo l’avvio dell’app macOS; nessun errore runtime segnalato.

Le migrazioni sono verificate da database planning v1, v2 e v3, preservando i record preesistenti. Notifiche locali macOS non implementate.

## Esito audit direttiva completamento finale

L’applicazione è un monolite locale Flutter + FastAPI + SQLite. Chat/provider, memoria contestuale, Knowledge Core e Pianificazione sono nel percorso esistente; test e documentazione precedenti ne attestano i flussi supportati. Le aree che non vanno confuse con funzionalità già operative sono:

- Security Center e autorizzazioni per filesystem/strumenti: non presenti come policy manager centralizzato; è disponibile solo una vista informativa dello stato.
- Agenti specialistici permanenti, coordinamento, esecuzione strumenti e Background Engine: non presenti. Le missioni Planning sono record pianificati, non agenti eseguibili.
- Evolution Lab e self-development: non presenti.
- Network Center/distribuzione: non presenti; il backend resta vincolato a `127.0.0.1`.
- Ripristino end-user, backup prima del ripristino e preferenze generali: non presenti.
- System Monitor: ora presente come diagnostica locale read-only, non come controllo/gestione hardware.

### Percorso ordinato per il completamento

1. **Affidabilità locale:** implementare ripristino con validazione completa dell’archivio, database di sicurezza pre-ripristino, quiescenza/rollback e conferma esplicita; valutare cifratura dei backup e completare preferenze generali.
2. **Control Plane e sicurezza:** completare autenticazione delle identità, Permission Manager e Policy Engine fail-closed; introdurre approvazioni non aggirabili, audit delle decisioni e un emergency stop effettivo. Solo dopo verificare minacce e gate prima di esporre strumenti. Le fondamenta dichiarative presenti non sono enforcement.
3. **Agenti e missioni:** registro agenti con capacità dichiarate, assegnazione alle missioni, stato/progresso, limiti e coordinamento. In questa fase nessuna esecuzione libera.
4. **Execution Plane / Background Engine:** coda persistente, annullamento, timeout, limiti di risorse e strumenti allowlist in sandbox; scrittura/cancellazione e comunicazioni esterne dietro approvazione.
5. **Evolution Lab e self-development:** solo dopo i gate precedenti, in worktree isolato con patch reviewabile, test, rollback e approvazione per modifiche critiche.
6. **Settings e Network Center:** preferenze utente, diagnostica completa e, solo se richiesta, architettura distribuita con autenticazione e trasporto sicuro.

Ordine basato sulle dipendenze di sicurezza: nessun agente riceverà capacità di esecuzione generale prima del punto 2. Questa roadmap non autorizza modifiche a credenziali, protezioni, permessi o operazioni irreversibili.

### Avanzamento della direttiva

- **Implementato nei cicli recenti:** endpoint `/api/v1/system/monitor`, `GET/POST /api/v1/system/backups`, `POST /api/v1/system/backups/{filename}/validate` e `GET /api/v1/system/security-status`; monitor Settings, backup privati con snapshot SQLite coerenti, verifica read-only di ZIP/manifest/integrità SQLite e quadro sicurezza dichiaratamente informativo. In `development` è presente anche la base dichiarativa del Control Plane; vedi la sezione dedicata e il documento architetturale.
- **Non implementato:** ripristino, enforcement di sicurezza/permessi, autenticazione delle identità, valutazione policy, approvazioni operative, emergency stop, agenti eseguibili, coordinamento, Background Engine, Evolution Lab, self-development e Network Center.
- Nessuna chiamata a provider AI effettuata durante le verifiche di questo incremento. Lo sviluppo è limitato a `development`; `main` non è stato modificato.
- Verifica completamento di questo incremento: backend **63 passed** (+ 4 subtests), `flutter analyze` pulito, Flutter **41 test superati**, build macOS riuscita (46,9 MB) e hot restart verificato tramite VM Service.

## Chiusura e limiti della Fase 2

La Fase 2 è implementata e verificata per gli endpoint e i flussi elencati sopra. Rimangono fuori perimetro/aperte: notifiche locali macOS, interpretazione AI generativa (il parser resta deterministico) e test manuale end-to-end con backend avviato nell’app desktop. Lo scheduler delle ricorrenze e il catalogo completo delle zone IANA sono presenti. Il ripristino dei backup non è disponibile; non è stata effettuata alcuna chiamata a provider.

Non avviare la Fase 3 finché la Pianificazione non è stata completata e verificata e non è stata ricevuta autorizzazione.
