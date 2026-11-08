"""Diagnostics for Live Calendar."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_PASSWORD, CONF_URL, CONF_USERNAME, CONF_WEBHOOK_ID

TO_REDACT = {CONF_URL, CONF_USERNAME, CONF_PASSWORD, CONF_WEBHOOK_ID}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics (secrets redacted)."""
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "last_update_success": coordinator.last_update_success,
        "update_interval_seconds": (
            coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None
        ),
        "calendar_objects": len(coordinator.data or []),
        "last_change": coordinator.last_change.isoformat()
        if coordinator.last_change
        else None,
    }
