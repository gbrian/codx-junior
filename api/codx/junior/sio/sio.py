import os
import logging
import socketio
import functools
import asyncio

from concurrent.futures import ThreadPoolExecutor

from codx.junior.sio.session_channel import SessionChannel
from codx.junior.engine import CODXJuniorSession

from codx.junior.context import (
    AICodeGenerator
)

from codx.junior.sio.model import (
    SioMessage,
    SioChatMessage,
    SioFileReadMessage,
    SioFileDiffMessage
)

from codx.junior.ai import AIManager
from codx.junior.security.user_management import get_authenticated_user_from_token

CODX_JUNIOR_API_BACKGROUND = os.environ.get("CODX_JUNIOR_API_BACKGROUND")

USERS = {}

logger = logging.getLogger(__name__)

#Socket io (sio) create a Socket.IO server
sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')

SIO_POOL = ThreadPoolExecutor(max_workers=10)

# Response events emitted when a long-running file operation (read / diff) finishes.
# Results are delivered as an event (correlated by request_id) because long
# operations run in the SIO_POOL and must not block the request path.
SIO_FILE_READ_RESPONSE_EVENT = "codx-junior-file-read-response"
SIO_FILE_DIFF_RESPONSE_EVENT = "codx-junior-file-diff-response"

# Message returned by the deprecated task-creation SIO events.
SUBTASKS_DEPRECATED_MESSAGE = (
    "Sub-task generation is deprecated and has been removed. Tasks are created "
    "explicitly, with all their information, through the 'create_task' or "
    "'project_manager' (action='create_task') tools or through "
    "POST /api/chats/tasks."
)

def sio_api_endpoint(func):
    """Decorator to process sio API requests."""
    @functools.wraps(func)
    async def wrapper(sid: str, data: dict):
        logger.info(f"SIO REquest {sid} {data}")
        base_data = SioMessage(**data)
        channel = SessionChannel(sio=sio, sid=sid)
        user = get_authenticated_user_from_token(USERS[sid]["user"]["token"])
        codxjunior_session = CODXJuniorSession(
                                channel=channel,
                                user=user,
                                codx_path=base_data.codx_path) if base_data.codx_path \
                                  else None # Global requests
        try:
            if not asyncio.iscoroutinefunction(func):
                return SIO_POOL.submit(func, sid, data, codxjunior_session).result
            else:
                def worker():
                    try:
                        return asyncio.run(func(sid, data, codxjunior_session))
                    except Exception as ex:
                        logger.exception(f"Error processing async sio message")
                    return None
                return SIO_POOL.submit(worker)
        except Exception as ex:
            logger.exception(f"Error processing sio message")
        return None
    return wrapper

async def sio_send_event(event, data):
    return await sio.emit(event, data)

def _sio_file_response(request_id: str = None, path: str = None,
                       result: dict = None, error: str = None) -> dict:
    """
    Build the payload of the file read / diff response events.

    File requests must *always* end with a response event: the handler runs in
    ``SIO_POOL``, so the Socket.IO acknowledgement is not used and clients wait
    for the response event (correlated by ``request_id``). A payload that cannot
    be processed must therefore answer with ``error`` instead of returning
    silently.

    Args:
        request_id: Id of the request being answered (echoed back).
        path: File path of the request.
        result: Operation result (read/diff) when it succeeded.
        error: Error message when it failed.

    Returns:
        Dict with ``request_id`` and ``path``, plus either ``result`` or ``error``.
    """
    response = {
        "request_id": request_id,
        "path": path,
    }
    if error:
        response["error"] = error
    else:
        response["result"] = result
    return response

@sio.on("error")
async def error():
    logger.error(f"Socket error")

@sio.on("connect")
async def connect(sid, env):
    logger.info("New Client Connected to This id :"+" "+str(sid))

@sio.on("disconnect")
async def disconnect(sid):
    logger.info("Client Disconnected: "+" "+str(sid))
    if USERS.get(sid):
        del USERS[sid]
    send_online_users(sid)  

def send_online_users(sid):
    channel = SessionChannel(sio=sio, sid=sid)
    online_users = [{
      "username": USERS[sid]["user"].get("username"),
      "avatar": USERS[sid]["user"].get("avatar"),
      "sid": sid
    } for sid in USERS.keys() if USERS.get("sid",{}).get("user")]
    channel.send_event('codx-junior-online-users', { "users": online_users })

