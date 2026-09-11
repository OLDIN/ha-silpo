"""Config flow інтеграції Silpo: телефон -> OTP -> entry."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SilpoAuth, SilpoAuthError, SilpoError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SilpoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Двокроковий OTP-флоу."""

    VERSION = 1

    def __init__(self) -> None:
        self._auth: SilpoAuth | None = None
        self._phone: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Крок 1: ввід телефону, надсилання SMS."""
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            self._auth = SilpoAuth(session)
            self._phone = user_input["phone"]
            try:
                await self._auth.async_request_otp(self._phone)
            except ValueError:
                errors["base"] = "invalid_phone"
            except SilpoError:
                errors["base"] = "cannot_connect"
            else:
                return await self.async_step_otp()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("phone"): str}),
            errors=errors,
        )

    async def async_step_otp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Крок 2: ввід коду з SMS, отримання токенів."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                tokens = await self._auth.async_verify_otp(user_input["code"])
            except ValueError:
                errors["base"] = "invalid_code"
            except SilpoAuthError:
                errors["base"] = "invalid_auth"
            else:
                return self.async_create_entry(
                    title=f"Silpo {self._phone}",
                    data={
                        "phone": self._phone,
                        "access_token": tokens["access_token"],
                        "refresh_token": tokens.get("refresh_token"),
                        "expires_in": tokens.get("expires_in"),
                    },
                )

        return self.async_show_form(
            step_id="otp",
            data_schema=vol.Schema({vol.Required("code"): str}),
            errors=errors,
        )
