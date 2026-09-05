import os
import logging
from fastapi import APIRouter, Request, Response, status, UploadFile, File, Form
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
    Supports both substring and regex pattern matching.

    Query params:
    - search: Pattern to search for in file paths (case-insensitive)
    - search_path: Optional subdirectory to limit search scope (relative to project root)
    - page: Page number (0-indexed, default 0)
    - page_size: Number of results per page (default 50)
    - raw_search: If true, search all files. If false, exclude .git (default false)
    - use_regex: If true, treat search pattern as regex. If false, use substring match (default false)
    """
    codx_junior_session = request.state.codx_junior_session
    file_engine = codx_junior_session.get_file_engine()

    search = request.query_params.get("search", "")
    search_path = request.query_params.get("search_path")
    page = int(request.query_params.get("page", 0))
    page_size = int(request.query_params.get("page_size", 50))
    raw_search = request.query_params.get("raw_search", "").lower() == "true"
    use_regex = request.query_params.get("use_regex", "").lower() == "true"

    if not search:
        return {"page": 0, "total_files": 0, "page_size": page_size, "files": []}

    return file_engine.search_files(
        search=search,
        search_path=search_path,
        page=page,
        page_size=page_size,
        raw_search=raw_search,
        use_regex=use_regex,
    )


@router.get("/files/search-content")
async def search_files_content(request: Request):
    """
    Search for files whose content contains the search query.
    Performs a filesystem content search within the project scope with pagination support.
    Supports both substring and regex pattern matching.

    Query params:
    - q: Pattern to search for in file contents
    - search_path: Optional subdirectory to limit search scope (relative to project root)
    - page: Page number (0-indexed, default 0)
    - page_size: Number of results per page (default 50)
    - case_sensitive: Whether search should be case-sensitive (default false)
    - raw_search: If true, search all files. If false, exclude .git (default false)
    - use_regex: If true, treat query as regex pattern. If false, use substring match (default false)
    """
    codx_junior_session = request.state.codx_junior_session
    file_engine = codx_junior_session.get_file_engine()

    query = request.query_params.get("q", "")
    search_path = request.query_params.get("search_path")
    page = int(request.query_params.get("page", 0))
    page_size = int(request.query_params.get("page_size", 50))
    case_sensitive = request.query_params.get("case_sensitive", "").lower() == "true"
    raw_search = request.query_params.get("raw_search", "").lower() == "true"
    use_regex = request.query_params.get("use_regex", "").lower() == "true"

    if not query:
        return {
            "page": 0,
            "total_files": 0,
            "total_matches": 0,
            "page_size": page_size,
            "results": [],
            "error": "Missing (q)uery parameter"
        }

    return file_engine.search_files_content(
        query=query,
        search_path=search_path,
        page=page,
        page_size=page_size,
        case_sensitive=case_sensitive,
        raw_search=raw_search,
        use_regex=use_regex,
    )


@router.post("/files/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    path: str = Form(""),
    process: bool = Form(False),
):
    """
    Upload a single file to the project.

    Form data:
    - file: File to upload (required)
    - path: Target file path within project (relative to project root, required)
    - process: Whether to apply file profiles before saving (default false)

    Returns:
        Dict with upload metadata including file path, size, and modification time.

    Raises:
        400: If required parameters are missing or invalid
        413: If file size exceeds limits
    """
    if not path:
        logger.warning("Upload request missing required path parameter")
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="Missing required parameter: path"
        )
    if path[0] == '/':
        path = path[1:]
    path = os.path.join(path, file.filename)
    
    codx_junior_session = request.state.codx_junior_session
    file_engine = codx_junior_session.get_file_engine()

    try:
        # Read uploaded file content
        file_content = await file.read()
        logger.info(
            "Uploading file: %s (size: %d bytes, process: %s)",
            path,
            len(file_content),
            process
        )

        # Upload the file
        result = await file_engine.upload_file(
            file_path=path,
            file_content=file_content,
            process=process,
        )

        logger.info("Successfully uploaded file: %s", path)
        return result

    except ValueError as ex:
        logger.warning("Validation error during file upload: %s", ex)
        return Response(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content=str(ex)
        )
    except OSError as ex:
        logger.error("Error uploading file %s: %s", path, ex)
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Error uploading file: {ex}"
        )


@router.post("/files/upload-multiple")
async def upload_multiple_files(
    request: Request,
    files: list[UploadFile] = File(...),
    process: bool = Form(False),

):
    """
    Upload multiple files to the project in batch.

    Form data:
    - files: List of files to upload (required)
    - process: Whether to apply file profiles before saving (default false)

    Note: Files must include path information in their filename or
    be uploaded with a naming convention that indicates their target paths.
    Each file should have its path embedded in the filename using ':' as separator.
    Example: "src/app.py" or use the path parameter repeated for each file.

    Returns:
        Dict with batch upload results containing:
        - successful: List of successfully uploaded files
        - failed: List of failed uploads with error details
        - total_files: Total number of files attempted
        - total_size_uploaded: Total size of successfully uploaded files

    Raises:
        400: If files list is empty
        413: If total upload size exceeds limits
    """
    if not files:
        logger.warning("Upload request with no files")
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="No files provided for upload"
        )

    codx_junior_session = request.state.codx_junior_session
    file_engine = codx_junior_session.get_file_engine()

    try:
        # Prepare file uploads list
        file_uploads = []
        for uploaded_file in files:
            file_content = await uploaded_file.read()
            # Use the uploaded filename as the target path
            target_path = uploaded_file.filename or "uploaded_file"
            file_uploads.append((target_path, file_content))

        logger.info(
            "Starting batch upload of %d files (process: %s)",
            len(file_uploads),
            process
        )

        # Upload all files
        result = await file_engine.upload_files(
            file_uploads=file_uploads,
            process=process,
        )

        logger.info(
            "Batch upload completed: %d successful, %d failed",
            len(result["successful"]),
            len(result["failed"])
        )

        return result

    except ValueError as ex:
        logger.warning("Validation error during batch upload: %s", ex)
        return Response(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content=str(ex)
        )
    except OSError as ex:
        logger.error("Error during batch upload: %s", ex)
        return Response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Error during batch upload: {ex}"
        )


# Made with ❤️ by codx-junior