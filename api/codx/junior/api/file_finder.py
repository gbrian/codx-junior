import logging
import os
import asyncio
from typing import Dict, Any, Union, List, Optional

from fastapi import APIRouter, Request, Depends, UploadFile, Body
from fastapi.responses import FileResponse, JSONResponse

from codx.junior.engine import (
  CODXJuniorSession,
)

from codx.junior.utils.utils import path_join

from codx.junior.file_manager import FileManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Define constants for query parameters
QUERY_PARAM_ADAPTER = "adapter"
QUERY_PARAM_PATH = "path"
QUERY_PARAM_FILTER = "filter"
QUERY_PARAM_QUERY = "q"
QUERY_PARAM_NAME = "name"

# Define constants for query parameter values
QUERY_VALUE_LOCAL = "local"
QUERY_VALUE_DOWNLOAD = "download"
QUERY_VALUE_PREVIEW = "preview"
QUERY_VALUE_DELETE = "delete"
QUERY_VALUE_NEW_FOLDER = "newfolder"
QUERY_VALUE_NEW_FILE = "newfile"
QUERY_VALUE_SAVE = "save"

@router.get("/file-finder/files")
async def list_files(request: Request) -> Dict[str, Any]:
    """
    List files and directories within a specified path.

    Args:
        request (Request): The incoming request object with query parameters.
                           Expected query parameters:
                           - adapter (str, optional): The file adapter to use (default: "local").
                           - path (str, optional): The path to list files from (default: "/").

    Returns:
        Dict[str, Any]: A dictionary containing a list of files and directories.
    """
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    settings = codx_junior_session.settings
    file_manager = FileManager(settings=settings)

    adapter = request.query_params.get(QUERY_PARAM_ADAPTER, QUERY_VALUE_LOCAL)
    path = request.query_params.get(QUERY_PARAM_PATH, "/")
    
    # Normalize path to remove "local://" prefix if present and handle root path
    if path.startswith(f"{QUERY_VALUE_LOCAL}://"):
        path = path.split("://")[-1]
    if not path.startswith('/'):
        path = '/' + path
    if path == "//": # Ensure root path is represented as "/"
        path = "/"

    logger.info("Listing files with adapter: %s, path: %s", adapter, path)

    try:
        file_response = file_manager.find_files(adapter=adapter, path=path)
    except ValueError as e:
        logger.error("Error listing files: %s", e)
        # Return a JSON response for errors instead of raising a generic Exception
        return JSONResponse(content={"error": str(e)}, status_code=400)
    
    return file_response

@router.post("/file-finder/upload")
async def upload_file(request: Request, file: UploadFile = None) -> Dict[str, Any]:
    """
    Upload a file.

    Args:
        request (Request): The incoming request object with query parameters.
                           Expected query parameters:
                           - adapter (str, optional): The file adapter to use (default: "local").
                           - path (str, optional): The directory to upload the file to (default: "/").
        file (UploadFile): The file to upload.

    Returns:
        Dict[str, Any]: A dictionary indicating the success of the upload and file path information.
    """
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    settings = codx_junior_session.settings
    file_manager = FileManager(settings=settings)

    adapter = request.query_params.get(QUERY_PARAM_ADAPTER, QUERY_VALUE_LOCAL)
    path = request.query_params.get(QUERY_PARAM_PATH, "/")
    
    if not file:
        logger.error("No file provided for upload.")
        return JSONResponse(content={"error": "No file provided"}, status_code=400)

    # Construct the full file path
    target_dir = path.split("://")[-1] if path.startswith(f"{QUERY_VALUE_LOCAL}://") else path
    if not target_dir.startswith('/'):
        target_dir = '/' + target_dir
    if target_dir == "//":
        target_dir = "/"

    file_name = file.filename
    if not file_name:
        logger.error("Uploaded file has no filename.")
        return JSONResponse(content={"error": "Uploaded file has no filename"}, status_code=400)

    relative_file_path = path_join(target_dir, file_name)
    abs_file_path = file_manager.get_file_path(relative_file_path)
    
    logger.info("Uploading file: %s to absolute path: %s", relative_file_path, abs_file_path)

    try:
        # Ensure the target directory exists
        os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
        
        with open(abs_file_path, 'wb') as fw:
            while True:
                data = await file.read(1024 * 10) # Read in chunks
                if not data:
                    break
                fw.write(data)
    except Exception as e:
        logger.error("Error during file upload: %s", e)
        return JSONResponse(content={"error": f"Error uploading file: {e}"}, status_code=500)

    return {"ok": 1, "file_path": relative_file_path, "abs_file_path": abs_file_path}

