"""Інжектнути config entry silpo у .storage HA (для UI-демо без OTP)."""
import json, sys, uuid
from pathlib import Path

cfg = Path(sys.argv[1])
p = cfg / ".storage" / "core.config_entries"
d = json.loads(p.read_text())
entries = [e for e in d["data"]["entries"] if e.get("domain") != "silpo"]
tmpl = dict(entries[0])
tmpl.update({
    "entry_id": uuid.uuid4().hex, "domain": "silpo", "title": "Silpo (UI demo)",
    "data": {"phone": "+380500000000", "access_token": "ui-demo-token",
             "refresh_token": "ui-demo-refresh", "expires_in": 10800},
    "options": {"scan_interval": 5}, "source": "user", "unique_id": None, "version": 1,
    "minor_version": 1, "discovery_keys": {}, "subentries": [],
    "disabled_by": None, "pref_disable_new_entities": False,
    "pref_disable_polling": False,
})
entries.append(tmpl)
d["data"]["entries"] = entries
p.write_text(json.dumps(d, indent=2))
print("silpo entry інжектовано")


# --- окремий dashboard "Silpo" у бічному меню ---
storage = cfg / ".storage"
cards = [
    {"type": "custom:silpo-order-card",
     "entity": "sensor.silpo_order_status",
     "eta_entity": "sensor.silpo_courier_eta",
     "distance_entity": "sensor.silpo_courier_distance"},
    {"type": "map", "entities": ["device_tracker.silpo_courier", "zone.home"], "hours_to_show": 0},
    {"type": "entities", "title": "Деталі", "entities": [
        "sensor.silpo_order_status", "sensor.silpo_courier_distance", "sensor.silpo_courier_eta"]},
]
(storage / "lovelace.silpo").write_text(json.dumps(
    {"version": 1, "key": "lovelace.silpo",
     "data": {"config": {"title": "Silpo", "views": [
         {"title": "Silpo", "path": "silpo", "cards": cards}]}}},
    ensure_ascii=False, indent=2))

# зареєструвати dashboard у sidebar (зберегти існуючі, напр. Map)
dpath = storage / "lovelace_dashboards"
dashboards = json.loads(dpath.read_text()) if dpath.exists() else {
    "version": 1, "key": "lovelace_dashboards", "data": {"items": []}}
items = [d for d in dashboards["data"]["items"] if d.get("id") != "silpo"]
items.append({"id": "silpo", "icon": "mdi:cart", "title": "Silpo",
              "url_path": "silpo", "show_in_sidebar": True,
              "mode": "storage", "require_admin": False})
dashboards["data"]["items"] = items
dpath.write_text(json.dumps(dashboards, ensure_ascii=False, indent=2))
print("окремий dashboard Silpo у sidebar записано (ресурс реєструє сама інтеграція)")
