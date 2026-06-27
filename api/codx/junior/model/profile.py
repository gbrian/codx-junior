from pydantic import BaseModel, Field
from typing import List, Optional

from codx.junior.model.user import CodxUser


class ProfileApiSettings(BaseModel):
    active: bool = Field(description="Model is visible through API", default=False)
    model_name: Optional[str] = Field(description="Model's name", default=None)
    description: Optional[str] = Field(description="Model's description", default=None)


class Profile(BaseModel):
    name: str = Field(default="")
    url: str = Field(default="")
    avatar: str = Field(default="")
    description: str = Field(default="")
    category: str = Field(default="", description="Profile category: global, file, coding, ...")
    file_match: str = Field(default="",
        description="Optional regex to apply profiles based on file absolute path.")
    content: Optional[str] = Field(default=None)
    parsed_content: Optional[str] = Field(default=None)
    path: str = Field(default="")
    content_path: str = Field(default="")
    profiles: Optional[List[str]] = Field(default=[], description="Linked profiles to include with this profile")
    llm_model: Optional[str] = Field(default='')
    use_knowledge: Optional[bool] = Field(default=True)
    user: Optional[CodxUser] = Field(default=CodxUser())
    tools: Optional[List[str]] = Field(default=[])
    tags: Optional[List[str]] = Field(default=[])
    api_settings: Optional[ProfileApiSettings] = Field(description="Indicates if the profile is accessible through the LLM API", default=ProfileApiSettings())
    chat_mode: Optional[str] = Field(description="Affects on how conversation works. Like writing a document or chat messages", default=None)
    project_id: Optional[str] = Field(description="Profile's project", default=None)
    chat_id: Optional[str] = Field(default="", description="Unique identifier for chat")