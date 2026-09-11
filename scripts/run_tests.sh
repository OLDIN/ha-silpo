#!/usr/bin/env bash
# Прогнати весь набір тестів (unit + E2E). Самодостатньо.
set -e
cd "$(dirname "$0")/.."
VENV=".venv-ha/bin/python"
echo "── UNIT (логіка, API, координатор, config flow, сенсори) ──"
$VENV -m pytest tests --ignore=tests/e2e -q
echo ""
echo "── E2E (справжнє HA-ядро + mock Silpo, повний цикл доставки) ──"
SILPO_E2E_PORT="${SILPO_E2E_PORT:-8799}" $VENV -m pytest tests/e2e -q
