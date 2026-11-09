# Computer use: AI-assisted desktops, VMs and remote machines

Computer sessions generalize browser sessions. A session is **one real machine
shared by the user and the AI**: the human watches and can take over through a
live view, the AI drives the same screen through desktop tools. The original
Chromium sessions are now the `browser` kind of this model, so nothing is lost.

| Kind | What runs | AI control | Typical use |
| --- | --- | --- | --- |
| `browser` | Chromium container | Chrome DevTools Protocol | The existing browser co-pilot (DOM snapshots, scripts, downloads). |
| `linux` | LinuxServer.io webtop desktop container (Xvfb + KDE/XFCE + Selkies) | `docker exec` with `xdotool` + Pillow screenshots | A full Linux desktop: terminals, IDEs, GUI apps, package installs. |
| `windows` | `dockurr/windows` QEMU VM | VNC (RFB) | Windows-only software, testing an installer, Windows browsers. |
| `macos` | `dockurr/macos` QEMU VM or a remote Mac | VNC (RFB) + optional SSH | Xcode/Simulator, macOS-only tooling; a physical Mac via Screen Sharing. |
| `remote` | An existing machine reachable over VNC | VNC (RFB) + optional SSH | A Mac mini in the office, a lab workstation, a cloud desktop. |

## Why this design

