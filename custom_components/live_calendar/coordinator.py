"""Data coordinator for Live Calendar."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
from typing import Any

from ical.calendar import Calendar
from ical.calendar_stream import IcsCalendarStream
from ical.exceptions import CalendarParseError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AuthError, CaldavSource, IcsSource, SourceError
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_CHANGED,
    MAX_EVENTS_IN_PAYLOAD,
    MIN_SCAN_INTERVAL,
)
from .diff import diff_snapshots, snapshot

_LOGGER = logging.getLogger(__name__)


class InvalidCalendar(ValueError):
    """None of the downloaded data could be parsed as a calendar."""


def parse_ics_texts(texts: list[str]) -> list[Calendar]:
    """Parse ICS documents. Runs in the executor (parsing is CPU-bound).

    A single unparsable resource (CalDAV can return hundreds) is skipped with a
    warning; it is only an error when nothing at all could be parsed.
    """
    calendars: list[Calendar] = []
    last_error: Exception | None = None
    for text in texts:
        try:
            calendars.append(IcsCalendarStream.calendar_from_ics(text))
        except CalendarParseError as err:
            last_error = err
            _LOGGER.warning("Skipping unparsable calendar data: %s", err)
    if texts and not calendars:
        raise InvalidCalendar(str(last_error))
    return calendars


def _is_cancelled(event: Any) -> bool:
    status = getattr(event, "status", None)
    value = getattr(status, "value", status)
    return bool(value) and str(value).upper() == "CANCELLED"


def sort_key(event: Any) -> datetime:
    """Sortable aware datetime for date or datetime event starts."""
    start = event.start
    if isinstance(start, datetime):
        return dt_util.as_utc(start)
    return dt_util.as_utc(dt_util.start_of_local_day(start))


class LiveCalendarCoordinator(DataUpdateCoordinator[list[Calendar]]):
    """Poll cheaply, parse only on change, and accept push-style refreshes."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        source: IcsSource | CaldavSource,
    ) -> None:
        interval = max(
            MIN_SCAN_INTERVAL,
            int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(seconds=interval),
            always_update=False,
        )
        self.source = source
        self.last_change: datetime | None = None
        self._force = False
        self._snapshot: dict = {}

    async def async_force_refresh(self) -> None:
        """Refresh right now, ignoring cached validators (used by the webhook)."""
        self._force = True
        await self.async_refresh()

    async def _async_update_data(self) -> list[Calendar]:
        force, self._force = self._force, False
        try:
            result = await self.source.fetch(force=force)
        except AuthError as err:
            raise ConfigEntryAuthFailed("Calendar credentials were rejected") from err
        except SourceError as err:
            raise UpdateFailed(str(err)) from err

        if not result.changed and self.data is not None:
            return self.data

        try:
            calendars = await self.hass.async_add_executor_job(
                parse_ics_texts, result.texts
            )
        except InvalidCalendar as err:
            raise UpdateFailed(f"Could not parse calendar: {err}") from err

        new_snapshot = snapshot(calendars)
        if self.data is not None:
            changes = diff_snapshots(
                self._snapshot, new_snapshot, limit=MAX_EVENTS_IN_PAYLOAD
            )
            if changes:
                self.last_change = dt_util.utcnow()
                self.hass.bus.async_fire(
                    EVENT_CHANGED,
                    {
                        "entry_id": self.config_entry.entry_id,
                        "calendar": self.config_entry.title,
                        "added": changes.added,
                        "removed": changes.removed,
                        "updated": changes.updated,
                    },
                )
        self._snapshot = new_snapshot
        return calendars

    # ------------------------------------------------------------------
    # Queries used by the calendar entity
    # ------------------------------------------------------------------

    def get_events(self, start: datetime | date, end: datetime | date) -> list[Any]:
        """Return non-cancelled events overlapping [start, end), sorted."""
        tz = dt_util.get_default_time_zone()
        events: list[Any] = []
        for calendar in self.data or []:
            for event in calendar.timeline_tz(tz).overlapping(start, end):
                if not _is_cancelled(event):
                    events.append(event)
        events.sort(key=sort_key)
        return events

    def next_event(self, now: datetime) -> Any | None:
        """Return the active or next upcoming non-cancelled event."""
        tz = dt_util.get_default_time_zone()
        best: Any | None = None
        for calendar in self.data or []:
            for event in calendar.timeline_tz(tz).active_after(now):
                if _is_cancelled(event):
                    continue
                if best is None or sort_key(event) < sort_key(best):
                    best = event
                break
        return best
