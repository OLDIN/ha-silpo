"""Розрахунок відстані й часу до кур'єра по дорогах через Waze."""
from __future__ import annotations

import logging

from pywaze.route_calculator import WazeRouteCalculator

_LOGGER = logging.getLogger(__name__)


async def async_get_route(
    start_lat: float,
    start_lon: float,
    dest_lat: float,
    dest_lon: float,
    region: str = "EU",
) -> dict | None:
    """Повернути маршрут по дорогах від кур'єра до адреси.

    -> {distance_km, distance_m, duration_min} або None, якщо Waze недоступний.
    """
    calc = WazeRouteCalculator(region=region)
    try:
        routes = await calc.calc_routes(
            f"{start_lat},{start_lon}", f"{dest_lat},{dest_lon}", alternatives=1
        )
    except Exception as exc:  # мережа/парсинг Waze — не валимо координатора
        _LOGGER.debug("Waze route failed: %s", exc)
        return None
    finally:
        await calc.close()

    if not routes:
        return None
    r = routes[0]
    return {
        "distance_km": round(r.distance, 2),
        "distance_m": round(r.distance * 1000),
        "duration_min": round(r.duration),
    }
