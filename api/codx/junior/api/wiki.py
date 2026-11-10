"""
Wiki API: docs-site manifest, pages, assistant and update status.

The legacy endpoints (``/wiki`` and ``/wiki-engine/*``) are kept so existing
clients and the wiki settings screen keep working. The modern docs UI uses the
``/wiki/site``, ``/wiki/page``, ``/wiki/assistant`` and ``/wiki/updates``
endpoints.

A ``project`` query/body parameter can target a related project (child,
parent or dependency) without switching the active project. This is what makes
a parent wiki able to navigate the wikis of the projects inside it.
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional
from urllib.parse import unquote

from fastapi import APIRouter, Body, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse

from codx.junior.engine import CODXJuniorSession
from codx.junior.project.project_discover import (
    find_all_projects,
    find_project_by_name,
    get_project_dependencies,
    is_path_child_of,
)
from codx.junior.wiki.assistant import WikiAssistant
from codx.junior.wiki.scheduler import (
    get_wiki_scheduler,
    read_update_status,
    schedule_wiki_update,
)
from codx.junior.wiki.site import WikiSiteBuilder
from codx.junior.wiki.wiki_manager import WikiManager

from codx.junior.sio.sio import (
    sio,
    sio_api_endpoint,
    sio_send_event,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _session(request: Request) -> CODXJuniorSession:
    session = getattr(request.state, "codx_junior_session", None)
    if session is None:
        raise HTTPException(status_code=401, detail="No project session")
    return session


def _related_projects(settings: Any) -> list:
    """Return every project whose wiki may be opened from this one."""
    related = [settings]
    try:
        related.extend(get_project_dependencies(settings))
        related.extend(find_project_by_name(p.project_name) for p in settings.get_sub_projects())
        current_path = settings.abs_project_path
        related.extend(
            project
            for project in find_all_projects().values()
            if project.abs_project_path
            and (
                is_path_child_of(project.abs_project_path, current_path)
                or is_path_child_of(current_path, project.abs_project_path)
            )
        )
    except Exception as ex:  # pragma: no cover - discovery is optional
        logger.debug("Cannot resolve related projects for wiki: %s", ex)
    # Include the whole hierarchy under the same root, so clicking a sibling
    # or cousin project in the docs tree is allowed too.
    try:
        root = min(
            [settings] + [p for p in related if p and is_path_child_of(settings.abs_project_path, p.abs_project_path)],
            key=lambda project: len(project.abs_project_path or ""),
        )
        root_path = root.abs_project_path
        for project in find_all_projects().values():
            if not project.abs_project_path:
                continue
            if project.abs_project_path == root_path or is_path_child_of(project.abs_project_path, root_path):
                related.append(project)
    except Exception as ex:  # pragma: no cover - discovery is optional
        logger.debug("Cannot resolve wiki project hierarchy: %s", ex)
    unique = {}
    for project in related:
        if project is None:
            continue
        unique[project.project_id or project.codx_path] = project
    return list(unique.values())


def _resolve_settings(session: CODXJuniorSession, project_name: Optional[str]) -> Any:
    """
    Resolve the project whose wiki is requested.

    Only the current project or a related project (child/parent/dependency) can
    be opened, which prevents the wiki endpoint from becoming a project
    enumeration API.
    """
    current = session.settings
    if not project_name:
        return current
    project_name = unquote(project_name)
    if project_name in (current.project_name, current.project_id, current.codx_path):
        return current
    target = find_project_by_name(project_name)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")
    allowed = {project.project_id for project in _related_projects(current)}
    if target.project_id not in allowed:
        raise HTTPException(status_code=403, detail="Project is not related to the active project")
    return target


def _wiki_manager(settings: Any) -> WikiManager:
    return WikiManager(settings=settings)


def _site_payload(settings: Any, site: Dict[str, Any]) -> Dict[str, Any]:
    """Return the browser-facing site manifest.

    The on-disk manifest keeps full page metadata for the assistant and the
    server. The docs UI only needs navigation, search, hierarchy and landing
    data, so the page map (often hundreds of entries with headings) is removed
    from the HTTP response. This keeps navigation and search fast.
    """
    public = dict(site)
    public.pop("pages", None)
    public.pop("updates", None)
    # Navigation only needs presentation fields. Descriptions/tags/reading times
    # live in the search index; sending them twice makes large wikis heavy.
    public["navigation"] = [
        {
            **section,
            "items": [
                {key: item.get(key) for key in ("title", "path", "icon", "kind")}
                for item in section.get("items", [])
            ],
        }
        for section in site.get("navigation", [])
    ]
    search = dict(site.get("search", {}))
    search["items"] = (search.get("items") or [])[:600]
    public["search"] = search
    public.setdefault("project", {})
    public["project"].setdefault("name", settings.project_name)
    public["project"]["active"] = True
    return public


def _update_payload(settings: Any) -> Dict[str, Any]:
    status = read_update_status(settings)
    scheduler = get_wiki_scheduler()
    try:
        status.update(scheduler.status(settings))
    except Exception as ex:  # pragma: no cover - status is never critical
        logger.debug("Cannot read live wiki scheduler status: %s", ex)
    status.setdefault("pending", False)
    status.setdefault("running", False)
    status["auto_update"] = bool(getattr(settings, "wiki_auto_update", True))
    status["debounce_seconds"] = getattr(settings, "wiki_update_debounce_seconds", 60)
    status["scheduler_alive"] = scheduler.is_running()
    now = int(time.time())
    next_run = int(status.get("next_run_at") or 0)
    status["overdue_seconds"] = max(0, now - next_run) if status.get("pending") and next_run else 0
    status["stalled"] = bool(
        status.get("pending")
        and not status.get("running")
        and status["overdue_seconds"] > 60
    )
    try:
        status["manifest"] = WikiSiteBuilder(settings=settings).manifest_status()
    except Exception as ex:  # pragma: no cover - diagnostics only
        logger.debug("Cannot inspect wiki manifest freshness: %s", ex)
        status["manifest"] = {}
    return status


# ─────────────────────────────────────────────────────────────────────────────
# Modern docs site
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/wiki/site")
async def wiki_site(request: Request, project: Optional[str] = Query(default=None)):
    """
    Return the docs-site manifest (navigation, landing page, child projects…).

    The manifest is rebuilt on demand when it does not exist yet, so a project
    with generated markdown but an older version of the app still gets a site.
    """
    session = _session(request)
    settings = _resolve_settings(session, project)
    builder = WikiSiteBuilder(settings=settings)
    site = builder.load()
    if not site:
        # Every project has a wiki. Build the lightweight one on first read
        # (deterministic tree + category overviews), without blocking on AI.
        manager = WikiManager(settings=settings)
        await asyncio.to_thread(manager.ensure_initial_wiki, False)
        settings = manager.settings
        builder = WikiSiteBuilder(settings=settings)
        site = await asyncio.to_thread(lambda: builder.build(write=True))
    elif builder.is_stale(site):
        # Another process (or a restart) wrote pages after the manifest: rebuild
        # the cheap, AI-free navigation/index on read.
        site = await asyncio.to_thread(lambda: builder.build(write=True))
    return _site_payload(settings, site)


@router.get("/wiki/page")
async def wiki_page(
    request: Request,
    path: str = Query(default=""),
    project: Optional[str] = Query(default=None),
    file_path: Optional[str] = Query(default=None),
):
    """Return one wiki page as JSON (frontmatter stripped)."""
    session = _session(request)
    settings = _resolve_settings(session, project)
    builder = WikiSiteBuilder(settings=settings)
    page = builder.page(path or file_path or "")
    if not page:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    return page


@router.post("/wiki/assistant")
async def wiki_assistant(
    request: Request,
    payload: Dict[str, Any] = Body(default={}),
):
    """
    Ask the project documentation assistant a question.

    Body:
        {
          "question": "...",
          "project": "optional-related-project",
          "page": "current/page/path",
          "history": [{"role": "user", "content": "..."}],
          "use_knowledge": true
        }
    """
    session = _session(request)
    settings = _resolve_settings(session, payload.get("project"))
    if not getattr(settings, "wiki_assistant_enabled", True):
        raise HTTPException(status_code=403, detail="Wiki assistant is disabled for this project")
    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=422, detail="A question is required")
    assistant = WikiAssistant(settings=settings)
    try:
        return await assistant.answer(
            question=question,
            history=payload.get("history") or [],
            page_path=payload.get("page"),
            use_knowledge=bool(payload.get("use_knowledge", True)),
            include_children=payload.get("include_children"),
            child_depth=payload.get("child_depth"),
        )
    except ValueError as ex:
        raise HTTPException(status_code=422, detail=str(ex))
    except Exception as ex:
        logger.exception("Wiki assistant failed: %s", ex)
        raise HTTPException(status_code=500, detail="The documentation assistant is unavailable")


@router.get("/wiki/updates")
async def wiki_updates(request: Request, project: Optional[str] = Query(default=None)):
    """Return the debounced background update status for a project."""
    session = _session(request)
    settings = _resolve_settings(session, project)
    return _update_payload(settings)


@router.post("/wiki/updates")
async def wiki_updates_action(
    request: Request,
    payload: Dict[str, Any] = Body(default={}),
):
    """
    Schedule or force a wiki refresh.

    Body: ``{"project": "...", "action": "schedule"|"now", "files": [...]}``.
    """
    session = _session(request)
    settings = _resolve_settings(session, payload.get("project"))
    action = (payload.get("action") or "schedule").lower()
    files = [str(file) for file in (payload.get("files") or []) if file]
    if action == "now":
        manager = _wiki_manager(settings)
        if files:
            await asyncio.to_thread(manager.update_files, files, "manual-refresh")
        else:
            # Flush queued changes (if any) and rebuild the manifest. This is
            # what the refresh button in the docs site calls.
            await asyncio.to_thread(get_wiki_scheduler().flush, settings)
            if payload.get("home"):
                await asyncio.to_thread(manager.build_home)
        return {"ok": True, "action": "now", "status": _update_payload(settings)}
    scheduled = schedule_wiki_update(
        settings,
        files=files,
        reason="manual",
        debounce_seconds=int(payload.get("debounce_seconds") or 5),
    )
    return {"ok": scheduled, "action": "schedule", "status": _update_payload(settings)}


@router.post("/wiki/create")
async def wiki_create(
    request: Request,
    payload: Dict[str, Any] = Body(default={}),
):
    """
    Create a usable wiki for a project that does not have one.

    This enables the project wiki and performs the fast, deterministic part of
    the setup: category tree from the repository layout, one overview page per
    category, docs manifest and a small queued batch of detailed pages.
    """
    session = _session(request)
    settings = _resolve_settings(session, payload.get("project"))
    manager = WikiManager(settings=settings)
    await asyncio.to_thread(manager.ensure_initial_wiki, True)
    settings = manager.settings
    find_all_projects()
    site = await asyncio.to_thread(manager.build_site)
    return {
        "ok": True,
        "site": _site_payload(settings, site),
        "updates": _update_payload(settings),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Legacy endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/wiki")
async def wiki_page_file(request: Request, response: Response):
    """Serve a raw wiki markdown file (legacy viewer)."""
    codx_junior_session = _session(request)
    wiki_manager = codx_junior_session.get_wiki()
    if not wiki_manager.is_wiki_active:
        raise HTTPException(status_code=404, detail="Project has no wiki")

    wiki_path = request.query_params.get("file_path")
    file_path = (
        os.path.join(wiki_manager.wiki_path, wiki_path)
        if wiki_path
        else wiki_manager.wiki_home_path
    )
    file_path = os.path.abspath(file_path)
    root = os.path.abspath(wiki_manager.wiki_path)
    if not file_path.startswith(root + os.sep) or not os.path.isfile(file_path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return None
    return FileResponse(file_path)


@sio.on("codx-junior-wiki")
@sio_api_endpoint
async def io_chat(sid, data: dict, codxjunior_session: CODXJuniorSession):
    wiki_manager = codxjunior_session.get_wiki()
    step = data.get("step")

    async def return_data(result):
        await sio_send_event(
            "codx-junior-wiki",
            {"info": f"End processing wiki step: {step}", "step": step},
        )

    await sio_send_event(
        "codx-junior-wiki",
        {"info": f"Start processing wiki step: {step}", "step": step},
    )
    try:
        result = await asyncio.to_thread(
            _run_wiki_step_sync, wiki_manager, step, data
        )
        await return_data(result)
        return result
    except Exception as ex:
        logger.exception("Wiki step %s failed: %s", step, ex)
        await sio_send_event(
            "codx-junior-wiki",
            {"info": f"Wiki step {step} failed: {ex}", "step": step, "error": str(ex)},
        )
        raise


def _run_wiki_step_sync(wiki_manager: WikiManager, step: str, data: Dict[str, Any]) -> Any:
    """Synchronous implementation shared by the thread-offloaded socket handler."""
    file_path = data.get("file_path") or data.get("path")
    if step == "create_config":
        return wiki_manager.create_config()
    if step == "create_wiki_tree":
        return wiki_manager.create_wiki_tree()
    if step == "build_wiki_category":
        return wiki_manager.build_wiki_category(path=data.get("path"))
    if step == "build_home":
        return wiki_manager.build_home()
    if step == "build_site":
        return wiki_manager.build_site()
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
    if step == "update_files":
        return wiki_manager.update_files(files=data.get("files") or [], reason="manual")
    return wiki_manager.rebuild_wiki()


@router.get("/wiki-engine/build")
async def wiki_engine_build(request: Request):
    codx_junior_session = _session(request)
    wiki_manager = codx_junior_session.get_wiki()
    step = request.query_params.get("step")
    data = {
        "step": step,
        "path": request.query_params.get("path"),
        "file_path": request.query_params.get("file_path"),
        "files": request.query_params.getlist("files"),
    }
    return await asyncio.to_thread(_run_wiki_step_sync, wiki_manager, step, data)


@router.get("/wiki-engine/rebuild")
async def wiki_engine_rebuild(request: Request):
    codx_junior_session = _session(request)
    return await asyncio.to_thread(codx_junior_session.get_wiki().rebuild_wiki)


@router.get("/wiki-engine/config")
async def wiki_engine_config(request: Request):
    codx_junior_session = _session(request)
    wiki_manager = codx_junior_session.get_wiki()
    return wiki_manager.load_wiki_settings(with_files=True)


@router.get("/wiki-engine/index")
async def wiki_engine_index(request: Request):
    """Return the cached wiki_index.json without triggering a rebuild."""
    codx_junior_session = _session(request)
    wiki_manager = codx_junior_session.get_wiki()
    from codx.junior.wiki.wiki_index import WikiIndex

    wiki_index = WikiIndex(settings=wiki_manager.settings, db=wiki_manager.db)
    return wiki_index._load_index()


@router.put("/wiki-engine")
async def save_wiki_settings(request: Request):
    codx_junior_session = _session(request)
    wiki_manager = codx_junior_session.get_wiki()
    wiki_settings = await request.json()
    saved = wiki_manager.save_wiki_settings(wiki_settings)
    await asyncio.to_thread(wiki_manager.build_site)
    return saved


@sio.on("codx-junior-wiki-rebuild")
@sio_api_endpoint
async def io_wiki_rebuild(sid, data: dict, codxjunior_session: CODXJuniorSession):
    wiki_manager = codxjunior_session.get_wiki()
    return await asyncio.to_thread(wiki_manager.rebuild_wiki)
