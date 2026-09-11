"""HTTP-клієнт і авторизація Silpo."""
from __future__ import annotations

import logging

import aiohttp

from .const import (
    CITYRYDER_BASE,
    COURIER_LOCATION_PATH,
    ECOM_BASE,
    ORDERS_PATH,
)

_LOGGER = logging.getLogger(__name__)

_BROWSER_HEADERS = {
    "Origin": "https://silpo.ua",
    "Referer": "https://silpo.ua/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
}


class SilpoError(Exception):
    """Загальна помилка Silpo API."""


class SilpoAuthError(SilpoError):
    """Помилка авторизації (протух токен тощо)."""


class SilpoClient:
    """Клієнт до публічних API Сільпо (замовлення, локація кур'єра)."""

    def __init__(self, session: aiohttp.ClientSession, token: str) -> None:
        self._session = session
        self._token = token

    def set_token(self, token: str) -> None:
        """Оновити access-токен (після рефрешу)."""
        self._token = token

    def _headers(self) -> dict[str, str]:
        return {**_BROWSER_HEADERS, "Authorization": f"Bearer {self._token}"}

    async def async_get_orders(self) -> list[dict]:
        """Отримати список замовлень користувача."""
        url = f"{ECOM_BASE}{ORDERS_PATH}"
        params = {"filter[business][]": "silpo", "limit": 10, "offset": 0}
        async with self._session.get(
            url, params=params, headers=self._headers()
        ) as resp:
            if resp.status == 401:
                raise SilpoAuthError("Токен недійсний (401)")
            resp.raise_for_status()
            data = await resp.json()
        return data.get("items", [])

    async def async_get_courier_location(self, courier_id: str) -> dict | None:
        """Отримати поточну локацію кур'єра або None, якщо недоступна."""
        url = f"{CITYRYDER_BASE}{COURIER_LOCATION_PATH.format(courier_id=courier_id)}"
        async with self._session.get(url, headers=self._headers()) as resp:
            if resp.status != 200:
                return None
            return await resp.json()


import base64
import hashlib
import re
import secrets
from urllib.parse import parse_qs, urlparse

from .const import AUTH_BASE, CLIENT_ID, REDIRECT_URI, SCOPE

_PHONE_RE = re.compile(r"^\+380\d{9}$")
_OTP_RE = re.compile(r"^\d{6}$")


class SilpoAuth:
    """OpenID Connect авторизація Сільпо через OTP (SMS) + refresh."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._phone: str | None = None
        self._verifier: str | None = None

    async def async_request_otp(self, phone: str) -> dict:
        """Крок 1: надіслати SMS з кодом."""
        if not _PHONE_RE.match(phone):
            raise ValueError("Номер має бути у форматі +380XXXXXXXXX")
        self._phone = phone
        self._verifier = secrets.token_urlsafe(64)
        async with self._session.post(
            f"{AUTH_BASE}/api/v2/Login/ByPhone",
            json={
                "phone": phone,
                "recaptcha": None,
                "delivery_method": "sms",
                "phoneChannelType": 0,
            },
            headers=_BROWSER_HEADERS,
        ) as resp:
            data = await resp.json()
            if not resp.ok:
                raise SilpoError(f"ByPhone failed: {data}")
        return data

    async def async_verify_otp(self, code: str) -> dict:
        """Крок 2: перевірити код і отримати токени (PKCE)."""
        if not _OTP_RE.match(code):
            raise ValueError("OTP код має містити 6 цифр")
        if not self._phone or not self._verifier:
            raise SilpoError("Спочатку викличте async_request_otp")

        async with self._session.post(
            f"{AUTH_BASE}/api/v2/Login/LoginWithOTP",
            json={"phone": self._phone, "otp": code, "phoneChannelType": 0},
            headers=_BROWSER_HEADERS,
        ) as resp:
            data = await resp.json()
            if not resp.ok or data.get("error"):
                raise SilpoAuthError(f"Невірний OTP: {data}")

        challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(self._verifier.encode()).digest()
            )
            .rstrip(b"=")
            .decode("ascii")
        )
        params = {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPE,
            "state": secrets.token_urlsafe(16),
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "response_mode": "query",
        }
        async with self._session.get(
            f"{AUTH_BASE}/connect/authorize",
            params=params,
            headers=_BROWSER_HEADERS,
            allow_redirects=False,
        ) as resp:
            location = resp.headers.get("Location", "")
            code_param = parse_qs(urlparse(location).query).get("code", [None])[0]
        if not code_param:
            raise SilpoAuthError("Не отримано код авторизації")

        return await self._exchange_code(code_param)

    async def _exchange_code(self, auth_code: str) -> dict:
        async with self._session.post(
            f"{AUTH_BASE}/connect/token",
            data={
                "client_id": CLIENT_ID,
                "code": auth_code,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": self._verifier,
                "grant_type": "authorization_code",
            },
            headers=_BROWSER_HEADERS,
        ) as resp:
            data = await resp.json()
            if not resp.ok or "access_token" not in data:
                raise SilpoAuthError(f"Обмін коду не вдався: {data}")
        return data

    async def async_refresh(self, refresh_token: str) -> dict:
        """Оновити токен через refresh_token (без SMS)."""
        async with self._session.post(
            f"{AUTH_BASE}/connect/token",
            data={
                "client_id": CLIENT_ID,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers=_BROWSER_HEADERS,
        ) as resp:
            data = await resp.json()
            if not resp.ok or "access_token" not in data:
                raise SilpoAuthError(f"Refresh не вдався: {data}")
        return data
