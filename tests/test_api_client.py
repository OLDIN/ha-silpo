"""Тести HTTP-клієнта Silpo (get_orders, get_courier_location)."""
from __future__ import annotations

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.silpo.api import SilpoClient


@pytest.mark.asyncio
async def test_get_orders_returns_items(orders_delivery_envelope):
    """get_orders повертає список замовлень із envelope 'items'."""
    async with aiohttp.ClientSession() as session:
        client = SilpoClient(session, token="tok123")
        with aioresponses() as m:
            m.get(
                "https://ecom-api.silpo.ua/v3/store-front/orders"
                "?filter[business][]=silpo&limit=10&offset=0",
                payload=orders_delivery_envelope,
            )
            orders = await client.async_get_orders()

    assert len(orders) == 1
    assert orders[0]["status"] == "delivery_in_progress"


@pytest.mark.asyncio
async def test_get_orders_sends_bearer_token(orders_delivery_envelope):
    """Клієнт додає Authorization: Bearer та Origin silpo.ua."""
    captured = {}
    async with aiohttp.ClientSession() as session:
        client = SilpoClient(session, token="secret-token")
        with aioresponses() as m:
            def cb(url, **kwargs):
                captured.update(kwargs["headers"])
            m.get(
                "https://ecom-api.silpo.ua/v3/store-front/orders"
                "?filter[business][]=silpo&limit=10&offset=0",
                payload=orders_delivery_envelope,
                callback=cb,
            )
            await client.async_get_orders()

    assert captured["Authorization"] == "Bearer secret-token"
    assert captured["Origin"] == "https://silpo.ua"


@pytest.mark.asyncio
async def test_get_courier_location(courier_location):
    """get_courier_location повертає координати кур'єра."""
    async with aiohttp.ClientSession() as session:
        client = SilpoClient(session, token="tok")
        with aioresponses() as m:
            m.get(
                "https://cityryder-public-api.silpo.ua/v1/couriers/CID/location",
                payload=courier_location,
            )
            loc = await client.async_get_courier_location("CID")

    assert loc["latitude"] == courier_location["latitude"]
    assert loc["longitude"] == courier_location["longitude"]


@pytest.mark.asyncio
async def test_get_courier_location_404_returns_none():
    """Якщо локації немає (404) -> None, без винятку."""
    async with aiohttp.ClientSession() as session:
        client = SilpoClient(session, token="tok")
        with aioresponses() as m:
            m.get(
                "https://cityryder-public-api.silpo.ua/v1/couriers/CID/location",
                status=404,
            )
            loc = await client.async_get_courier_location("CID")

    assert loc is None
