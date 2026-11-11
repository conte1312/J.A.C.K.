# Riferimento storico — J.A.C.K. V1

Questa pagina documenta il vecchio progetto J.A.C.K. (versione 1), conservato come
riferimento storico e funzionale. Non costituisce un vincolo architetturale
per J.A.C.K. 2.0 e non è utilizzato dal nuovo codice.

## Dove si trova il codice V1

Il codice completo di V1 è conservato nella directory `legacy/v1/` di questo
branch (`rewrite/jack-2.0`) e, integralmente con la sua storia Git, nei branch
`main` e `development` della repository.

## Struttura di `legacy/v1/`

- `backend/` — servizio FastAPI + Python originale (V1)
- `jack/` — app desktop Flutter/Dart originale (V1, macOS)
- `docs/` — documentazione originale
- `.gitignore`, `AGENTS.md`, `CHANGELOG.md`, `README.md`, `ROADMAP.md`, `start.sh`

## Stato del codice V1 (ultimo commit su `development`)

Commit: `784c73a feat(control-plane): add curated agency agent catalog`
Branch: `development` (allineato a `origin/development`)

Funzionalità effettivamente presenti in V1:
- Chat multi-provider reale (router con failover, solo modelli gratuiti, Cost Guard)
- Conversazioni persistenti SQLite
- Memoria locale CRUD, ricerca, filtri, MemoryLink, knowledge graph
- AI Hub: provider, API key (Keychain macOS), test connessione, routing
- Knowledge Core da dati reali SQLite
- Pianificazione (task, progetti, dipendenze, ricorrenze, missioni, fuso orario)
- Control Plane: catalogo consultivo di 10 profili selezionati da `agency-agents`
- Monitor di sistema, backup locali (ZIP, read-only), security-status informativo
- Build macOS verificata

## Rapporto con J.A.C.K. 2.0

- La nuova applicazione 2.0 **non dipende** da alcun modulo V1 per funzionare.
- I branch `main` e `development` restano intatti con la loro storia Git
  (nessuna riscrittura, nessun `reset --hard`, nessun `clean`, nessun force push).
- Il codice V1 è un riferimento, non un vincolo: le decisioni architetturali di
  2.0 sono indipendenti dall'implementazione precedente.

## V1 vs 2.0 (per schermata/dominio)

Questa mappatura viene compilata in dettaglio in M2.