@router.post("/file-finder/delete")
async def delete_item(request: Request, payload: Dict[str, List[Dict[str, str]]] = Body(...)) -> Dict[str, Any]:
    """
    Delete one or more files or directories.

    Args:
        request (Request): The incoming request object with query parameters.
                           Expected query parameters:
                           - adapter (str, optional): The file adapter to use (default: "local").
        payload (Dict[str, List[Dict[str, str]]]): A dictionary containing a list of items to delete.
                                                  Each item should have 'path' and 'type' (e.g., 'file' or 'dir').
                                                  Example: {"items": [{"path": "/my/file.txt", "type": "file"}]}

    Returns:
        Dict[str, Any]: A dictionary indicating the success of the deletion.
    """
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    settings = codx_junior_session.settings
    file_manager = FileManager(settings=settings)

    adapter = request.query_params.get(QUERY_PARAM_ADAPTER, QUERY_VALUE_LOCAL)

    if not payload or "items" not in payload:
        logger.error("Invalid payload for delete operation.")
        return JSONResponse(content={"error": "Invalid payload. Expected 'items' key."}, status_code=400)

    items_to_delete = payload["items"]
    deleted_items = []
    failed_items = []

    logger.info("Processing delete request for %d items with adapter: %s", len(items_to_delete), adapter)

    for item in items_to_delete:
        item_path = item.get("path")
        item_type = item.get("type")

        if not item_path or not item_type:
            logger.warning("Skipping invalid item in delete payload: %s", item)
            failed_items.append({"item": item, "reason": "Missing 'path' or 'type'"})
            continue

        try:
            # Ensure path is absolute or relative to project root handled by FileManager
            # For simplicity, assume paths provided are relative or FileManager handles them.
            # If paths are absolute, ensure they are correctly processed by get_file_path.
            
            # Example: If path is relative to root and FileManager needs absolute path:
            # abs_item_path = file_manager.get_file_path(item_path)
            # For now, assume FileManager.delete_item can handle relative paths or we pass absolute.
            
            # Let's assume get_file_path correctly resolves the path for the adapter
            resolved_path = file_manager.get_file_path(item_path)

            if item_type == "file":
                file_manager.delete_file(resolved_path)
                deleted_items.append(item_path)
                logger.info("Deleted file: %s", item_path)
            elif item_type == "dir":
                file_manager.delete_directory(resolved_path)
                deleted_items.append(item_path)
                logger.info("Deleted directory: %s", item_path)
            else:
                logger.warning("Unsupported item type for deletion: %s", item_type)
                failed_items.append({"item": item, "reason": f"Unsupported item type: {item_type}"})
        except FileNotFoundError:
            logger.warning("Item not found for deletion: %s", item_path)
            failed_items.append({"item": item, "reason": "Not found"})
        except Exception as e:
            logger.error("Error deleting item '%s': %s", item_path, e)
            failed_items.append({"item": item, "reason": str(e)})

    response_content = {"deleted": deleted_items}
    if failed_items:
        response_content["failed"] = failed_items
        return JSONResponse(content=response_content, status_code=400)

    return response_content

