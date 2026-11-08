# Troubleshooting

## Enable debug logs

```yaml
logger:
  logs:
    custom_components.live_calendar: debug
```

## "Could not reach the server"
- Check the URL opens from the Home Assistant host. Trailing slash matters for some CalDAV servers.
- Self-signed certificate? Disable **Verify SSL** for that entry.

## "Server rejected the username or password"
- Use an **app password** (iCloud, Fastmail, Nextcloud with 2FA).
- Use your full username (often the e-mail address).
- HA will prompt to re-authenticate if credentials stop working later.

## "No calendars were found"
- Use the exact calendar URL instead of the server root.
- Task-only (VTODO) collections are ignored.

## Changes show up late
- Is the source slow? Google "secret address" and Outlook.com ICS feeds lag for hours; see [providers](providers.md).
- Lower the interval under **Configure** (minimum 10 s).
- Open the calendar *panel* again; it loads events when displayed.
- Test the webhook with `curl`. A `200` means HA refreshed; if the event still isn't there, the server hasn't published it.

## Entity shows unavailable
The last refresh failed. Check **Settings → System → Logs** for `live_calendar`. It recovers by itself on the next successful check.

## An event is missing
- Cancelled events are hidden by design.
- Check the calendar's time zone and the event's recurrence rule.

## Download diagnostics
Devices & services → Live Calendar → ⋮ → **Download diagnostics** (secrets are redacted) and attach it to your issue.
