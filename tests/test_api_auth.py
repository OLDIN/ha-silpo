"""Тести авторизації Silpo (OTP-флоу + refresh)."""
from __future__ import annotations

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.silpo.api import SilpoAuth, SilpoAuthError


@pytest.mark.asyncio
async def test_request_otp_sends_sms():
    """request_otp б'є ByPhone і повертає nextStep."""
    async with aiohttp.ClientSession() as session:
        auth = SilpoAuth(session)
        with aioresponses() as m:
            m.post(
                "https://auth.silpo.ua/api/v2/Login/ByPhone",
                payload={"nextStep": "LoginWithOTP", "error": None},
            )
            result = await auth.async_request_otp("+380500000000")

    assert result["nextStep"] == "LoginWithOTP"


@pytest.mark.asyncio
async def test_request_otp_rejects_bad_phone():
    """Невірний формат телефону -> ValueError, без мережі."""
    async with aiohttp.ClientSession() as session:
        auth = SilpoAuth(session)
        with pytest.raises(ValueError):
            await auth.async_request_otp("12345")


@pytest.mark.asyncio
async def test_refresh_returns_new_tokens():
    """refresh обмінює refresh_token на новий access_token."""
    async with aiohttp.ClientSession() as session:
        auth = SilpoAuth(session)
        with aioresponses() as m:
            m.post(
                "https://auth.silpo.ua/connect/token",
                payload={
                    "access_token": "new-access",
                    "refresh_token": "new-refresh",
                    "expires_in": 10800,
                },
            )
            tokens = await auth.async_refresh("old-refresh")

    assert tokens["access_token"] == "new-access"
    assert tokens["refresh_token"] == "new-refresh"
    assert tokens["expires_in"] == 10800


@pytest.mark.asyncio
async def test_refresh_raises_on_invalid_grant():
    """Протухлий refresh_token -> SilpoAuthError (потрібен новий OTP)."""
    async with aiohttp.ClientSession() as session:
        auth = SilpoAuth(session)
        with aioresponses() as m:
            m.post(
                "https://auth.silpo.ua/connect/token",
                status=400,
                payload={"error": "invalid_grant"},
            )
            with pytest.raises(SilpoAuthError):
                await auth.async_refresh("expired")
