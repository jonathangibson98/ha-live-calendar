"""Detect which events changed between two parsed calendar snapshots.

Pure Python (no Home Assistant imports) so it is easy to unit test.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

_SIGNATURE_FIELDS = (
    "summary",
    "start",
    "end",
    "location",
    "description",
    "rrule",
    "status",
)

Snapshot = dict[str, tuple[str, tuple[str, ...]]]


@dataclass
class ChangeSet:
    """Events added, removed or modified between two snapshots."""

    added: list[dict[str, str]] = field(default_factory=list)
    removed: list[dict[str, str]] = field(default_factory=list)
    updated: list[dict[str, str]] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.added or self.removed or self.updated)


def _key(event: Any) -> str:
    uid = getattr(event, "uid", None) or ""
    rid = getattr(event, "recurrence_id", None) or ""
    return f"{uid}|{rid}"


def _signature(event: Any) -> tuple[str, ...]:
    return tuple(str(getattr(event, name, None)) for name in _SIGNATURE_FIELDS)


def snapshot(calendars: Iterable[Any]) -> Snapshot:
    """Build ``{event-key: (summary, signature)}`` for all master events."""
    out: Snapshot = {}
    for calendar in calendars:
        for event in getattr(calendar, "events", None) or []:
            out[_key(event)] = (str(getattr(event, "summary", "") or ""), _signature(event))
    return out


def _item(key: str, summary: str) -> dict[str, str]:
    return {"uid": key.split("|", 1)[0], "summary": summary}


def diff_snapshots(old: Snapshot, new: Snapshot, limit: int = 50) -> ChangeSet:
    """Return what changed going from ``old`` to ``new`` (each list capped)."""
    changes = ChangeSet()
    for key, (summary, sig) in new.items():
        if key not in old:
            changes.added.append(_item(key, summary))
        elif old[key][1] != sig:
            changes.updated.append(_item(key, summary))
    for key, (summary, _sig) in old.items():
        if key not in new:
            changes.removed.append(_item(key, summary))
    changes.added = changes.added[:limit]
    changes.removed = changes.removed[:limit]
    changes.updated = changes.updated[:limit]
    return changes
