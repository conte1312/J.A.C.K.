# J.A.C.K. 2.0 — Guida di setup e sviluppo

## Panoramica

J.A.C.K. 2.0 è una ricostruzione completa (rewrite) di J.A.C.K., progettata per essere
pulita, modulare, documentata e pronta a evolvere nel tempo.

Stack:
- **Frontend:** Flutter (Dart), desktop macOS come prima piattaforma,
  predisposto per Windows, Linux, iOS, Android.
- **Backend:** Python + FastAPI, vincolato a loopback `127.0.0.1`.
- **Database:** SQLite iniziale, repository pattern, migrazioni versionate.
- **Catalogo agenti:** `msitarzewski/agency-agents` (importazione completa, MIT).

## Struttura repository

```
J.A.C.K./
├── backend/              Python + FastAPI (API v1 legacy + v2 attiva)
├── jack/                 Flutter frontend
├── catalog/              agency-agents (originali upstream + adattamenti J.A.C.K.)
├── docs/                 documentazione
├── legacy/v1/            riferimento storico del vecchio progetto (intatto)
├── migrations/           migrazioni SQL versionate
├── tests/                test automatici (backend + frontend)
├── start.sh              avvio rapido backend + frontend
└── .gitignore
```

## Prerequisiti

- macOS (prima piattaforma) con Xcode e strumenti da riga di comando.
- Flutter SDK con Dart compatibile con `^3.13.7`.
- Python 3.10+ (consigliato 3.11+).
- Git.

## Avvio backend (terminale 1)

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # opzionale; nessuna API key nel codice
python -m app
```

Il backend si lega solo a `http://127.0.0.1:8000`.

Endpoint disponibili in M1:
- `GET /health`
- `GET /api/v1/health`
- `GET /api/v1/v1/health` (V1 legacy)
- `GET /api/v1/v2/health` (J.A.C.K. 2.0 attivo)
- `GET /api/v1/v2/info`

## Avvio frontend (terminale 2)

```sh
cd jack
flutter pub get
flutter run -d macos
```

## Avvio rapido completo

```sh
./start.sh
```

## Test

Backend:

```sh
cd backend
source .venv/bin/activate
python -m unittest discover -s tests -v
```

Flutter:

```sh
cd jack
flutter analyze --no-pub
flutter test --no-pub
```

Build macOS:

```sh
cd jack
flutter build macos --no-pub
```

## Sicurezza e credenziali

- Nessuna API key nel codice né nei file committati.
- Le credenziali sono gestite dal backend (Keychain su macOS, fallback `.env`).
- Il logging non espone mai segreti (`SecretRedactingFormatter`).
- Il backend è vincolato a loopback; nessuna esposizione sulla rete esterna.

## Conservazione del vecchio codice (V1)

Il progetto V1 è conservato integralmente in `legacy/v1/` come riferimento storico.
La nuova applicazione 2.0 non dipende da alcun modulo V1 per funzionare.
I branch `main` e `development` restano intatti con la loro storia Git.

## Milestone

Lo sviluppo procede per milestone (M0 audit → M10 integrazione in `main`).
Vedi `ROADMAP.md` e la documentazione di ogni milestone.
