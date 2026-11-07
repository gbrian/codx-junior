# Browser use and co-browsing

Browser use gives every chat a real Chromium browser that **you and the AI
share**. It is not an AI-only headless browser and not a second "user browser":
there is one page, one history, one cookie jar and one live view.

## What you can do

- Open a browser session from **Browser sessions** or from a chat and watch the
  page live while the AI works.
- Click, type, scroll and navigate directly in the live view; the AI sees the
  same page on its next tool call.
- Ask the AI to navigate, click, fill forms, run JavaScript, read the page text,
  list links, take screenshots, inspect the HTML source, or review what the user
  did recently.
- Keep the browser profile (cookies, logins, local storage) across restarts.

## Architecture

```text
                   codx-junior_default Docker network
 ┌────────────────────┐        CDP (port 9223)        ┌──────────────────────┐
 │  API / SmolAgent   │ ────────────────────────────► │  Chromium container  │
 │  Playwright        │                               │  ┌────────────────┐  │
 └─────────┬──────────┘                               │  │ CDP proxy      │  │
           │                                          │  │ 9223 → 9222    │  │
           │ REST / Socket.IO                         │  └────────────────┘  │
 ┌─────────▼──────────┐      Traefik route            │  ┌────────────────┐  │
 │  User browser      │ ────────────────────────────► │  │ Selkies VNC    │  │
 │  live view iframe  │      /browser/<id>/           │  │ port 3000      │  │
 └────────────────────┘                               │  └────────────────┘  │
                                                      └──────────────────────┘
```

- **User control / viewing** — the LinuxServer.io Chromium image exposes a
  Selkies web desktop. Traefik routes it at `/browser/<session_id>/`; the
  session is configured with `SUBFOLDER` so all assets and websockets work
  behind the path prefix.
- **AI control** — Chromium binds DevTools to `127.0.0.1` and rejects non-local
  `Host` headers. A tiny in-container proxy (`cdp_proxy.py`) listens on
  `0.0.0.0:9223`, rewrites the header and tunnels the connection to
  `127.0.0.1:9222`. Playwright connects to the proxy over the shared Docker
  network; both actors therefore drive the **same page**.
- **Persistence** — the container mounts
  `.codx/browser_sessions/<session_id>/chromium_profile` at `/config`.

## Using it

### From the UI

Open **Browser sessions**, create a session with a name and optional start URL,
then select it. The live browser is embedded in the panel:

- address bar, back, forward and refresh send actions through the REST API;
- clicking and typing in the iframe controls the browser directly;
- the **Shared activity** panel shows `User`, `AI` and `System` actions;
- the **AI cost** panel shows the SmolAgent token usage and cxjcoins of every
  chat linked to the session;
- the session list on the left can be collapsed with the chevron on its edge,
  giving the live browser and chat more room (the state is remembered);
- **Chat** at the bottom opens the chat picker: choose an existing chat,
  open one of the chats already linked to the session, or click **New chat** to
  create one. The chat gets the `browser` profile and shares the page with the
  live view, so you can ask the AI to act on what you are watching without
  leaving the screen.

### From a chat

Browser tools are available to the agent by default (`browser` tools):

| Tool | Purpose |
| --- | --- |
| `start_session` | Start or resume the chat's shared browser. Returns `session_id` and the live-view URL. |
| `browse_action` | `navigate`, `click`, `fill`, `execute`, `text`, `links`, `back`, `forward`, `refresh`, `wait`, `press`, `select`, `hover`, `scroll`. |
| `get_screenshot` | Capture the current page (the user sees the image inline). |
| `get_source_code` | Return the page HTML (capped to keep model context small). |
| `browser_activity` | Recent user/AI actions, so the AI notices manual changes. |
| `finish_session` | Stop (or delete) the session, keeping the Chromium profile. |

The running chat id is injected automatically into these tools, so a session
started by the AI is linked to the chat the user is looking at.

## Configuration

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `CODX_BROWSER_IMAGE` | `lscr.io/linuxserver/chromium:latest` | Browser container image. |
| `CODX_BROWSER_NETWORK` | `codx-junior_default` | Docker network shared with the API. |
| `CODX_BROWSER_AUTO_PULL` | `1` | Pull the image when it is missing. |
| `CODX_BROWSER_PUBLIC_BASE_URL` | — | Override the public live-view base URL (e.g. behind a different proxy). |
| `CODX_BROWSER_AUTH_MIDDLEWARE` | `codx-junior-auth` | Traefik middleware on the live-view route; set empty to disable. |
| `CODX_BROWSER_CDP_PROXY_PORT` | `9223` | In-container CDP proxy port. |
| `CODX_BROWSER_START_URL` | `about:blank` | Default URL when no session URL is supplied. |

The API process needs access to the Docker socket, as it does for workspaces.

## REST API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/browsers` | List sessions. |
| `POST` | `/api/browsers` | Create `{ name, chat_id?, initial_url? }`. |
| `GET` | `/api/browsers/{id}` | Session details (live view + CDP URLs). |
| `PUT` | `/api/browsers/{id}` | Rename. |
| `DELETE` | `/api/browsers/{id}` | Stop, remove and delete the session. |
| `POST` | `/api/browsers/{id}/action` | Execute a page action. |
| `POST` | `/api/browsers/{id}/screenshot` | Capture a PNG data URI. |
| `GET` | `/api/browsers/{id}/source` | Page HTML. |
| `GET` | `/api/browsers/{id}/activity` | User/AI audit trail. |
| `GET` | `/api/browsers/{id}/cost` | SmolAgent cost and token summary for linked chats. |
| `POST` | `/api/browsers/{id}/chat` | Reuse/create the chat linked to the session (browser profile active). |
| `POST` | `/api/browsers/{id}/restart` | Restart the container (profile preserved). |
| `POST` | `/api/browsers/{id}/stop` | Stop the container (kept for restart). |

## Auditing and cost

- Every user/AI action is appended to
  `.codx/browser_sessions/<session_id>/activity.jsonl` with timestamp, actor,
  action, parameters, URL, title, duration and result/error.
- SmolAgent records token usage and cxjcoins through the existing analytics
  pipeline (`/api/browsers/{id}/cost` reconciles with the chat cost header).
- Tool calls are also archived by SmolAgent's tool-usage analytics, including
  the action, arguments and result.

## Requirements and notes

- The Chromium image is large (~2 GB compressed). The first session may take a
  while if the image is not cached; `CODX_BROWSER_AUTO_PULL=0` disables pulling.
- One container per session; the live view and the API must share the Docker
  network so the CDP proxy is reachable.
- The browser runs headful inside the container so the user's VNC view and the
  AI's automation share the exact same rendering surface.
