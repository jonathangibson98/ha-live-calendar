"""Constants for the Live Calendar integration."""

from __future__ import annotations

DOMAIN = "live_calendar"

CONF_SOURCE = "source"
SOURCE_ICS = "ics"
SOURCE_CALDAV = "caldav"

CONF_URL = "url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_VERIFY_SSL = "verify_ssl"
CONF_WEBHOOK_ID = "webhook_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 30  # seconds
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 3600

# Minimum number of seconds between two webhook-triggered refreshes.
WEBHOOK_MIN_GAP = 2.0

# Fired on the Home Assistant event bus whenever events were added, removed or
# modified in the connected calendar.
EVENT_CHANGED = f"{DOMAIN}_changed"

# Max number of changed events listed in the bus event payload.
MAX_EVENTS_IN_PAYLOAD = 50
