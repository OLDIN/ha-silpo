"""Тести config flow (phone -> OTP -> entry)."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries, data_entry_flow

from custom_components.silpo.const import DOMAIN

TOKENS = {
    "access_token": "acc", "refresh_token": "ref", "expires_in": 10800,
}


async def test_full_otp_flow_creates_entry(hass):
    """Успіх: телефон -> код -> config entry з токенами."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.silpo.config_flow.SilpoAuth.async_request_otp",
        new=AsyncMock(return_value={"nextStep": "LoginWithOTP"}),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"phone": "+380500000000"}
        )
    assert result["step_id"] == "otp"

    with patch(
        "custom_components.silpo.config_flow.SilpoAuth.async_verify_otp",
        new=AsyncMock(return_value=TOKENS),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"code": "123456"}
        )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["access_token"] == "acc"
    assert result["data"]["refresh_token"] == "ref"
    assert result["data"]["phone"] == "+380500000000"


async def test_invalid_phone_shows_error(hass):
    """Невірний телефон -> помилка форми, без переходу на otp."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.silpo.config_flow.SilpoAuth.async_request_otp",
        new=AsyncMock(side_effect=ValueError("bad phone")),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"phone": "123"}
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"]


async def test_wrong_otp_shows_error(hass):
    """Невірний код -> помилка на кроці otp."""
    from custom_components.silpo.api import SilpoAuthError

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.silpo.config_flow.SilpoAuth.async_request_otp",
        new=AsyncMock(return_value={"nextStep": "LoginWithOTP"}),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"phone": "+380500000000"}
        )
    with patch(
        "custom_components.silpo.config_flow.SilpoAuth.async_verify_otp",
        new=AsyncMock(side_effect=SilpoAuthError("bad code")),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"code": "000000"}
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "otp"
    assert result["errors"]


async def test_reauth_flow_updates_tokens(hass):
    """Reauth: при протуханні — повторний OTP оновлює токени без видалення."""
    from unittest.mock import AsyncMock, patch
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"phone": "+380500000000", "access_token": "old",
              "refresh_token": "old", "expires_in": 10800},
        title="Silpo",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.silpo.config_flow.SilpoAuth.async_request_otp",
        new=AsyncMock(return_value={"nextStep": "LoginWithOTP"}),
    ):
        result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "custom_components.silpo.config_flow.SilpoAuth.async_verify_otp",
        new=AsyncMock(return_value={
            "access_token": "fresh", "refresh_token": "freshr", "expires_in": 10800}),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"code": "123456"}
        )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["access_token"] == "fresh"
    assert entry.data["refresh_token"] == "freshr"


async def test_options_flow_toggle_reauth_notify(hass):
    """Опції: можна вимкнути сповіщення про повторний вхід."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"phone": "+380500000000", "access_token": "t", "refresh_token": "r"},
        options={}, title="Silpo",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"reauth_notify": False, "scan_interval": 30}
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.options["reauth_notify"] is False
