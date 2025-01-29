class SessionChannel:
    def __init__(self, sio, sid=None):
        self.sid = sid
        self.sio = sio

    async def send_event(self, event, data):
        await self.sio.emit(event, data)
