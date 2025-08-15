import logging
from typing import Dict, Any, Union, List, Optional

from fastapi import APIRouter, Request, Depends, UploadFile
from fastapi.responses import FileResponse

from codx.junior.engine import (
  CODXJuniorSession,
)

from codx.junior.file_manager import FileManager

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/file-finder")
async def find_files(request: Request) -> Dict:
    """
    Process file finder requests and return file information based on the request query parameters.

    Args:
        request (Request): The incoming request object with query parameters.

    Returns:
        Dict[str, Union[str, List[Dict[str, Any]]]]: A dictionary containing file information.
    """
    # Retrieve the session from the request state
    codx_junior_session = request.state.codx_junior_session
    settings = codx_junior_session.settings
    file_manager = FileManager(settings=settings)
    
    # Extracting query parameters for adapter and path
    adapter = request.query_params.get("adapter", "local")
    path = request.query_params.get("path") or "/"
    path = path.split("://")[-1]
    if "local:" in path:
        path = "/"
    q = request.query_params.get("q")

    logger.info("Processing file finder request with adapter: %s, path: %s, q: %s", adapter, path, q)

    if q in ['download', 'preview']:
        file_path = file_manager.get_file_path(path)
        return FileResponse(file_path)

    try:
        # Use FileManager to retrieve file information
        file_response = file_manager.find_files(adapter=adapter, path=path)
    except ValueError as e:
        # Specific exception on file processing
        logger.error("An error occurred: %s", e)
        raise Exception(str(e))
    
    return file_response

@router.post("/file-finder")
async def upload_files(request: Request, file: UploadFile) -> Dict:
    """
    Process file finder requests and return file information based on the request query parameters.

    Args:
        request (Request): The incoming request object with query parameters.

    Returns:
        Dict[str, Union[str, List[Dict[str, Any]]]]: A dictionary containing file information.
    """
    # Retrieve the session from the request state
    codx_junior_session = request.state.codx_junior_session
    settings = codx_junior_session.settings
    file_manager = FileManager(settings=settings)
    
    # Extracting query parameters for adapter and path
    adapter = request.query_params.get("adapter", "local")
    path = request.query_params.get("path") or "local:///"
    q = request.query_params.get("q")

    logger.info("Processing file finder request with adapter: %s, path: %s, q: %s", adapter, path, q)

    file_path = file.filename if path == '/' else f"{path}/{file.filename}"
    abs_file_path = file_manager.get_file_path(file_path)
    logger.info("Uploading file: %s - %s ", file_path, abs_file_path)
    
    with open(abs_file_path, 'wb') as fw:      
        while True:
            data = await file.read(1024 * 10)
            if not data:
                break
            fw.write(data)
    
    return { "ok": 1, "file_path": file_path, "abs_file_path": abs_file_path }