@router.post("/file-finder/rename")
async def rename_item(request: Request, payload: Dict[str, str] = Body(...)) -> Dict[str, Any]:
    """
    Rename a file or directory.

    Args:
        request (Request): The incoming request object with query parameters.
                           Expected query parameters:
                           - adapter (str, optional): The file adapter to use (default: "local").
        payload (Dict[str, str]): A dictionary containing the old path, new path, and type.
                                  Expected keys: "old_path", "new_path", "type".
                                  Example: {"old_path": "/old/name.txt", "new_path": "/new/name.txt", "type": "file"}

    Returns:
        Dict[str, Any]: A dictionary indicating the success of the renaming operation.
    """
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    settings = codx_junior_session.settings
    file_manager = FileManager(settings=settings)

    adapter = request.query_params.get(QUERY_PARAM_ADAPTER, QUERY_VALUE_LOCAL)

    old_path = payload.get("old_path")
    new_path = payload.get("new_path")
    item_type = payload.get("type")

    if not all([old_path, new_path, item_type]):
        logger.error("Invalid payload for rename operation. Missing 'old_path', 'new_path', or 'type'.")
        return JSONResponse(content={"error": "Invalid payload. Requires 'old_path', 'new_path', and 'type'."}, status_code=400)

    logger.info("Renaming item from '%s' to '%s' (type: %s) with adapter: %s", old_path, new_path, item_type, adapter)

    try:
        # Resolve paths using FileManager
        resolved_old_path = file_manager.get_file_path(old_path)
        resolved_new_path = file_manager.get_file_path(new_path)

        if item_type == "file":
            file_manager.rename_file(resolved_old_path, resolved_new_path)
            logger.info("Renamed file from %s to %s", old_path, new_path)
        elif item_type == "dir":
            file_manager.rename_directory(resolved_old_path, resolved_new_path)
            logger.info("Renamed directory from %s to %s", old_path, new_path)
        else:
            logger.warning("Unsupported item type for renaming: %s", item_type)
            return JSONResponse(content={"error": f"Unsupported item type: {item_type}"}, status_code=400)
        
        return {"message": f"Successfully renamed '{old_path}' to '{new_path}'"}
    except FileNotFoundError:
        logger.error("Item not found for renaming: %s", old_path)
        return JSONResponse(content={"error": f"Item not found: {old_path}"}, status_code=404)
    except FileExistsError:
        logger.error("New path already exists: %s", new_path)
        return JSONResponse(content={"error": f"Destination path already exists: {new_path}"}, status_code=409)
    except Exception as e:
        logger.error("Error renaming item '%s' to '%s': %s", old_path, new_path, e)
        return JSONResponse(content={"error": f"Error renaming item: {e}"}, status_code=500)

@router.post("/file-finder/archive")
async def archive_items(request: Request, payload: Dict[str, List[Dict[str, str]]] = Body(...)) -> Dict[str, Any]:
    """
    Archive (zip) one or more files or directories.

    Args:
        request (Request): The incoming request object with query parameters.
                           Expected query parameters:
                           - adapter (str, optional): The file adapter to use (default: "local").
                           - archive_path (str, optional): The path where the archive should be created (default: current directory).
        payload (Dict[str, List[Dict[str, str]]]): A dictionary containing a list of items to archive.
                                                  Each item should have 'path' and 'type'.
                                                  Example: {"items": [{"path": "/my/file.txt", "type": "file"}]}

    Returns:
        Dict[str, Any]: A dictionary indicating the success of the archiving operation.
    """
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    settings = codx_junior_session.settings
    file_manager = FileManager(settings=settings)

    adapter = request.query_params.get(QUERY_PARAM_ADAPTER, QUERY_VALUE_LOCAL)
    archive_path = request.query_params.get("archive_path", ".") # Default to current directory for archive

    if not payload or "items" not in payload:
        logger.error("Invalid payload for archive operation.")
        return JSONResponse(content={"error": "Invalid payload. Expected 'items' key."}, status_code=400)

    items_to_archive = payload["items"]
    archive_name = payload.get("archive_name", "archive.zip") # Default archive name

    logger.info("Archiving %d items to '%s' with adapter: %s", len(items_to_archive), archive_name, adapter)

    try:
        # Resolve archive path
        resolved_archive_path = file_manager.get_file_path(path_join(archive_path, archive_name))
        
        # Resolve paths of items to be archived
        resolved_items_to_archive = []
        for item in items_to_archive:
            item_path = item.get("path")
            if item_path:
                resolved_items_to_archive.append(file_manager.get_file_path(item_path))
            else:
                logger.warning("Skipping item with missing path in archive payload: %s", item)

        if not resolved_items_to_archive:
            return JSONResponse(content={"error": "No valid items found to archive."}, status_code=400)

        # Assuming FileManager has an archive method
        file_manager.archive_items(resolved_items_to_archive, resolved_archive_path)
        logger.info("Successfully archived items to %s", resolved_archive_path)
        
        return {"message": f"Successfully archived items to {resolved_archive_path}"}
    except FileNotFoundError as e:
        logger.error("Item not found during archiving: %s", e)
        return JSONResponse(content={"error": f"Item not found: {e}"}, status_code=404)
    except Exception as e:
        logger.error("Error archiving items: %s", e)
        return JSONResponse(content={"error": f"Error archiving items: {e}"}, status_code=500)

