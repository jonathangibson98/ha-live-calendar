# Provider compatibility

> **Status:** none of these have been verified against a live account yet. The "Expected" column is based on each provider's documented behavior. If you test one, please open an issue or PR with the result.

| Provider | Source to use | Expected freshness | Notes |
|---|---|---|---|
| Nextcloud | CalDAV | Seconds | URL `https://HOST/remote.php/dav`. Use an app password (Settings → Security). |
| iCloud | CalDAV | Seconds | URL `https://caldav.icloud.com`. Requires an **app-specific password** from appleid.apple.com. |
| Fastmail | CalDAV | Seconds | URL `https://caldav.fastmail.com/dav/`. App password with CalDAV access. |
| Radicale / Baïkal / SOGo / Synology | CalDAV | Seconds | Use the server's DAV address. |
| Proton Calendar | ICS | Provider-dependent | Share link (ICS). No CalDAV. |
| Google Calendar | ICS | **Slow (hours)** | The "secret address in iCal format" is cached by Google. Google's CalDAV needs OAuth, which this version doesn't support. |
| Outlook.com / Microsoft 365 | ICS | **Slow (hours)** | Published calendar links are cached by Microsoft; there is no basic-auth CalDAV. |

## Getting fast sync from Google or Microsoft calendars

No integration can read changes faster than the provider publishes them. Options:

- Sync the calendar into a CalDAV server you control (for example Nextcloud's external-calendar subscription or a sync tool such as vdirsyncer) and connect Live Calendar to that.
- Keep the ICS feed and accept the provider's delay; the webhook won't help here because the feed itself is stale.

## Tips

- If discovery fails, paste the exact calendar collection URL (it usually ends in `/`).
- Provider URLs with a username containing `@` are fine; enter it in the Username field, not in the URL.
