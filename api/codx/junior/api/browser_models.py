"""
Pydantic models for browser session API requests/responses.

Defines request payloads and response schemas for REST endpoints and the
Socket.IO request/event models used by the long-running browser lifecycle
operations (create / stop / restart / delete).
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class BrowserSharedFolder(BaseModel):
    """One project folder mounted inside the browser container."""

    id: Optional[str] = Field(default=None, description="Immutable share identifier")
    name: Optional[str] = Field(default=None, description="Human-readable label")
    folder: Optional[str] = Field(default=None, description="Project-relative folder ('' = project root)")
    host_path: str = Field(description="Host folder bind mounted into the container")
    mount_path: str = Field(description="Container path of the folder (e.g. /home/proj/docs)")
    readonly: bool = Field(default=False, description="Whether the folder is mounted read-only")


class BrowserSessionResponse(BaseModel):
    """Response model for a browser session."""

    id: str = Field(description="Unique session identifier")
    name: Optional[str] = Field(default=None, description="Human-readable session name")
    description: Optional[str] = Field(default=None, description="Optional session description")
    chat_ids: List[str] = Field(default_factory=list, description="Chat IDs connected to this session")
    container_id: Optional[str] = Field(default=None, description="Docker container ID")
    container_name: Optional[str] = Field(default=None, description="Container name")
    status: str = Field(description="Session status: idle, running, stopped, error")
    kind: str = Field(default="browser", description="Session kind: browser, linux, macos, windows, remote")
    control: Optional[str] = Field(default=None, description="AI control channel: cdp, docker, vnc, ssh")
    engine: str = Field(default="chromium", description="Engine: chromium, desktop or remote")
    os_version: Optional[str] = Field(default=None, description="OS release/version label")
    image: Optional[str] = Field(default=None, description="Docker image running the session")
    image_provider: Optional[str] = Field(default=None, description="linuxserver, kasmweb, dockurr or custom")
    library_item_id: Optional[str] = Field(default=None, description="Saved computer library item used at creation")
    library_item_name: Optional[str] = Field(default=None, description="Saved computer name")
    live_view: Optional[str] = Field(default=None, description="selkies, kasmvnc, vnc or screenshot")
    live_scheme: Optional[str] = Field(default=None, description="http or https")
    live_port: Optional[int] = Field(default=None, description="Container port of the live view")
    strip_prefix: bool = Field(default=False, description="Whether the visible path prefix is stripped")
    viewer_user: Optional[str] = Field(default=None, description="Live-view login user (KasmVNC)")
    cpu_cores: Optional[int] = Field(default=None, description="vCPUs configured for the machine")
    ram_size: Optional[str] = Field(default=None, description="RAM configured for the machine (e.g. 8G)")
    disk_size: Optional[str] = Field(default=None, description="VM disk size (e.g. 64G)")
    shm_size: Optional[str] = Field(default=None, description="Shared memory of browser/Linux containers")
    extra_env: Dict[str, str] = Field(default_factory=dict, description="Extra image environment variables")
    vnc_url: Optional[str] = Field(default=None, description="Live view (VNC/Selkies) URL via Traefik")
    vnc_path: Optional[str] = Field(default=None, description="Same-origin live view path")
    vnc_public_url: Optional[str] = Field(default=None, description="Viewer URL supplied by the user")
    vnc_public_port: Optional[int] = Field(default=None, description="Host port published for a VNC client")
    debug_url: Optional[str] = Field(default=None, description="DevTools/CDP WebSocket URL")
    browser_profile_path: Optional[str] = Field(default=None, description="Persistent browser/desktop profile path")
    profile_path: Optional[str] = Field(default=None, description="Generic profile path alias")
    display: Optional[str] = Field(default=None, description="X11 display for Linux desktops")
    desktop_width: int = Field(default=1920, description="Desktop width in pixels")
    desktop_height: int = Field(default=1080, description="Desktop height in pixels")
    vnc_host: Optional[str] = Field(default=None, description="Host of the AI VNC connection")
    vnc_port: int = Field(default=5900, description="VNC/RFB port")
    ssh_host: Optional[str] = Field(default=None, description="SSH host configured for shell access")
    ssh_port: int = Field(default=22, description="SSH port")
    ssh_user: Optional[str] = Field(default=None, description="SSH username")
    guest_share_path: Optional[str] = Field(default=None, description="Where the shared folder appears inside the VM")
    capabilities: List[str] = Field(default_factory=list, description="Supported actions")
    project_name: Optional[str] = Field(default=None, description="Project name used for the container home folder")
    home_path: Optional[str] = Field(default=None, description="Container folder holding the project folders")
    shared_folders: List[BrowserSharedFolder] = Field(
        default_factory=list, description="Project folders mounted in the container"
    )
    downloads_path: Optional[str] = Field(
        default=None, description="Host folder receiving the browser downloads"
    )
    downloads_folder: Optional[str] = Field(
        default=None, description="Project-relative folder receiving the downloads"
    )
    downloads_mount: Optional[str] = Field(
        default=None, description="Container path where the downloads are written"
    )
    downloads_own_mount: bool = Field(
        default=True, description="Whether the downloads folder has its own bind mount"
    )
    current_url: Optional[str] = Field(default=None, description="Currently loaded page URL")
    current_title: Optional[str] = Field(default=None, description="Currently loaded page title")
    last_action: Optional[str] = Field(default=None, description="Last user/AI action")
    last_action_at: Optional[str] = Field(default=None, description="Timestamp of the last action")
    controller: str = Field(default="ai", description="Who may drive: ai, user or none")
    controller_chat_id: Optional[str] = Field(default=None, description="Chat owning the control lease")
    user_active_until: Optional[str] = Field(default=None, description="Recent user input keeps the AI paused until")
    handoff_reason: Optional[str] = Field(default=None, description="Why the AI handed control to the user")
    last_user_event_at: Optional[str] = Field(default=None, description="Last real user interaction captured in the page")
    created_at: str = Field(description="ISO timestamp when created")
    last_active: str = Field(description="ISO timestamp of last activity")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    traefik_domain: Optional[str] = Field(default=None, description="Traefik domain")
    traefik_path_prefix: Optional[str] = Field(default=None, description="Traefik path prefix")


class BrowserSessionListResponse(BaseModel):
    """Response model for listing browser sessions."""

    count: int = Field(description="Total number of sessions")
    sessions: List[BrowserSessionResponse] = Field(description="List of sessions")


class BrowserSessionCreateRequest(BaseModel):
    """Request model to create a new browser session."""

    name: str = Field(description="Human-readable session name")
    description: Optional[str] = Field(default=None, description="Optional session description")
    chat_id: Optional[str] = Field(default=None, description="Optional chat ID to connect the session to")
    initial_url: Optional[str] = Field(default=None, description="Optional URL opened at startup")
    share_project: Optional[bool] = Field(
        default=None,
        description=(
            "Mount the whole project at /home/<project_name>. Omit it to mount "
            "the project root only when share_folders is empty."
        ),
    )
    share_folders: Optional[List[Any]] = Field(
        default=None,
        description=(
            "Project folders to mount under /home/<project_name>/<folder>. Each "
            "entry is a relative path ('docs', 'docs/api') or an object with "
            "folder, name, mount_path and readonly."
        ),
    )
    readonly: Optional[bool] = Field(default=None, description="Mount the listed folders read-only")
    downloads_folder: Optional[str] = Field(
        default=None,
        description="Project-relative folder receiving the downloads (.codx/browser_downloads/<id> by default)",
    )
    downloads_mount: Optional[str] = Field(
        default=None,
        description="Container path forcing a dedicated downloads mount (e.g. /downloads)",
    )
    kind: str = Field(
        default="browser",
        description="browser, linux, macos, windows or remote (aliases: mac, win, ubuntu)",
    )
    os_version: Optional[str] = Field(
        default=None, description="OS release for VM images (Windows '11', macOS '15')"
    )
    image: Optional[str] = Field(default=None, description="Docker image override")
    image_provider: Optional[str] = Field(
        default=None,
        description="Image provider: linuxserver, kasmweb or custom (inferred when omitted)",
    )
    library_item_id: Optional[str] = Field(
        default=None,
        description="Start from a saved computer in the project library",
    )
    cpu_cores: Optional[int] = Field(
        default=None, ge=1, le=128, description="vCPUs for the machine (advanced settings)"
    )
    ram_size: Optional[str] = Field(
        default=None, description="RAM for the machine, e.g. '8G' (advanced settings)"
    )
    disk_size: Optional[str] = Field(
        default=None, description="Disk size for a Windows/macOS VM image, e.g. '64G'"
    )
    shm_size: Optional[str] = Field(
        default=None, description="Docker shared memory for browser/Linux containers, e.g. '2G'"
    )
    extra_env: Optional[Dict[str, str]] = Field(
        default=None,
        description="Extra environment variables passed to the image (advanced settings)",
    )
    desktop_width: Optional[int] = Field(
        default=None, ge=640, le=7680, description="Desktop/browser width in pixels"
    )
    desktop_height: Optional[int] = Field(
        default=None, ge=480, le=4320, description="Desktop/browser height in pixels"
    )
    control: Optional[str] = Field(
        default=None, description="Force the control channel (cdp, docker, vnc)"
    )
    vnc_host: Optional[str] = Field(
        default=None, description="Remote VNC host (kind=remote; inferred for VMs)"
    )
    vnc_port: Optional[int] = Field(default=5900, description="Remote VNC port")
    vnc_password: Optional[str] = Field(default=None, description="Remote VNC password")
    vnc_public_url: Optional[str] = Field(
        default=None, description="Viewer URL supplied by the user (noVNC, etc.)"
    )
    ssh_host: Optional[str] = Field(default=None, description="SSH host for shell access")
    ssh_port: Optional[int] = Field(default=22, description="SSH port")
    ssh_user: Optional[str] = Field(default=None, description="SSH username")
    ssh_key_path: Optional[str] = Field(default=None, description="Host path of the SSH private key")
    ssh_password: Optional[str] = Field(default=None, description="SSH password (alternative to a key)")
    guest_share_path: Optional[str] = Field(
        default=None, description="Where the shared folder appears in the VM guest"
    )


class BrowserSessionUpdateRequest(BaseModel):
    """Request model to update a computer session (rename + connection fields)."""

    name: Optional[str] = Field(default=None, description="New human-readable session name")
    description: Optional[str] = Field(default=None, description="New description")
    control: Optional[str] = Field(default=None, description="Control channel override")
    vnc_host: Optional[str] = Field(default=None, description="VNC host")
    vnc_port: Optional[int] = Field(default=None, description="VNC port")
    vnc_password: Optional[str] = Field(default=None, description="VNC password ('' clears it)")
    vnc_public_url: Optional[str] = Field(default=None, description="Viewer URL supplied by the user")
    ssh_host: Optional[str] = Field(default=None, description="SSH host")
    ssh_port: Optional[int] = Field(default=None, description="SSH port")
    ssh_user: Optional[str] = Field(default=None, description="SSH user")
    ssh_key_path: Optional[str] = Field(default=None, description="SSH private key path")
    ssh_password: Optional[str] = Field(default=None, description="SSH password ('' clears it)")
    # Advanced container/VM settings. Omitted fields are left unchanged; send
    # "" / null / {} to clear a value. They apply on restart (container recreated).
    image: Optional[str] = Field(default=None, description="Docker image override ('' resets to default)")
    cpu_cores: Optional[int] = Field(
        default=None, ge=1, le=128, description="vCPUs for the machine"
    )
    ram_size: Optional[str] = Field(default=None, description="RAM for the machine, e.g. '8G'")
    disk_size: Optional[str] = Field(
        default=None, description="VM disk size, e.g. '128G' (growing requires a restart)"
    )
    shm_size: Optional[str] = Field(
        default=None, description="Docker shared memory for browser/Linux containers"
    )
    extra_env: Optional[Dict[str, str]] = Field(
        default=None, description="Extra environment variables passed to the image"
    )
    desktop_width: Optional[int] = Field(
        default=None, ge=640, le=7680, description="Desktop/browser width in pixels"
    )
    desktop_height: Optional[int] = Field(
        default=None, ge=480, le=4320, description="Desktop/browser height in pixels"
    )


class BrowserSessionChatRequest(BaseModel):
    """Optional chat selection when opening a chat from a browser session."""

    chat_id: Optional[str] = Field(
        default=None,
        description="Existing chat to link. Omit to reuse/create the session's chat.",
    )
    create_new: bool = Field(
        default=False,
        description=(
            "When true, always create a new chat even if the session already "
            "has linked chats. Ignored when chat_id is provided."
        ),
    )


class BrowserSessionChatResponse(BaseModel):
    """Chat linked to a browser session, ready to be rendered in the UI."""

    session: BrowserSessionResponse
    chat: Dict[str, Any]


class BrowserSessionActionRequest(BaseModel):
    """Request model for browser actions (navigate, click, fill, execute...)."""

    action: str = Field(
        description=(
            "Action type: navigate, click, fill, execute, text, links, snapshot, "
            "back, forward, refresh, wait, press, select, hover, scroll, "
            "screenshot, batch"
        )
    )
    selector: Optional[str] = Field(default=None, description="CSS selector (click/fill/wait/press/select/hover)")
    ref: Optional[str] = Field(default=None, description="Element ref from snapshot (preferred over selector)")
    text: Optional[str] = Field(default=None, description="Visible text to click/wait for")
    value: Optional[str] = Field(default=None, description="Value to fill/select")
    url: Optional[str] = Field(default=None, description="URL to navigate to")
    script: Optional[str] = Field(default=None, description="JavaScript to execute")
    key: Optional[str] = Field(default=None, description="Keyboard key for press")
    timeout: Optional[int] = Field(default=5000, description="Timeout in milliseconds (wait)")
    x: Optional[int] = Field(default=0, description="Horizontal scroll offset")
    y: Optional[int] = Field(default=0, description="Vertical scroll offset")
    full_page: Optional[bool] = Field(default=True, description="Capture the full page (screenshot)")
    steps: Optional[List[Dict[str, Any]]] = Field(default=None, description="Ordered steps for action='batch'")
    variables: Optional[Dict[str, Any]] = Field(default=None, description="Values for {{name}} placeholders")


class ComputerSessionActionRequest(BaseModel):
    """Request model for desktop actions (mouse, keyboard, OCR, shell...)."""

    action: str = Field(
        description=(
            "Action: screenshot, ocr, click, double_click, right_click, click_text, "
            "move, drag, scroll, type, key, hotkey, wait, windows, active_window, "
            "focus_window, close_window, open_app, list_apps, run_command, "
            "clipboard_get, clipboard_set, screen_size, batch"
        )
    )
    # Browser page actions (kind=browser)
    url: Optional[str] = Field(default=None, description="Target URL for navigate")
    selector: Optional[str] = Field(default=None, description="CSS selector for page actions")
    ref: Optional[str] = Field(default=None, description="Element ref from a browser snapshot")
    value: Optional[str] = Field(default=None, description="Value to fill/select")
    script: Optional[str] = Field(default=None, description="JavaScript to execute")
    full_page: Optional[bool] = Field(default=True, description="Full-page browser screenshot")
    x: Optional[int] = Field(default=None, description="X coordinate (display pixels)")
    y: Optional[int] = Field(default=None, description="Y coordinate (display pixels)")
    x2: Optional[int] = Field(default=None, description="Drag end X")
    y2: Optional[int] = Field(default=None, description="Drag end Y")
    from_x: Optional[int] = Field(default=None, description="Drag start X")
    from_y: Optional[int] = Field(default=None, description="Drag start Y")
    to_x: Optional[int] = Field(default=None, description="Drag end X")
    to_y: Optional[int] = Field(default=None, description="Drag end Y")
    text: Optional[str] = Field(default=None, description="Text to type or click (click_text)")
    key: Optional[str] = Field(default=None, description="Key or combo for key/hotkey")
    combo: Optional[str] = Field(default=None, description="Key combo (ctrl+shift+t)")
    button: Optional[str] = Field(default="left", description="Mouse button: left, middle, right")
    clicks: Optional[int] = Field(default=1, description="Click count (1-3)")
    amount: Optional[int] = Field(default=3, description="Scroll wheel steps")
    direction: Optional[str] = Field(default="down", description="Scroll direction: up, down")
    seconds: Optional[float] = Field(default=1, description="Seconds to wait")
    command: Optional[str] = Field(default=None, description="Shell command (run_command)")
    app: Optional[str] = Field(default=None, description="Application to launch (open_app)")
    window_id: Optional[str] = Field(default=None, description="Window id for focus/close")
    title: Optional[str] = Field(default=None, description="Window title to find")
    timeout: Optional[float] = Field(default=60, description="Command timeout in seconds")
    include_text: Optional[bool] = Field(default=True, description="Run OCR on screenshots")
    max_width: Optional[int] = Field(default=1600, description="Max width of the returned screenshot")
    index: Optional[int] = Field(default=0, description="Match index for click_text")
    double: Optional[bool] = Field(default=False, description="Double click for click_text")
    steps: Optional[List[Dict[str, Any]]] = Field(default=None, description="Steps for batch")
    variables: Optional[Dict[str, Any]] = Field(default=None, description="Values for batch placeholders")


class ComputerScreenshotRequest(BaseModel):
    """Options for a desktop screenshot (browser screenshots use full_page)."""

    include_text: bool = Field(default=True, description="Run OCR and return text/words")
    max_width: int = Field(default=1600, description="Maximum width of the returned image")


class ComputerVncTicketResponse(BaseModel):
    """One-time ticket for the noVNC WebSocket bridge."""

    session_id: str
    socket_path: str = Field(description="Relative WebSocket path (includes the ticket)")
    password: Optional[str] = Field(default=None, description="VNC password for the viewer (this session only)")
    expires_in: int


class BrowserActionResponse(BaseModel):
    """Response model for browser actions."""

    success: bool = Field(description="Whether action succeeded")
    message: str = Field(description="Action result message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Action-specific data")


class BrowserControlRequest(BaseModel):
    """Move the human/AI control lease of a browser session."""

    action: str = Field(
        description="take_control/take, give_back/release, pause, resume, handoff, status"
    )
    chat_id: Optional[str] = Field(default=None, description="Chat requesting/owning the lease")
    reason: Optional[str] = Field(default=None, description="Why the AI hands control to the user")


class BrowserControlResponse(BaseModel):
    """Result of a control operation."""

    success: bool = True
    message: str
    session: BrowserSessionResponse


class BrowserScreenshotRequest(BaseModel):
    """Request model for a screenshot (all fields optional)."""

    full_page: bool = Field(default=True, description="Capture the whole scrollable page")


class BrowserScreenshotResponse(BaseModel):
    """Response model for screenshot."""

    success: bool = Field(description="Whether screenshot succeeded")
    screenshot: Optional[str] = Field(default=None, description="Base64-encoded PNG data URI")
    data: Optional[Dict[str, Any]] = Field(default=None, description="OCR text/words and dimensions")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class BrowserSourceResponse(BaseModel):
    """Response model for page source."""

    success: bool = Field(description="Whether retrieval succeeded")
    html: Optional[str] = Field(default=None, description="HTML content (truncated)")
    url: Optional[str] = Field(default=None, description="Current page URL")
    title: Optional[str] = Field(default=None, description="Current page title")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class BrowserSharedFile(BaseModel):
    """One file the browser session saved inside the project."""

    name: str = Field(description="File name")
    relative_path: str = Field(description="Path relative to the session downloads folder")
    path: str = Field(description="Project-relative path (absolute when outside the project)")
    container_path: str = Field(description="Path of the file inside the browser container")
    size: int = Field(description="File size in bytes")
    modified_at: str = Field(description="ISO timestamp of the last modification")


class BrowserSharedFilesResponse(BaseModel):
    """Project folder mapping and files shared with a browser session."""

    session_id: str = Field(description="Session ID")
    project_name: Optional[str] = Field(default=None, description="Project name")
    home_path: Optional[str] = Field(default=None, description="Container folder holding the project folders")
    folders: List[BrowserSharedFolder] = Field(
        default_factory=list, description="Project folders mounted in the container"
    )
    downloads_path: Optional[str] = Field(default=None, description="Host downloads folder")
    downloads_folder: Optional[str] = Field(default=None, description="Project-relative downloads folder")
    downloads_mount: Optional[str] = Field(default=None, description="Container downloads path")
    downloads_own_mount: bool = Field(default=True, description="Whether the downloads folder has its own bind")
    count: int = Field(default=0, description="Number of files returned")
    files: List[BrowserSharedFile] = Field(default_factory=list, description="Downloaded files")


class BrowserActivityEntry(BaseModel):
    """One user/AI action recorded in the session audit trail."""

    ts: str
    session_id: Optional[str] = None
    chat_id: Optional[str] = None
    actor: str
    action: str
    success: bool = True
    params: Dict[str, Any] = Field(default_factory=dict)
    url: Optional[str] = None
    title: Optional[str] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    result: Optional[str] = None


class BrowserActivityResponse(BaseModel):
    """Response model for the browser activity audit trail."""

    session_id: str
    count: int
    activity: List[BrowserActivityEntry] = Field(default_factory=list)


class BrowserCostResponse(BaseModel):
    """AI cost/usage summary for the chats connected to a browser session."""

    session_id: str
    chats: List[Dict[str, Any]] = Field(default_factory=list)
    total_cost_cxjcoins: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_llm_calls: int = 0
    total_tool_calls: int = 0
    window: str = "all-time"


# ============================================================================
# Socket.IO Browser Session Models
# ============================================================================

class SioBrowserCreateRequest(BaseModel):
    """Socket.IO request model to create a new browser session."""

    codx_path: str = Field(description="Project codx path")
    name: str = Field(description="Human-readable session name")
    description: Optional[str] = Field(default=None, description="Optional session description")
    initial_url: Optional[str] = Field(default=None, description="Optional URL opened at startup")
    kind: str = Field(default="browser", description="browser, linux, macos, windows or remote")
    os_version: Optional[str] = Field(default=None, description="OS release for VM images")
    image: Optional[str] = Field(default=None, description="Docker image override")
    image_provider: Optional[str] = Field(
        default=None,
        description="Image provider: linuxserver, kasmweb or custom (inferred when omitted)",
    )
    library_item_id: Optional[str] = Field(
        default=None,
        description="Start from a saved computer in the project library",
    )
    cpu_cores: Optional[int] = Field(
        default=None, ge=1, le=128, description="vCPUs for the machine (advanced settings)"
    )
    ram_size: Optional[str] = Field(
        default=None, description="RAM for the machine, e.g. '8G' (advanced settings)"
    )
    disk_size: Optional[str] = Field(
        default=None, description="Disk size for a Windows/macOS VM image, e.g. '64G'"
    )
    shm_size: Optional[str] = Field(
        default=None, description="Docker shared memory for browser/Linux containers, e.g. '2G'"
    )
    extra_env: Optional[Dict[str, str]] = Field(
        default=None,
        description="Extra environment variables passed to the image (advanced settings)",
    )
    desktop_width: Optional[int] = Field(
        default=None, ge=640, le=7680, description="Desktop/browser width in pixels"
    )
    desktop_height: Optional[int] = Field(
        default=None, ge=480, le=4320, description="Desktop/browser height in pixels"
    )
    control: Optional[str] = Field(default=None, description="Force the control channel")
    vnc_host: Optional[str] = Field(default=None, description="Remote VNC host")
    vnc_port: Optional[int] = Field(default=5900, description="Remote VNC port")
    vnc_password: Optional[str] = Field(default=None, description="Remote VNC password")
    ssh_host: Optional[str] = Field(default=None, description="SSH host")
    ssh_port: Optional[int] = Field(default=22, description="SSH port")
    ssh_user: Optional[str] = Field(default=None, description="SSH user")
    ssh_key_path: Optional[str] = Field(default=None, description="SSH private key path")
    ssh_password: Optional[str] = Field(default=None, description="SSH password")
    chat_id: Optional[str] = Field(default=None, description="Optional chat ID to connect the session to")
    share_project: Optional[bool] = Field(
        default=None,
        description="Mount the whole project at /home/<project_name> (None uses the default)",
    )
    share_folders: Optional[List[Any]] = Field(
        default=None,
        description="Project folders to mount under /home/<project_name>/<folder>",
    )
    readonly: Optional[bool] = Field(default=None, description="Mount the listed folders read-only")
    downloads_folder: Optional[str] = Field(
        default=None, description="Project-relative folder receiving the downloads"
    )
    downloads_mount: Optional[str] = Field(
        default=None, description="Container path forcing a dedicated downloads mount"
    )


class SioBrowserDeleteRequest(BaseModel):
    """Socket.IO request model to delete a browser session."""

    codx_path: str = Field(description="Project codx path")
    session_id: str = Field(description="Session ID to delete")


class SioBrowserRestartRequest(BaseModel):
    """Socket.IO request model to restart a browser session."""

    codx_path: str = Field(description="Project codx path")
    session_id: str = Field(description="Session ID to restart")


class SioBrowserStopRequest(BaseModel):
    """Socket.IO request model to stop a browser session."""

    codx_path: str = Field(description="Project codx path")
    session_id: str = Field(description="Session ID to stop")


class BrowserStatusEvent(BaseModel):
    """Socket.IO event model for browser session status updates."""

    status: str = Field(
        description=(
            "Operation status: starting, created, starting_container, ready, "
            "restarting, stopping, stopped, deleted, error"
        )
    )
    session_id: Optional[str] = Field(default=None, description="Session ID")
    name: Optional[str] = Field(default=None, description="Human-readable session name")
    description: Optional[str] = Field(default=None, description="Optional session description")
    chat_ids: List[str] = Field(default_factory=list, description="Chats connected to the session")
    container_id: Optional[str] = Field(default=None, description="Docker container ID")
    message: str = Field(description="Human-readable status message")
    error: Optional[str] = Field(default=None, description="Error message if status is error")
    session: Optional[BrowserSessionResponse] = Field(
        default=None, description="Full session details (included in ready status)"
    )
    ts: Optional[int] = Field(default=None, description="Timestamp of event")

# Made with ❤️ by codx-junior

class ComputerViewerCredentialsResponse(BaseModel):
    """Live-view login credentials for the built-in desktop viewer."""

    session_id: str
    live_view: str
    user: Optional[str] = None
    password: Optional[str] = None
    note: Optional[str] = None
