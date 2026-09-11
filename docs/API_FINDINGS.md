# Silpo API — знахідки розвідки (2026-09-11)

Зібрано наживо під час активного замовлення №<ORDER_NUMBER> (Полтава),
статус переходив collected → delivery_in_progress саме під час запису.

## Авторизація (auth.silpo.ua, OpenID Connect)
- OTP-флоу працює на чистому httpx, БЕЗ браузера (Cloudflare НЕ блокує API).
- Кроки:
  1. POST /api/v2/Login/ByPhone  {phone, recaptcha:null, delivery_method:"sms", phoneChannelType:0}
     → 200 {nextStep:"LoginWithOTP"}, ставить cookies visitor + __cf_bm
  2. POST /api/v2/Login/LoginWithOTP  {phone, otp, phoneChannelType:0}
     → 200 {nextStep:"Authenticated", profileId}
  3. GET /connect/authorize?client_id=profile--profile--cabinet&redirect_uri=https://id.silpo.ua/signin-oidc
        &response_type=code&scope=...&code_challenge=...&code_challenge_method=S256&response_mode=query
     (з cookies кроку 1-2) → 302 на redirect_uri?code=...
  4. POST /connect/token  grant_type=authorization_code + code + code_verifier (PKCE)
     → {access_token, id_token, expires_in:10800, token_type:Bearer}  (3 години)
- client_id: profile--profile--cabinet ; redirect_uri: https://id.silpo.ua/signin-oidc
- Токен: 3 год. У нашому флоу refresh_token НЕ повертається.
- АЛЕ auth підтримує: offline_access scope + grant_types [refresh_token, otp, device_code, ...]
  → для HA: додати `offline_access` у scope, отримати refresh_token, рефрешити без SMS.
  → grant_type=otp може дозволити прямий токен через /connect/token (перевірити при імплементації).
- Silent refresh через prompt=none + OTP-cookies НЕ працює (login_required).

## Замовлення (ecom-api.silpo.ua) — ГОЛОВНЕ ДЖЕРЕЛО
- GET /v3/store-front/orders?filter[business][]=silpo&limit=10&offset=0
  Headers: Authorization: Bearer <token>, Origin: https://silpo.ua, Referer: https://silpo.ua/
  → {limit, offset, total, items:[ {orderId, number, status, aggregatedShipmentStatus,
      delivery:{type,timeSlot,deliveredAt,courierId}, address:{latitude,longitude,...},
      amount, shipments:[...], createdAt, processingStartedAt, completedAt, updatedAt, ...} ]}
- Деталь одного: GET /v3/store-front/orders/{orderId}  (те саме, без items)
       або /v2/store-front/orders/{orderId} (з items товарів)
- Активні: GET /v1/store-front/guests/{guestId}/orders/in-progress (був 0 — фільтрує інакше)

### СТАТУСИ (з OpenAPI спеки ecom-api, schema PublicOrderStatus):
    new → collecting → collected → delivery_in_progress → received
    + returned, canceled
  ** "КУР'ЄР ВИЇХАВ" = перехід  collected → delivery_in_progress **  (підтверджено наживо)
  На сайті UI: Нове / Збираємо / Замовлення зібрано / "...виїхав" / Замовлення доставлено

### aggregatedShipmentStatus (дублюючий сигнал):
    compiling → delivery → done
### ShipmentStatusReadModel.status (внутрішній):
    draft, new, preparation, ready_for_delivery, delivery_in_progress, returning, delivered, returned, canceled

## GPS кур'єра (cityryder-public-api.silpo.ua) — ПРАЦЮЄ з веб-токеном
- GET /v1/couriers/{courierId}/location
  → {userId, latitude, longitude, updatedAt}   (courierId з order.delivery.courierId)
- Відстань до order.address.{latitude,longitude} = апроксимація наближення.

## ЧЕРГА (скільки замовлень попереду) — ВІДКЛАДЕНО, майбутня фіча
- На веб-сайті ЧЕРГИ НЕМАЄ (лише 5 текстових статусів). Карта+черга — тільки в МОБ. додатку.
- cityryder-public-api /v1/orders/{orderId} існує, але дає 403 "no required scopes"
  (наш веб-scope недостатній; моб. додаток має ширший scope).
- Наш scope: openid, public-my, profile--security..., core--media..., payments--wallet...
- Щоб дістати чергу пізніше: перехопити моб. трафік (mitmproxy) або підібрати mobile client_id/scope.
- Кандидати-хости (з crt.sh): sf-mobile-api, cityryder-public-api, api.signalr.ecom (realtime).

## OpenAPI спека ecom-api (повна, 126 ендпоінтів)
- https://ecom-api.silpo.ua/swagger/index.html  +  /swagger/swagger.json
- Збережена: captures/swagger.json

## Стабільні ID (наш акаунт)
- guestId/sub: <GUEST_ID> (значення лише локально у captures/)
- активне замовлення: <ORDER_ID> / <ORDER_NUMBER>
- courierId: <COURIER_ID>
- companyId: 1ec88c5d-a050-669c-8467-570a157f3e31