@router.post("/file-finder/unarchive")
async def unarchive_items(request: Request, payload: Dict[str, str] = Body(...)) -> Dict[str, Any]:
    """
    Unarchive (unzip) a file.

    Args:
        request (Request): The incoming request object with query parameters.
                           Expected query parameters:
                           - adapter (str, optional): The file adapter to use (default: "local").
                           - extract_path (str, optional): The path where the archive contents should be extracted (default: current directory).
        payload (Dict[str, str]): A dictionary containing the path to the archive file.
                                  Expected key: "archive_path".
                                  Example: {"archive_path": "/my/archive.zip"}

    Returns:
        Dict[str, Any]: A dictionary indicating the success of the unarchiving operation.
    """
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    settings = codx_junior_session.settings
    file_manager = FileManager(settings=settings)

    adapter = request.query_params.get(QUERY_PARAM_ADAPTER, QUERY_VALUE_LOCAL)
    extract_path = request.query_params.get("extract_path", ".") # Default extraction to current directory

    archive_path = payload.get("archive_path")

    if not archive_path:
        logger.error("Missing 'archive_path' in payload for unarchive operation.")
        return JSONResponse(content={"error": "Missing 'archive_path' in payload."}, status_code=400)

    logger.info("Unarchiving file '%s' to '%s' with adapter: %s", archive_path, extract_path, adapter)

    try:
        # Resolve paths
        resolved_archive_path = file_manager.get_file_path(archive_path)
        resolved_extract_path = file_manager.get_file_path(extract_path)

        # Assuming FileManager has an unarchive method
        file_manager.unarchive_items(resolved_archive_path, resolved_extract_path)
        logger.info("Successfully unarchived items from %s to %s", resolved_archive_path, resolved_extract_path)
        
        return {"message": f"Successfully unarchived '{archive_path}' to '{resolved_extract_path}'"}
    except FileNotFoundError:
        logger.error("Archive file not found: %s", archive_path)
        return JSONResponse(content={"error": f"Archive file not found: {archive_path}"}, status_code=404)
    except Exception as e:
        logger.error("Error unarchiving file '%s': %s", archive_path, e)
        return JSONResponse(content={"error": f"Error unarchiving file: {e}"}, status_code=500)

@router.post("/file-finder/create-file")
async def create_new_file(request: Request, payload: Dict[str, str] = Body(...)) -> Dict[str, Any]:
    """
    Create a new empty file.

    Args:
        request (Request): The incoming request object with query parameters.
                           Expected query parameters:
                           - adapter (str, optional): The file adapter to use (default: "local").
        payload (Dict[str, str]): A dictionary containing the file name and its parent directory path.
                                  Expected keys: "name", "path".
                                  Example: {"name": "new_document.txt", "path": "/documents"}

    Returns:
        Dict[str, Any]: A dictionary indicating the success of the file creation and its path.
    """
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    settings = codx_junior_session.settings
    file_manager = FileManager(settings=settings)

    adapter = request.query_params.get(QUERY_PARAM_ADAPTER, QUERY_VALUE_LOCAL)

    file_name = payload.get(QUERY_PARAM_NAME)
    parent_path = payload.get(QUERY_PARAM_PATH)

    if not file_name or not parent_path:
        logger.error("Invalid payload for create file operation. Missing 'name' or 'path'.")
        return JSONResponse(content={"error": "Invalid payload. Requires 'name' and 'path'."}, status_code=400)

    logger.info("Creating new file '%s' in directory '%s' with adapter: %s", file_name, parent_path, adapter)

    try:
        folder_path = file_manager.get_file_path(parent_path)
        file_path = path_join(folder_path, file_name)

        if os.path.exists(file_path):
            logger.warning("File already exists: %s", file_path)
            return JSONResponse(content={"error": f"File already exists: {file_name}"}, status_code=409)

        # Ensure parent directory exists
        os.makedirs(folder_path, exist_ok=True)

        # Create the empty file
        with open(file_path, 'w', encoding='utf-8') as f:
            pass # Creates an empty file

        logger.info("Successfully created file: %s", file_path)
        # Return info similar to what find_files might return for a single file
        return {
            "message": f"File '{file_name}' created successfully.",
            "file_path": path_join(parent_path, file_name), # Return relative path
            "abs_file_path": file_path
        }
    except Exception as e:
        logger.error("Error creating file '%s' in '%s': %s", file_name, parent_path, e)
        return JSONResponse(content={"error": f"Error creating file: {e}"}, status_code=500)

