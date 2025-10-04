import logging
import os
from typing import Dict, Any, Union, List, Optional

from fastapi import APIRouter, Request, Depends, UploadFile, Body
from fastapi.responses import FileResponse

from codx.junior.engine import (
  CODXJuniorSession,
)

from codx.junior.utils.utils import path_join

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
    path = request.query_params.get("path", "/")
    search_filter = request.query_params.get("filter")
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
        file_response = file_manager.find_files(adapter=adapter, path=path, search=search_filter)
    except ValueError as e:
        # Specific exception on file processing
        logger.error("An error occurred: %s", e)
        raise Exception(str(e))
    
    return file_response

@router.post("/file-finder")
async def upload_files(request: Request, file: UploadFile = None) -> Dict:
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

    if q == 'delere':
        # {items: [{path: "/java", type: "dir"}]}
        payload = await request.json()
        raise Exception(f'not implemented: {q}')

    if q == 'newfolder':
        payload = await request.json()
        name = payload.get("name")
        folder_path = path_join(settings.project_path, path, name)
        logger.info("Creating new foler: %s", folder_path)
        os.makedirs(folder_path, exist_ok=True)
        return file_manager.find_files(adapter=adapter, path=folder_path)
    
    if q == 'newfile':
        payload = await request.json()
        name = payload.get("name")
        folder_path = path_join(settings.project_path, path)
        file_path = path_join(folder_path, name)
        if os.path.isfile(file_path) or os.path.isdir(file_path):
            raise Exception(f'File already exists: {file_path}')
        os.makedirs(folder_path, exist_ok=True)
        with open(file_path, 'w') as f:
            pass
        return file_manager.find_files(adapter=adapter, path=folder_path)
    
    if q == 'save':
        payload = await request.json()
        content = payload.get("content")
        file_path = path_join(settings.project_path, path)
        with open(file_path, 'w') as f:
            f.write(content)
        return file_manager.find_files(adapter=adapter, path=path)
    
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
