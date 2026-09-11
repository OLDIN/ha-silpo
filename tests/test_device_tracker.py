"""Тест device_tracker — кур'єр на карті HA."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.silpo.const import DOMAIN

ENTRY_DATA = {
    "phone": "+380500000000", "access_token": "acc",
    "refresh_token": "ref", "expires_in": 10800,
}


async def _setup(hass, orders, location):
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


async def test_courier_tracker_shows_coordinates(hass, order_delivery, courier_location):
    """device_tracker.silpo_courier має координати кур'єра (для карти HA)."""
    await _setup(hass, [order_delivery], courier_location)

    state = hass.states.get("device_tracker.silpo_courier")
    assert state is not None
    assert state.attributes["latitude"] == courier_location["latitude"]
    assert state.attributes["longitude"] == courier_location["longitude"]
    assert state.attributes["source_type"] == "gps"


async def test_courier_tracker_no_coords_without_delivery(
    hass, order_collected, courier_location
):
    """До виїзду кур'єра (collected) координат немає."""
    await _setup(hass, [order_collected], None)

    state = hass.states.get("device_tracker.silpo_courier")
    assert state is not None
    assert state.attributes.get("latitude") is None


async def test_courier_tracker_has_truck_picture(hass, order_delivery, courier_location):
    """Маркер кур'єра на карті — картинка вантажівки (entity_picture), не текст."""
    await _setup(hass, [order_delivery], courier_location)

    state = hass.states.get("device_tracker.silpo_courier")
    pic = state.attributes.get("entity_picture", "")
    assert pic.startswith("data:image/svg+xml"), f"очікували SVG-картинку, маємо: {pic[:40]}"
