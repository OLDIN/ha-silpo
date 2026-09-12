# Silpo — інтеграція для Home Assistant

Неофіційна інтеграція, що стежить за вашим активним онлайн-замовленням у
[Сільпо](https://silpo.ua) і генерує події та сутності в Home Assistant:
статус доставки, відстань кур'єра, його позиція на карті. Головна мета —
озвучувати на колонці ключові моменти: **«кур'єр виїхав»**, **«кур'єр близько»**,
**«замовлення доставлено»**.

> ⚠️ Неофіційна інтеграція. Не пов'язана з ТОВ «Сільпо» / Fozzy Group. Використовує
> ті самі публічні API, що й сайт silpo.ua. Працездатність залежить від змін на боці Сільпо.

---

## Можливості

- 🚚 **Статус замовлення** — сенсор із поточним станом доставки.
- 📍 **Відстань кур'єра по дорогах** — реальна відстань маршрутом (через Waze), не по прямій.
- ⏱️ **Час прибуття (ETA)** — скільки хвилин їхати кур'єру (через Waze, безкоштовно, без ключа).
- 🗺️ **Кур'єр на карті** — рухома позначка-вантажівка на стандартній карті HA.
- 🔔 **Події** для автоматизацій: зміна статусу та перетин порогів наближення.
- 🔐 **Авторизація OTP** (через SMS), автоматичне оновлення токена без повторного входу.

---

## Вимоги

- Home Assistant **2024.1** або новіший.
- Акаунт Сільпо з номером телефону, на який приходить SMS з кодом.
- Активне онлайн-замовлення — сутності наповнюються даними, поки замовлення в процесі.

---

## Встановлення

### Варіант A — HACS (рекомендовано)

1. HACS → Integrations → ⋮ → **Custom repositories**.
2. Додайте URL цього репозиторію, категорія **Integration**.
3. Знайдіть **Silpo** у списку → **Download**.
4. Перезапустіть Home Assistant.

### Варіант B — вручну

1. Скопіюйте теку `custom_components/silpo/` у `‹config›/custom_components/silpo/`.
2. Перезапустіть Home Assistant.

---

## Налаштування

Після встановлення інтеграція налаштовується повністю через UI (config flow) —
редагувати `configuration.yaml` не потрібно.

1. **Налаштування → Пристрої та служби → Додати інтеграцію**.
2. Знайдіть **Silpo**.
3. **Екран 1 — Телефон:** введіть номер у форматі `+380XXXXXXXXX`. Натисніть **Далі** —
   на номер прийде SMS з кодом.
4. **Екран 2 — OTP-код:** введіть 6-значний код із SMS.
5. Готово — інтеграцію додано, з'являться сутності.

Токен доступу оновлюється автоматично у фоні. Якщо колись знадобиться повторний вхід,
HA покаже сповіщення «Потрібна повторна авторизація» — пройдете ті самі два кроки.

---

## Сутності

Інтеграція створює такі сутності (`silpo` у прикладах — типова частина `entity_id`):

| Сутність | Тип | Опис |
|---|---|---|
| `sensor.silpo_order_status` | sensor | Поточний статус активного замовлення |
| `sensor.silpo_courier_distance` | sensor (distance, м) | Відстань по дорогах до адреси (Waze; fallback — по прямій) |
| `sensor.silpo_courier_eta` | sensor (min) | Орієнтовний час прибуття кур'єра по дорогах (Waze) |
| `device_tracker.silpo_courier` | device_tracker | Позиція кур'єра на карті (лише під час доставки) |

> **Відстань і час — по дорогах.** `sensor.silpo_courier_distance` і `sensor.silpo_courier_eta`
> рахуються через **Waze** (реальний маршрут вулицями, безкоштовно, без API-ключа) — не по
> прямій. Якщо Waze тимчасово недоступний, відстань падає на розрахунок по прямій (гаверсинус),
> а ETA стає порожнім.

### `sensor.silpo_order_status`

Стан = код статусу (див. таблицю нижче). Атрибути:

| Атрибут | Опис |
|---|---|
| `order_number` | Номер замовлення (напр. `36999352`) |
| `order_id` | Внутрішній UUID замовлення |
| `aggregated_status` | Дубль-статус відвантаження (`compiling`/`delivery`/`done`) |
| `amount` | Сума замовлення, грн |
| `time_slot_from`, `time_slot_to` | Вікно доставки (ISO-час) |
| `courier_id` | UUID кур'єра (коли призначений) |

### `sensor.silpo_courier_distance`

Стан = відстань у метрах **по дорогах** (Waze; device_class `distance`). Поза доставкою — `unknown`.
Атрибути: `distance_km` (км по дорогах), `courier_updated_at`.

### `sensor.silpo_courier_eta`

Стан = **хвилини до прибуття** кур'єра по дорогах (Waze). Поза доставкою або коли Waze
недоступний — `unknown`. Атрибут `distance_km`.

### `device_tracker.silpo_courier`

`source_type: gps`, координати кур'єра, іконка-вантажівка на карті. Поза доставкою
координат немає — позначка з карти зникає. Атрибут `courier_updated_at`.

---

## Статуси замовлення

| Код (`sensor.silpo_order_status`) | Значення |
|---|---|
| `new` | Нове замовлення |
| `collecting` | Збирається на складі |
| `collected` | Зібрано, очікує кур'єра |
| `delivery_in_progress` | **Кур'єр виїхав, у дорозі** |
| `received` | **Доставлено / отримано** |
| `returned` | Повернено |
| `canceled` | Скасовано |

---

## Події

Інтеграція публікує події на шину HA — використовуйте їх як тригер `platform: event`.

### `silpo_order_status_changed`

Спрацьовує при будь-якій зміні статусу. Дані:

```yaml
order_id: "1f1a…"
order_number: "36999352"
old_status: "collected"
new_status: "delivery_in_progress"
aggregated_old: "compiling"
aggregated_new: "delivery"
```

- «Кур'єр виїхав» → `new_status: delivery_in_progress`
- «Доставлено» → `new_status: received`

### `silpo_courier_proximity`

Спрацьовує, коли кур'єр перетинає поріг наближення (спадання). Пороги: **1000 / 500 / 200 м**.

```yaml
order_number: "36999352"
distance_m: 480
threshold_m: 500
```

---

## Приклади автоматизацій

```yaml
automation:
  # Кур'єр виїхав
  - alias: "Silpo: кур'єр виїхав"
    trigger:
      - platform: event
        event_type: silpo_order_status_changed
        event_data:
          new_status: delivery_in_progress
    action:
      - service: tts.speak
        target: { entity_id: media_player.kitchen }
        data:
          cache: false
          media_player_entity_id: media_player.kitchen
          message: "Кур'єр Сільпо виїхав до вас"

  # Кур'єр близько (500 м)
  - alias: "Silpo: кур'єр близько"
    trigger:
      - platform: event
        event_type: silpo_courier_proximity
        event_data:
          threshold_m: 500
    action:
      - service: tts.speak
        target: { entity_id: media_player.kitchen }
        data:
          media_player_entity_id: media_player.kitchen
          message: "Кур'єр Сільпо за 500 метрів"

  # Замовлення доставлено
  - alias: "Silpo: доставлено"
    trigger:
      - platform: event
        event_type: silpo_order_status_changed
        event_data:
          new_status: received
    action:
      - service: tts.speak
        target: { entity_id: media_player.kitchen }
        data:
          media_player_entity_id: media_player.kitchen
          message: "Замовлення Сільпо доставлено"
```

---

## Картки Lovelace

**Кур'єр на карті** (стандартна картка Map):

```yaml
type: map
entities:
  - device_tracker.silpo_courier
  - zone.home
hours_to_show: 0
```

**Статус доставки** (Entities):

```yaml
type: entities
title: Замовлення Сільпо
entities:
  - entity: sensor.silpo_order_status
    name: Статус
  - entity: sensor.silpo_courier_distance
    name: Відстань кур'єра (по дорогах)
  - entity: sensor.silpo_courier_eta
    name: Час прибуття
```

**Автоматизація по ETA** (озвучити «кур'єр за 5 хвилин»):

```yaml
automation:
  - alias: "Silpo: кур'єр за 5 хвилин"
    trigger:
      - platform: numeric_state
        entity_id: sensor.silpo_courier_eta
        below: 6
    action:
      - service: tts.speak
        target: { entity_id: media_player.kitchen }
        data:
          media_player_entity_id: media_player.kitchen
          message: "Кур'єр Сільпо прибуде приблизно за 5 хвилин"
```

**Умовна картка** (показувати лише під час доставки):

```yaml
type: conditional
conditions:
  - entity: sensor.silpo_order_status
    state: delivery_in_progress
card:
  type: map
  entities:
    - device_tracker.silpo_courier
    - zone.home
```

---

## Вирішення проблем

**На карті напис «API KEY REQUIRED».** Це не проблема інтеграції — постачальник фонових
мап (CARTO) почав вимагати ключ, що зачепило всіх користувачів HA. Виправлено в свіжих
релізах Home Assistant — **оновіть HA**. Обхід до оновлення: картка `custom:map-card`
(HACS) з тайлами OpenStreetMap.

**Кур'єр зник з карти після доставки.** Це навмисно: після статусу `received` координати
більше не оновлюються, позначку прибрано.

**Потрібна повторна авторизація.** Токен не вдалося оновити автоматично — пройдіть
config flow (телефон → OTP) ще раз через сповіщення HA.

---

## Розробка та тести

```bash
python3 -m venv .venv-ha
.venv-ha/bin/pip install -r requirements-test.txt

scripts/run_tests.sh      # unit + E2E
scripts/run_e2e.sh        # лише E2E (справжнє HA-ядро + mock Сільпо)

# Локальний UI-стенд: справжній HA (без Docker) + mock Сільпо, з UI на :8123.
# Сам проходить onboarding і встановлює інтеграцію.
scripts/dev_ha_ui.sh up                            # http://localhost:8123 (admin/silpo1234)
scripts/dev_ha_ui.sh status delivery_in_progress   # емулювати «кур'єр виїхав»
scripts/dev_ha_ui.sh status received               # емулювати «доставлено»
scripts/dev_ha_ui.sh down                          # зупинити
```

Технічні деталі API Сільпо — `docs/API_FINDINGS.md`. Дизайн — `docs/superpowers/specs/`.

---

## Плани

- 📦 **Черга** — скільки замовлень попереду вашого. Наразі доступна лише в мобільному
  API Сільпо (потрібен ширший scope); підхід зафіксовано в `docs/API_FINDINGS.md`.

---

## Ліцензія

MIT.
