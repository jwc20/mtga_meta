#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ -n "$WINDIR" ]]; then
  VENV_ACTIVATE="Scripts/activate"
else
  VENV_ACTIVATE="bin/activate"
fi

if [[ -f "venv/$VENV_ACTIVATE" ]]; then
  source "venv/$VENV_ACTIVATE"
elif [[ -f ".venv/$VENV_ACTIVATE" ]]; then
  source ".venv/$VENV_ACTIVATE"
else
  echo "No virtual environment found. Creating .venv..."
  python3 -m venv .venv || python -m venv .venv
  source ".venv/$VENV_ACTIVATE"
  echo "Installing dependencies..."
  pip install --upgrade pip
  if [[ -f "pyproject.toml" ]]; then
    pip install -e .
  elif [[ -f "requirements.txt" ]]; then
    pip install -r requirements.txt
  fi
  echo "Virtual environment created and activated."
fi

FOLLOWER_PID=""
FASTAPI_PID=""

cleanup() {
  echo ""
  echo "Shutting down gracefully..."

  if [[ -n "$FASTAPI_PID" ]] && kill -0 $FASTAPI_PID 2>/dev/null; then
    echo "Stopping FastAPI app (PID: $FASTAPI_PID)..."
    kill -TERM $FASTAPI_PID 2>/dev/null
    wait $FASTAPI_PID 2>/dev/null || true
    echo "FastAPI app stopped."
  fi

  if [[ -n "$FOLLOWER_PID" ]] && kill -0 $FOLLOWER_PID 2>/dev/null; then
    echo "Stopping MTGA Follower (PID: $FOLLOWER_PID)..."
    kill -TERM $FOLLOWER_PID 2>/dev/null
    wait $FOLLOWER_PID 2>/dev/null || true
    echo "MTGA Follower stopped."
  fi

  echo "All processes stopped."
  exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo "Starting MTGA Follower..."
python seventeenlands/mtga_follower.py &
FOLLOWER_PID=$!
echo "MTGA Follower started (PID: $FOLLOWER_PID)"

echo "Starting FastAPI app..."
uvicorn app.main:app --reload --host=0.0.0.0 --port=8765 &
FASTAPI_PID=$!
echo "FastAPI app started (PID: $FASTAPI_PID)"

echo ""
echo "Both processes running. Press Ctrl+C to stop."
echo ""

wait $FOLLOWER_PID $FASTAPI_PID