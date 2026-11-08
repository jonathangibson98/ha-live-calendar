# Installation

Requires Home Assistant **2026.3.0 or newer** (that is the first release where custom integrations can ship their own logos).

## Publish the repository (once)

1. Create an empty GitHub repository named `ha-live-calendar`.
2. Replace the placeholder with your GitHub username everywhere:
   ```bash
   ./scripts/set_github_user.sh jonathangibson98 "Your Name"
   ```
3. Push:
   ```bash
   git init && git add . && git commit -m "Initial release"
   git branch -M main
   git remote add origin https://github.com/jonathangibson98/ha-live-calendar.git
   git push -u origin main
   git tag v0.1.0 && git push --tags
   ```
   The tag matters: HACS installs the latest **release**, and falls back to the default branch if there is none. The release workflow creates the release for you when a `v*` tag is pushed.

## Install with HACS

1. HACS → ⋮ → **Custom repositories**.
2. Repository: `https://github.com/jonathangibson98/ha-live-calendar`, Category: **Integration**.
3. Find **Live Calendar** in HACS, **Download**, then **restart Home Assistant**.
4. **Settings → Devices & services → Add integration → Live Calendar**.

Updates then appear in HACS like any other integration.

## Install manually

Copy the `custom_components/live_calendar` folder into `<config>/custom_components/`, restart, and add the integration from the UI.

## Uninstall

Remove each Live Calendar entry under Devices & services, then remove the integration in HACS (or delete the folder) and restart.
