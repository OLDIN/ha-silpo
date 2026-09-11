"""Локальний mock-сервер API Сільпо для E2E-тестів.

Віддає фікстури замовлень і локацію кур'єра; має тестові ручки, щоб
змінювати поточний статус замовлення та координати кур'єра «наживо».
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from aiohttp import web

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


class MockSilpoState:
    """Змінюваний стан, спільний для хендлерів."""

    def __init__(self) -> None:
        self.order = _load("order_collected")
        self.location = _load("courier_location")

    def set_status(self, status: str) -> None:
        base = {
            "collected": "order_collected",
            "delivery_in_progress": "order_delivery_in_progress",
            "received": "order_received",
        }.get(status)
        if base:
            self.order = _load(base)
        else:
            self.order = {**self.order, "status": status}


def build_app() -> web.Application:
    state = MockSilpoState()
    app = web.Application()
    app["state"] = state

    async def orders(request: web.Request) -> web.Response:
        st = request.app["state"]
        return web.json_response(
            {"limit": 10, "offset": 0, "total": 1, "items": [copy.deepcopy(st.order)]}
        )

    async def courier_location(request: web.Request) -> web.Response:
        st = request.app["state"]
        return web.json_response(copy.deepcopy(st.location))

    async def set_status(request: web.Request) -> web.Response:
        body = await request.json()
        request.app["state"].set_status(body["status"])
        return web.json_response({"ok": True, "status": body["status"]})

    async def set_courier(request: web.Request) -> web.Response:
        body = await request.json()
        request.app["state"].location = {**request.app["state"].location, **body}
        return web.json_response({"ok": True})

    app.router.add_get("/v3/store-front/orders", orders)
    app.router.add_get("/v1/couriers/{cid}/location", courier_location)
    app.router.add_post("/_test/set_status", set_status)
    app.router.add_post("/_test/set_courier", set_courier)
    return app
