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

from codx.junior.sio.sio import (
  sio,
  sio_api_endpoint,
  sio_send_event
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/wiki")
async def wiki_page(request: Request, response: Response):
    codx_junior_session = request.state.codx_junior_session
    wiki_manager = codx_junior_session.get_wiki()
    if not wiki_manager.is_wiki_active:
        raise Exception("Project has no wiki")

    wiki_path = request.query_params.get("file_path")
    file_path = f"{wiki_manager.wiki_path}/{wiki_path}" if wiki_path else wiki_manager.wiki_home_path
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    response.status_code = status.HTTP_404_NOT_FOUND

@sio.on("codx-junior-wiki")
@sio_api_endpoint
async def io_chat(sid, data: dict, codxjunior_session: CODXJuniorSession):
    wiki_manager = codxjunior_session.get_wiki()
    step = data.get("step")
    file_path = data.get("file_path")

    async def return_data(result):
        await sio_send_event("codx-junior-wiki", { 
                                          "info": f"End processing wiki step: {step}",
                                          "step": step
                                      })
    await sio_send_event("codx-junior-wiki", { "info": f"Start processing wiki step: {step}" })
    if step == "create_config":
        await return_data(wiki_manager.create_config())
    if step == "create_wiki_tree":
        await return_data(wiki_manager.create_wiki_tree())
    if step == "build_wiki_category":
        path = data.get("path")
        await return_data(wiki_manager.build_wiki_category(path=path))
    if step == "build_home":
        await return_data(wiki_manager.build_home())
    if step == "compile_wiki":
        await return_data(wiki_manager.compile_wiki())
    if step == "create_wiki_document":
        await return_data(wiki_manager.create_wiki_document(file_path))
    if step == "rebuild_wiki":
        await return_data(wiki_manager.rebuild_wiki())
    if step == "build_dependency_graph":
        await return_data(wiki_manager.build_dependency_graph())
    if step == "build_domains":
        await return_data(wiki_manager.build_domains())
    if step == "build_wiki_index":
        await return_data(wiki_manager.build_wiki_index())
    if step == "build_module_page":
        await return_data(wiki_manager.build_module_page(file_path))

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
    if step == "build_wiki_category":
        path = request.query_params.get("path")
        return wiki_manager.build_wiki_category(path=path)
    if step == "build_home":
        return wiki_manager.build_home()
    if step == "compile_wiki":
        return wiki_manager.compile_wiki()
    if step == "create_wiki_document":
        return wiki_manager.create_wiki_document(file_path)
    if step == "rebuild_wiki":
        return wiki_manager.rebuild_wiki()
    if step == "build_dependency_graph":
        return wiki_manager.build_dependency_graph()
    if step == "build_domains":
        return wiki_manager.build_domains()
    if step == "build_wiki_index":
        return wiki_manager.build_wiki_index()
    if step == "build_module_page":
        return wiki_manager.build_module_page(file_path)

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

@router.get("/wiki-engine/index")
async def wiki_engine_index(request: Request):
    """Return the cached wiki_index.json without triggering a rebuild."""
    codx_junior_session = request.state.codx_junior_session
    wiki_manager = codx_junior_session.get_wiki()
    from codx.junior.wiki.wiki_index import WikiIndex
    wiki_index = WikiIndex(settings=wiki_manager.settings, db=wiki_manager.db)
    return wiki_index._load_index()


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
