import time
import asyncio
import logging

from threading import Thread
from typing import List, Optional
from pydantic import BaseModel, Field

from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class IOEvent(BaseModel):
    sid: Optional[str] = Field(default=None) 
    event: str
    data: dict

EVENT_QUEUE: List[IOEvent] = []

def process_event_queue():
    from codx.junior.sio.sio import sio
    while True:
        if EVENT_QUEUE:
            try:
                event: IOEvent = EVENT_QUEUE.pop(0)
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
        """
        try:
            asyncio.get_running_loop() # Triggers RuntimeError if no running event loop
            # Create a separate thread so we can block before returning
            with ThreadPoolExecutor(1) as pool:
                pool.submit(lambda: asyncio.run(self.sio.emit(event, data))).result()
        except RuntimeError:
            asyncio.run(self.sio.emit(event, data))
        """
        EVENT_QUEUE.append(IOEvent(sid=self.sid, event=event, data=data))

        
