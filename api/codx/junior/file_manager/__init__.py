import logging
from pathlib import Path
from typing import Any, Dict, List, Union
import os

# Setting up logging
logger = logging.getLogger(__name__)

# Constants for file types and visibility status
FILE_TYPE_DIR = "dir"
FILE_TYPE_FILE = "file"
VISIBILITY_PUBLIC = "public"
DEFAULT_ENCODING = "utf-8"
STORAGE_LOCAL = "local"

class FileManager:
    """
    A class to manage and find files based on the settings provided.
    """
    settings: 'CODXJuniorSettings'

    def __init__(self, settings: 'CODXJuniorSettings') -> None:
        """
        Initialize the FileManager with settings.

        Args:
            settings (CODXJuniorSettings): Configuration settings for file management.
        """
        self.settings = settings
        logger.debug("FileManager initialized with CODXJuniorSettings: %s", settings)

    def get_file_path(self, path):
        local_path = path
        if local_path == '/':
            local_path = ''
        elif local_path[0] == '/':
            local_path = local_path[1:]
        
        return os.path.join(self.settings.project_path, local_path)         
        

    def find_files(self, adapter: str, path: str, search: str = None) -> Dict[str, Union[str, List[Dict[str, Any]]]]:
        """
        Find files in the specified path using the given adapter.

        Args:
            adapter (str): The storage adapter to use (e.g., "local").
            path (str): The path to search for files.

        Returns:
            Dict[str, Union[str, List[Dict[str, Any]]]]: A dictionary containing file information.
        """
        abs_base_path = self.get_file_path(path)         
        dirname = abs_base_path.replace(self.settings.project_path, '')
        if dirname[0] != '/':
            dirname = ("/%s", dirname) 
        result = {
            "adapter": adapter,
            "storages": [self.settings.project_name],
            "dirname": dirname,
            "files": []
        }

        logger.debug("Finding files with adapter %s at path %s", adapter, abs_base_path)
        try:
            base_path = Path(abs_base_path)
            if not base_path.exists():
                logger.error("Path does not exist: %s", path)
                return result

            for item in base_path.iterdir():
                file_info = self._get_file_info(item)
                result["files"].append(file_info)
                # logger.info("Found file: %s", file_info)

        except OSError as e:
            logger.error("An error occurred during file search: %s", e)

        return result

    def get_mime_type(self, file_path: str) -> str:
        extension_to_mime = {
            # Image MIME types
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".ico": "image/x-icon",
            ".tif": "image/tiff",
            ".tiff": "image/tiff",
            ".eps": "image/eps",
            ".raw": "image/raw",
            ".cr2": "image/x-canon-cr2",
            ".nef": "image/x-nikon-nef",
            ".orf": "image/x-olympus-orf",
            ".sr2": "image/x-sony-sr2",
            ".ppm": "image/x-portable-pixmap",
            ".heif": "image/heif",

            # Application MIME types
            ".zip": "application/zip",
            ".pdf": "application/pdf",
            ".profile": "application/x-profile",

            # Video MIME types
            ".flv": "video/x-flv",
            ".avi": "video/x-msvideo",
            ".mp4": "video/mp4",
            ".3gp": "video/3gpp",
            ".mov": "video/quicktime",
            ".webm": "video/webm",
            ".ogg": "video/ogg",
            ".qt": "video/quicktime",
            ".avchd": "video/avchd",

            # Audio MIME types
            ".flac": "audio/flac",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".wma": "audio/x-ms-wma",
            ".aac": "audio/aac",
        }

        # Extract the file extension from the path
        ext = "." + file_path.split(".")[-1]

        # Get the MIME type from the dictionary, default to "text/plain" if not found
        return extension_to_mime.get(ext, "text/plain")

    def _get_file_info(self, item: Path) -> Dict[str, Any]:
        """
        Get detailed information about a file or directory.

        Args:
            item (Path): The file or directory path.

        Returns:
            Dict[str, Any]: A dictionary containing information about the file or directory.
        """
        file_path = str(item)
        file_type = FILE_TYPE_DIR if item.is_dir() else FILE_TYPE_FILE
        file_name = file_path.replace(self.settings.project_path, '')
        info = {
            "type": file_type,
            "path": file_name,
            "visibility": VISIBILITY_PUBLIC,
            "last_modified": int(item.stat().st_mtime),
            "extra_metadata": [],
            "basename": item.name,
            "extension": item.suffix[1:] if file_type == FILE_TYPE_FILE else "",
            "storage": STORAGE_LOCAL,
        }

        if file_type == FILE_TYPE_FILE:
            info["file_size"] = item.stat().st_size
            info["mime_type"] = self.get_mime_type(item.name)

        return info
