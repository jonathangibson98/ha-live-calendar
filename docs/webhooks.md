# Instant refresh with the push webhook

Each Live Calendar entry registers a secret webhook. Calling it makes Home Assistant refresh that calendar **immediately** (ignoring cached validators), instead of waiting for the next check.

## Find the URL

**Settings → Devices & services → Live Calendar → Configure.** The dialog shows the URL. If Home Assistant has no external URL configured, it shows the local path (`/api/webhook/<id>`); prepend your own address.

## Calling it

`GET`, `POST` and `PUT` are accepted; no body is needed.

```bash
curl -X POST "https://ha.example.com/api/webhook/<id>"
```

| Response | Meaning |
|---|---|
| `200` | Refreshed successfully |
| `429` | Called again within 2 seconds, ignored |
| `502` | The refresh ran but the calendar source failed |

## Ideas for who should call it

- A **Nextcloud** Flow / webhook-listener or a small cron script after calendar edits.
- A **CalDAV server hook** (Radicale hook, Baïkal/SOGo scripts).
- A phone **shortcut** or any automation tool you use after editing a calendar.
- A Home Assistant automation that calls `homeassistant.update_entity` on a trigger of your choosing (no URL needed).

Remember: the webhook only helps if the **source already has the new data**. See [providers](providers.md) for feeds that lag.

## Security

The id in the URL is the only secret. Don't post it publicly. It can only trigger a refresh; it cannot read calendar data or change anything. To rotate it, delete and re-add the entry.
