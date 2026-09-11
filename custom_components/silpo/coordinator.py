"""Координатор Silpo: опитування API, детекція переходів, події HA."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import SilpoAuthError
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_COURIER_PROXIMITY,
    EVENT_STATUS_CHANGED,
    PROXIMITY_THRESHOLDS,
    STATUS_DELIVERY_IN_PROGRESS,
)
from .orders import (
    crossed_thresholds,
    detect_status_change,
    haversine_m,
    select_tracked,
)

_LOGGER = logging.getLogger(__name__)


class SilpoCoordinator(DataUpdateCoordinator):
    """Опитує замовлення Сільпо і кидає події на зміну статусу/наближення."""

    def __init__(
        self, hass: HomeAssistant, client, options: dict,
        auth=None, refresh_token: str | None = None, entry=None,
    ) -> None:
        interval = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self._client = client
        self._auth = auth
        self._refresh_token = refresh_token
        self._entry = entry
        self._prev_active: dict | None = None
        self._prev_distance: float | None = None

    async def _fetch_orders_with_refresh(self) -> list[dict]:
        """Отримати замовлення; при протуханні токена — рефреш і повтор."""
        try:
            return await self._client.async_get_orders()
        except SilpoAuthError:
            if not self._auth or not self._refresh_token:
                raise
            tokens = await self._auth.async_refresh(self._refresh_token)
            self._client.set_token(tokens["access_token"])
            self._refresh_token = tokens.get("refresh_token", self._refresh_token)
            self._persist_tokens(tokens)
            return await self._client.async_get_orders()

    def _persist_tokens(self, tokens: dict) -> None:
        """Зберегти оновлені токени у config entry (щоб пережити рестарт HA)."""
        if self._entry is None:
            return
        new_data = {
            **self._entry.data,
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token", self._refresh_token),
            "expires_in": tokens.get("expires_in"),
        }
        self.hass.config_entries.async_update_entry(self._entry, data=new_data)

    async def _async_update_data(self) -> dict:
        orders = await self._fetch_orders_with_refresh()
        prev_id = self._prev_active.get("orderId") if self._prev_active else None
        active = select_tracked(orders, prev_id)

        # відстань до кур'єра (лише під час доставки)
        distance = None
        location = None
        if active and active.get("status") == STATUS_DELIVERY_IN_PROGRESS:
            courier_id = (active.get("delivery") or {}).get("courierId")
            address = active.get("address") or {}
            if courier_id and address.get("latitude"):
                location = await self._client.async_get_courier_location(courier_id)
                if location and location.get("latitude"):
                    distance = haversine_m(
                        location["latitude"], location["longitude"],
                        address["latitude"], address["longitude"],
                    )

        # подія зміни статусу
        change = detect_status_change(self._prev_active, active)
        if change:
            self.hass.bus.async_fire(EVENT_STATUS_CHANGED, change)
            _LOGGER.info("Silpo статус: %s -> %s", change["old_status"], change["new_status"])

        # події наближення
        for threshold in crossed_thresholds(
            self._prev_distance, distance, PROXIMITY_THRESHOLDS
        ):
            self.hass.bus.async_fire(
                EVENT_COURIER_PROXIMITY,
                {
                    "order_number": active.get("number") if active else None,
                    "distance_m": round(distance) if distance else None,
                    "threshold_m": threshold,
                },
            )

        self._prev_active = active
        self._prev_distance = distance
        return {"active": active, "distance_m": distance, "location": location}
