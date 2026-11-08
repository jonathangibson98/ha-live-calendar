"""Tests for change detection (no Home Assistant needed)."""

from types import SimpleNamespace as NS

import diff


def ev(uid, summary="Meeting", start="2026-11-09 10:00", end="2026-11-09 11:00", **kw):
    return NS(
        uid=uid,
        summary=summary,
        start=start,
        end=end,
        location=kw.get("location"),
        description=kw.get("description"),
        rrule=kw.get("rrule"),
        status=kw.get("status"),
        recurrence_id=kw.get("recurrence_id"),
    )


def cal(*events):
    return NS(events=list(events))


def test_no_change():
    snap = diff.snapshot([cal(ev("a"), ev("b"))])
    assert not diff.diff_snapshots(snap, diff.snapshot([cal(ev("a"), ev("b"))]))


def test_added():
    old = diff.snapshot([cal(ev("a"))])
    new = diff.snapshot([cal(ev("a"), ev("b", "Dentist"))])
    ch = diff.diff_snapshots(old, new)
    assert ch.added == [{"uid": "b", "summary": "Dentist"}]
    assert not ch.removed and not ch.updated


def test_removed():
    old = diff.snapshot([cal(ev("a"), ev("b", "Dentist"))])
    new = diff.snapshot([cal(ev("a"))])
    ch = diff.diff_snapshots(old, new)
    assert ch.removed == [{"uid": "b", "summary": "Dentist"}]


def test_updated_time_and_title():
    old = diff.snapshot([cal(ev("a"))])
    moved = diff.snapshot([cal(ev("a", start="2026-11-09 12:00"))])
    renamed = diff.snapshot([cal(ev("a", summary="Standup"))])
    assert diff.diff_snapshots(old, moved).updated[0]["uid"] == "a"
    assert diff.diff_snapshots(old, renamed).updated == [{"uid": "a", "summary": "Standup"}]


def test_recurring_overrides_are_distinct_keys():
    base = ev("r", rrule="FREQ=DAILY")
    override = ev("r", "Moved", recurrence_id="20261110T100000")
    snap = diff.snapshot([cal(base, override)])
    assert len(snap) == 2
    new = diff.snapshot([cal(base)])
    assert diff.diff_snapshots(snap, new).removed == [{"uid": "r", "summary": "Moved"}]


def test_multiple_calendars_are_merged():
    snap = diff.snapshot([cal(ev("a")), cal(ev("b"))])
    assert set(snap) == {"a|", "b|"}


def test_limit_caps_each_list():
    old = diff.snapshot([cal()])
    new = diff.snapshot([cal(*[ev(f"u{i}") for i in range(10)])])
    assert len(diff.diff_snapshots(old, new, limit=3).added) == 3
