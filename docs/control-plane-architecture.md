# Fondamenta Control Plane

## Scopo e stato

Il Control Plane è il futuro punto di governo per identità, capability, permessi,
policy, approvazioni, audit ed emergency stop. Questo incremento aggiunge
contratti, un registro locale di dichiarazioni e una traccia audit per le
operazioni sul registro. Non abilita agenti, strumenti o missioni a eseguire
azioni; non valuta policy e non concede privilegi.

Il Control Plane è un componente del backend FastAPI esistente, non un servizio
separato. La sua API resta sul bind loopback già imposto dal backend. Non sono
state aggiunte dipendenze o richieste a provider AI.

## Punti d'integrazione esistenti

- `backend/app/main.py` costruisce i servizi, li espone via `app.state`, inizializza
  i repository nel lifespan e registra i database per monitor e backup.
- `backend/app/api/dependencies.py` e `backend/app/api/router.py` sono i punti
  esistenti per dependency injection e composizione delle API.
- Le missioni pianificate e i task appartengono a Planning (`missions` nel
  database `tasks.sqlite3`). Restano dati di pianificazione; non sono un
  executor né un'identità agente autenticata.
- Credenziali e Cost Guard appartengono al sottosistema AI e non vengono letti,
  modificati o duplicati dal Control Plane.
- `LocalBackupService` crea snapshot di tutti i database registrati dal bootstrap;
  il nuovo database Control Plane viene incluso nello stesso backup locale. La
  validazione legacy ammette l'assenza del solo database Control Plane negli
  archivi creati prima di questa fase e restituisce
  `missing_optional_databases`; i database memoria e Planning restano richiesti.
- La UI Flutter mantiene le sezioni attuali. In questa fase non è stata aggiunta
  una UI di gestione permessi o agenti.

## Moduli e persistenza

Il package `backend/app/control_plane/` separa:

- `models.py`: identità e vocabolari condivisi di rischio, esito e stato
  approvazione.
- `schemas.py`: contratti API e futuri contratti di richiesta permesso, regola,
  approvazione ed emergency-stop.
- `repository.py`: SQLite, dichiarazioni e audit atomico.
- `service.py`: validazione delle dichiarazioni; deliberatamente nessuna
  decisione di autorizzazione.
- `routes.py`: API per dichiarazioni e consultazione audit.
- `agent_catalog.py`: catalogo statico in sola lettura di profili specialistici
  selezionati dal repository MIT `msitarzewski/agency-agents`. I file Markdown
  originali e l'avviso di licenza sono in `agency_profiles/`; il catalogo è
  fissato a un commit upstream, non scarica aggiornamenti a runtime.

Il database dedicato `control-plane.sqlite3` usa `PRAGMA user_version=1`, file
mode `0600` e directory applicativa `0700`. Le tabelle sono:

- `control_plane_identities`: chiave composta `(kind, id)` per separare
  `user`, `agent`, `service`, `tool` e `node`.
- `control_plane_capabilities`: dichiarazioni di risorsa, operazioni, ambito,
  rischio e necessità di approvazione; il proprietario deve essere un'identità
  dichiarata.
- `control_plane_audit_events`: eventi per la registrazione delle identità e
  capability. La mutazione e la scrittura audit avvengono nella stessa
  transazione; trigger SQLite rifiutano update e delete degli eventi.

Non esiste migrazione di un database applicativo precedente: il file è nuovo e
indipendente. L'inizializzazione crea lo schema senza cancellare o riscrivere
record; rifiuta una versione futura. L'integrazione è inclusa nel monitor
read-only e nei backup esistenti.

## Contratti di autorizzazione

I contratti condividono un riferimento identità tipizzato (`kind`, `id`).
`PermissionRequestContract` rappresenta:

- richiedente;
- risorsa e operazione;
- ambito strutturato;
- durata opzionale limitata a un anno;
- livello di rischio.

`PolicyRuleContract` descrive un match per risorsa, operazione, tipo richiedente,
ambito e rischio e un esito (`deny`, `requires_approval`, `allow`) con flag di
approvazione. `ApprovalRecordContract` modella richiesta, stato, richiedente,
risolutore e scadenza. `EmergencyStopStatusContract` è unicamente un read-model
per lo stato desiderato.

Questi modelli non sono ancora servizi, decisioni o stato persistito. Non
esistono endpoint per chiedere/decidere permessi, applicare regole, approvare
azioni o cambiare emergency stop. Il campo `approval_required` di una
capability è una proprietà dichiarata, non un requisito effettivamente
enforced.

## API attive

Prefisso `/api/v1/control-plane`:

- `GET /identities`: consulta le identità dichiarate, con filtro per tipo e
  paginazione.
- `POST /identities`: registra una dichiarazione, senza autenticare né
  confermare l'identità reale del chiamante.
- `GET /capabilities`: consulta dichiarazioni, con filtri proprietario/risorsa
  e paginazione.
- `POST /capabilities`: registra una dichiarazione solo per un'identità già
  registrata; non abilita la risorsa o l'operazione.
- `GET /audit-events`: consulta gli eventi immutabili del registro con filtri
  per soggetto/azione e paginazione.
- `GET /agent-profiles`: elenca i profili curati, con provenienza e stato
  esplicitamente inattivo.
- `GET /agent-profiles/{profile_id}`: legge il profilo Markdown originale
  selezionato. Non esistono endpoint per abilitarlo, assegnargli strumenti o
  avviarne l'esecuzione.

Il primo set contiene dieci ruoli per architettura, backend, desktop, AI,
sistemi multi-agente, modifiche minime, code review, privacy, test automation e
gestione progetto. I profili sono testo consultivo: `enabled` ed
`execution_enabled` sono sempre `false`, `tools` e `capabilities` sono vuoti.
Il catalogo non crea identità nel registro persistente né modifica missioni o
permessi. “Gratuito” si riferisce ai profili MIT; eventuali chiamate a modelli
restano soggette al Cost Guard e alle disponibilità dei provider configurati.

Le mutazioni generano eventi attribuiti al servizio `control-plane-api`, perché
il backend attuale non autentica l'identità umana o agente che invoca l'API.
Questi eventi attestano la registrazione vista dal servizio, non l'identità
fisica del chiamante né un'approvazione. L'audit SQLite è append-only a livello
applicativo e tramite trigger, ma non è una prova antimanomissione contro chi
controlla il file o il processo.

## Vincoli prima dell'Execution Plane

Prima di collegare strumenti o agenti dovranno essere completati e testati:

1. autenticazione delle identità e provenienza non falsificabile del richiedente;
2. un Permission Manager con grant espliciti, ambito e scadenza e revoca;
3. un Policy Engine fail-closed con precedenza del deny e senza fallback;
4. un Approval Manager che lega approvazione a una richiesta immutabile,
   scadente, monouso e verificata al momento dell'esecuzione;
5. enforcement in un unico confine di esecuzione: nessun agente deve ottenere
   accesso diretto ai servizi o strumenti che permetta di saltare il gate;
6. emergency stop effettivo, atomico e testato prima di qualsiasi autonomia;
7. audit delle decisioni ed esecuzioni con gestione di privacy, retention e
   minacce alla manomissione;
8. test end-to-end che provino il rifiuto delle chiamate dirette e il
   comportamento fail-closed.

La fase corrente non modifica Core Protection, permessi filesystem, credenziali,
Cost Guard, terminale, policy attive o emergency stop.
