# J.A.C.K. — Regole permanenti del progetto

Questo file definisce le regole di lavoro per chiunque modifichi il repository J.A.C.K. (agente o umano). Si applica a tutto il repository: `jack/` (app desktop Flutter/Dart per macOS) e `backend/` (servizio locale FastAPI + SQLite).

## Obiettivo del progetto

J.A.C.K. ("Just Another Chill Kernel") è un prototipo desktop privato per macOS: conversazione con l'assistente, AI Hub per la configurazione dei provider AI, memoria locale. L'AI Hub e la chat devono poter funzionare realmente attraverso il backend FastAPI con provider AI multi-provider (NVIDIA Nemotron, Google Gemini, GroqCloud, OpenRouter, Ollama), senza ricominciare il progetto da zero e senza rimuovere funzionalità già implementate.

## Architettura

- `jack/`: interfaccia desktop Flutter/Dart per macOS.
- `backend/`: servizio locale Python + FastAPI. Endpoint principali:
  - `GET /health`, `GET /api/v1/info`
  - `GET/PUT/DELETE /api/v1/ai/providers/...` (configurazione multi-provider, credenziali, test connessione, selezione/abilitazione modelli, ordine routing)
  - `POST /api/v1/chat` (completazione chat con routing multi-provider)
  - `GET/POST/PUT/DELETE /api/v1/conversations/...` (conversazioni e messaggi persistenti)
  - `GET/POST/PUT/DELETE /api/v1/memories...` (memoria locale SQLite)
- SQLite: memorie, conversazioni e messaggi in `~/Library/Application Support/J.A.C.K./memories.sqlite3` (macOS).
- Le credenziali API per ogni provider sono custodite nel macOS Keychain (servizio `J.A.C.K.`, account `J.A.C.K.<PROVIDER>_API_KEY`) o via variabile d'ambiente (`<PROVIDER>_API_KEY`).

## Regole obbligatorie (Milestone 1 e successive)

1. **Non ricominciare il progetto da zero.** Modificare l'esistente.
2. **Non eliminare funzionalità già implementate.** Le parti dimostrative residue sono solo dati di visualizzazione del Knowledge Core, non risposte AI simulate.
3. **Prima di modificare un file, leggere il contenuto e le dipendenze.**
4. **Non aggiungere pacchetti inutili.** Verificare quali dipendenze servono realmente prima di toccare `pubspec.yaml` o `requirements.txt`.
5. **Non introdurre Riverpod o altri sistemi di state management** senza dimostrare che siano necessari per il milestone in corso.
6. **Mantenere il design attuale di J.A.C.K.** (tema scuro, JackPalette ambra/cyan, `JackPanel`, `SectionEyebrow`, `DemoBadge`, `StatusDot`).
7. **Non modificare il backend se i relativi endpoint funzionano già.**
8. **Non introdurre nuove funzionalità fuori dal perimetro concordato.**
9. **Non inviare richieste a modelli a pagamento.** Il Cost Guard blocca qualsiasi chiamata a provider/modelli non gratuiti.
10. **Non esporre API key nei log, nel codice o nel database.** Le credenziali restano nel Keychain macOS.
11. **Non inventare API key, credenziali, risultati di test o funzionalità non implementate.**
12. **Non eseguire commit o push Git senza autorizzazione.**

## Come avviare

### Backend (terminale 1)

```sh
cd backend
.venv/bin/python -m pip install -r requirements.txt   # se necessario
.venv/bin/python -m app                               # oppure: uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Il backend si lega solo a `127.0.0.1:8000`. L'app Flutter lo chiama su `http://127.0.0.1:8000` (variabile `JACK_BACKEND_URL`).

### Frontend (terminale 2)

```sh
cd jack
flutter pub get
flutter run -d macos
```

### Test

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

## Credenziali e sicurezza

- Non inserire mai API key nel codice né nei file di configurazione committati.
- `backend/.env.example` contiene le variabili d'ambiente commentate (`GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `NVIDIA_API_KEY`).
- Chiavi e credenziali non apparire mai nei log, nelle risposte di errore né nei test.
- Il backend invia richieste solo a modelli gratuiti verificati dal Cost Guard.

## Stato delle funzionalità

| Funzionalità | Stato | Note |
|---|---|---|
| Schermata principale, conversazioni, Knowledge Core | Implementato | UI desktop, grafico da dati reali o di esempio |
| Conversazioni persistenti (crea, elenco, apri, rinomina, elimina) | Implementato | Salvate in SQLite, sopravvivono al riavvio |
| Chat reale multi-provider | Implementato | Router con failover, risposte reali, loading, errore, riprova |
| Recupero contesto memoria nella chat | Implementato | Ricordi pertinenti inclusi nel contesto AI |
| AI Hub: provider NVIDIA, Gemini, Groq, OpenRouter, Ollama | Implementato | Dati reali dal backend, chiavi in Keychain |
| Knowledge Core da dati reali | Implementato | Nodi e relazioni da SQLite |
| Memoria locale (CRUD, ricerca, grafo, link) | Implementato | FastAPI + SQLite, testato |
| Indicatore stato backend | Implementato | `/health`, `/api/v1/info` |
| macOS Keychain per credenziali | Implementato (backend) | Chiave per provider; fallback `.env` |
| Protezione contro costi involontari | Implementato | Solo modelli gratuiti, nessun fallback premium |
| Packaging/firma/distribuzione macOS | Pianificato | Non parte della V1 |

## Convenzioni di codice

- Dart: `flutter_lints` (flutter.yaml), analisi con `flutter analyze`.
- Python: FastAPI, Pydantic, unittest standard. I test backend avviano un server reale su porta libera.
- Messaggi UI in italiano.
- Nessun nuovo state-management tool oltre a `ValueNotifier`/`StatefulWidget` già usati, salvo dimostrata necessità.
