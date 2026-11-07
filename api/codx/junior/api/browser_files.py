"""
Browser session files REST API — the project folders mapped into a session.

A browser session mounts any number of project folders inside its container
under ``/home/<project_name>/<folder>`` and writes every download inside the
project, so this router exposes the mapping and the files the browser saved:

    GET /api/browsers/<session_id>/files?limit=200

The router is discovered automatically by ``codx.junior.api.discover_routers``
(every module in this package exporting ``router`` is included with the
``/api`` prefix), so ``app.py`` and ``api/browser.py`` stay untouched by it.
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, Request, status

from codx.junior.engine.session import CODXJuniorSession
from codx.junior.api.browser_models import (
    BrowserSharedFile,
    BrowserSharedFilesResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/browsers", tags=["browser"])


async def get_session_context(request: Request) -> CODXJuniorSession:
    """Dependency: get the current session context from request state."""
    session = getattr(request.state, "codx_junior_session", None)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active session",
        )
    return session


def _browser_manager(session: CODXJuniorSession):
    """
    Return a BrowserManager for the session.

    Reuses ``session.browser_manager`` when present so a long-lived manager can
    be injected, otherwise constructs one from the project settings.
    """
    manager = getattr(session, "browser_manager", None)
    if manager:
        return manager
    from codx.junior.browser.browser_manager import BrowserManager
    return BrowserManager(session.settings)


@router.get(
    "/{session_id}/files",
    response_model=BrowserSharedFilesResponse,
    summary="List the folders and files shared with a browser session",
    responses={
        200: {"description": "Project mapping and downloaded files"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        500: {"description": "Server error"},
    },
)
async def get_shared_files(
    request: Request,
    session_id: str,
    limit: int = 200,
) -> BrowserSharedFilesResponse:
    """
    Return the folder mapping of a session and the files it downloaded.

    Every project folder is mounted inside the browser container under
    ``home_path`` — so pages can open ``file:///home/<project>/<folder>/...`` and
    a file picker can upload project files — while everything the browser
    downloads is written to ``downloads_path`` inside the project.
    """
    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)

        browser_session = browser_manager.get_session(session_id)
        if not browser_session:
            logger.error("get_shared_files: session not found: %s", session_id)
            raise HTTPException(status_code=404, detail="Session not found")

        paths = browser_manager.get_shared_paths(session_id) or {"session_id": session_id}
        files: List[dict] = browser_manager.get_shared_files(session_id, limit=limit)
        logger.info(
            "get_shared_files: session %s shares %d folder(s) and %d file(s)",
            session_id[:8], len(paths.get("folders") or []), len(files),
        )
        return BrowserSharedFilesResponse(
            **paths,
            count=len(files),
            files=[BrowserSharedFile(**entry) for entry in files],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_shared_files: unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# Made with ❤️ by codx-junior