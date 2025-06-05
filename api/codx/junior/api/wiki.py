import logging
import datetime
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from codx.junior.engine import (
  find_project_by_name,
  CODXJuniorSession
)

from codx.junior.security.user_management import UserSecurityManager, get_authenticated_user
from codx.junior.model.model import CodxUser, CodxUserLogin

from codx.junior.wiki.wiki_manager import WikiManager


logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/wiki/{project_name}/{wiki_path:path}")
async def wiki_page(request: Request, project_name: str, wiki_path: str):
    project = find_project_by_name(project_name)
    if not project or not project.project_wiki:
        raise Exception("Project has no wiki")

    if not wiki_path:
        wiki_path = "index.html"
    dist_path = CODXJuniorSession(settings=project).get_wiki().dist_dir    
    return FileResponse(f"{dist_path}/{wiki_path}")

@router.get("/wiki-engine/build")
async def wiki_engine_build(request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.get_wiki().build_wiki()