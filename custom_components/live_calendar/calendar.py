"""Calendar platform for Live Calendar."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import LiveCalendarCoordinator


def _rrule(event: Any) -> str | None:
    rrule = getattr(event, "rrule", None)
    if not rrule:
        return None
    try:
        return rrule.as_rrule_str()
    except AttributeError:
        return None


def to_calendar_event(event: Any) -> CalendarEvent:
    """Convert an ``ical`` event into a Home Assistant CalendarEvent."""
    start, end = event.start, event.end
    if isinstance(start, datetime):
        start = dt_util.as_local(start)
    if isinstance(end, datetime):
        end = dt_util.as_local(end)
    return CalendarEvent(
        summary=event.summary or "",
        start=start,
        end=end,
        description=getattr(event, "description", None),
        location=getattr(event, "location", None),
        uid=getattr(event, "uid", None),
        recurrence_id=getattr(event, "recurrence_id", None),
        rrule=_rrule(event),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the calendar entity."""
    async_add_entities([LiveCalendarEntity(entry.runtime_data, entry)])


class LiveCalendarEntity(CoordinatorEntity[LiveCalendarCoordinator], CalendarEntity):
    """A read-only calendar that updates as soon as the source changes."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: LiveCalendarCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Live Calendar",
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next event (computed live, never stale)."""
        found = self.coordinator.next_event(dt_util.now())
        return to_calendar_event(found) if found else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return events in a date range."""
        return [
            to_calendar_event(e) for e in self.coordinator.get_events(start_date, end_date)
        ]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose when the calendar last changed."""
        last = self.coordinator.last_change
        return {"last_change": last.isoformat() if last else None}
