from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from langchain.output_parsers import PydanticOutputParser

# Define logger
import logging
logger = logging.getLogger(__name__)

class ProjectCategoryFiles(BaseModel):
    category: str = Field(default="")
    files: List[str] = Field(default=[])

class ProjectCategories(BaseModel):
    categories: List[ProjectCategoryFiles] = Field(default=[])
    last_update: Optional[str] = Field(default=None)

class SidebarItem(BaseModel):
    text: str
    link: str

class SidebarSection(BaseModel):
    text: str
    items: List[SidebarItem]

class ProjectConfig(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    repository: Optional[str] = None

class WikiConfig(BaseModel):
    project: ProjectConfig = Field(default=ProjectConfig())
    sidebar: List[SidebarSection] = Field(default=None)
    last_update: Optional[str] = Field(default=None)



WIKI_CATEGORY_PARSER = PydanticOutputParser(pydantic_object=ProjectCategories)