Browser automation answers "what is in the DOM"; a computer needs "what is on
the screen and how do I click it". The implementation follows the same pattern
that projects such as [OpenHands](https://docs.openhands.dev/openhands/usage/architecture/runtime)
and Anthropic's [computer-use demo](https://github.com/anthropics/claude-quickstarts/tree/main/computer-use-demo)
use: a containerized desktop, a live VNC view for the human, and an
input/screenshot channel for the agent. Instead of requiring one agent binary
inside every image:

- **Linux** uses the image's own X11 tools. A small script
  (`computer/agent/computer_agent.py`) is mounted read-only and executed through
  `docker exec`; no extra port or daemon is exposed. Screenshots come from
  Pillow's X11 grab, input from `xdotool`.
- **Windows/macOS/remote** use a pure-Python RFB client
  (`computer/vnc.py`). QEMU exposes a standard VNC server on port 5900, so the
  same code works for the dockurr VMs and for a real Mac with Screen Sharing.
  The human gets the same framebuffer through a noVNC client in the panel.
- **OCR everywhere.** `computer/ocr.py` runs tesseract on every screenshot and
  returns word boxes. The model reads terminal output, dialog labels and menus,
  and `click_text` clicks the centre of a matched word, so it does not have to
  guess pixel coordinates or have vision.

Reference projects worth reading: [trycua/cua](https://github.com/trycua/cua)
(computer-use sandboxes for macOS/Linux/Windows), [dockur/windows](https://github.com/dockur/windows)
and [dockur/macos](https://github.com/dockur/macos) (OS in Docker),
[LinuxServer.io webtop/Selkies](https://docs.linuxserver.io/selkies/components/selkies/),
and [noVNC](https://github.com/novnc/noVNC).

## Image library (Kasmweb + LinuxServer.io)

The **Library** button in the Computer sessions sidebar opens the standalone
image browser (`ComputerImageLibrary.vue`): search, category chips, provider
tabs and image details.  Picking an image opens the new-session dialog with that
image already selected.  The same browser is also embedded in the new-session
dialog under **Desktop image**.  The library ships with two curated providers
and resolves the live-view transport automatically:

| Provider | Examples | Live view | AI control |
| --- | --- | --- | --- |
| **LinuxServer.io** | `webtop:debian-kde`, `ubuntu-xfce`, `ubuntu-kde`, `fedora-xfce`, `arch-i3`, `latest` (Alpine XFCE) | Selkies on `3000` (HTTP, path prefix) | `docker exec` agent (`xdotool`/Pillow) |
| **Kasmweb** | `desktop`, `ubuntu-jammy-desktop`, `core-kali-rolling`, `alma/rocky/oracle` desktops, `firefox`, `chrome`, `vs-code`, `terminal`, `libre-office`, `gimp`, … | KasmVNC on `6901` (HTTPS, stripped prefix) | `docker exec` agent (libX11/XTest + `xwd` fallback) |

The selector shows name, category, description, screenshot/logo, provider and
default tag.  Selecting a Kasmweb card loads its Docker Hub tags so a specific
release can be pinned; LinuxServer flavours are themselves the image tags and
therefore already appear as cards.  Any other `registry/image:tag` can be
entered under **Custom image**; unknown images use the screenshot fallback until
a known profile is chosen.

Kasmweb images are started with `VNC_PW`, `VNC_RESOLUTION`, `--shm-size=512m`
and the API user's group so shared project folders stay writable.  KasmVNC uses
a self-signed HTTPS certificate; Traefik reaches it through a shared
`codx-insecure` transport, injects the per-session Basic auth for the iframe,
and strips `/computer/<id>` so KasmVNC's relative assets/websocket work.  The
per-session KasmVNC login is also available from the viewer banner (and from
`POST /api/computers/{id}/viewer-credentials`).

LinuxServer images keep the existing `/config` profile persistence.  Kasmweb's
home directory is container-local (project files and downloads are shared), so
desktop preferences reset when the container is recreated.

## Saved computers (reuse a customized desktop)

The floppy-disk button in a running Linux/Kasmweb desktop commits the container
to a local Docker image and adds a **Saved** entry to the project's image
library. The AI can do the same with the `save_computer` tool when asked. The creation
dialog's image selector has a **Saved** tab; selecting an entry starts a new
session from that snapshot.

What is stored in `.codx/computer_library/<item-id>/`:

| File | Purpose |
| --- | --- |
| `item.json` | image, provider, live-view profile, author, size, defaults |
| `preview.png` | screenshot captured at save time |
| `profile.tar.gz` | optional LinuxServer `/config` archive (caches excluded) |

The committed image contains installed packages and changes in the container
filesystem.  LinuxServer's `/config` is a bind mount, so its settings are only
included when **Include home/profile data** is ticked; profiles may contain
logins, cookies and keys.  Kasmweb's home lives inside the container and is
always part of the commit, so the save dialog warns that it is shared with
project users.

Saved entries keep the source provider/live-view settings (`Selkies` on 3000
or `KasmVNC` on 6901) and resource/env defaults.  Starting from a saved entry
restores the optional profile before the container starts; image names like
`codx-saved/<project>/<name>:<timestamp>` are never re-canonicalised to their
upstream base.

Saving is limited to Linux desktop containers.  Windows/macOS VM state lives on
the `/storage` disk volume, not in the container layer; a VM disk snapshot flow
is still needed.  Images are local to the Docker host, so they are reusable by
users of the same project on that host; a multi-host deployment needs a registry
push.  Deleting a saved entry removes its library folder and local image, but is
blocked while a session started from it is still present.

## Architecture

```text
                        codx-junior_default Docker network
 ┌────────────────────┐   docker exec (Linux)   ┌──────────────────────────┐
 │ API / agent        │ ──────────────────────► │ Linux webtop container   │
 │ DesktopRuntime     │   xdotool + Pillow      │ Xvfb + KDE + Selkies     │
 │  ├ Linux backend   │                         └──────────┬───────────────┘
 │  ├ VNC backend     │   RFB (TCP 5900)        ┌──────────▼───────────────┐
 │  └ OCR (tesseract) │ ──────────────────────► │ Windows/macOS QEMU VM    │
 └─────────┬──────────┘                         │ VNC + noVNC              │
           │ REST / WebSocket                   └──────────────────────────┘
 ┌─────────▼──────────┐   /computer/<id>/  (Linux, Selkies)
 │ User browser       │   /api/computers/<id>/vnc (Windows/macOS/remote,
 │ live view + bar    │    one-time ticket → raw RFB WebSocket bridge)
 └────────────────────┘
```

- **Session record** — one `BrowserSession`/`ComputerSession` model stores
  `kind`, `control` (`cdp`, `docker`, `vnc`), VNC/SSH endpoints, capabilities,
  desktop size, folder sharing and the control lease. Browser sessions are
  unchanged at the storage level (`.codx/browser_sessions/`), so existing
  sessions load as `kind="browser"`.
- **Containers** — `DockerBrowserManager`/`DockerComputerManager` builds a
  different `docker run` per kind:
  - browser: Chromium + CDP proxy + `/browser/<id>/` Traefik route;
  - Linux: webtop + agent mount + `/computer/<id>/` Traefik route;
  - VM: dockurr image, `/dev/kvm`, `/dev/net/tun`, `NET_ADMIN`, `/storage`
    disk, one `/shared` folder, VNC 5900 (AI + optional external client) and
    8006 (noVNC, not required by the panel).
- **Runtime** — `DesktopRuntime` owns one backend per session and a lock, so the
  AI and the human never interleave half-finished clicks or drags. It enforces
  the same control lease as the browser runtime and writes every action to the
  shared `activity.jsonl`.
- **Live view** — Linux uses the webtop Selkies iframe. Windows/macOS/remote use
  the built-in noVNC viewer: `POST /api/computers/{id}/vnc-ticket` issues a
  single-use ticket bound to that session's VNC endpoint, and the WebSocket
  bridge tunnels raw RFB bytes. The panel therefore works through the same
  origin/Traefik route without exposing the VNC port publicly.

## Using it

### From the UI

**Computer sessions** → **New session** → choose the machine:

- **Linux desktop** (default): shell, GUI apps and project folders under
  `/home/<project_name>`; downloads/saved files land in the project.
- **Windows VM** / **macOS VM**: pick the OS release. The project root is shared
  as `Z:\` (Windows) or `/shared` (macOS). **Windows/macOS VMs require KVM** on
  the Docker host.
- **Remote machine**: VNC host/port/password, plus optional SSH host/user/key
  (or password with `sshpass`) so the AI can run builds/tests.
- **Browser only**: the original Chromium co-browsing session.

The panel shows the live view plus an action bar: type text, key buttons and
shortcuts, a shell command box (when the machine has a shell), screenshot/OCR,
"Ask AI", control handoff. Clicking the screenshot in fallback mode clicks the
desktop at the corresponding display coordinate.

### From a chat

The `computer` profile provides:

| Tool | Purpose |
| --- | --- |
| `start_computer` | Create/resume a `linux`, `windows`, `macos`, `remote` or `browser` session. Returns `session_id` and the live view. |
| `computer_action` | `screenshot`, `ocr`, `click`, `double_click`, `right_click`, `click_text`, `move`, `drag`, `scroll`, `type`, `key`, `hotkey`, `wait`, `windows`, `active_window`, `focus_window`, `close_window`, `open_app`, `list_apps`, `run_command`, `screen_size`, `batch`. |
| `computer_screenshot` | Capture the screen and return OCR text + clickable word centres. |
| `computer_status` | Kind, status, control lease, desktop size, VNC/SSH endpoints. Without an id: list sessions. |
| `computer_control` | `status`, `handoff`, `take_control`, `give_back`, `pause`. |
| `computer_activity` | Recent user/AI actions (what the human did in the live view). |
| `finish_computer` | Stop (keep profile/VM storage) or delete. |

The screenshot response includes `text` and `words` (`text`, `cx`, `cy`,
`confidence`), which is how a text-only model "sees" a GUI. `click_text` matches
case-insensitively and clicks the word centre.

### Example prompts

```text
# Linux
Start a Linux desktop. Install ripgrep, clone the repo into the project folder
and run the tests; show me the desktop while it works.

# Windows
Start a Windows 11 VM and install the app from the shared folder. Tell me if
the installer needs a reboot.

# macOS / mobile development
Connect to my Mac mini over VNC (ssh user osx). Open Xcode, boot the iPhone 16
simulator, build the app and run it; use SSH for xcodebuild output.

# Remote debugging
Open the office workstation, read the error dialog on screen and try the fix in
the terminal.
```

## Configuration

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `CODX_COMPUTER_LINUX_IMAGE` | `lscr.io/linuxserver/webtop:debian-kde` | Default Linux desktop image. |
| `CODX_COMPUTER_WEBTOP_TAG` | `debian-kde` | Default LinuxServer webtop flavour. |
| `CODX_COMPUTER_KASM_TAG` | `1.19.0` | Default Kasmweb release tag. |
| `CODX_COMPUTER_KASM_UID` | `1000` | Kasmweb container user (the image home is owned by it). |
| `CODX_COMPUTER_SAVE_MAX_PROFILE_BYTES` | `2147483648` | Maximum archived `/config` profile size for a saved computer. |
| `CODX_COMPUTER_WINDOWS_IMAGE` | `dockurr/windows` | Windows VM image. |
| `CODX_COMPUTER_MACOS_IMAGE` | `dockurr/macos` | macOS VM image. |
| `CODX_COMPUTER_VM_AUTO_PULL` | same as `CODX_BROWSER_AUTO_PULL` | Pull VM images when missing. |
| `CODX_COMPUTER_VM_RAM` / `_CPUS` / `_DISK` | `8G` / `4` / `64G` | Default VM resources (overridden per session by the advanced settings; macOS uses `128G` when `_DISK` is unset). |
| `CODX_COMPUTER_WINDOWS_DISK` / `_MACOS_DISK` | `64G` / `128G` | Per-kind disk defaults, checked before `CODX_COMPUTER_VM_DISK`. |
| `CODX_COMPUTER_VM_USER` / `_PASSWORD` | `Docker` / `admin` | Windows account created by dockurr. |
| `CODX_COMPUTER_DISPLAY` | `:1` | X11 display inside Linux desktop containers. |
| `CODX_COMPUTER_VNC_PORT` | `5900` | VM VNC port. |
| `CODX_COMPUTER_WEB_PORT` | `8006` | VM noVNC port (published; the panel does not need it). |
| `CODX_COMPUTER_PUBLISH_VNC` | `1` | Publish VM VNC/8006 on `127.0.0.1` for external clients. |
| `CODX_COMPUTER_OCR_LANG` | `eng` | Tesseract language(s), e.g. `eng+spa`. |
| `CODX_BROWSER_IMAGE` / `CODX_BROWSER_NETWORK` | unchanged | Browser container settings. |
| `CODX_BROWSER_REQUEST_TIMEOUT_SECONDS` | `600` | Long-request budget for `/api/computers` (VM image pull/first boot, long actions). |

### Advanced settings per session

Windows/macOS sessions show a dedicated **VM resources** section (vCPUs, RAM
and disk size) in the **New computer session** dialog. Browser/Linux sessions
keep the same resources under *Advanced settings*. The values are stored on the
session record, applied when the machine is created and preserved by restarts
that recreate the container:

| Setting | Browser / Linux | Windows / macOS VM |
| --- | --- | --- |
| **Docker image** | Overrides the Chromium/webtop image. A custom image must keep the same live-view and control contract. | Overrides `dockurr/windows` or `dockurr/macos`. |
| **vCPUs** | `docker run --cpus`. | `CPU_CORES` for QEMU (guest CPUs). |
| **RAM** | `docker run --memory`. | `RAM_SIZE` for QEMU (guest RAM). |
| **Disk size** | Not applicable (the container uses the host disk). | `DISK_SIZE`; used when the VM disk is first created. Increasing it and restarting the session expands the existing disk (dockurr keeps the data). |
| **Shared memory** | `docker run --shm-size` (default `2G`). | Not applicable. |
| **Desktop size** | Browser window size / Selkies manual resolution. | Resolution is controlled by the guest OS. |
| **Environment variables** | Extra `-e KEY=VALUE` passed to the image. | Extra `-e KEY=VALUE` passed to the image. |

Environment names managed by codx-junior (`SUBFOLDER`, `TITLE`, `DISPLAY`,
`VERSION`, `RAM_SIZE`, `CPU_CORES`, `DISK_SIZE`, `USERNAME`, `PASSWORD`…) are
reserved: values supplied in the advanced section cannot override them, because
breaking them would detach the live view or the AI control channel.

The same fields are editable after creation from the session's **Session
settings** screen. Use **Save & restart** to apply resource changes: Docker
cannot change CPU/RAM/disk on a running container, so the restart recreates it
while keeping the browser profile and the VM disk. For a macOS VM, 64 GB is the
upstream default; codx-junior defaults macOS to 128 GB, and 256 GB is safer when
installing Xcode/Simulator. On first boot, erase the VirtIO disk in Disk Utility
before reinstalling macOS. After expanding the disk, macOS may need the two
`diskutil` commands documented by
[dockur/macos](https://github.com/dockur/macos) to allocate the extra space.

The API needs the Docker socket (as for workspaces) and, for VMs, the host must
expose `/dev/kvm` (and `/dev/net/tun`). VMs are heavy: at least 2 GB RAM and
32 GB disk per Windows/macOS guest, plus the image pull.

## REST API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/computers` | List all computer sessions. |
| `POST` | `/api/computers` | Create `{ name, kind, os_version?, initial_url?, image?, image_provider?, library_item_id?, cpu_cores?, ram_size?, disk_size?, shm_size?, extra_env?, desktop_width?, desktop_height?, share_* }`. |
| `GET` | `/api/computers/{id}` | Details + live-view/control endpoints. |
| `PUT` | `/api/computers/{id}` | Update name, VNC/SSH fields, image and resources (`image`, `cpu_cores`, `ram_size`, `disk_size`, `shm_size`, `extra_env`, desktop size). Applied on restart. |
| `DELETE` | `/api/computers/{id}` | Stop, remove and delete. |
| `POST` | `/api/computers/{id}/action` | Page or desktop action. |
| `POST` | `/api/computers/{id}/screenshot` | PNG data URI + OCR text/words. |
| `GET` | `/api/computers/{id}/source` | Browser HTML (browser kind only). |
| `GET` | `/api/computers/{id}/activity` | User/AI audit trail. |
| `GET` | `/api/computers/{id}/cost` | AI cost of linked chats. |
| `GET` | `/api/computers/{id}/files` | Mounted folders + saved files. |
| `POST` | `/api/computers/{id}/control` | Control lease. |
| `POST` | `/api/computers/{id}/restart` / `stop` | Lifecycle. |
| `GET` | `/api/computers/images` | Browse Kasmweb/LinuxServer images (`provider`, `q`, `category`, `kind`). |
| `GET` | `/api/computers/images/tags` | Tags for one repository (`provider`, `repository`). |
| `POST` | `/api/computers/{id}/viewer-credentials` | KasmVNC login for the embedded viewer. |
| `POST` | `/api/computers/{id}/save` | Commit a running Linux/Kasmweb desktop into the project library. |
| `GET` | `/api/computers/library` | List reusable saved computers. |
| `GET` | `/api/computers/library/{item}` | Saved computer metadata. |
| `GET` | `/api/computers/library/{item}/preview` | Saved screenshot. |
| `DELETE` | `/api/computers/library/{item}` | Delete a saved computer and its image. |
| `POST` | `/api/computers/{id}/vnc-ticket` | One-time noVNC WebSocket path. |
| `WS` | `/api/computers/{id}/vnc?ticket=…` | Raw RFB bridge. |

`/api/browsers` remains as a backwards-compatible alias for existing clients;
both prefixes operate on the same records.

## Security and limits

- **Control lease** — the AI yields while the user is driving or has taken
  control. Desktops use the same `controller`/`user_active_until`/handoff
  protocol as browsers; the AI must call `computer_control(handoff)` for
  passwords, MFA, captchas and payment approvals.
- **Secrets** — VNC/SSH passwords and the SSH key path are stripped from the
  general session record (`to_public_dict`), Socket.IO events and activity
  logs; they are stored in the session file (mode controlled by the project
  `.codx`). The VNC password is returned only by the authenticated, one-time
  `vnc-ticket` endpoint so the built-in viewer can authenticate.
- **Ticket-scoped live view** — the noVNC bridge only connects to the host/port
  captured when an authenticated HTTP request issued the ticket; tickets are
  single-use and expire in 60 s.
- **Shell** — `run_command` is powerful by design. It runs only on `linux`
  containers or on a remote session with SSH configured, is bounded by a
  timeout, and is always recorded in the activity log. The browser profile and
  the computer profile instruct the model never to exfiltrate files or secrets.
- **KVM and licensing** — Windows/macOS VMs need hardware virtualization. macOS
  in a VM is only permitted on Apple hardware per Apple's EULA; prefer
  `kind="remote"` for a real Mac.
- **Not implemented yet** — clipboard sync over VNC (use SSH or the Linux
  agent), audio, multi-monitor, and file drag-and-drop inside VMs. Windows/macOS
  guests have no shell unless SSH is configured; use the GUI terminal there.
- **Live-view input detection** — Windows/macOS/remote viewer input is reported
  by the RFB bridge, so the AI yields automatically. The Linux Selkies and
  KasmVNC iframe views do not expose input events to the API: press
  **Take control** before driving a Linux/Kasmweb desktop manually, or the AI
  may keep acting.

## Tests

```bash
cd api
pytest tests/computer -q
```

The suite covers the session model/migration, docker commands per kind,
DES/VNC protocol (including a fake RFB server), OCR word matching and the
desktop runtime/control lease. An end-to-end smoke test with the real webtop
image is documented in the PR notes.
