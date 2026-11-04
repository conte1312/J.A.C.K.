# J.A.C.K. — Just Another Chill Kernel

J.A.C.K. è un prototipo desktop per macOS in sviluppo. L'interfaccia segue il riferimento visivo Base44 e usa un tema scuro con accenti ambra e dettagli cyan.

> **Stato:** prototipo in sviluppo, non pronto per la produzione. L'AI Hub è dimostrativo: al momento non sono collegati provider AI reali.

## Architettura

- `jack/`: interfaccia desktop Flutter/Dart per macOS.
- `backend/`: servizio locale Python + FastAPI.
- SQLite: memorie aggiunte esplicitamente dall'utente, gestite dal backend.
- AI Hub: configurazione dimostrativa dei modelli e delle regole di routing salvata localmente dall'app.

Il backend espone `/health`, `/api/v1/info` e le API CRUD per le memorie in `/api/v1/memories`. Su macOS il database viene creato in `~/Library/Application Support/J.A.C.K./memories.sqlite3`.

## Funzionalità presenti

- Schermata principale desktop con conversazioni demo, navigazione e Knowledge Core interattivo.
- AI Hub demo con gestione dei modelli dimostrativi, modello predefinito e routing simulato.
- Memoria locale con creazione, modifica, eliminazione, ricerca e filtro per categoria tramite FastAPI e SQLite.
- Indicatore dello stato reale del backend, separato dallo stato dei provider AI.
- Stati di caricamento, errore e backend non disponibile per le funzioni che richiedono il servizio locale.

Le memorie vengono inserite dall'utente e restano nel database locale. La chat non viene letta automaticamente per creare ricordi; i contenuti non vengono sincronizzati sul cloud né inviati a provider AI.

## Prerequisiti

- macOS e Xcode (con gli strumenti da riga di comando).
- Flutter con Dart compatibile con il vincolo `^3.13.7` indicato in `jack/pubspec.yaml`.
- Python 3.10 o successivo.
- Git.

## Avvio

Avvia il backend in un terminale:

```sh
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env  # facoltativo: configurazione solo locale
.venv/bin/python -m app
```

Avvia l'app in un secondo terminale:

```sh
cd jack
flutter pub get
flutter run -d macos
```

L'app resta utilizzabile anche quando il backend è spento; in quel caso le funzioni Memoria mostrano che il servizio locale non è disponibile. L'AI Hub demo non effettua chiamate ai modelli.

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

## Limiti attuali

Non sono implementati provider AI reali, gestione di API key, account o abbonamenti, sincronizzazione cloud, memoria semantica, voce, wake word o controllo del Mac. Le credenziali non vengono salvate; l'integrazione con macOS Keychain non è ancora presente. Costi, quote e disponibilità mostrati nell'AI Hub sono dati di esempio e non rappresentano offerte reali.

## Roadmap sintetica

1. Consolidare UX, accessibilità e gestione degli errori del prototipo.
2. Progettare in milestone separate l'integrazione sicura dei provider e delle credenziali con macOS Keychain.
3. Valutare esportazione e backup locali della memoria.
4. Preparare packaging, firma e distribuzione macOS dopo le verifiche di sicurezza e qualità.
