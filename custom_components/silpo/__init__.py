"""Silpo — інтеграція стеження за замовленнями Сільпо."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SilpoAuth, SilpoClient
from .const import DOMAIN
from .coordinator import SilpoCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Підняти інтеграцію: клієнт, координатор, платформи."""
    session = async_get_clientsession(hass)
    client = SilpoClient(session, token=entry.data["access_token"])
    auth = SilpoAuth(session)
    coordinator = SilpoCoordinator(
        hass, client, options=dict(entry.options),
        auth=auth, refresh_token=entry.data.get("refresh_token"), entry=entry,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Вивантажити інтеграцію."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
