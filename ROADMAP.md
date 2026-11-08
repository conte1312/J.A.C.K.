# J.A.C.K. — ROADMAP (stato FASE 1 / V1.1)

**Data:** 08 Nov 2026
**Branch:** `main` — commit V1.0/V1.1 integrato `acaf71d`; configurazione piattaforme `e0fb81e`. Nessun tag o push effettuato.
**Stack:** Flutter 3.47.9 / Dart 3.13.7 (macOS), FastAPI backend, SQLite, macOS Keychain.

## Stato FASE 1 — COMPLETAMENTO V1.1 (conclusa)

| Intervento | Stato | Note |
|---|---|---|
| A. Routing multi-provider dinamico | ✅ Già applicato | `_newConversation()` usa `providerId: _aiConfiguration!.selectedProviderId` (non più `'nvidia'` hardcoded). `_sendMessage` usa già `selectedModel!.id`. |
| B. Memoria contestuale nella chat | ✅ Già implementato | Backend `POST /conversations/{id}/chat` → `chat_with_context()` con `memory_repository`; recupera ricordi pertinenti e li inietta come blocchi di sistema. Frontend `chatInConversation()` già collegato. |
| C. Knowledge Core su dati reali | ✅ Implementato | Rimosso fallback `jackCoreDemoGraph` dal codice produzione (`jack_home_page.dart`, `right_rail.dart`). Sostituito con `JackCoreGraph.empty` (stato vuoto, nessun dato demo). Il file `jack_core_demo_data.dart` è mantenuto solo perché usato dai test. |
| D. Grafo reattivo | ✅ Implementato | - `_graphLoading` inizializzato a `false` (era `true`: bloccava per sempre il primo caricamento via `_loadBackend`).<br>- `MemoryScreen` accetta `onMemoryChanged`; lo invoca dopo crea/aggiorna/elimina ricordo.<br>- `JackHomePage` lo collega a `_loadLiveGraph()` e passa `graph` a `RightRail`. |
| E. Primo avvio guidato | ✅ Già presente | `_NoProviderNotice` guida all'AI Hub con pulsante "Apri AI Hub" e cita Ollama (locale, senza chiave API). |
| F. Pulizia codice | ✅ Implementato | Rimosso `_aiNotConfigured` (inutilizzato). `_ContextChip` e `_showMessage` di `ai_hub_screen.dart` già assenti. |

## Risultati verifiche

- `flutter analyze`: 0 errori. 10 warning/info preesistenti (escono con exit code 1, nessun errore di compilazione). Nessuna nuova issue introdotta.
- `flutter test`: **34/34 passati** (tra cui `conversation_redesign_test` aggiornato a dati reali).
- Backend (`venv pytest`): **25/25 passati**, 4 subtest.
- Backend `/health`: `ok` su `127.0.0.1:8000`.

## Dipendenze / problemi aperti

- Nessuna nuova dipendenza. Nessun provider a pagamento attivato. Nessuna credenziale in chiaro.
- Questo documento registra lo stato V1.1; le modifiche di Pianificazione V1.2 restano fuori dai commit V1.0/V1.1 e non costituiscono una release completata.
- La cronologia separa in un commit integrato il core AI/chat e la memoria contestuale/Knowledge Core, perché i rispettivi bootstrap condividono file applicativi. Non è stato creato alcun tag di release.

## Prossimo passo

La FASE 2 (Pianificazione / task management) non è dichiarata completata. Non iniziare la FASE 3.
