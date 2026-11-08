# J.A.C.K. — app macOS

Questa cartella contiene l'interfaccia desktop Flutter/Dart di J.A.C.K. Per architettura, prerequisiti, avvio del backend locale e test, consulta il [README principale](../README.md).

Avvio rapido dell'app da questa cartella:

```sh
flutter pub get
flutter run -d macos
```

Il backend FastAPI è nella cartella sorella `../backend/`. L'AI Hub legge e aggiorna tramite backend la configurazione reale dei provider AI (NVIDIA, Gemini, Groq, OpenRouter, Ollama), inclusi modelli selezionati/abilitati e ordine di routing. La chat invia i messaggi a `POST /api/v1/conversations/{id}/chat` tramite il router multi-provider; conversazioni e messaggi sono persistenti in SQLite.
