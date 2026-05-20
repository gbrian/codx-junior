import os
import logging
import socketio
import functools
import asyncio
import time

from concurrent.futures import ThreadPoolExecutor

from codx.junior.sio.session_channel import SessionChannel
from codx.junior.engine import CODXJuniorSession

from codx.junior.context import (
    AICodeGenerator
)

from codx.junior.sio.model import (
    SioMessage,
    SioChatMessage
)

from codx.junior.ai import AIManager
from codx.junior.security.user_management import get_authenticated_user_from_token

CODX_JUNIOR_API_BACKGROUND = os.environ.get("CODX_JUNIOR_API_BACKGROUND")

USERS = {}

logger = logging.getLogger(__name__)

# Socket io (sio) create a Socket.IO server
sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')

SIO_POOL = ThreadPoolExecutor(max_workers=10)


def _log_request_start(event_name: str, sid: str) -> float:
    """Log the start of an SIO request and return the start time."""
    start_time = time.monotonic()
    logger.info("SIO request started | event=%s | sid=%s", event_name, sid)
    return start_time


def _log_request_end(
    event_name: str,
    sid: str,
    start_time: float,
    error: Exception = None
) -> None:
    """Log the end of an SIO request with elapsed time and optional error."""
    elapsed_ms = (time.monotonic() - start_time) * 1000
    if error:
        logger.error(
            "SIO request failed | event=%s | sid=%s | elapsed_ms=%.2f | error=%s",
            event_name, sid, elapsed_ms, error
        )
    else:
        logger.info(
            "SIO request completed | event=%s | sid=%s | elapsed_ms=%.2f",
            event_name, sid, elapsed_ms
        )


def _build_session(
    sid: str,
    base_data: SioMessage,
    channel: "SessionChannel"
) -> "CODXJuniorSession | None":
    """
    Build a CODXJuniorSession from the SIO message data.

    Returns None for global (non-project) requests where codx_path is absent.
    """
    if not base_data.codx_path:
        logger.debug(
            "No codx_path provided, building global session | sid=%s", sid
        )
        return None

    user = get_authenticated_user_from_token(USERS[sid]["user"]["token"])
    return CODXJuniorSession(
        channel=channel,
        user=user,
        codx_path=base_data.codx_path
    )


def sio_api_endpoint(func):
    """
    Decorator to process sio API requests.

    Wraps each Socket.IO event handler with:
    - Session and user context setup
    - Request timing
    - Structured start/end/error logging
    - Proper async/sync dispatch

    Diagram::

        sequenceDiagram
            participant SIO as Socket.IO
            participant W as Wrapper
            participant H as Handler
            SIO->>W: event(sid, data)
            W->>W: parse SioMessage, build session
            alt async handler
                W->>H: await func(sid, data, session)
            else sync handler
                W->>ThreadPool: submit func(...)
                W->>W: await loop.run_in_executor
            end
            W-->>SIO: result
    """
    @functools.wraps(func)
    async def wrapper(sid: str, data: dict):
        event_name = func.__name__
        start_time = _log_request_start(event_name, sid)

        try:
            base_data = SioMessage(**data)
            channel = SessionChannel(sio=sio, sid=sid)
            codxjunior_session = _build_session(sid, base_data, channel)

            if asyncio.iscoroutinefunction(func):
                # Async handlers: await directly — no thread pool needed.
                result = await func(sid, data, codxjunior_session)
                _log_request_end(event_name, sid, start_time)
                return result

            # Sync handlers: offload to thread pool to avoid blocking the event loop.
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                SIO_POOL,
                functools.partial(func, sid, data, codxjunior_session)
            )
            _log_request_end(event_name, sid, start_time)
            return result

        except (ValueError, KeyError, RuntimeError, TypeError) as ex:
            _log_request_end(event_name, sid, start_time, error=ex)
            logger.exception(
                "SIO request handler error | event=%s | sid=%s | error=%s",
                event_name, sid, ex
            )
        return None

    return wrapper


async def sio_send_event(event: str, data: dict) -> None:
    """Broadcast an event to all connected clients."""
    return await sio.emit(event, data)


@sio.on("error")
async def error() -> None:
    """Handle Socket.IO error events."""
    logger.error("Socket error received")


@sio.on("connect")
async def connect(sid: str, env: dict) -> None:
    """Handle new client connections."""
    logger.info("New client connected | sid=%s", sid)


@sio.on("disconnect")
async def disconnect(sid: str) -> None:
    """Handle client disconnections and clean up user session."""
    logger.info("Client disconnected | sid=%s", sid)
    if USERS.get(sid):
        del USERS[sid]
    send_online_users(sid)


def send_online_users(sid: str) -> None:
    """Broadcast the current list of online users to all clients."""
    channel = SessionChannel(sio=sio, sid=sid)
    online_users = [
        {
            "username": USERS[uid]["user"].get("username"),
            "avatar": USERS[uid]["user"].get("avatar"),
            "sid": uid
        }
        for uid in USERS.keys()
        if USERS.get(uid, {}).get("user")
    ]
    channel.send_event('codx-junior-online-users', {"users": online_users})