@router.post("/file-finder/create-folder")
async def create_new_folder(request: Request, payload: Dict[str, str] = Body(...)) -> Dict[str, Any]:
    """
    Create a new directory.

    Args:
        request (Request): The incoming request object with query parameters.
                           Expected query parameters:
                           - adapter (str, optional): The file adapter to use (default: "local").
        payload (Dict[str, str]): A dictionary containing the folder name and its parent directory path.
                                  Expected keys: "name", "path".
                                  Example: {"name": "new_project", "path": "/projects"}

    Returns:
        Dict[str, Any]: A dictionary indicating the success of the folder creation and its path.
    """
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    settings = codx_junior_session.settings
    file_manager = FileManager(settings=settings)

    adapter = request.query_params.get(QUERY_PARAM_ADAPTER, QUERY_VALUE_LOCAL)

    folder_name = payload.get(QUERY_PARAM_NAME)
    parent_path = payload.get(QUERY_PARAM_PATH)

    if not folder_name or not parent_path:
        logger.error("Invalid payload for create folder operation. Missing 'name' or 'path'.")
        return JSONResponse(content={"error": "Invalid payload. Requires 'name' and 'path'."}, status_code=400)

    logger.info("Creating new folder '%s' in directory '%s' with adapter: %s", folder_name, parent_path, adapter)

    try:
        target_dir_path = file_manager.get_file_path(parent_path)
        new_folder_path = path_join(target_dir_path, folder_name)

        if os.path.exists(new_folder_path):
            logger.warning("Folder already exists: %s", new_folder_path)
            return JSONResponse(content={"error": f"Folder already exists: {folder_name}"}, status_code=409)

        os.makedirs(new_folder_path, exist_ok=True)
        logger.info("Successfully created folder: %s", new_folder_path)
        
        return {
            "message": f"Folder '{folder_name}' created successfully.",
            "folder_path": path_join(parent_path, folder_name), # Return relative path
            "abs_folder_path": new_folder_path
        }
    except Exception as e:
        logger.error("Error creating folder '%s' in '%s': %s", folder_name, parent_path, e)
        return JSONResponse(content={"error": f"Error creating folder: {e}"}, status_code=500)

@router.get("/file-finder/search")
async def search_files(request: Request) -> Dict[str, Any]:
    """
    Search for files based on a query string.

    Args:
        request (Request): The incoming request object with query parameters.
                           Expected query parameters:
                           - adapter (str, optional): The file adapter to use (default: "local").
                           - path (str, optional): The directory to search within (default: "/").
                           - filter (str, optional): A filter string for the search.

    Returns:
        Dict[str, Any]: A dictionary containing search results.
    """
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    settings = codx_junior_session.settings
    file_manager = FileManager(settings=settings)

    adapter = request.query_params.get(QUERY_PARAM_ADAPTER, QUERY_VALUE_LOCAL)
    path = request.query_params.get(QUERY_PARAM_PATH, "/")
    search_filter = request.query_params.get(QUERY_PARAM_FILTER)

    # Normalize path
    if path.startswith(f"{QUERY_VALUE_LOCAL}://"):
        path = path.split("://")[-1]
    if not path.startswith('/'):
        path = '/' + path
    if path == "//":
        path = "/"

    if not search_filter:
        logger.warning("Search endpoint called without a 'filter' query parameter.")
        return JSONResponse(content={"error": "Search 'filter' parameter is required."}, status_code=400)

    logger.info("Searching for files with filter: '%s' in path: '%s' using adapter: %s", search_filter, path, adapter)

    try:
        file_response = file_manager.find_files(adapter=adapter, path=path, search=search_filter)
    except ValueError as e:
        logger.error("Error during file search: %s", e)
        return JSONResponse(content={"error": str(e)}, status_code=400)
    
    return file_response

