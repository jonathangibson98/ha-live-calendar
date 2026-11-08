"""Live Calendar: a read-only calendar that syncs (almost) in real time."""

from __future__ import annotations

import logging
import time

from aiohttp import web

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_WEBHOOK_ID, DOMAIN, WEBHOOK_MIN_GAP
from .coordinator import LiveCalendarCoordinator
from .util import build_source

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CALENDAR]

type LiveCalendarConfigEntry = ConfigEntry[LiveCalendarCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: LiveCalendarConfigEntry) -> bool:
    """Set up Live Calendar from a config entry."""
    coordinator = LiveCalendarCoordinator(hass, entry, build_source(hass, dict(entry.data)))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    webhook_id: str = entry.data[CONF_WEBHOOK_ID]
    last_call = 0.0

    async def _handle_webhook(
        hass: HomeAssistant, _webhook_id: str, request: web.Request
    ) -> web.Response:
        """Refresh immediately when something pings the push URL."""
        nonlocal last_call
        now = time.monotonic()
        if now - last_call < WEBHOOK_MIN_GAP:
            return web.Response(status=429, text="Too many requests")
        last_call = now
        await coordinator.async_force_refresh()
        if coordinator.last_update_success:
            return web.Response(status=200, text="OK")
        return web.Response(status=502, text="Calendar refresh failed")

    webhook.async_register(
        hass,
        DOMAIN,
        f"Live Calendar: {entry.title}",
        webhook_id,
        _handle_webhook,
        allowed_methods=["GET", "POST", "PUT"],
    )
    entry.async_on_unload(lambda: webhook.async_unregister(hass, webhook_id))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: LiveCalendarConfigEntry) -> None:
    """Reload when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: LiveCalendarConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
