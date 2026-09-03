#!/usr/bin/env bash
set -euo pipefail

# Swissfin Bench convenience commands. SWISSFIN_DB_PATH selects the database.

cd "$(dirname "$0")/.."

if [ -n "${SWISSFIN_PYTHON_BIN:-}" ]; then
  :
elif [ -x ".venv/bin/python" ]; then
  SWISSFIN_PYTHON_BIN=".venv/bin/python"
elif [ -x "venv/bin/python" ]; then
  SWISSFIN_PYTHON_BIN="venv/bin/python"
else
  SWISSFIN_PYTHON_BIN="python"
fi

case "${1:-help}" in
  backoffice)
    "${SWISSFIN_PYTHON_BIN}" -m streamlit run backoffice/app.py
    ;;
  input)
    "${SWISSFIN_PYTHON_BIN}" app.py input "${@:2}"
    ;;
  run)
    "${SWISSFIN_PYTHON_BIN}" app.py run "${@:2}"
    ;;
  install)
    "${SWISSFIN_PYTHON_BIN}" -m pip install -e ".[backoffice,test]"
    ;;
  test)
    if ! "${SWISSFIN_PYTHON_BIN}" -c 'import pytest' >/dev/null 2>&1; then
      echo "pytest not found for ${SWISSFIN_PYTHON_BIN}; installing test dependencies..."
      "${SWISSFIN_PYTHON_BIN}" -m pip install -e ".[test]"
    fi
    if ! "${SWISSFIN_PYTHON_BIN}" -c 'import pytest' >/dev/null 2>&1; then
      echo "pytest is still unavailable for ${SWISSFIN_PYTHON_BIN}."
      echo "Set SWISSFIN_PYTHON_BIN to your intended interpreter and retry."
      echo "Example: SWISSFIN_PYTHON_BIN=/path/to/venv/bin/python ./scripts/run.sh test"
      exit 1
    fi
    "${SWISSFIN_PYTHON_BIN}" -m pytest
    ;;
  help|*)
    echo "Usage: ./scripts/run.sh {install|test|input|run|backoffice} [arguments]"
    echo "Set SWISSFIN_DB_PATH to avoid using the canonical myfile.db."
    ;;
esac
