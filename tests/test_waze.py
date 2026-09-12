"""Тест Waze-маршрутизації (відстань і час по дорогах)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.silpo.waze import async_get_route


@pytest.mark.asyncio
async def test_get_route_returns_road_distance_and_eta():
    """async_get_route повертає distance_km і duration_min по дорогах."""
    fake = [SimpleNamespace(duration=12.6, distance=3.42, name="r", street_names=[])]
    with patch(
        "custom_components.silpo.waze.WazeRouteCalculator.calc_routes",
        new=AsyncMock(return_value=fake),
    ), patch(
        "custom_components.silpo.waze.WazeRouteCalculator.close", new=AsyncMock()
    ):
        route = await async_get_route(49.57, 34.53, 49.5883, 34.5514)

    assert route["distance_km"] == 3.42
    assert route["duration_min"] == 13  # округлено
    assert route["distance_m"] == 3420


@pytest.mark.asyncio
async def test_get_route_none_on_error():
    """Якщо Waze недоступний -> None (спрацює fallback)."""
    with patch(
        "custom_components.silpo.waze.WazeRouteCalculator.calc_routes",
        new=AsyncMock(side_effect=Exception("waze down")),
    ), patch(
        "custom_components.silpo.waze.WazeRouteCalculator.close", new=AsyncMock()
    ):
        route = await async_get_route(49.57, 34.53, 49.5883, 34.5514)

    assert route is None
