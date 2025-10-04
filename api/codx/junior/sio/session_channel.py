import os
import time
import asyncio
import logging

from threading import Thread
from typing import List, Optional
from pydantic import BaseModel, Field

from concurrent.futures import ThreadPoolExecutor

CODX_JUNIOR_API_BACKGROUND = os.environ.get("CODX_JUNIOR_API_BACKGROUND")

logger = logging.getLogger(__name__)

class IOEvent(BaseModel):
    sid: Optional[str] = Field(default=None) 
    event: str
    data: dict

EVENT_QUEUE: List[IOEvent] = []

def process_event_queue():
    from codx.junior.sio.sio import sio
    from codx.junior.sio.sio_background import sio_client
                    
    while True:
        if EVENT_QUEUE:
            try:
                event: IOEvent = EVENT_QUEUE.pop(0)
                    
                if CODX_JUNIOR_API_BACKGROUND:
                    resend_event = { "event": event.event, "data": event.data }
                    logger.info(f"Sending event bacground: {resend_event}")
                    sio_client.emit("background-event", resend_event)
                else:
                    asyncio.run(sio.emit(event.event, event.data))
            except Exception as e:
                logger.error(f"Error processing event: {e}")
        else:
            time.sleep(0.2)
Thread(target=process_event_queue).start()

class SessionChannel:
    def __init__(self, sio, sid=None):
        self.sid = sid
        self.sio = sio

    def send_event(self, event, data):
        data["ts"] = int(time.time())
        EVENT_QUEUE.append(IOEvent(sid=self.sid, event=event, data=data))

        
