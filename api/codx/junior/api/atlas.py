"""
Project atlas API.

Read-only navigation endpoints used by the UI and by non-agent clients. The
agent-facing surface is the tool registry (``project_map``/``project_locate``/
``project_trace``/``project_impact``/``project_health``); this router exposes the
same packets as JSON.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from codx.junior.atlas import ProjectAtlas
from codx.junior.engine import CODXJuniorSession

logger = logging.getLogger(__name__)

router = APIRouter()


def _session(request: Request) -> CODXJuniorSession:
    session = getattr(request.state, "codx_junior_session", None)
    if session is None:
        raise HTTPException(status_code=401, detail="No project session")
    if not bool(getattr(session.settings, "project_atlas_enabled", True)):
        raise HTTPException(status_code=404, detail="Project atlas is disabled")
    return session


@router.get("/atlas/health")
def api_atlas_health(request: Request) -> Dict[str, Any]:
    """Return index coverage, freshness and warnings."""
    session = _session(request)
    with ProjectAtlas(session.settings) as atlas:
        return atlas.health().to_dict()


@router.get("/atlas/map")
def api_atlas_map(
    request: Request,
    query: str = Query(default=""),
    path: str = Query(default=""),
    limit: int = Query(default=12, ge=3, le=30),
) -> Dict[str, Any]:
    """Return the project map (domains, entry points, reading order)."""
    session = _session(request)
    with ProjectAtlas(session.settings) as atlas:
        packet = atlas.map(query=query, path=path, limit=limit)
    return packet.to_dict()


@router.get("/atlas/locate")
def api_atlas_locate(
    request: Request,
    query: str = Query(..., min_length=1),
    path: str = Query(default=""),
    include: str = Query(default=""),
    regex: bool = Query(default=False),
    case_sensitive: bool = Query(default=False),
    limit: int = Query(default=8, ge=1, le=20),
    include_tests: bool = Query(default=True),
    kind: str = Query(default=""),
) -> Dict[str, Any]:
    """Return ranked `path:line` evidence for a symbol, string, route or glob."""
    session = _session(request)
    with ProjectAtlas(session.settings) as atlas:
        packet = atlas.locate(
            query=query,
            path=path,
            include=include,
            regex=regex,
            case_sensitive=case_sensitive,
            limit=limit,
            include_tests=include_tests,
            kind=kind,
        )
    return packet.to_dict()


@router.get("/atlas/trace")
def api_atlas_trace(
    request: Request,
    symbol: str = Query(..., min_length=1),
    direction: str = Query(default="out"),
    depth: int = Query(default=2, ge=1, le=4),
) -> Dict[str, Any]:
    """Follow imports/calls/routes from a symbol or file."""
    session = _session(request)
    with ProjectAtlas(session.settings) as atlas:
        packet = atlas.trace(symbol=symbol, direction=direction, depth=depth)
    return packet.to_dict()


@router.get("/atlas/impact")
def api_atlas_impact(
    request: Request,
    paths: Optional[List[str]] = Query(default=None),
    depth: int = Query(default=2, ge=1, le=4),
) -> Dict[str, Any]:
    """Return reverse dependencies, tests and docs for one or more files."""
    session = _session(request)
    with ProjectAtlas(session.settings) as atlas:
        packet = atlas.impact(paths=paths or [], depth=depth)
    return packet.to_dict()


@router.post("/atlas/rebuild")
def api_atlas_rebuild(request: Request) -> Dict[str, Any]:
    """Force a full rebuild (normally the atlas refreshes itself)."""
    session = _session(request)
    with ProjectAtlas(session.settings) as atlas:
        health = atlas.rebuild()
    return health.to_dict()
