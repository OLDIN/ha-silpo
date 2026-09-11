"""Тести координатора: polling, детекція переходів, події на шині HA."""
from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.silpo.const import (
    EVENT_COURIER_PROXIMITY,
    EVENT_STATUS_CHANGED,
)
from custom_components.silpo.coordinator import SilpoCoordinator


class FakeClient:
    """Підставний клієнт, що віддає задану послідовність замовлень."""

    def __init__(self, order_sequence, location=None):
        self._seq = list(order_sequence)
        self._i = 0
        self._location = location

    async def async_get_orders(self):
        orders = self._seq[min(self._i, len(self._seq) - 1)]
        self._i += 1
        return orders

    async def async_get_courier_location(self, courier_id):
        return self._location


async def test_courier_departed_fires_status_event(
    hass, order_collected, order_delivery
):
    """collected -> delivery_in_progress кидає silpo_order_status_changed."""
    client = FakeClient([[order_collected], [order_delivery]])
    coordinator = SilpoCoordinator(hass, client, options={})
    events = async_capture_events(hass, EVENT_STATUS_CHANGED)

    await coordinator._async_update_data()  # collected — перша поява
    await coordinator._async_update_data()  # delivery — перехід

    assert len(events) == 1
    assert events[0].data["new_status"] == "delivery_in_progress"
    assert events[0].data["old_status"] == "collected"


async def test_no_event_when_status_unchanged(hass, order_delivery):
    """Однаковий статус двічі -> жодної події."""
    client = FakeClient([[order_delivery], [order_delivery]])
    coordinator = SilpoCoordinator(hass, client, options={})
    events = async_capture_events(hass, EVENT_STATUS_CHANGED)

    await coordinator._async_update_data()
    await coordinator._async_update_data()

    assert len(events) == 0


async def test_proximity_event_on_threshold_cross(
    hass, order_delivery, courier_location
):
    """Кур'єр перетинає поріг наближення -> silpo_courier_proximity."""
    # координати кур'єра відносно адреси замовлення (стійко до зміни фікстур):
    # ~0.02° ≈ 2.2 км (далеко), ~0.008° ≈ 900 м (близько)
    addr = order_delivery["address"]
    far = {**courier_location, "latitude": addr["latitude"] + 0.02,
           "longitude": addr["longitude"]}
    near = {**courier_location, "latitude": addr["latitude"] + 0.008,
            "longitude": addr["longitude"]}
    client = FakeClient([[order_delivery], [order_delivery]], location=far)
    coordinator = SilpoCoordinator(hass, client, options={})
    events = async_capture_events(hass, EVENT_COURIER_PROXIMITY)

    await coordinator._async_update_data()          # далеко
    client._location = near
    await coordinator._async_update_data()          # перетнув 1000

    assert any(e.data["threshold_m"] == 1000 for e in events)


from custom_components.silpo.api import SilpoAuthError


class FakeAuth:
    """Підставний auth: рефреш повертає нові токени."""

    def __init__(self):
        self.refresh_calls = 0

    async def async_refresh(self, refresh_token):
        self.refresh_calls += 1
        return {"access_token": "new-acc", "refresh_token": "new-ref", "expires_in": 10800}


class FlakyClient:
    """Перший get_orders кидає 401, після set_token — віддає замовлення."""

    def __init__(self, order):
        self._order = order
        self._token_ok = False
        self.tokens_set = []

    def set_token(self, token):
        self._token_ok = True
        self.tokens_set.append(token)

    async def async_get_orders(self):
        if not self._token_ok:
            raise SilpoAuthError("401")
        return [self._order]

    async def async_get_courier_location(self, courier_id):
        return None


async def test_coordinator_refreshes_token_on_auth_error(hass, order_collected):
    """При 401 координатор рефрешить токен і повторює запит успішно."""
    client = FlakyClient(order_collected)
    auth = FakeAuth()
    coordinator = SilpoCoordinator(
        hass, client, options={}, auth=auth, refresh_token="ref"
    )

    data = await coordinator._async_update_data()

    assert auth.refresh_calls == 1
    assert client.tokens_set == ["new-acc"]
    assert data["active"]["status"] == "collected"
