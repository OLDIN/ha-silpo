#!/usr/bin/env bash
# Піднімає СПРАВЖНІЙ Home Assistant (процес, з UI на :8123) з інтеграцією silpo,
# на mock-сервері Сільпо. Повністю автоматично: onboarding, config entry,
# перевірка. Дозволяє демонструвати переходи статусів через API mock.
#
#   scripts/dev_ha_ui.sh up      — підняти все (HA + mock)
#   scripts/dev_ha_ui.sh status <collected|delivery_in_progress|received>
#   scripts/dev_ha_ui.sh down    — зупинити
set -euo pipefail
cd "$(dirname "$0")/.."
VENV="$PWD/.venv-ha/bin"
CFG="$PWD/ha_config"
PORT_HA=8123
PORT_MOCK=8799
BASE="http://127.0.0.1:$PORT_HA"
MOCK="http://127.0.0.1:$PORT_MOCK"
export SILPO_ECOM_BASE=$MOCK SILPO_CITYRYDER_BASE=$MOCK SILPO_AUTH_BASE=$MOCK SILPO_E2E_PORT=$PORT_MOCK

_wait_port_free() { for i in $(seq 1 20); do lsof -ti :$1 >/dev/null 2>&1 || return 0; sleep 1; done; return 1; }
_wait_ha() { for i in $(seq 1 40); do curl -sf -o /dev/null $BASE/ 2>/dev/null && return 0; sleep 5; done; return 1; }

cmd_up() {
  cmd_down  # прибрати попередні процеси/порти
  # 1. свіжий config + symlink інтеграції
  rm -rf "$CFG"; mkdir -p "$CFG/custom_components"
  ln -sfn "$PWD/custom_components/silpo" "$CFG/custom_components/silpo"
  printf 'default_config:\nlogger:\n  default: warning\n  logs:\n    custom_components.silpo: debug\n' > "$CFG/configuration.yaml"
  _wait_port_free $PORT_HA >/dev/null || true; _wait_port_free $PORT_MOCK >/dev/null || true
  # 2. mock фоном
  SILPO_E2E_PORT=$PORT_MOCK nohup "$VENV/python" scripts/run_mock.py > "$CFG/mock.log" 2>&1 &
  echo "mock PID $!"
  # 3. hass перший старт (генерує config)
  nohup "$VENV/hass" --config "$CFG" > "$CFG/ha.log" 2>&1 &
  echo "hass PID $! (чекаю :8123...)"; _wait_ha || { echo "HA не піднявся"; tail -20 "$CFG/ha.log"; exit 1; }
  # 4. onboarding + токен (надійний Python-хелпер)
  ACCESS=$("$VENV/python" scripts/ha_auth.py $BASE admin silpo1234 | tail -1)
  [ -z "$ACCESS" ] && { echo "auth не вдався"; tail -15 "$CFG/ha.log"; exit 1; }
  echo "$ACCESS" > "$CFG/.ha_token"
  # 5. зупинити, інжектнути config entry, стартувати знову
  pkill -TERM -f "hass --config" 2>/dev/null || true
  for i in $(seq 1 20); do pgrep -f "hass --config" >/dev/null || break; sleep 1; done
  _wait_port_free $PORT_HA || echo "порт ще зайнятий"
  "$VENV/python" scripts/inject_entry.py "$CFG"
  nohup "$VENV/hass" --config "$CFG" > "$CFG/ha.log" 2>&1 &
  echo "hass рестарт PID $! (чекаю :8123...)"; _wait_ha || { echo "рестарт не вдався"; exit 1; }
  for i in $(seq 1 15); do cmd_show 2>/dev/null | grep -q sensor.silpo && break; sleep 2; done
  echo ""; echo "✅ ГОТОВО. UI: $BASE  (admin / silpo1234)"
  cmd_show
}

cmd_show() {
  ACCESS=$(cat "$CFG/.ha_token")
  curl -s $BASE/api/states -H "Authorization: Bearer $ACCESS" | "$VENV/python" -c "
import sys,json
try: d=json.load(sys.stdin)
except Exception: print('  (HA ще не готовий)'); sys.exit()
ents=[x for x in d if 'silpo' in x['entity_id']] if isinstance(d,list) else []
[print(f\"  {x['entity_id']} = {x['state']}\") for x in ents] or print('  (сенсорів ще немає)')"
}

cmd_status() {
  curl -s -X POST $MOCK/_test/set_status -H 'Content-Type: application/json' -d "{\"status\":\"$1\"}" >/dev/null
  echo "статус mock -> $1 (чекаю опитування координатора ~7с)"; sleep 7; cmd_show
}

cmd_down() {
  pkill -9 -f "hass --config" 2>/dev/null || true
  pkill -9 -f "run_mock.py" 2>/dev/null || true
  sleep 2
  lsof -ti :$PORT_HA 2>/dev/null | xargs kill -9 2>/dev/null || true
  lsof -ti :$PORT_MOCK 2>/dev/null | xargs kill -9 2>/dev/null || true
  echo "зупинено"
}

case "${1:-up}" in
  up) cmd_up ;;
  status) cmd_status "${2:?статус: collected|delivery_in_progress|received}" ;;
  show) cmd_show ;;
  down) cmd_down ;;
  *) echo "usage: $0 {up|status <s>|show|down}"; exit 1 ;;
esac
