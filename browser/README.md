# `browser/` — legacy standalone launcher

This folder contains an early standalone Chromium/Puppeteer launcher
(`pupeteer.js`) that was used to expose a CDP port from a desktop container.
It is **not** used by the codx-junior API.

The production co-browsing implementation lives in:

- `api/codx/junior/browser/docker_browser_manager.py` — creates the shared
  Chromium container (live VNC view + CDP proxy).
- `api/codx/junior/browser/browser.py` — Playwright/CDP automation.
- `api/codx/junior/tools/browser_tools.py` — the tools exposed to SmolAgent.
- `client/src/components/browsers/BrowserViewer.vue` — the user's live view.

See [Browser use and co-browsing](../docs/features/browser-use.md).
