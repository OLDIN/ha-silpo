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
