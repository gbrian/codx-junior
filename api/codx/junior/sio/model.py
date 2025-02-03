from pydantic import BaseModel, Field

from codx.junior.db import Chat

class SioMessage(BaseModel):
    codx_path: str = Field(default=None)
    sid: str = Field(default=None)
    request_id: str = Field(default=None)
    
class SioChatMessage(SioMessage):
    chat: Chat