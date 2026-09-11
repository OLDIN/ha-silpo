"""Чиста логіка роботи із замовленнями Сільпо (без залежності від HA)."""
from __future__ import annotations

from .const import ACTIVE_STATUSES


def pick_active(orders: list[dict]) -> dict | None:
    """Повернути перше активне замовлення (ще в процесі) або None."""
    for order in orders:
        if order.get("status") in ACTIVE_STATUSES:
            return order
    return None


import math


def detect_status_change(prev: dict | None, curr: dict | None) -> dict | None:
    """Повернути опис зміни статусу або None, якщо зміни немає.

    prev=None (перша поява) не вважається зміною — щоб не спамити подіями
    одразу після старту HA.
    """
    if prev is None or curr is None:
        return None
    old, new = prev.get("status"), curr.get("status")
    if old == new:
        return None
    return {
        "order_id": curr.get("orderId"),
        "order_number": curr.get("number"),
        "old_status": old,
        "new_status": new,
        "aggregated_old": prev.get("aggregatedShipmentStatus"),
        "aggregated_new": curr.get("aggregatedShipmentStatus"),
    }


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Відстань між двома точками (метри) за формулою гаверсинуса."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def crossed_thresholds(
    prev_dist: float | None, curr_dist: float | None, thresholds
) -> list[int]:
    """Пороги (метри), які кур'єр перетнув НАБЛИЖАЮЧИСЬ (prev > поріг >= curr).

    Повертає у порядку спадання порогів. prev=None або curr=None -> [].
    """
    if prev_dist is None or curr_dist is None:
        return []
    return [t for t in sorted(thresholds, reverse=True) if prev_dist > t >= curr_dist]
