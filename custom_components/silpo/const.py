"""Константи інтеграції Silpo."""
from __future__ import annotations

import os

DOMAIN = "silpo"

# API endpoints
AUTH_BASE = os.getenv("SILPO_AUTH_BASE", "https://auth.silpo.ua")
ECOM_BASE = os.getenv("SILPO_ECOM_BASE", "https://ecom-api.silpo.ua")
CITYRYDER_BASE = os.getenv("SILPO_CITYRYDER_BASE", "https://cityryder-public-api.silpo.ua")
ORDERS_PATH = "/v3/store-front/orders"
COURIER_LOCATION_PATH = "/v1/couriers/{courier_id}/location"

# OpenID
CLIENT_ID = "profile--profile--cabinet"
REDIRECT_URI = "https://id.silpo.ua/signin-oidc"
SCOPE = (
    "openid offline_access public-my "
    "profile--security--identity-service:internal-api--call "
    "core--core--media-service:media--upload "
    "payments--payments--wallet-service:cards--read-my"
)

# Статуси замовлення (PublicOrderStatus)
STATUS_NEW = "new"
STATUS_COLLECTING = "collecting"
STATUS_COLLECTED = "collected"
STATUS_DELIVERY_IN_PROGRESS = "delivery_in_progress"
STATUS_RECEIVED = "received"
STATUS_RETURNED = "returned"
STATUS_CANCELED = "canceled"

# Активні статуси (замовлення ще в процесі)
ACTIVE_STATUSES = frozenset(
    {STATUS_NEW, STATUS_COLLECTING, STATUS_COLLECTED, STATUS_DELIVERY_IN_PROGRESS}
)

# Події на шині HA
EVENT_STATUS_CHANGED = "silpo_order_status_changed"
EVENT_COURIER_PROXIMITY = "silpo_courier_proximity"

# Пороги наближення кур'єра (метри, спадання)
PROXIMITY_THRESHOLDS = (1000, 500, 200)

# Опції
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 30

# Іконка кур'єра для маркера на карті (mdi:truck-delivery, self-contained)
COURIER_PICTURE = "data:image/svg+xml;utf8,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%2048%2048%22%3E%3Ccircle%20cx%3D%2224%22%20cy%3D%2224%22%20r%3D%2223%22%20fill%3D%22%23e6007e%22/%3E%3Cg%20transform%3D%22translate%2812%2C12%29%22%3E%3Cpath%20fill%3D%22%23fff%22%20d%3D%22M3%2C4A2%2C2%200%200%2C0%201%2C6V17H3A3%2C3%200%200%2C0%206%2C20A3%2C3%200%200%2C0%209%2C17H15A3%2C3%200%200%2C0%2018%2C20A3%2C3%200%200%2C0%2021%2C17H23V12L20%2C8H17V4M10%2C6L14%2C10L10%2C14V11H4V9H10M17%2C9.5H19.5L21.47%2C12H17M6%2C15.5A1.5%2C1.5%200%200%2C1%207.5%2C17A1.5%2C1.5%200%200%2C1%206%2C18.5A1.5%2C1.5%200%200%2C1%204.5%2C17A1.5%2C1.5%200%200%2C1%206%2C15.5M18%2C15.5A1.5%2C1.5%200%200%2C1%2019.5%2C17A1.5%2C1.5%200%200%2C1%2018%2C18.5A1.5%2C1.5%200%200%2C1%2016.5%2C17A1.5%2C1.5%200%200%2C1%2018%2C15.5Z%22/%3E%3C/g%3E%3C/svg%3E"
