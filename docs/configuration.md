# Configuration

Everything is configured in the UI. Add the integration once per calendar.

## CalDAV (recommended)

| Field | Notes |
|---|---|
| Server or calendar URL | A server root (`https://caldav.icloud.com`), a DAV base (`https://cloud.example.com/remote.php/dav`) or the exact calendar collection URL. |
| Username / Password | HTTP Basic. Use an **app-specific password** where offered (iCloud, Fastmail). |
| Verify SSL certificate | Turn off only for a self-signed server on your own network. |

The integration discovers the principal, the calendar home and the calendars that support events. If more than one is found you choose one. Task-only collections are ignored.

## ICS / webcal feed

| Field | Notes |
|---|---|
| Calendar name | Becomes the device and entity name. |
| Calendar URL | `https://` or `webcal://` address of a `.ics` file. |
| Username / Password | Optional, HTTP Basic. |
| Verify SSL certificate | As above. |

## Options (Configure button)

| Option | Default | Range | Meaning |
|---|---|---|---|
| Check for changes every | 30 s | 10 to 3600 s | How often the source is asked whether anything changed. |

The dialog also shows the secret **push URL** for this calendar (see [webhooks](webhooks.md)).

A shorter interval is cheap when nothing changed (a `304`, or one tiny CalDAV request), but respect your provider's rate limits, especially for hosted services.

## Entity

`calendar.<name>` is **on** during an event and **off** otherwise. Attributes follow Home Assistant's standard calendar model for the current or next event (`message`, `start_time`, `end_time`, `location`, `description`, `all_day`) plus `last_change` (UTC timestamp of the last add, remove or edit).

## Event: `live_calendar_changed`

Fired when events were added, removed or edited. Payload:

```yaml
entry_id: 01J...
calendar: Family
added:   [{uid: "abc", summary: "Dentist"}]
removed: []
updated: [{uid: "def", summary: "Team sync"}]
```

Each list is capped at 50 items. The first load after startup never fires the event.
