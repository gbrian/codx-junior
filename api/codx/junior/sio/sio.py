import logging
import socketio
import functools

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
    def wrapper(sid: str, data: SioMessage):
        channel = SessionChannel(sid=sid)
        codxjunior_session = CODXJuniorSession(
                                channel=channel,
                                codx_path=data.codx_path)
        
        if not asyncio.iscoroutinefunction(func):
            return func(sid=sid, data=data, codxjunior_session=codxjunior_session)
        else:
            async def tmp():
                return (await func(sid=sid, data=data, codxjunior_session=codxjunior_session))
            return tmp()
    return wrapper

@sio.on("codx-junior-chat")
@sio_api_endpoint
async def io_chat(sid, data: SioChatMessage, codxjunior_session: CODXJuniorSession):
    await codx_junior_session.chat_event(chat=data.chat, message="Chatting with project...")
    await codx_junior_session.chat_with_project(chat=data.chat, use_knowledge=True)
    codx_junior_session.save_chat(data.chat)
    return True
