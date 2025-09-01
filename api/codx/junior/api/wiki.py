import os
import logging
import datetime
from fastapi import APIRouter, Request, Response, status
from fastapi.responses import FileResponse

from typing import Any, Dict

from codx.junior.engine import (
  CODXJuniorSession
)

from codx.junior.project.project_discover import find_project_by_name

from codx.junior.security.user_management import UserSecurityManager, get_authenticated_user
from codx.junior.model.model import CodxUser, CodxUserLogin

from codx.junior.wiki.wiki_manager import WikiManager

from codx.junior.sio.sio import sio, sio_api_endpoint


logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/wiki/{project_name}/{wiki_path:path}")
async def wiki_page(request: Request, project_name: str, wiki_path: str, response: Response):
    project = find_project_by_name(project_name)
    if not project or not project.project_wiki:
        raise Exception("Project has no wiki")

    if not wiki_path:
        wiki_path = "index.html"
    dist_path = CODXJuniorSession(settings=project).get_wiki().dist_dir    
    file_path = f"{dist_path}/{wiki_path}"
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    response.status_code = status.HTTP_404_NOT_FOUND

@router.get("/wiki-engine/build")
async def wiki_engine_build(request: Request):
    codx_junior_session = request.state.codx_junior_session
    wiki_manager = codx_junior_session.get_wiki()
    step = request.query_params.get("step")
    file_path = request.query_params.get("file_path")
    if step == "create_config":
        return wiki_manager.create_config()
    if step == "create_wiki_tree":
        return wiki_manager.create_wiki_tree()
    if step == "build_config_sidebar":
        return wiki_manager.build_config_sidebar()
    if step == "build_home":
        return wiki_manager.build_home()
    if step == "compile_wiki":
        return wiki_manager.compile_wiki()
    if step == "create_wiki_document":
        return wiki_manager.create_wiki_document(file_path)
    return wiki_manager.build_wiki()

@router.get("/wiki-engine/rebuild")
async def wiki_engine_rebuild(request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.get_wiki().rebuild_wiki()

@router.get("/wiki-engine/config")
async def wiki_engine_config(request: Request):
    codx_junior_session = request.state.codx_junior_session
    wiki_manager = codx_junior_session.get_wiki()
    return wiki_manager.load_wiki_settings(with_files=True)


@router.put('/wiki-engine')
async def save_wiki_settings(request: Request):
    codx_junior_session = request.state.codx_junior_session
    wiki_manager = codx_junior_session.get_wiki()
    wiki_settings = await request.json()
    return wiki_manager.save_wiki_settings(wiki_settings)
  

@sio.on("codx-junior-wiki-rebuild")
@sio_api_endpoint
async def io_wiki_rebuild(sid, data: dict, codxjunior_session: CODXJuniorSession):
    return codxjunior_session.get_wiki().rebuild_wiki()
