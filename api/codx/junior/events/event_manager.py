from codx.junior.sio.session_channel import SessionChannel
from codx.junior.db import Chat, Message

class EventManager:
    def __init__(self,
            codx_path: str,
            channel: SessionChannel = None):
        if not channel:
            from codx.junior.sio.sio import sio
            channel = SessionChannel(sio=sio)

        self.codx_path = codx_path
        self.channel = channel

    def event_data(self, data: dict):
        data['codx_path'] = self.codx_path
        return data

    def send_notification(self, **kwargs):
        if not kwargs.get("type"):
            kwargs["type"] = "notification"
        self.channel.send_event('codx-junior', self.event_data(kwargs))

    def send_event(self, message: str):
        self.channel.send_event('codx-junior', self.event_data({ 'text': message, "type": "event" }))
        # self.log_info(f"Sending event {message}- SENT!")
    def send_knowled_event(self, **kwargs):
        self.channel.send_event('knowledge-event', self.event_data(kwargs))

    def chat_event(self, chat: Chat, message: str = None, event_type: str = None):
        self.channel.send_event('chat-event', self.event_data({ 'chat': { 'id': chat.id }, 'text': message, 'type': event_type }))
        # self.log_info(f"SEND MESSAGE {message}- SENT!")

    def message_event(self, chat: Chat, message: Message):
        self.channel.send_event('message-event', self.event_data({ 'chat': { 'id': chat.id }, 'message': message.model_dump() }))
        # self.log_info(f"SEND MESSAGE {message.role} {message.doc_id}- SENT!")
