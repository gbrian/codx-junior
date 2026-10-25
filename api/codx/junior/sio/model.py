from typing import Optional

from pydantic import BaseModel, Field

from codx.junior.db import Chat

class SioMessage(BaseModel):
    """
    Base envelope shared by every Socket.IO API message.

    All fields are optional: clients serialize the whole request object and
    often send explicit ``null`` values (``codx_path: null``,
    ``request_id: null``). A plain ``str`` field would reject that with a
    pydantic ``ValidationError`` before the handler can answer.
    """
    codx_path: Optional[str] = Field(default=None)
    sid: Optional[str] = Field(default=None)
    request_id: Optional[str] = Field(default=None)
    
class SioChatMessage(SioMessage):
    chat: Chat

class SioFileReadMessage(SioMessage):
    """
    Request payload for the ``codx-junior-file-read`` Socket.IO event.

    Attributes:
        path: File path to read (relative to the project or absolute).
    """
    path: Optional[str] = Field(default=None)

class SioFileDiffMessage(SioMessage):
    """
    Request payload for the ``codx-junior-file-diff`` Socket.IO event.

    Every field is optional on purpose: diff requests are built from an editor
    state and sent with explicit nulls for the unused fields
    (``from_branch: null``, ``to_branch: null``). Declaring them as plain
    ``str`` made pydantic reject those payloads, the handler never emitted the
    ``codx-junior-file-diff-response`` event and clients timed out.

    Attributes:
        path: File path to diff (relative to the project or absolute).
        content: New content to diff the file against (``null`` means empty).
        from_branch: Optional, reserved for branch-based comparisons.
        to_branch: Optional, reserved for branch-based comparisons.
    """
    path: Optional[str] = Field(default=None)
    content: Optional[str] = Field(default="")
    from_branch: Optional[str] = Field(default=None)
    to_branch: Optional[str] = Field(default=None)