@sio.on("codx-junior-ping")
async def io_ping(sid: str, data: dict = None) -> bool:
    """Respond to ping events to verify connectivity."""
    return True


@sio.on("background-event")
async def on_background_event(sid: str, data: dict) -> None:
    """
    Handle background events forwarded from the background worker.

    Special 'hello' event returns a greeting; all others are re-emitted.
    """
    event = data["event"]
    if event == "hello":
        return f"Hi! Is back: {CODX_JUNIOR_API_BACKGROUND}"
    await sio_send_event(data["event"], data["data"])


@sio.on("codx-junior-login")
def io_login(sid: str, data: dict) -> None:
    """Register a user session on login."""
    USERS[sid] = data
    send_online_users(sid)


@sio.on("codx-junior-chat")
@sio_api_endpoint
async def io_chat(sid: str, data: dict, codxjunior_session: CODXJuniorSession) -> None:
    """Handle chat messages directed at the project AI assistant."""
    chat_data = SioChatMessage(**data)
    logger.info(
        "codx-junior-chat | chat=%s | project=%s",
        chat_data.chat.name, codxjunior_session.settings.project_name
    )
    codxjunior_session.event_manager.chat_event(
        chat=chat_data.chat, message="Chatting with project..."
    )
    await codxjunior_session.chat_with_project(chat=chat_data.chat)


@sio.on("codx-junior-chat-search")
@sio_api_endpoint
async def io_chat_search(
    sid: str,
    msg_data: dict,
    codxjunior_session: CODXJuniorSession
) -> None:
    """Handle chat search requests within a project."""
    chat_data = SioChatMessage(**msg_data)
    query = msg_data["query"]
    logger.info(
        "codx-junior-chat-search | chat=%s | project=%s | query=%s",
        chat_data.chat.name, codxjunior_session.settings.project_name, query
    )
    codxjunior_session.event_manager.chat_event(chat=chat_data.chat, message="Chat search...")
    await codxjunior_session.chat_search(chat_id=chat_data.chat.id, query=query)


@sio.on("codx-junior-subtasks")
@sio_api_endpoint
async def io_chat_subtasks(
    sid: str,
    data: dict,
    codxjunior_session: CODXJuniorSession
) -> None:
    """Generate subtasks from a given chat and optional instructions."""
    sio_chat = SioChatMessage(**data)
    instructions = data.get("instructions")
    logger.info("codx-junior-subtasks | chat_id=%s", sio_chat.chat.id)
    return await codxjunior_session.generate_tasks(
        chat=sio_chat.chat,
        instructions=instructions
    )


@sio.on("codx-junior-improve")
@sio_api_endpoint
async def io_run_improve(
    sid: str,
    data: dict,
    codxjunior_session: CODXJuniorSession
) -> None:
    """Trigger improvement of existing code based on chat context."""
    chat_data = SioChatMessage(**data)
    await codxjunior_session.improve_existing_code(chat=chat_data.chat)


@sio.on("codx-junior-generate-tasks")
@sio_api_endpoint
async def io_create_chat_tasks(
    sid: str,
    data: dict,
    codxjunior_session: CODXJuniorSession
) -> None:
    """Generate tasks from a chat conversation."""
    chat_data = SioChatMessage(**data)
    await codxjunior_session.generate_tasks(chat=chat_data.chat)


@sio.on("codx-junior-improve-patch")
@sio_api_endpoint
async def sio_run_improve_patch(
    sid: str,
    data: dict,
    codxjunior_session: CODXJuniorSession
) -> dict:
    """Apply an improvement patch to existing code and return result info."""
    code_generator = AICodeGenerator(**data["code_generator"])
    chat_data = SioChatMessage(**data)
    info, error = await codxjunior_session.improve_existing_code_patch(
        chat=chat_data.chat,
        code_generator=code_generator
    )
    return {
        "info": info,
        "error": error
    }


@sio.on("codx-junior-generate-code")
@sio_api_endpoint
async def sio_run_generate_code(
    sid: str,
    data: dict,
    codxjunior_session: CODXJuniorSession
) -> None:
    """Generate code for a specific code block within a chat context."""
    code_block_info = data["code_block_info"]
    chat_data = SioChatMessage(**data)
    await codxjunior_session.generate_code(
        chat=chat_data.chat,
        code_block_info=code_block_info
    )


@sio.on("codx-junior-ai-load-model")
@sio_api_endpoint
async def sio_ai_load_model(sid: str, data: dict, codxjunior_session: CODXJuniorSession) -> None:
    """Load a specific AI model via the AIManager."""
    AIManager().load_model(model=data["model"])

# Made with ❤️ by codx-junior