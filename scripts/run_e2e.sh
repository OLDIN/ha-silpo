#!/usr/bin/env bash
# E2E: піднімає справжнє HA-ядро, встановлює інтеграцію, mock Silpo віддає
# фікстури й перемикає статуси; перевіряє події та стани сенсорів.
set -e
cd "$(dirname "$0")/.."
export SILPO_E2E_PORT="${SILPO_E2E_PORT:-8799}"
.venv-ha/bin/python -m pytest tests/e2e -v
