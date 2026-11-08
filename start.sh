#!/usr/bin/env bash
# J.A.C.K. — Avvio rapido completo
# Avvia backend FastAPI e frontend Flutter (macOS) in un colpo solo.
#
# Uso: ./start.sh
#      Oppure: bash start.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/jack"
BACKEND_URL="http://127.0.0.1:8000"

echo "============================================================"
echo "  J.A.C.K. — Just Another Chill Kernel"
echo "  Avvio rapido completo"
echo "============================================================"
echo ""

# Verifica che siamo su macOS
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "⚠️  Attenzione: J.A.C.K. è progettato per macOS. Stai eseguendo su $(uname -s)."
fi

# 1. Verifica/avvia backend
echo "[1/3] Verifica backend su $BACKEND_URL..."
if curl -s -m 2 "$BACKEND_URL/health" > /dev/null 2>&1; then
  echo "   ✓ Backend già in esecuzione su $BACKEND_URL"
else
  echo "   → Avvio backend FastAPI..."
  if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
    echo "   Creazione ambiente virtuale Python..."
    python3 -m venv "$BACKEND_DIR/.venv"
    "$BACKEND_DIR/.venv/bin/python" -m pip install -r "$BACKEND_DIR/requirements.txt" > /dev/null 2>&1
  fi

  # Avvia backend in background (nohup)
  cd "$BACKEND_DIR"
  nohup .venv/bin/python -m app > /tmp/jack_backend.log 2>&1 &
  BACKEND_PID=$!
  echo "   PID backend: $BACKEND_PID"

  # Attendi che sia pronto
  for i in $(seq 1 30); do
    if curl -s -m 1 "$BACKEND_URL/health" > /dev/null 2>&1; then
      echo "   ✓ Backend pronto su $BACKEND_URL"
      break
    fi
    sleep 0.5
  done

  if ! curl -s -m 1 "$BACKEND_URL/health" > /dev/null 2>&1; then
    echo "   ✗ Impossibile avviare il backend. Controlla /tmp/jack_backend.log"
    exit 1
  fi
fi

# 2. Verifica Flutter
echo ""
echo "[2/3] Verifica ambiente Flutter..."
if ! command -v flutter > /dev/null 2>&1; then
  echo "   ✗ Flutter non trovato nel PATH. Installa Flutter da https://flutter.dev"
  exit 1
fi

cd "$FRONTEND_DIR"

# Esegue flutter pub get se necessario
if [[ ! -d ".dart_tool" ]]; then
  echo "   → Esecuzione flutter pub get..."
  flutter pub get > /tmp/jack_pubget.log 2>&1 || {
    echo "   ✗ flutter pub get fallito. Controlla /tmp/jack_pubget.log"
    exit 1
  }
fi

# 3. Avvia frontend su macOS
echo ""
echo "[3/3] Avvio applicazione macOS..."
echo "   Comando: flutter run -d macos"
echo ""
echo "   Premi 'q' nel terminale Flutter per uscire dall'app."
echo "   Premi Ctrl+C in questo terminale per fermare tutto."
echo ""
echo "   Avvio in corso..."
echo ""

# Avvia Flutter in foreground (l'utente interagisce qui)
cd "$FRONTEND_DIR"
flutter run -d macos

# Quando Flutter esce, ferma il backend se lo abbiamo avviato noi
if [[ -n "${BACKEND_PID:-}" ]]; then
  echo ""
  echo "   Arresto backend (PID $BACKEND_PID)..."
  kill "$BACKEND_PID" 2>/dev/null || true
fi

echo ""
echo "   J.A.C.K. chiuso."
echo "============================================================"
