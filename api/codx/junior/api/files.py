import os
import logging
from fastapi import APIRouter, Request, Response, status
from fastapi.responses import FileResponse

from codx.junior.engine import CODXJuniorSession

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/files")
async def list_files(request: Request):
    """
    List files in a directory.
    
    Query params:
    - path: Directory path (relative or absolute)
    """
    codx_junior_session = request.state.codx_junior_session
    file_engine = codx_junior_session.get_file_engine()
    
    path = request.query_params.get("path", ".")
    abs_path = file_engine.get_project_file_path(path)
    
    if not os.path.isdir(abs_path):
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    
    return file_engine.read_directory(abs_path)


@router.get("/files/read")
async def read_file(request: Request):
    """
    Read a file and return its content with metadata.
    
    Query params:
    - path: File path (relative or absolute)
    """
    codx_junior_session = request.state.codx_junior_session
    file_engine = codx_junior_session.get_file_engine()
    
    path = request.query_params.get("path")
    if not path:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)
    
    try:
        return file_engine.read_file(path)
    except FileNotFoundError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)


@router.get("/files/search")
async def search_files(request: Request):
    """
    Search for files whose paths contain the search pattern.
    Performs a filesystem search within the project scope with pagination support.
    
    Query params:
    - search: Pattern to search for in file paths (case-insensitive)
    - search_path: Optional subdirectory to limit search scope (relative to project root)
    - page: Page number (0-indexed, default 0)
    - page_size: Number of results per page (default 50)
    - raw_search: If true, search all files. If false, exclude .git (default false)
    """
    codx_junior_session = request.state.codx_junior_session
    file_engine = codx_junior_session.get_file_engine()
    
    search = request.query_params.get("search", "")
    search_path = request.query_params.get("search_path")
    page = int(request.query_params.get("page", 0))
    page_size = int(request.query_params.get("page_size", 50))
    raw_search = request.query_params.get("raw_search", "").lower() == "true"
    
    if not search:
        return {"page": 0, "total_files": 0, "page_size": page_size, "files": []}
    
    return file_engine.search_files(
        search=search,
        search_path=search_path,
        page=page,
        page_size=page_size,
        raw_search=raw_search
    )


@router.get("/files/search-content")
async def search_files_content(request: Request):
    """
    Search for files whose content contains the search query.
    Performs a filesystem content search within the project scope with pagination support.
    
    Query params:
    - q: Pattern to search for in file contents
    - search_path: Optional subdirectory to limit search scope (relative to project root)
    - page: Page number (0-indexed, default 0)
    - page_size: Number of results per page (default 50)
    - case_sensitive: Whether search should be case-sensitive (default false)
    - raw_search: If true, search all files. If false, exclude .git (default false)
    """
    codx_junior_session = request.state.codx_junior_session
    file_engine = codx_junior_session.get_file_engine()
    
    query = request.query_params.get("q", "")
    search_path = request.query_params.get("search_path")
    page = int(request.query_params.get("page", 0))
    page_size = int(request.query_params.get("page_size", 50))
    case_sensitive = request.query_params.get("case_sensitive", "").lower() == "true"
    raw_search = request.query_params.get("raw_search", "").lower() == "true"
    
    if not query:
        return {
            "page": 0,
            "total_files": 0,
            "total_matches": 0,
            "page_size": page_size,
            "results": []
        }
    
    return file_engine.search_files_content(
        query=query,
        search_path=search_path,
        page=page,
        page_size=page_size,
        case_sensitive=case_sensitive,
        raw_search=raw_search
    )