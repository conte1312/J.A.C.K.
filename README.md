# J.A.C.K. — Just Another Chill Kernel

J.A.C.K. è un prototipo desktop per macOS in sviluppo. L'interfaccia segue il riferimento visivo Base44 e usa un tema scuro con accenti ambra e dettagli cyan.

> **Stato:** prima versione stabile (V1). L'AI Hub e la chat usano il backend locale FastAPI con supporto multi-provider AI (NVIDIA Nemotron, Google Gemini, GroqCloud, OpenRouter, Ollama); le parti dimostrative residue sono solo dati di visualizzazione del Knowledge Core, non risposte AI simulate.

## Architettura

- `jack/`: interfaccia desktop Flutter/Dart per macOS.
- `backend/`: servizio locale Python + FastAPI.
- SQLite: memorie, conversazioni e messaggi aggiunti dall'utente, gestiti dal backend.
- AI Hub: configurazione dei provider AI (chiave API, test connessione, selezione e abilitazione modelli, ordine di routing) letta dal backend.

Il backend espone `/health`, `/api/v1/info`, le API AI in `/api/v1/ai/...`, la chat persistente `POST /api/v1/conversations/{id}/chat` (oltre all'endpoint diretto `POST /api/v1/chat`), le API conversazioni in `/api/v1/conversations/...` e le API CRUD per le memorie in `/api/v1/memories`. Su macOS il database viene creato in `~/Library/Application Support/J.A.C.K./memories.sqlite3`.

## Funzionalità presenti

- **Schermata principale desktop** con conversazioni persistenti, navigazione e Knowledge Core interattivo.
- **Conversazioni persistenti:** creazione, elenco, apertura, rinomina ed eliminazione con conferma. I messaggi sono salvati in SQLite e sopravvivono alla chiusura e riapertura dell'app.
- **Chat reale multi-provider:** l'invio dalla schermata principale chiama `POST /api/v1/chat` attraverso un router intelligente che seleziona il provider disponibile (Gemini → Groq → OpenRouter → Ollama → NVIDIA), mostra le risposte, con stati di caricamento, gestione errori e possibilità di riprovare. Quando il backend non è disponibile non vengono mostrate risposte simulate.
- **Recupero contesto:** durante la chat il backend recupera i ricordi pertinenti dalla memoria locale e li include nel contesto inviato al modello, rispettando categorie ed esclusioni.
- **AI Hub:** gestione multi-provider con stato reale (configurato, disponibile, quota esaurita, errore), salvataggio chiavi API nel Keychain macOS, test connessione per provider, selezione modello, abilitazione/disabilitazione provider, ordine di routing personalizzabile.
- **Knowledge Core:** visualizza i nodi (ricordi) e le relazioni reali restituiti dal backend, distinguendo per categorie. Si aggiorna quando le memorie vengono create o eliminate.
- **Memoria locale:** creazione, modifica, eliminazione, ricerca e filtro per categoria tramite FastAPI e SQLite.
- **Indicatore dello stato reale del backend**, separato dallo stato dei provider AI.

## Configurazione dei provider AI

L'app Flutter non salva né gestisce credenziali. Le chiavi API si configurano nell'AI Hub dell'app e vengono inviate al backend locale, che le custodisce nel Keychain macOS.

Provider supportati (tutti con piano gratuito):

| Provider | Tipo | Chiave d'ambiente | Modelli gratuiti |
|---|---|---|---|
| Google Gemini | Online | `GEMINI_API_KEY` | gemini-1.5-flash, gemini-1.5-flash-8b, gemini-1.5-pro |
| GroqCloud | Online | `GROQ_API_KEY` | llama-3.1-8b-instant, llama-3.1-70b-versatile, mixtral-8x7b-32768 |
| OpenRouter | Online | `OPENROUTER_API_KEY` | solo modelli con suffisso `:free` |
| Ollama | Locale | Nessuna | Modelli installati localmente |
| NVIDIA Nemotron | Online | `NVIDIA_API_KEY` | nemotron-3.5-lightning-30b-a3b, nemotron-3.5-bolt-e4b |

Nessuna API key va inserita nel codice né committata nel repository.

## Protezione contro costi involontari

J.A.C.K. invia richieste esclusivamente a modelli gratuiti. Il backend:

- Blocca qualsiasi richiesta verso modelli a pagamento.
- Non effettua fallback verso piani premium.
- Non acquista crediti né effettua upgrade automatici.
- Se un provider esaurisce la quota gratuita, passa al successivo (se autorizzato) o mostra un errore.
- Se nessun provider gratuito è disponibile, la chat segnala l'errore senza inviare richieste a pagamento.

## Prerequisiti

- macOS e Xcode (con gli strumenti da riga di comando).
- Flutter con Dart compatibile con il vincolo `^3.13.7` indicato in `jack/pubspec.yaml`.
- Python 3.10 o successivo (consigliato 3.11+ per il venv del backend).
- Git.

## Avvio

Avvia il backend in un terminale:

```sh
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env  # facoltativo: API key solo locale
.venv/bin/python -m app
```

Avvia l'app in un secondo terminale:

```sh
cd jack
flutter pub get
flutter run -d macos
```

L'app resta utilizzabile anche quando il backend è spento; in quel caso le funzioni Memoria mostrano che il servizio locale non è disponibile e la chat segnala l'errore invece di mostrare risposte simulate.

## Test e controlli

Backend:

```sh
cd backend
.venv/bin/python -m unittest discover -s tests -v
```

Flutter:

```sh
cd jack
dart format lib test
flutter analyze --no-pub
flutter test --no-pub
```

## Stato implementazione (V1)

| Funzionalità | Stato | Note |
|---|---|---|
| Schermata principale, conversazioni, Knowledge Core | Implementato | |
| Conversazioni persistenti (crea, elenco, apri, rinomina, elimina) | Implementato | Salvate in SQLite |
| Chat reale multi-provider | Implementato | Router con failover, loading, errore, riprova |
| Recupero contesto memoria nella chat | Implementato | Ricordi pertinenti inclusi nel contesto AI |
| AI Hub: multi-provider, chiavi API, test connessione, ordine routing | Implementato | Dati reali dal backend |
| Knowledge Core da dati reali | Implementato | Nodi e relazioni da SQLite |
| Memoria locale (CRUD, ricerca, grafo, link) | Implementato | FastAPI + SQLite |
| Indicatore stato backend | Implementato | `/health`, `/api/v1/info` |
| macOS Keychain credenziali | Implementato (backend) | Chiave per provider, fallback `.env` |
| Protezione contro costi involontari | Implementato | Solo modelli gratuiti, nessun fallback premium |
| Packaging/firma/distribuzione macOS | Pianificato | Non parte della V1 |

## Limiti attuali

Non sono implementati account, abbonamenti, sincronizzazione cloud, memoria semantica (embedding/DB vettoriali), voce, wake word, controllo del Mac. Il database SQLite non è cifrato a riposo. Ollama è disponibile come provider locale ma non scarica modelli automaticamente. In assenza di memorie reali, il Knowledge Core mostra uno stato vuoto; i dati dimostrativi sono confinati ai test.

## Roadmap sintetica

1. Consolidare UX, accessibilità e gestione degli errori della V1.
2. Progettare in milestone separate l'integrazione sicura dei provider e delle credenziali con macOS Keychain.
3. Valutare esportazione e backup locali della memoria.
4. Preparare packaging, firma e distribuzione macOS dopo le verifiche di sicurezza e qualità.
5. Introdurre capacità operative future (Task Engine, Planning Engine, Module Engine) con permessi granulari.
# J.A.C.K.