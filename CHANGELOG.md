# Changelog

All notable changes are documented here. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-11-08

### Added
- Initial release.
- ICS / webcal feed source with conditional requests (`ETag`, `Last-Modified`) and content hashing.
- CalDAV source with automatic calendar discovery and incremental sync via ctag / sync-token and per-event ETags.
- Secret push webhook for instant refresh, rate-limited to one call per 2 seconds.
- `live_calendar_changed` event listing added, removed and updated events.
- Calendar entity with current/next event, event queries and recurrence expansion; cancelled events are hidden.
- Configurable check interval (10 to 3600 s, default 30 s).
- Re-authentication flow, diagnostics with secrets redacted, and bundled brand images.

[Unreleased]: https://github.com/YOUR_GITHUB_USERNAME/ha-live-calendar/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YOUR_GITHUB_USERNAME/ha-live-calendar/releases/tag/v0.1.0
