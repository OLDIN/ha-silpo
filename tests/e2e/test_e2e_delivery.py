"""E2E: справжнє HA-ядро + реальний HTTP до mock — повний цикл доставки."""
from __future__ import annotations

import aiohttp
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)

from custom_components.silpo.const import DOMAIN, EVENT_STATUS_CHANGED

ENTRY = {
    "phone": "+380500000000",
    "access_token": "e2e-token",
    "refresh_token": "e2e-refresh",
    "expires_in": 10800,
}


import os


async def _advance(app, status: str) -> None:
    base = f"http://127.0.0.1:{os.environ.get('SILPO_E2E_PORT', '8799')}"
    url = f"{base}/_test/set_status"
    async with aiohttp.ClientSession() as sess:
        await sess.post(url, json={"status": status})


async def test_full_delivery_flow_fires_event_and_updates_sensor(hass, mock_silpo):
    """Реальний HA опитує mock; перехід на доставку кидає подію + оновлює сенсор."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY, title="Silpo E2E")
    entry.add_to_hass(hass)

    # старт: замовлення 'collected'
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.silpo_order_status").state == "collected"

    events = async_capture_events(hass, EVENT_STATUS_CHANGED)

    # кур'єр виїхав: mock перемикає статус, координатор оновлюється
    await _advance(mock_silpo, "delivery_in_progress")
    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # перевірка: подія на шині + сенсор оновився
    assert len(events) == 1, "очікувалась подія silpo_order_status_changed"
    assert events[0].data["new_status"] == "delivery_in_progress"
    assert events[0].data["old_status"] == "collected"
    assert hass.states.get("sensor.silpo_order_status").state == "delivery_in_progress"


async def test_delivered_transition(hass, mock_silpo):
    """Доставлено: delivery_in_progress -> received теж кидає подію."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY, title="Silpo E2E")
    entry.add_to_hass(hass)
    await _advance(mock_silpo, "delivery_in_progress")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    events = async_capture_events(hass, EVENT_STATUS_CHANGED)
    await _advance(mock_silpo, "received")
    await hass.data[DOMAIN][entry.entry_id].async_refresh()
    await hass.async_block_till_done()

    assert any(e.data["new_status"] == "received" for e in events)
