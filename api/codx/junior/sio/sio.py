import logging
import socketio
import functools
import asyncio

from codx.junior.sio.session_channel import SessionChannel
from codx.junior.engine import CODXJuniorSession

from codx.junior.model import (
    SioMessage,
    SioChatMessage
)

logger = logging.getLogger(__name__)

#Socket io (sio) create a Socket.IO server
sio = socketio.AsyncServer(cors_allowed_origins='*',async_mode='asgi')
socket_app = socketio.ASGIApp(sio)


@sio.on("error")
async def error():
    logger.error(f"Socket error")

@sio.on("connect")
async def connect(sid, env):
    logger.info("New Client Connected to This id :"+" "+str(sid))

@sio.on("disconnect")
async def disconnect(sid):
    logger.info("Client Disconnected: "+" "+str(sid))

@sio.on("codx-junior-ping")
async def io_ping(sid, data: dict = None):
    return True


def sio_api_endpoint(func):
    """Decorator to process sio API requests."""
    @functools.wraps(func)
    async def wrapper(sid: str, data: dict):
        logger.info(f"SIO REquest {sid} {data}")
        base_data = SioMessage(**data)
        channel = SessionChannel(sio=sio, sid=sid)
        codxjunior_session = CODXJuniorSession(
                                channel=channel,
                                codx_path=base_data.codx_path)
        
        if not asyncio.iscoroutinefunction(func):
            return func(sid=sid, data=data, codxjunior_session=codxjunior_session)
        else:
            return (await func(sid=sid, data=data, codxjunior_session=codxjunior_session))
    return wrapper

@sio.on("codx-junior-chat")
@sio_api_endpoint
async def io_chat(sid, data: dict, codxjunior_session: CODXJuniorSession):
    data = SioChatMessage(**data)
    logger.info(f"codx-junior-chat {data.chat.name} {codxjunior_session.settings.project_name}")
    await codxjunior_session.chat_event(chat=data.chat, message="Chatting with project...")
    await codxjunior_session.chat_with_project(chat=data.chat, use_knowledge=True)
    codxjunior_session.save_chat(data.chat)
    return True
