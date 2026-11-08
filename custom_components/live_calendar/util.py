"""Small helpers shared by the integration and its config flow."""

from __future__ import annotations

from typing import Any

from aiohttp import BasicAuth

from homeassistant.components import webhook
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .api import CaldavSource, IcsSource
from .const import (
    CONF_PASSWORD,
    CONF_SOURCE,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    SOURCE_CALDAV,
)


def make_auth(username: str | None, password: str | None) -> BasicAuth | None:
    """Return HTTP Basic credentials, or None when no username is set."""
    if not username:
        return None
    return BasicAuth(username, password or "")


def build_source(hass: HomeAssistant, data: dict[str, Any]) -> IcsSource | CaldavSource:
    """Create the right source object for a config entry's data."""
    session = async_get_clientsession(hass, verify_ssl=data.get(CONF_VERIFY_SSL, True))
    auth = make_auth(data.get(CONF_USERNAME), data.get(CONF_PASSWORD))
    if data.get(CONF_SOURCE) == SOURCE_CALDAV:
        return CaldavSource(session, data[CONF_URL], auth)
    return IcsSource(session, data[CONF_URL], auth)


def get_webhook_url(hass: HomeAssistant, webhook_id: str) -> str:
    """Return the best URL available for the push webhook."""
    try:
        return webhook.async_generate_url(hass, webhook_id)
    except NoURLAvailableError:
        path = webhook.async_generate_path(webhook_id)
        try:
            return f"{get_url(hass)}{path}"
        except NoURLAvailableError:
            return path
