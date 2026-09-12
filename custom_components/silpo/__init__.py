"""Silpo — інтеграція стеження за замовленнями Сільпо."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SilpoAuth, SilpoClient
from .const import DOMAIN
from .coordinator import SilpoCoordinator

PLATFORMS = [Platform.SENSOR, Platform.DEVICE_TRACKER]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Зареєструвати статику й авто-підключити Lovelace-картку."""
    import os

    from homeassistant.components.frontend import add_extra_js_url
    from homeassistant.components.http import StaticPathConfig

    www = os.path.join(os.path.dirname(__file__), "www")
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig("/silpo_static", www, False)]
        )
        await _async_register_card_resource(hass)
    except Exception:  # noqa: BLE001 — http/frontend недоступні (напр. у тестах)
        pass
    return True


async def _async_register_card_resource(hass: HomeAssistant) -> None:
    """Надійно зареєструвати картку як lovelace-ресурс (storage-режим).

    Один канал завантаження замість add_extra_js_url — уникає race при рендері.
    """
    url = "/silpo_static/silpo-order-card.js"
    lovelace = hass.data.get("lovelace")
    resources = getattr(lovelace, "resources", None) if lovelace else None
    if resources is None:
        return
    if not resources.loaded:
        await resources.async_load()
        resources.loaded = True
    # не дублювати, якщо вже зареєстровано
    if any(r.get("url") == url for r in resources.async_items()):
        return
    await resources.async_create_item({"res_type": "module", "url": url})


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
