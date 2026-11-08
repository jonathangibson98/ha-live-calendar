# Architecture

```
 calendar server ──(ICS GET / CalDAV PROPFIND+REPORT)──▶ api.py  ──▶ coordinator.py ──▶ calendar.py
        ▲                                                   ▲            │  (parse in executor,        (entity: state,
        │                                                   │            │   diff, fire event)          get_events)
  secret webhook (GET/POST/PUT) ─────────────▶ __init__.py ──┘            ▼
                                                                  live_calendar_changed
```

| File | Responsibility |
|---|---|
| `api.py` | `IcsSource` (conditional GET + SHA-256) and `CaldavSource` (ctag, ETag diff, multiget), plus calendar discovery. |
| `caldav_xml.py` | Pure XML request bodies and parsers. Unit tested. |
| `coordinator.py` | Polls the source, parses only when changed (in the executor), diffs, fires events, answers event queries. |
| `diff.py` | Pure add/remove/update detection by `(uid, recurrence-id)`. Unit tested. |
| `calendar.py` | Read-only `CalendarEntity`; the current/next event is computed live so it never goes stale. |
| `config_flow.py` | CalDAV/ICS setup, discovery picker, reauth, options. |
| `__init__.py` | Setup plus the rate-limited webhook. |

## Why polling plus push?

Standard calendar protocols don't deliver push notifications to a self-hosted client. Cheap conditional polling gives a worst-case delay equal to the interval; the webhook removes the delay when something can notify Home Assistant.

## CalDAV sync cycle

1. `PROPFIND` depth 0 for `getctag` / `sync-token`. Unchanged → done.
2. `PROPFIND` depth 1 for `getetag` of every event resource.
3. `REPORT calendar-multiget` for resources whose ETag is new or different (chunks of 50).
4. Resources that disappeared are dropped. The token is only stored when every resource downloaded, so partial failures retry.

## Design notes

- Parsing runs in the executor; unparsable single resources are skipped with a warning.
- Cancelled events are filtered from queries and the state, matching Remote Calendar.
- The webhook id is stored in the config entry and never logged or placed in state attributes.