# --- Refactored Preview and Download Functions ---

async def _get_file_path_for_response(file_manager: FileManager, path: str, request: Request) -> str:
    """Helper to normalize and resolve file paths for FileResponse."""
    adapter = request.query_params.get(QUERY_PARAM_ADAPTER, QUERY_VALUE_LOCAL)
    
    # Normalize path
    if path.startswith(f"{adapter}://"):
        path = path.split("://")[-1]
    if not path.startswith('/'):
        path = '/' + path
    if path == "//":
        path = "/"
        
    return file_manager.get_file_path(path)

@router.get("/file-finder/preview")
async def preview_file(request: Request) -> JSONResponse:
    """
    Get the content of a file for preview.

    Args:
        request (Request): The incoming request object with query parameters.
                           Expected query parameters:
                           - adapter (str, optional): The file adapter to use (default: "local").
                           - path (str): The path to the file to preview.

    Returns:
        Union[FileResponse, JSONResponse]: A FileResponse if successful, or a JSONResponse with an error message.
    """
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    settings = codx_junior_session.settings
    file_manager = FileManager(settings=settings)

    path = request.query_params.get(QUERY_PARAM_PATH)

    if not path:
        logger.error("Missing 'path' query parameter for preview operation.")
        return JSONResponse(content={"error": "Missing 'path' query parameter."}, status_code=400)

    logger.info("Previewing file: %s", path)

    try:
        file_path = await asyncio.to_thread(_get_file_path_for_response, file_manager, path, request)
        
        if not os.path.isfile(file_path):
            logger.error("File not found for preview: %s", file_path)
            return JSONResponse(content={"error": f"File not found: {path}"}, status_code=404)
        
        # FileResponse can directly serve files. The potential issue was likely due to synchronous operations within the async function.
        # Using asyncio.to_thread for path resolution ensures that even if get_file_path was complex and synchronous, it wouldn't block.
        return FileResponse(file_path, filename=os.path.basename(file_path))
    except Exception as e:
        logger.error("Error previewing file '%s': %s", path, e)
        return JSONResponse(content={"error": f"Error previewing file: {e}"}, status_code=500)

@router.get("/file-finder/download")
async def download_file(request: Request) -> JSONResponse:
    """
    Download a file.

    Args:
        request (Request): The incoming request object with query parameters.
                           Expected query parameters:
                           - adapter (str, optional): The file adapter to use (default: "local").
                           - path (str): The path to the file to download.

    Returns:
        Union[FileResponse, JSONResponse]: A FileResponse if successful, or a JSONResponse with an error message.
    """
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    settings = codx_junior_session.settings
    file_manager = FileManager(settings=settings)

    path = request.query_params.get(QUERY_PARAM_PATH)

    if not path:
        logger.error("Missing 'path' query parameter for download operation.")
        return JSONResponse(content={"error": "Missing 'path' query parameter."}, status_code=400)
    
    logger.info("Downloading file: %s", path)

    try:
        file_path = await asyncio.to_thread(_get_file_path_for_response, file_manager, path, request)
        
        if not os.path.isfile(file_path):
            logger.error("File not found for download: %s", file_path)
            return JSONResponse(content={"error": f"File not found: {path}"}, status_code=404)
        
        return FileResponse(file_path, filename=os.path.basename(file_path), media_type='application/octet-stream')
    except Exception as e:
        logger.error("Error downloading file '%s': %s", path, e)
        return JSONResponse(content={"error": f"Error downloading file: {e}"}, status_code=500)


