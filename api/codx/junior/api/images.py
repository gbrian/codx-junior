"""
Images router – serves and stores the images of a project.

Images (AI generated images, images uploaded to a chat...) are project
resources: they are stored inside the project folder
(``settings.images_folder``, ``.codx/images`` by default) and served by this
router, instead of the global ``CODX_JUNIOR_STATIC_FOLDER`` static mount that is
shared by every project.

Route layout
------------
GET  /api/images/{file_path}  – serve a file from the project images folder
POST /api/images              – upload an image into the project images folder

The project is identified by the ``codx_path`` query parameter (or the
``x-codx-path`` header), which the app middleware uses to expose
``request.state.codx_junior_session``. URLs built by
``CODXJuniorSettings.get_image_url`` already carry the query parameter, so a
plain ``<img src="...">`` works.

Diagram
-------
graph TD
    A[ImageEngine.generate_image] -->|writes| B[<project>/.codx/images/generated]
    C[POST /api/images] -->|writes| D[<project>/.codx/images/message]
    B --> E[GET /api/images/generated/x.png?codx_path=...]
    D --> E
"""

import hashlib
import logging
import mimetypes
import os

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["images"])

# Extensions accepted by the upload endpoint
ALLOWED_IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]

# Sub folder used for the images attached to a chat message
MESSAGE_IMAGES_SUB_FOLDER = "message"


def _get_settings(request: Request) -> CODXJuniorSettings:
    """
    Return the project settings resolved for the incoming request.

    Args:
        request: Incoming request carrying the middle injected session.

    Returns:
        The project settings of the request.

    Raises:
        HTTPException: 400 when the request does not identify a project
            (missing ``codx_path``).
    """
    session = getattr(request.state, "codx_junior_session", None)
    settings = getattr(session, "settings", None)
    if not settings:
        logger.warning("Images request without project context: %s", request.url)
        raise HTTPException(
            status_code=400,
            detail="Missing codx_path: the project could not be resolved",
        )
    return settings


def _resolve_image_path(settings: CODXJuniorSettings, file_path: str) -> str:
    """
    Resolve and validate the absolute path of an image file.

    The path is confined to the project images folder: a resolved path outside
    of it is rejected, so ``../`` sequences cannot read other project files.

    Args:
        settings: Project settings.
        file_path: Path relative to the images folder.

    Returns:
        Absolute path of the image file.

    Raises:
        HTTPException: 400 when the path escapes the images folder.
    """
    images_root = os.path.realpath(settings.get_images_folder_path())
    requested_path = os.path.realpath(
        os.path.join(images_root, (file_path or "").lstrip("/"))
    )

    if requested_path != images_root and not requested_path.startswith(images_root + os.sep):
        logger.warning("Invalid image path '%s' for %s", file_path, images_root)
        raise HTTPException(status_code=400, detail="Invalid image path")

    return requested_path


@router.get("/images/{file_path:path}")
def api_get_image(file_path: str, request: Request):
    """
    Serve a file stored in the project images folder.

    Args:
        file_path: Path relative to the images folder, e.g.
            ``generated/a1b2c3.png``.
        request: Incoming request (must identify the project).

    Returns:
        The image file, with the MIME type guessed from the extension.

    Raises:
        HTTPException: 400 for an invalid path, 404 when the file is missing.

    Example:
        GET /api/images/generated/a1b2c3.png?codx_path=%2Fprojects%2Fapp%2F.codx
    """
    settings = _get_settings(request)
    image_path = _resolve_image_path(settings, file_path)

    if not os.path.isfile(image_path):
        logger.warning("Image not found: %s", image_path)
        raise HTTPException(status_code=404, detail="Image not found")

    media_type, _ = mimetypes.guess_type(image_path)
    return FileResponse(
        image_path,
        media_type=media_type or "application/octet-stream",
        filename=os.path.basename(image_path),
    )


@router.post("/images")
async def api_upload_image(request: Request, file: UploadFile = File(...)):
    """
    Upload an image into the project images folder.

    The file is stored under the ``message`` sub folder using the MD5 of its
    content as name (so uploading the same image twice does not duplicate it)
    and returned with the URL served by :func:`api_get_image`.

    Args:
        request: Incoming request (must identify the project).
        file: Image file uploaded by the client.

    Returns:
        Dict with ``path`` (relative to the images folder), ``url`` and
        ``size`` (bytes).

    Raises:
        HTTPException: 400 for an empty file or a missing extension, 413 when
            the file exceeds ``image_max_file_size_mb``, 415 for an unsupported
            extension.

    Example:
        POST /api/images?codx_path=/projects/app/.codx  (multipart field: file)
        -> {"path": "message/a1b2c3.png",
            "url": "/api/images/message/a1b2c3.png?codx_path=%2Fprojects...",
            "size": 20480}
    """
    settings = _get_settings(request)

    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="Empty image file")

    max_bytes = settings.get_image_max_file_size_mb() * 1024 * 1024
    if len(file_content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                "Image too large: %d bytes (max %d MB)"
                % (len(file_content), settings.get_image_max_file_size_mb())
            ),
        )

    extension = os.path.splitext(file.filename or "")[1].lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                "Unsupported image extension '%s'. Allowed: %s"
                % (extension or "", ", ".join(ALLOWED_IMAGE_EXTENSIONS))
            ),
        )

    relative_path = f"{MESSAGE_IMAGES_SUB_FOLDER}/{hashlib.md5(file_content).hexdigest()}{extension}"
    image_path = os.path.join(settings.get_images_folder_path(), relative_path)

    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    if not os.path.exists(image_path):
        with open(image_path, "wb") as file_object:
            file_object.write(file_content)
        logger.info("Image uploaded: %s", image_path)

    return {
        "path": relative_path,
        "url": settings.get_image_url(relative_path),
        "size": len(file_content),
    }

# Made with ❤️ by codx-junior