@sio.on("codx-junior-ping")
async def io_ping(sid, data: dict = None):
    return True


@sio.on("background-event")
async def on_background_event(sid, data: dict):
    # logger.info(f"***************** On event bacground: {data}")
    event = data["event"]
    if event == "hello":
        return f"Hi! Is back: {CODX_JUNIOR_API_BACKGROUND}"
    await sio_send_event(data["event"], data["data"])

@sio.on("codx-junior-login")
def io_login(sid, data: dict):
    USERS[sid] = data
    send_online_users(sid)

@sio.on("codx-junior-chat")
@sio_api_endpoint
async def io_chat(sid, data: dict, codxjunior_session: CODXJuniorSession):
    data = SioChatMessage(**data)
    logger.info(f"codx-junior-chat {data.chat.name} {codxjunior_session.settings.project_name}")
    existing = codxjunior_session.get_chat_manager().find_by_id(data.chat.id)
    if getattr(existing, "external_source", None) == "dsh":
        codxjunior_session.event_manager.chat_event(
            chat=existing,
            message=(
                "This task mirrors a DSH session. Continue it in DSH or use "
                f"POST /api/dsh/tasks/{existing.external_id}/prompt."
            ),
        )
        return
    codxjunior_session.event_manager.chat_event(chat=data.chat, message="Chatting with project...")
    await codxjunior_session.chat_with_project(chat_id=data.chat.id, owner_project_id=data.chat.owner_project_id)

@sio.on("codx-junior-chat-search")
@sio_api_endpoint
async def io_chat_search(sid, msg_data: dict, codxjunior_session: CODXJuniorSession):
    data = SioChatMessage(**msg_data)
    logger.info(f"codx-junior-chat-search {data.chat.name} {codxjunior_session.settings.project_name}")
    codxjunior_session.event_manager.chat_event(chat=data.chat, message="Chat search...")
    chat_id = data.chat.id
    query = msg_data["query"]
    await codxjunior_session.chat_search(chat_id=chat_id, query=query)

@sio.on("codx-junior-subtasks")
@sio_api_endpoint
async def io_chat_subtasks(sid, data: dict, codxjunior_session: CODXJuniorSession):
    """
    DEPRECATED event — used to split a chat into sub-tasks with the AI.

    It no longer creates anything: it answers with a deprecation payload so
    older clients surface a clear message instead of failing silently.
    """
    logger.warning(
        "SIO 'codx-junior-subtasks' is deprecated: %s", SUBTASKS_DEPRECATED_MESSAGE
    )
    return {"error": SUBTASKS_DEPRECATED_MESSAGE, "deprecated": True}

@sio.on("codx-junior-improve")
@sio_api_endpoint
async def io_run_improve(sid, data: dict, codxjunior_session: CODXJuniorSession):
    data = SioChatMessage(**data)
    await codxjunior_session.improve_existing_code(chat=data.chat)

@sio.on("codx-junior-generate-tasks")
@sio_api_endpoint
async def io_create_chat_tasks(sid, data: dict, codxjunior_session: CODXJuniorSession):
    """
    DEPRECATED event — used to generate tasks from a chat with the AI.

    It no longer creates anything: it answers with a deprecation payload so
    older clients surface a clear message instead of failing silently.
    """
    logger.warning(
        "SIO 'codx-junior-generate-tasks' is deprecated: %s", SUBTASKS_DEPRECATED_MESSAGE
    )
    return {"error": SUBTASKS_DEPRECATED_MESSAGE, "deprecated": True}

@sio.on("codx-junior-improve-patch")
@sio_api_endpoint
async def sio_run_improve_patch(sid, data: dict, codxjunior_session: CODXJuniorSession):
    code_generator = AICodeGenerator(**data["code_generator"])
    data = SioChatMessage(**data)
    info, error = await codxjunior_session.improve_existing_code_patch(
                            chat=data.chat,
                            code_generator=code_generator)
    return {
        "info": info, 
        "error": error
    }

@sio.on("codx-junior-generate-code")
@sio_api_endpoint
async def sio_run_generate_code(sid, data: dict, codxjunior_session: CODXJuniorSession):
    code_block_info = data["code_block_info"]
    data = SioChatMessage(**data)
    await codxjunior_session.generate_code(
                            chat=data.chat,
                            code_block_info=code_block_info)

