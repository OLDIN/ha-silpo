"""Постійний mock-сервер Silpo для ручного UI-демо (порт із SILPO_E2E_PORT)."""
from __future__ import annotations

import os
import sys

from aiohttp import web

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.e2e.mock_silpo import build_app

port = int(os.environ.get("SILPO_E2E_PORT", "8799"))
web.run_app(build_app(), host="127.0.0.1", port=port)
