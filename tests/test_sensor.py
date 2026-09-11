"""Тести сенсорів через повний setup інтеграції."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.silpo.const import DOMAIN

ENTRY_DATA = {
    "phone": "+380500000000",
    "access_token": "acc",
    "refresh_token": "ref",
    "expires_in": 10800,
}


async def _setup(hass, orders, location=None):
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, title="Silpo")
    entry.add_to_hass(hass)
    with patch(
        "custom_components.silpo.SilpoClient.async_get_orders",
        new=AsyncMock(return_value=orders),
    ), patch(
        "custom_components.silpo.SilpoClient.async_get_courier_location",
        new=AsyncMock(return_value=location),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_status_sensor_reflects_active_order(hass, order_delivery, courier_location):
    """sensor.silpo_order_status = статус активного замовлення."""
    await _setup(hass, [order_delivery], courier_location)

    state = hass.states.get("sensor.silpo_order_status")
    assert state is not None
    assert state.state == "delivery_in_progress"
    assert state.attributes["order_number"] == order_delivery["number"]


async def test_distance_sensor_has_value_during_delivery(
    hass, order_delivery, courier_location
):
    """sensor.silpo_courier_distance має числову відстань під час доставки."""
    await _setup(hass, [order_delivery], courier_location)

    state = hass.states.get("sensor.silpo_courier_distance")
    assert state is not None
    assert float(state.state) > 0
