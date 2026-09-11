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
