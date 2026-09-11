"""Спільні фікстури тестів."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    """Завантажити JSON-фікстуру за іменем (без розширення)."""
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def order_collected() -> dict:
    return load_fixture("order_collected")


@pytest.fixture
def order_delivery() -> dict:
    return load_fixture("order_delivery_in_progress")


@pytest.fixture
def order_received() -> dict:
    return load_fixture("order_received")


@pytest.fixture
def courier_location() -> dict:
    return load_fixture("courier_location")


@pytest.fixture
def orders_delivery_envelope() -> dict:
    return load_fixture("orders_delivery")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Дозволити завантаження custom_components у тестах HA."""
    yield
