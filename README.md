# Silpo — Home Assistant інтеграція

Стежить за активним онлайн-замовленням у [Сільпо](https://silpo.ua) і **генерує події
Home Assistant при зміні статусу доставки** — щоб озвучувати на колонці «кур'єр виїхав»,
«кур'єр близько», «замовлення доставлено».

## Можливості
- 🚚 **Сенсор статусу замовлення** — `sensor.silpo_order_status`
  (`new` → `collecting` → `collected` → `delivery_in_progress` → `received`).
- 📍 **Сенсор відстані кур'єра** — `sensor.silpo_courier_distance` (метри до вашої адреси, під час доставки).
- 🗺️ **Кур'єр на карті** — `device_tracker.silpo_courier` (GPS-позиція на стандартній карті HA).
- 🔔 **Події на шині HA** для автоматизацій:
  - `silpo_order_status_changed` — `{order_number, old_status, new_status, ...}`.
    **«Кур'єр виїхав» = `new_status: delivery_in_progress`**; «доставлено» = `received`.
  - `silpo_courier_proximity` — `{order_number, distance_m, threshold_m}` при перетині 1000/500/200 м.
- 🔐 **Авторизація OTP** (SMS), автономний рефреш токена через `offline_access`.

## Приклад автоматизації (озвучення «кур'єр виїхав»)
```yaml
automation:
  - alias: "Silpo: кур'єр виїхав"
    trigger:
      - platform: event
        event_type: silpo_order_status_changed
        event_data:
          new_status: delivery_in_progress
    action:
      - service: tts.speak
        data:
          message: "Кур'єр Сільпо виїхав до вас"
        target: { entity_id: media_player.kitchen }

  - alias: "Silpo: кур'єр близько (500 м)"
    trigger:
      - platform: event
        event_type: silpo_courier_proximity
        event_data:
          threshold_m: 500
    action:
      - service: tts.speak
        data: { message: "Кур'єр Сільпо за 500 метрів" }
        target: { entity_id: media_player.kitchen }

  - alias: "Silpo: доставлено"
    trigger:
      - platform: event
        event_type: silpo_order_status_changed
        event_data:
          new_status: received
    action:
      - service: tts.speak
        data: { message: "Замовлення Сільпо доставлено" }
        target: { entity_id: media_player.kitchen }
```

## Встановлення
1. Скопіювати `custom_components/silpo/` у `config/custom_components/` вашого HA.
2. Налаштування → Пристрої та служби → Додати інтеграцію → **Silpo**.
3. Ввести номер телефону (+380XXXXXXXXX) → код з SMS.

## Розробка й тести
```bash
python3 -m venv .venv-ha
.venv-ha/bin/pip install -r requirements-test.txt
scripts/run_tests.sh      # unit + E2E
scripts/run_e2e.sh        # лише E2E (справжнє HA-ядро + mock Silpo)
scripts/develop           # запустити справжній HA UI з інтеграцією (порт 8123)

# Автоматичний UI-харнес: піднімає СПРАВЖНІЙ HA (без Docker) + mock Сільпо,
# сам проходить onboarding і встановлює інтеграцію. Демонстрація переходів:
scripts/dev_ha_ui.sh up                          # підняти HA на :8123 (admin/silpo1234)
scripts/dev_ha_ui.sh status delivery_in_progress # 'кур'\''єр виїхав' — сенсори+трекер оновляться
scripts/dev_ha_ui.sh status received             # 'доставлено'
scripts/dev_ha_ui.sh down                        # зупинити
```

Технічні деталі API — `docs/API_FINDINGS.md`. Дизайн — `docs/superpowers/specs/`.

## Статус
Черга «скільки замовлень попереду кур'єра» — **майбутня фіча** (доступна лише в
мобільному API Сільпо; підхід зафіксовано в `docs/API_FINDINGS.md`).