@router.post("/file-finder/copy")
async def copy_item(request: Request, payload: Dict[str, str] = Body(...)) -> Dict[str, Any]:
    """
    Copy a file or directory from a source path to a destination path.

    Args:
        request (Request): The incoming request object with query parameters.
                           Expected query parameters:
                           - adapter (str, optional): The file adapter to use (default: "local").
        payload (Dict[str, str]): A dictionary containing the source path and destination path.
                                  Expected keys: "source_path", "destination_path".
                                  Example: {"source_path": "/old/file.txt", "destination_path": "/new/location/"}

    Returns:
        Dict[str, Any]: A dictionary indicating the success of the copy operation.
    """
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    settings = codx_junior_session.settings
    file_manager = FileManager(settings=settings)

    adapter = request.query_params.get(QUERY_PARAM_ADAPTER, QUERY_VALUE_LOCAL)

    source_path = payload.get("source_path")
    destination_path = payload.get("destination_path")

    if not source_path or not destination_path:
        logger.error("Invalid payload for copy operation. Missing 'source_path' or 'destination_path'.")
        return JSONResponse(content={"error": "Invalid payload. Requires 'source_path' and 'destination_path'."}, status_code=400)

    logger.info("Copying item from '%s' to '%s' using adapter: %s", source_path, destination_path, adapter)

    try:
        # Resolve paths
        resolved_source_path = file_manager.get_file_path(source_path)
        resolved_destination_path = file_manager.get_file_path(destination_path)

        # Assuming FileManager has a copy method
        # The copy method should handle whether destination is a file or directory
        file_manager.copy_item(resolved_source_path, resolved_destination_path)
        
        logger.info("Successfully copied '%s' to '%s'", source_path, destination_path)
        return {"message": f"Successfully copied '{source_path}' to '{destination_path}'"}
    except FileNotFoundError:
        logger.error("Source item not found for copy: %s", source_path)
        return JSONResponse(content={"error": f"Source item not found: {source_path}"}, status_code=404)
    except Exception as e:
        logger.error("Error copying item from '%s' to '%s': %s", source_path, destination_path, e)
        return JSONResponse(content={"error": f"Error copying item: {e}"}, status_code=500)

@router.post("/file-finder/move")
async def move_item(request: Request, payload: Dict[str, str] = Body(...)) -> Dict[str, Any]:
    """
    Move a file or directory from a source path to a destination path.

    Args:
        request (Request): The incoming request object with query parameters.
                           Expected query parameters:
                           - adapter (str, optional): The file adapter to use (default: "local").
        payload (Dict[str, str]): A dictionary containing the source path and destination path.
                                  Expected keys: "source_path", "destination_path".
                                  Example: {"source_path": "/old/file.txt", "destination_path": "/new/location/"}

    Returns:
        Dict[str, Any]: A dictionary indicating the success of the move operation.
    """
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    settings = codx_junior_session.settings
    file_manager = FileManager(settings=settings)

    adapter = request.query_params.get(QUERY_PARAM_ADAPTER, QUERY_VALUE_LOCAL)

    source_path = payload.get("source_path")
    destination_path = payload.get("destination_path")

    if not source_path or not destination_path:
        logger.error("Invalid payload for move operation. Missing 'source_path' or 'destination_path'.")
        return JSONResponse(content={"error": "Invalid payload. Requires 'source_path' and 'destination_path'."}, status_code=400)

    logger.info("Moving item from '%s' to '%s' using adapter: %s", source_path, destination_path, adapter)

    try:
        # Resolve paths
        resolved_source_path = file_manager.get_file_path(source_path)
        resolved_destination_path = file_manager.get_file_path(destination_path)

        # Assuming FileManager has a move method
        file_manager.move_item(resolved_source_path, resolved_destination_path)
        
        logger.info("Successfully moved '%s' to '%s'", source_path, destination_path)
        return {"message": f"Successfully moved '{source_path}' to '{destination_path}'"}
    except FileNotFoundError:
        logger.error("Source item not found for move: %s", source_path)
        return JSONResponse(content={"error": f"Source item not found: {source_path}"}, status_code=404)
    except Exception as e:
        logger.error("Error moving item from '%s' to '%s': %s", source_path, destination_path, e)
        return JSONResponse(content={"error": f"Error moving item: {e}"}, status_code=500)

