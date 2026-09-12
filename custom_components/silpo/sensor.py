"""Сенсори Silpo: статус замовлення і відстань кур'єра."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Створити сенсори для config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SilpoOrderStatusSensor(coordinator, entry),
            SilpoCourierDistanceSensor(coordinator, entry),
        ]
    )


class _Base(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._entry = entry


class SilpoOrderStatusSensor(_Base, SensorEntity):
    """Статус активного замовлення."""

    _attr_translation_key = "order_status"
    _attr_icon = "mdi:truck-delivery"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_order_status"
        self._attr_name = "Silpo order status"

    @property
    def native_value(self) -> str | None:
        active = (self.coordinator.data or {}).get("active")
        return active.get("status") if active else None

    @property
    def extra_state_attributes(self) -> dict:
        active = (self.coordinator.data or {}).get("active") or {}
        delivery = active.get("delivery") or {}
        slot = delivery.get("timeSlot") or {}
        return {
            "order_number": active.get("number"),
            "order_id": active.get("orderId"),
            "aggregated_status": active.get("aggregatedShipmentStatus"),
            "amount": active.get("amount"),
            "time_slot_from": slot.get("from"),
            "time_slot_to": slot.get("to"),
            "courier_id": delivery.get("courierId"),
        }


class SilpoCourierDistanceSensor(_Base, SensorEntity):
    """Відстань кур'єра до адреси доставки (метри)."""

    _attr_translation_key = "courier_distance"
    _attr_icon = "mdi:map-marker-distance"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.METERS

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_courier_distance"
        self._attr_name = "Silpo courier distance"

    @property
    def native_value(self) -> int | None:
        dist = (self.coordinator.data or {}).get("distance_m")
        return round(dist) if dist is not None else None

    @property
    def extra_state_attributes(self) -> dict:
        # без latitude/longitude — інакше HA намалює цей сенсор окремим маркером
        # на карті (координати кур'єра показує device_tracker.silpo_courier).
        loc = (self.coordinator.data or {}).get("location") or {}
        return {"courier_updated_at": loc.get("updatedAt")}
