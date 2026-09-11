# Silpo — Home Assistant інтеграція: дизайн

**Дата:** 2026-09-11
**Статус:** узгоджено, готово до плану реалізації

## Мета

Custom-компонент Home Assistant `silpo`, який стежить за активним онлайн-замовленням
у Сільпо і **генерує події HA при зміні статусу доставки** — насамперед при переході
«зібрано → кур'єр виїхав». Користувач прив'язує до цих подій свої автоматизації
(TTS на колонку тощо). Бонусом — сенсор GPS-відстані кур'єра до адреси доставки.

**Поза обсягом (майбутні фічі):** «черга» (скільки замовлень попереду кур'єра) — доступна
лише в мобільному API з ширшим scope; підхід зафіксовано в `captures/API_FINDINGS.md`.

## Ключові факти API (перевірено наживо 2026-09-11)

Повна довідка — `captures/API_FINDINGS.md`. Стисло:

- **Авторизація:** OTP через `auth.silpo.ua`, чистий HTTP (без браузера, Cloudflare не блокує API).
  - `POST /api/v2/Login/ByPhone` → SMS; `POST /api/v2/Login/LoginWithOTP` → авторизовані cookies.
  - OpenID PKCE: `GET /connect/authorize` (з cookies) → `code`; `POST /connect/token` → `access_token`.
  - `client_id=profile--profile--cabinet`, `redirect_uri=https://id.silpo.ua/signin-oidc`.
  - Токен живе **3 год**. Сервер оголошує `offline_access` scope і `refresh_token` grant →
    додаємо `offline_access`, отримуємо `refresh_token`, рефрешимо без SMS.
- **Замовлення:** `GET ecom-api.silpo.ua/v3/store-front/orders?filter[business][]=silpo&limit=10&offset=0`
  з `Authorization: Bearer`, `Origin/Referer: https://silpo.ua`.
- **Статуси** (`PublicOrderStatus`): `new → collecting → collected → delivery_in_progress → received`
  (+ `returned`, `canceled`). Дубль-сигнал `aggregatedShipmentStatus`: `compiling → delivery → done`.
  **«Кур'єр виїхав» = `collected → delivery_in_progress`** (підтверджено наживо).
- **GPS кур'єра:** `GET cityryder-public-api.silpo.ua/v1/couriers/{courierId}/location`
  → `{latitude, longitude, updatedAt}`. `courierId` з `order.delivery.courierId`.
  Відстань до `order.address.{latitude,longitude}` рахуємо гаверсинусом.

## Архітектура

Стандартна HA-інтеграція на `DataUpdateCoordinator`, config entry, config flow.

```
custom_components/silpo/
  __init__.py         # async_setup_entry: створити coordinator, forward платформи
  const.py            # DOMAIN, endpoints, EVENT_*, статуси, пороги GPS
  api.py              # SilpoAuth (OTP+refresh), SilpoClient (get_orders, get_courier_location)
  coordinator.py      # SilpoCoordinator: polling, детект переходів, fire events
  sensor.py           # OrderStatusSensor, CourierDistanceSensor
  config_flow.py      # user(phone) → otp(code) → entry; OptionsFlow (інтервал); reauth
  manifest.json, strings.json, translations/{uk,en}.json
```

### api.py
- `SilpoAuth`:
  - `async_request_otp(phone)` → крок ByPhone, тримає PKCE verifier + cookies у пам'яті сесії.
  - `async_verify_otp(code)` → LoginWithOTP + authorize + token; scope включає `offline_access`.
    Повертає `{access_token, refresh_token, expires_at, guest_id}`.
  - `async_refresh(refresh_token)` → `grant_type=refresh_token`. Якщо сервер не віддав
    `refresh_token` — кидає `SilpoReauthRequired`, що ініціює HA reauth flow.
  - `access_token_valid()` — перевірка `exp` з JWT, рефреш за <10 хв до закінчення.
- `SilpoClient(auth)`:
  - `async_get_orders()` → список замовлень (сирий payload зберігаємо для атрибутів).
  - `async_get_courier_location(courier_id)` → `{lat, lon, updated_at}` або `None`.
- Уся мережа — `aiohttp` через `async_get_clientsession(hass)`.

### coordinator.py
- `SilpoCoordinator(DataUpdateCoordinator)`, `update_interval` з опцій (деф. 30 с).
- `_async_update_data()`:
  1. Рефреш токена за потреби.
  2. `get_orders()`; вибрати «активне» = перший зі статусом у
     `{new, collecting, collected, delivery_in_progress}`.
  3. Якщо активне в `delivery_in_progress` і є `courierId` → `get_courier_location`,
     порахувати `distance_m` до адреси.
  4. Порівняти з попереднім знімком (зберігається в координаторі):
     - зміна `status` → `hass.bus.async_fire(EVENT_STATUS_CHANGED, {...})`.
     - перетин порогу відстані (1000/500/200 м, спадання) → `EVENT_COURIER_PROXIMITY`.
  5. Повернути нормалізований `SilpoData` (активне замовлення + локація + distance).
- Дедуплікація: подія лише коли значення реально змінилось відносно збереженого.

### Події (публічний контракт для автоматизацій)
- `silpo_order_status_changed`:
  `{order_id, order_number, old_status, new_status, aggregated_old, aggregated_new, time_slot}`.
  Приклад автоматизації: trigger `event_type: silpo_order_status_changed`,
  `event_data: {new_status: delivery_in_progress}` → TTS «кур'єр виїхав».
- `silpo_courier_proximity`:
  `{order_number, distance_m, threshold_m}` — при перетині порогу вниз.

### sensor.py
- `sensor.silpo_order_status` — стан = статус; атрибути: `number, aggregated_status,
  time_slot_from, time_slot_to, amount, courier_id, updated_at`. Іконка/`translation_key`.
- `sensor.silpo_courier_distance` — стан = метри (device_class distance), лише під час
  доставки; інакше `unknown`. Атрибути: `latitude, longitude, courier_updated_at`.

### config_flow.py
- Крок `user`: поле `phone` (валідація `+380XXXXXXXXX`) → `async_request_otp`.
- Крок `otp`: поле `code` (6 цифр) → `async_verify_otp` → `async_create_entry`
  з `{phone, access_token, refresh_token, expires_at, guest_id}`, `unique_id=guest_id`.
- `OptionsFlow`: `scan_interval`, пороги GPS, увімк/вимк proximity-подій.
- `async_step_reauth` / `reauth_confirm`: повторний OTP, якщо refresh протух.

## Тестування (два рівні)

### Рівень 1 — pytest (in-memory HA)
`pytest-homeassistant-custom-component` (дає `hass` fixture, мокає HA-ядро).
- `tests/fixtures/` — **реальні знімки** з `captures/`:
  `orders_collected.json`, `orders_delivery_in_progress.json`, `orders_received.json`,
  `courier_location.json`.
- `test_api.py` — OTP-флоу і refresh на замоканому `aiohttp` (`aioresponses`).
- `test_config_flow.py` — happy path (phone→otp→entry), помилки (невірний код, дубль).
- `test_coordinator.py` — подача послідовності фікстур; перевірка вибору активного
  замовлення, розрахунку distance, детекту переходів.
- `test_events.py` — при переході `collected→delivery_in_progress` на шину лягає
  рівно одна подія `silpo_order_status_changed` з правильним payload; при перетині
  порогу — `silpo_courier_proximity`; без зміни — жодної події.
- `test_sensor.py` — стани й атрибути сенсорів після оновлення координатора.

### Рівень 2 — E2E з реальним HA (самодебаг, як просив користувач)
- `scripts/develop` — запуск HA з `config/` (як у ha-poltava-poweroff).
- `tests/e2e/mock_silpo.py` — локальний `aiohttp` сервер, що імітує `auth`, `ecom-api`,
  `cityryder`: віддає фікстури і **дозволяє перемикати статус** через тестову ручку
  (`POST /_test/advance` → наступний статус у ланцюжку).
- `scripts/e2e_test.py` — оркестратор:
  1. Підняти `mock_silpo` на localhost; вказати інтеграції базові URL через env/const override.
  2. Запустити HA (підпроцес) з підготованим `config/` + встановленою інтеграцією
     (config entry через `.storage` або сервіс).
  3. Дочекатися готовності (`GET /api/` з long-lived token у тестовому config).
  4. Підписатися на event bus HA (WebSocket API) на `silpo_order_status_changed`.
  5. Смикнути `mock` → `collected` → `delivery_in_progress`; переконатися, що подія
     прийшла і `sensor.silpo_order_status` став `delivery_in_progress`.
  6. Вивести PASS/FAIL з деталями; коди виходу для CI.
- `scripts/run_e2e.sh` — обгортка: venv, залежності, запуск, тайм-аути, тірдаун.

## Автономність токена
Основний шлях — `offline_access` + `refresh_token` (перевірити наживо першим OTP при
реалізації config flow). Fallback — HA reauth flow з нотифікацією, якщо refresh не
підтримується для цього client_id.

## Ризики
- `offline_access` може не віддати `refresh_token` саме для web-client_id → fallback reauth.
- Черга недоступна web-scope (відкладено).
- E2E-запуск HA крихкіший за unit-тести → рівень 1 лишається основним гейтом якості.
