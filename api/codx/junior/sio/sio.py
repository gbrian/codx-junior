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
    SioChatMessage
)

from codx.junior.ai import AIManager
from codx.junior.security.user_management import get_authenticated_user_from_token

CODX_JUNIOR_API_BACKGROUND = os.environ.get("CODX_JUNIOR_API_BACKGROUND")

USERS = {}

logger = logging.getLogger(__name__)

#Socket io (sio) create a Socket.IO server
sio = socketio.AsyncServer(cors_allowed_origins='*',async_mode='asgi')

SIO_POOL = ThreadPoolExecutor(max_workers=10)

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

@sio.on("error")
async def error():
    logger.error(f"Socket error")

@sio.on("connect")
async def connect(sid, env):
    logger.info("New Client Connected to This id :"+" "+str(sid))

def send_online_users(sid):
    channel = SessionChannel(sio=sio, sid=sid)
    online_users = [{
      "username": USERS[sid]["user"].get("username"),
      "avatar": USERS[sid]["user"].get("avatar"),
      "sid": sid
    } for sid in USERS.keys() if USERS.get("sid",{}).get("user")]
    channel.send_event('codx-junior-online-users', { "users": online_users })
  

@sio.on("disconnect")
async def disconnect(sid):
    logger.info("Client Disconnected: "+" "+str(sid))
    if USERS.get(sid):
        del USERS[sid]
    send_online_users(sid)  

@sio.on("codx-junior-ping")
async def io_ping(sid, data: dict = None):
    return True


@sio.on("background-event")
async def on_background_event(sid, data: dict):
    logger.info(f"***************** On event bacground: {data}")
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
    codxjunior_session.event_manager.chat_event(chat=data.chat, message="Chatting with project...")
    await codxjunior_session.chat_with_project(chat=data.chat)
    await codxjunior_session.save_chat(data.chat)

@sio.on("codx-junior-subtasks")
@sio_api_endpoint
async def io_chat_subtasks(sid, data: dict, codxjunior_session: CODXJuniorSession):
    sio_chat = SioChatMessage(**data)
    instructions = data.get("instructions")
    return await codxjunior_session.generate_tasks(chat=sio_chat.chat, 
                                                    instructions=instructions)

@sio.on("codx-junior-improve")
@sio_api_endpoint
async def io_run_improve(sid, data: dict, codxjunior_session: CODXJuniorSession):
    data = SioChatMessage(**data)
    await codxjunior_session.improve_existing_code(chat=data.chat)
    await codxjunior_session.save_chat(data.chat)

@sio.on("codx-junior-generate-tasks")
@sio_api_endpoint
async def io_create_chat_tasks(sid, data: dict, codxjunior_session: CODXJuniorSession):
    data = SioChatMessage(**data)
    await codxjunior_session.generate_tasks(chat=data.chat)

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
