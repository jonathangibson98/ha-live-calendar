# Contributing

Thanks for helping! Bug reports about **which calendar provider you tested and what happened** are especially valuable.

## Reporting a bug

Open an issue using the bug template and include your Home Assistant version, the provider (Nextcloud, iCloud, ...), the source type (CalDAV or ICS), and the integration's diagnostics (Settings → Devices & services → Live Calendar → ⋮ → Download diagnostics; secrets are redacted). Never paste calendar URLs or webhook URLs.

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements_test.txt
pytest
```

The tests cover the parts that have no Home Assistant dependency (`caldav_xml.py`, `diff.py`). Everything else is checked in CI with HACS validation and hassfest. To try changes for real, copy `custom_components/live_calendar` into a dev Home Assistant instance.

Keep `caldav_xml.py` and `diff.py` free of Home Assistant imports so they stay testable.

## Brand images

Edit `scripts/generate_brand.py` and run `python3 scripts/generate_brand.py` (needs Pillow). It regenerates the PNGs in `custom_components/live_calendar/brand/` and the SVGs in `images/`.

## Releasing

1. Update `version` in `manifest.json` and move the `Unreleased` notes in `CHANGELOG.md` under the new version.
2. Commit, then tag: `git tag v0.1.1 && git push --tags`.
3. The release workflow creates the GitHub release; HACS then offers it as an update.
