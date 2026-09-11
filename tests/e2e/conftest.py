"""Фікстури E2E: mock-HTTP-сервер Silpo на фіксованому порту.

Env SILPO_*_BASE виставляються на рівні модуля — ДО того як тестові модулі
імпортують const інтеграції. Тому E2E запускається окремою pytest-сесією
(scripts/run_e2e.sh), де const ще не імпортований.
"""
from __future__ import annotations

import os

import pytest
import pytest_asyncio
from aiohttp import web

from .mock_silpo import build_app

# фіксований порт — виставляємо env НЕГАЙНО, до імпорту const у тестах
_PORT = int(os.environ.setdefault("SILPO_E2E_PORT", "8799"))
_BASE = f"http://127.0.0.1:{_PORT}"
os.environ["SILPO_ECOM_BASE"] = _BASE
os.environ["SILPO_CITYRYDER_BASE"] = _BASE
os.environ["SILPO_AUTH_BASE"] = _BASE


@pytest_asyncio.fixture
async def mock_silpo():
    """Підняти mock Silpo на фіксованому порту."""
    app = build_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", _PORT)
    await site.start()
    try:
        yield app
    finally:
        await runner.cleanup()


@pytest.fixture(autouse=True)
def auto_enable(enable_custom_integrations, socket_enabled):
    yield
