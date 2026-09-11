"""Тести чистої логіки роботи із замовленнями."""
from __future__ import annotations

from custom_components.silpo.orders import pick_active


def test_pick_active_returns_order_in_active_status(order_collected):
    """pick_active повертає замовлення, що ще в процесі (collected)."""
    orders = [order_collected]

    active = pick_active(orders)

    assert active is not None
    assert active["status"] == "collected"


def test_pick_active_ignores_received_orders(order_received):
    """Доставлене замовлення (received) не вважається активним."""
    active = pick_active([order_received])

    assert active is None


from custom_components.silpo.orders import detect_status_change, haversine_m


def test_detect_status_change_courier_departed(order_collected, order_delivery):
    """Перехід collected -> delivery_in_progress = 'кур'єр виїхав'."""
    change = detect_status_change(order_collected, order_delivery)

    assert change is not None
    assert change["old_status"] == "collected"
    assert change["new_status"] == "delivery_in_progress"
    assert change["order_number"] == order_delivery["number"]


def test_detect_status_change_none_when_same(order_delivery):
    """Немає зміни -> None (жодної події)."""
    assert detect_status_change(order_delivery, order_delivery) is None


def test_detect_status_change_from_no_previous(order_collected):
    """Перша поява замовлення (prev=None) не рахується зміною статусу."""
    assert detect_status_change(None, order_collected) is None


def test_haversine_known_distance():
    """~900 м між домом (49.5, 34.5) і точкою на північ (49.508092, 34.5)."""
    d = haversine_m(49.508092, 34.5, 49.5, 34.5)

    assert 850 <= d <= 950


from custom_components.silpo.orders import crossed_thresholds


def test_crossed_thresholds_going_closer():
    """Кур'єр перетнув 1000 м (був 1270, став 900) -> поріг 1000 спрацював."""
    crossed = crossed_thresholds(1270, 900, (1000, 500, 200))

    assert crossed == [1000]


def test_crossed_thresholds_multiple_at_once():
    """Різкий стрибок 1270 -> 150 перетинає одразу всі три пороги."""
    crossed = crossed_thresholds(1270, 150, (1000, 500, 200))

    assert crossed == [1000, 500, 200]


def test_crossed_thresholds_moving_away_none():
    """Кур'єр віддаляється (900 -> 1270) -> жодного порогу."""
    assert crossed_thresholds(900, 1270, (1000, 500, 200)) == []


def test_crossed_thresholds_no_previous():
    """Перший замір (prev=None) не тригерить пороги."""
    assert crossed_thresholds(None, 150, (1000, 500, 200)) == []


from custom_components.silpo.orders import select_tracked


def test_select_tracked_prefers_active(order_collected, order_received):
    """Є активне -> відстежуємо його."""
    tracked = select_tracked([order_received, order_collected], prev_id=None)
    assert tracked["status"] == "collected"


def test_select_tracked_keeps_finished_order_by_id(order_received):
    """Активного нема, але відстежуване щойно стало received -> тримаємо його,
    щоб спіймати фінальний перехід (подію 'доставлено')."""
    tracked = select_tracked([order_received], prev_id=order_received["orderId"])
    assert tracked is not None
    assert tracked["status"] == "received"


def test_select_tracked_none_when_no_active_and_unknown_prev(order_received):
    """Активного нема і prev невідомий -> None (нічого не відстежуємо)."""
    assert select_tracked([order_received], prev_id="some-other-id") is None
