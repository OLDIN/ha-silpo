"""Device tracker Silpo — кур'єр на карті Home Assistant."""
from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Створити трекер кур'єра."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SilpoCourierTracker(coordinator, entry)])


class SilpoCourierTracker(CoordinatorEntity, TrackerEntity):
    """Позиція кур'єра на карті (з GPS Сільпо)."""

    _attr_has_entity_name = True
    _attr_translation_key = "courier"
    _attr_icon = "mdi:truck-delivery"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_courier_tracker"
        self._attr_name = "Silpo courier"

    def _loc(self) -> dict:
        return (self.coordinator.data or {}).get("location") or {}

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        return self._loc().get("latitude")

    @property
    def longitude(self) -> float | None:
        return self._loc().get("longitude")

    @property
    def extra_state_attributes(self) -> dict:
        loc = self._loc()
        return {"courier_updated_at": loc.get("updatedAt")}
