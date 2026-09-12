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

    async def auth_byphone(request: web.Request) -> web.Response:
        return web.json_response({"nextStep": "LoginWithOTP", "error": None})

    async def auth_otp(request: web.Request) -> web.Response:
        return web.json_response({"nextStep": "Authenticated", "error": None})

    async def auth_authorize(request: web.Request) -> web.Response:
        # редірект на redirect_uri з фейковим code (як справжній OpenID)
        redirect = request.query.get("redirect_uri", "https://id.silpo.ua/signin-oidc")
        return web.HTTPFound(f"{redirect}?code=MOCKCODE&state={request.query.get('state','')}")

    async def auth_token(request: web.Request) -> web.Response:
        return web.json_response({
            "access_token": "mock-access-token", "refresh_token": "mock-refresh-token",
            "expires_in": 10800, "token_type": "Bearer"})

    app.router.add_post("/api/v2/Login/ByPhone", auth_byphone)
    app.router.add_post("/api/v2/Login/LoginWithOTP", auth_otp)
    app.router.add_get("/connect/authorize", auth_authorize)
    app.router.add_post("/connect/token", auth_token)
    app.router.add_get("/v3/store-front/orders", orders)
    app.router.add_get("/v1/couriers/{cid}/location", courier_location)
    app.router.add_post("/_test/set_status", set_status)
    app.router.add_post("/_test/set_courier", set_courier)
    return app
