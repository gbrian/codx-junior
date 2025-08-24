import os
import logging
from fastapi import APIRouter, Request, Response, HTTPException
from codx.junior.engine import CODXJuniorSession
from codx.junior.knowledge.knowledge_db import KnowledgeDB
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/data/query")
async def db_query_records(request: Request) -> List[Dict[str, Any]]:
    """Query records from the database using a custom filter."""
    try:
        search_filter = request.query_params.get("search_filter", "")
        limit = int(request.query_params.get("limit", 20))
        if not search_filter:
            logger.warning("No search filter provided.")
            raise HTTPException(status_code=400, detail="Search filter parameter is required.")
        
        logger.info("Fetching query_records with filter: %s", search_filter)
        codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
        knowledge_db: KnowledgeDB = codx_junior_session.get_knowledge().get_db()
        records = knowledge_db.raw_search(search_filter=search_filter, output_fields=[], limit=limit)
        return [record.dict() for record in records]
    except ValueError as ex:
        logger.error("Invalid search filter provided: %s", str(ex))
        raise HTTPException(status_code=400, detail="Invalid search filter.")
    except Exception as ex:
        logger.error("Failed to fetch query records: %s", str(ex))
        raise HTTPException(status_code=500, detail="Internal Server Error")