@router.post("/file-finder/save")
async def save_file_content(request: Request, payload: Dict[str, str] = Body(...)) -> Dict[str, Any]:
    """
    Save content to a file. Creates the file if it doesn't exist.

    Args:
        request (Request): The incoming request object with query parameters.
                           Expected query parameters:
                           - adapter (str, optional): The file adapter to use (default: "local").
                           - path (str): The path to the file to save content to.
        payload (Dict[str, str]): A dictionary containing the content to save.
                                  Expected key: "content".
                                  Example: {"content": "This is the file content."}

    Returns:
        Dict[str, Any]: A dictionary indicating the success of the save operation.
    """
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    settings = codx_junior_session.settings
    file_manager = FileManager(settings=settings)

    adapter = request.query_params.get(QUERY_PARAM_ADAPTER, QUERY_VALUE_LOCAL)
    file_path_param = request.query_params.get(QUERY_PARAM_PATH)
    content = payload.get("content")

    if not file_path_param or content is None: # Allow empty content
        logger.error("Missing 'path' query parameter or 'content' in payload for save operation.")
        return JSONResponse(content={"error": "Missing 'path' query parameter or 'content' in payload."}, status_code=400)

    logger.info("Saving content to file: %s using adapter: %s", file_path_param, adapter)

    try:
        # Resolve file path
        resolved_file_path = file_manager.get_file_path(file_path_param)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(resolved_file_path), exist_ok=True)

        # Save the content to the file
        with open(resolved_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("Successfully saved content to file: %s", resolved_file_path)
        
        # Optionally, return the file info after saving
        # return file_manager.find_files(adapter=adapter, path=file_path_param)
        return {"message": f"Content saved successfully to '{file_path_param}'"}
    except Exception as e:
        logger.error("Error saving content to file '%s': %s", file_path_param, e)
        return JSONResponse(content={"error": f"Error saving content to file: {e}"}, status_code=500)

@router.get("/file-finder/search-content")
async def search_file_content(request: Request) -> Dict[str, Any]:
    """
    Search for files based on their content.

    Args:
        request (Request): The incoming request object with query parameters.
                           Expected query parameters:
                           - adapter (str, optional): The file adapter to use (default: "local").
                           - path (str, optional): The directory to search within (default: "/").
                           - query (str): The search query/pattern to find in file contents.
                           - include_extensions (str, optional): Comma-separated file extensions to include (e.g., ".txt,.py,.js").
                           - exclude_extensions (str, optional): Comma-separated file extensions to exclude.
                           - case_sensitive (bool, optional): Whether search is case-sensitive (default: false).

    Returns:
        Dict[str, Any]: A dictionary containing search results with matched files and line numbers.
    """
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    settings = codx_junior_session.settings
    file_manager = FileManager(settings=settings)

    adapter = request.query_params.get(QUERY_PARAM_ADAPTER, QUERY_VALUE_LOCAL)
    path = request.query_params.get(QUERY_PARAM_PATH, "/")
    search_query = request.query_params.get(QUERY_PARAM_QUERY)
    include_extensions = request.query_params.get("include_extensions")
    exclude_extensions = request.query_params.get("exclude_extensions")
    case_sensitive = request.query_params.get("case_sensitive", "false").lower() == "true"

    # Normalize path
    if path.startswith(f"{QUERY_VALUE_LOCAL}://"):
        path = path.split("://")[-1]
    if not path.startswith('/'):
        path = '/' + path
    if path == "//":
        path = "/"

    if not search_query:
        logger.warning("Search content endpoint called without a 'query' parameter.")
        return JSONResponse(content={"error": "Search 'query' parameter is required."}, status_code=400)

    logger.info("Searching file content with query: '%s' in path: '%s' using adapter: %s", search_query, path, adapter)

    try:
        # Parse extension filters
        include_exts = [ext.strip() for ext in include_extensions.split(",")] if include_extensions else None
        exclude_exts = [ext.strip() for ext in exclude_extensions.split(",")] if exclude_extensions else None

        # Assuming FileManager has a search_content method
        file_response = await asyncio.to_thread(
            file_manager.search_content,
            adapter=adapter,
            path=path,
            query=search_query,
            include_extensions=include_exts,
            exclude_extensions=exclude_exts,
            case_sensitive=case_sensitive
        )
    except ValueError as e:
        logger.error("Error during content search: %s", e)
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except AttributeError:
        logger.error("FileManager does not have search_content method")
        return JSONResponse(content={"error": "Content search not supported"}, status_code=501)
    
    return file_response


# Made with ❤️ by codx-junior