@sio.on("codx-junior-ai-load-model")
@sio_api_endpoint
async def sio_ai_load_model(sid, data: dict):
    AIManager().load_model(model=data["model"])

@sio.on("codx-junior-file-read")
@sio_api_endpoint
async def sio_file_read(sid: str, data: dict, codxjunior_session: CODXJuniorSession):
    """
    Read a project file through Socket.IO instead of the blocking
    ``GET /files/read`` HTTP endpoint.

    Large files or files on slow disks can block an HTTP worker; this event runs
    the read in the shared ``SIO_POOL`` and reports the result asynchronously,
    keeping the HTTP API responsive.

    Request payload (``data``):
        - codx_path (str): Project path used to build the session (required).
        - request_id (str): Optional id echoed back to correlate the response.
        - path (str): File path to read (relative to the project or absolute).

    Response (emitted on ``codx-junior-file-read-response``):
        - Success: { request_id, path, result: { content, is_binary, ... } }
        - Failure: { request_id, path, error: "<message>" }

        A response is **always** emitted, even when the payload cannot be parsed,
        because clients wait for it (the acknowledgement is not used). The same
        payload is returned for acknowledgement-based clients.
    """
    data = data if isinstance(data, dict) else {}
    channel = SessionChannel(sio=sio, sid=sid)
    request_id = data.get("request_id")
    path = data.get("path")

    try:
        message = SioFileReadMessage(**data)
        if not message.path:
            response = _sio_file_response(request_id, path,
                                          error="Missing 'path' parameter")
        elif not codxjunior_session:
            response = _sio_file_response(request_id, path,
                                          error="codx_path is required to read project files")
        else:
            result = codxjunior_session.get_file_engine().read_file(path=message.path)
            response = _sio_file_response(message.request_id, message.path, result=result)
    except Exception as ex:
        logger.exception("Error reading file over SIO: %s", path)
        response = _sio_file_response(request_id, path, error=str(ex))

    channel.send_event(SIO_FILE_READ_RESPONSE_EVENT, response)
    return response

@sio.on("codx-junior-file-diff")
@sio_api_endpoint
async def sio_file_diff(sid: str, data: dict, codxjunior_session: CODXJuniorSession):
    """
    Compute a file diff through Socket.IO instead of the blocking
    ``POST /files/diff`` HTTP endpoint.

    The provided content is streamed to ``git diff``; for large files this can
    block an HTTP worker, so this event runs it in the shared ``SIO_POOL`` and
    reports the result asynchronously.

    Request payload (``data``):
        - codx_path (str): Project path used to build the session (required).
        - request_id (str): Optional id echoed back to correlate the response.
        - path (str): File path to diff (relative to the project or absolute).
        - content (str): New content to diff the file against (``null`` = empty).
        - from_branch (str | null): Optional, reserved for branch comparisons.
        - to_branch (str | null): Optional, reserved for branch comparisons.

        The branch fields are nullable: clients sending ``from_branch: null`` /
        ``to_branch: null`` must be accepted.

    Response (emitted on ``codx-junior-file-diff-response``):
        - Success: { request_id, path, result: { diff, stats, ... } }
        - Failure: { request_id, path, error: "<message>" }

        A response is **always** emitted, even when the payload cannot be parsed,
        because clients wait for it (the acknowledgement is not used).
    """
    data = data if isinstance(data, dict) else {}
    channel = SessionChannel(sio=sio, sid=sid)
    request_id = data.get("request_id")
    path = data.get("path")

    try:
        message = SioFileDiffMessage(**data)
        if not message.path:
            response = _sio_file_response(request_id, path,
                                          error="Missing 'path' parameter")
        elif not codxjunior_session:
            response = _sio_file_response(request_id, path,
                                          error="codx_path is required to diff project files")
        elif message.content is None and "content" not in data:
            response = _sio_file_response(message.request_id, message.path,
                                          error="Missing 'content' parameter")
        else:
            result = codxjunior_session.get_file_engine().diff_file(
                path=message.path,
                content=message.content or "",
                from_branch=message.from_branch,
                to_branch=message.to_branch,
            )
            response = _sio_file_response(message.request_id, message.path, result=result)
    except Exception as ex:
        logger.exception("Error diffing file over SIO: %s", path)
        response = _sio_file_response(request_id, path, error=str(ex))

    channel.send_event(SIO_FILE_DIFF_RESPONSE_EVENT, response)
    return response