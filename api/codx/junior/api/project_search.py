import logging
from fastapi import APIRouter, Request, HTTPException
from typing import List, Dict, Any

from codx.junior.engine import CODXJuniorSession

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/project/search")
async def search_projects(request: Request, query: str) -> List[Dict[str, Any]]:
    """
    Searches across project files, chat messages, and wiki pages.

    Args:
        query: The search string.

    Returns:
        A list of search results, each with an id, name, and resource_type.
    """
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    
    if not codx_junior_session:
        raise HTTPException(status_code=400, detail="CODXJuniorSession not found in request state.")


    return codx_junior_session.project_search(query=query)
