"""Рекордер API замовлень + GPS кур'єра Сільпо (для збору фікстур).

Опитує ecom-api (замовлення) і cityryder-public-api (локація кур'єра),
зберігає знімок при кожній зміні + повний GPS-трек. Мета — зафіксувати
переходи статусів (collected -> delivery_in_progress -> received) і рух
кур'єра, щоб будувати й тестувати HA-інтеграцію офлайн на реальних даних.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

OUT = Path(__file__).resolve().parent.parent / "captures"
ORDERS_URL = "https://ecom-api.silpo.ua/v3/store-front/orders"
COURIER_URL = "https://cityryder-public-api.silpo.ua/v1/couriers/{cid}/location"
HEADERS = {
    "Origin": "https://silpo.ua",
    "Referer": "https://silpo.ua/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
}
ACTIVE_STATUSES = {"new", "collecting", "collected", "delivery_in_progress"}


def _now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _haversine(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _active(payload: dict) -> dict | None:
    for o in payload.get("items", []):
        if o.get("status") in ACTIVE_STATUSES:
            return o
    return None


def main() -> None:
    token = json.loads((OUT / ".token.json").read_text())["access_token"]
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 14400

    headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    OUT.mkdir(parents=True, exist_ok=True)
    olog, glog = OUT / "poll_log.jsonl", OUT / "gps_log.jsonl"

    last_hash = None
    deadline = time.time() + duration
    with httpx.Client(timeout=25, headers=headers) as client:
        while time.time() < deadline:
            ts = _now()
            active = None
            # --- замовлення ---
            try:
                r = client.get(ORDERS_URL, params={
                    "filter[business][]": "silpo", "limit": 10, "offset": 0})
                if r.status_code == 200:
                    payload = r.json()
                    digest = hashlib.sha256(r.text.encode()).hexdigest()[:12]
                    active = _active(payload)
                    entry = {"ts": ts, "http": 200, "hash": digest,
                             "changed": digest != last_hash}
                    if active:
                        d = active.get("delivery") or {}
                        entry["active"] = (f"{active.get('number')}:{active.get('status')}"
                                           f"/{active.get('aggregatedShipmentStatus')}")
                    if digest != last_hash:
                        snap = OUT / f"orders_{ts}_{digest}.json"
                        snap.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
                        entry["file"] = snap.name
                        last_hash = digest
                else:
                    entry = {"ts": ts, "http": r.status_code, "body": r.text[:300]}
            except Exception as exc:
                entry = {"ts": ts, "error": f"{type(exc).__name__}: {exc}"}
            with olog.open("a") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            print("ORD ", json.dumps(entry, ensure_ascii=False), flush=True)

            # --- GPS кур'єра (лише поки замовлення в доставці) ---
            if active and active.get("status") == "delivery_in_progress":
                d = active.get("delivery") or {}
                cid = d.get("courierId")
                addr = active.get("address") or {}
                if cid:
                    g = {"ts": ts, "order": active.get("number"), "courierId": cid}
                    try:
                        rc = client.get(COURIER_URL.format(cid=cid))
                        g["http"] = rc.status_code
                        if rc.status_code == 200:
                            loc = rc.json()
                            g.update(lat=loc.get("latitude"), lon=loc.get("longitude"),
                                     updatedAt=loc.get("updatedAt"))
                            if addr.get("latitude") and loc.get("latitude"):
                                g["dist_m"] = round(_haversine(
                                    loc["latitude"], loc["longitude"],
                                    addr["latitude"], addr["longitude"]))
                        else:
                            g["body"] = rc.text[:200]
                    except Exception as exc:
                        g["error"] = f"{type(exc).__name__}: {exc}"
                    with glog.open("a") as fh:
                        fh.write(json.dumps(g, ensure_ascii=False) + "\n")
                    print("GPS ", json.dumps(g, ensure_ascii=False), flush=True)

            time.sleep(interval)


if __name__ == "__main__":
    main()
