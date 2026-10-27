import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Union

# Setting up logging
logger = logging.getLogger(__name__)

# Constants for file types and visibility status
FILE_TYPE_DIR = "dir"
FILE_TYPE_FILE = "file"
VISIBILITY_PUBLIC = "public"
DEFAULT_ENCODING = "utf-8"
STORAGE_LOCAL = "local"
DEFAULT_MIME_TYPE = "text/plain"

# Extension -> MIME type lookup table.
#
# It used to be re-created inside `get_mime_type` for every directory entry.
# Listing a folder with a few thousand files meant building the same 40 entries
# dict a few thousand times, which is pure (and useless) Python work. Building
# it once turns the per-entry cost into a single dict lookup.
MIME_TYPES = {
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


def _env_float(name: str, default: float) -> float:
    """Read a float from the environment, falling back to ``default``."""
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# Short lived cache of directory listings.
#
# A file explorer navigates back and forth between the same folders, and each
# navigation used to walk the filesystem again. A listing is cached per
# absolute directory path and validated against the directory `st_mtime_ns`,
# so creating, deleting or renaming an entry (including uploads) invalidates it
# automatically. The TTL only bounds how stale the per-file metadata
# (`last_modified` / `file_size`) can get when a file content changes in place.
LISTING_CACHE_TTL = _env_float("CODX_JUNIOR_FILE_LISTING_CACHE_TTL", 2.0)
LISTING_CACHE_MAX_DIRS = 128
_LISTING_CACHE: Dict[str, Any] = {}
_LISTING_CACHE_LOCK = threading.Lock()


def clear_listing_cache() -> None:
    """Drop every cached directory listing."""
    with _LISTING_CACHE_LOCK:
        _LISTING_CACHE.clear()


def _get_cached_listing(abs_path: str, dir_mtime_ns: int) -> Optional[List[Dict[str, Any]]]:
    """Return a cached listing when it is still valid for the directory mtime."""
    with _LISTING_CACHE_LOCK:
        cached = _LISTING_CACHE.get(abs_path)
    if not cached:
        return None

    timestamp, cached_mtime_ns, files = cached
    if cached_mtime_ns != dir_mtime_ns:
        return None
    if time.monotonic() - timestamp > LISTING_CACHE_TTL:
        return None
    return files


def _store_cached_listing(abs_path: str, dir_mtime_ns: int, files: List[Dict[str, Any]]) -> None:
    """Store a directory listing, keeping the cache bounded."""
    with _LISTING_CACHE_LOCK:
        if len(_LISTING_CACHE) >= LISTING_CACHE_MAX_DIRS:
            _LISTING_CACHE.clear()
        _LISTING_CACHE[abs_path] = (time.monotonic(), dir_mtime_ns, files)


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
            search (str, optional): Case insensitive basename filter.

        Returns:
            Dict[str, Union[str, List[Dict[str, Any]]]]: A dictionary containing file information.
        """
        abs_base_path = self.get_file_path(path)
        result = {
            "adapter": adapter,
            "storages": [self.settings.project_name],
            "dirname": self._to_project_dirname(abs_base_path),
            "files": []
        }

        logger.debug("Finding files with adapter %s at path %s", adapter, abs_base_path)

        try:
            if not os.path.isdir(abs_base_path):
                logger.error("Path does not exist: %s", path)
                return result
            files = self._list_directory(abs_base_path)
        except OSError as e:
            logger.error("An error occurred during file search: %s", e)
            return result

        # Filtering happens on the (cached) full listing so a search does not
        # populate the cache with a partial result.
        if search:
            needle = search.lower()
            files = [f for f in files if needle in f["basename"].lower()]

        result["files"] = files
        return result

    def _to_project_dirname(self, abs_path: str) -> str:
        """
        Return the project relative version of a directory path.

        Args:
            abs_path (str): Absolute (or project rooted) directory path.

        Returns:
            str: Project relative path using forwards slashes, "/" for the root.
        """
        project_path = (self.settings.project_path or "").rstrip("/")
        normalized = str(abs_path).replace("\\", "/")

        if project_path:
            if normalized in (project_path, f"{project_path}/"):
                return "/"
            if normalized.startswith(f"{project_path}/"):
                return normalized[len(project_path):]

        return normalized or "/"

    def _to_relative_path(self, file_path: str) -> str:
        """
        Return the project relative version of a file path.

        Args:
            file_path (str): Absolute (or project rooted) file path.

        Returns:
            str: Project relative path.
        """
        project_path = (self.settings.project_path or "").rstrip("/")
        normalized = str(file_path).replace("\\", "/")

        if project_path and normalized.startswith(f"{project_path}/"):
            return normalized[len(project_path):]

        return normalized

    def _list_directory(self, abs_path: str) -> List[Dict[str, Any]]:
        """
        List a directory, reusing a cached listing when the folder did not change.

        Args:
            abs_path (str): Directory to list.

        Returns:
            List[Dict[str, Any]]: Sorted entries (folders first, then name).
        """
        dir_mtime_ns = None
        try:
            dir_mtime_ns = os.stat(abs_path).st_mtime_ns
            cached = _get_cached_listing(abs_path, dir_mtime_ns)
            if cached is not None:
                # Copy the list: callers must not be able to mutate the cache.
                return list(cached)
        except OSError as e:
            logger.debug("Could not stat %s: %s", abs_path, e)

        files = self._read_directory(abs_path)

        if dir_mtime_ns is not None:
            _store_cached_listing(abs_path, dir_mtime_ns, files)

        return files

    def _read_directory(self, abs_path: str) -> List[Dict[str, Any]]:
        """
        Read a directory from the filesystem.

        Args:
            abs_path (str): Directory to read.

        Returns:
            List[Dict[str, Any]]: Sorted entries (folders first, then name).
        """
        files: List[Dict[str, Any]] = []
        try:
            # `os.scandir` reuses the `d_type` of each entry, so listing does not
            # need an extra syscall per entry to know if it is a directory.
            with os.scandir(abs_path) as entries:
                for entry in entries:
                    file_info = self._get_file_info(entry)
                    if file_info:
                        files.append(file_info)
        except OSError as e:
            logger.error("An error occurred while listing %s: %s", abs_path, e)
            return files

        # Folders first, then case insensitive name: the client renders the
        # list as it arrives and no longer has to sort it on every render.
        files.sort(key=lambda f: (f["type"] != FILE_TYPE_DIR, f["basename"].lower()))
        return files

    def get_mime_type(self, file_path: str) -> str:
        """
        Return the MIME type of a file based on its extension.

        Args:
            file_path (str): File name or path.

        Returns:
            str: MIME type, "text/plain" when the extension is unknown.
        """
        extension = os.path.splitext(file_path)[1].lower()
        return MIME_TYPES.get(extension, DEFAULT_MIME_TYPE)

    def _get_file_info(self, entry) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a directory entry.

        Args:
            entry (os.DirEntry): Entry returned by ``os.scandir``.

        Returns:
            Optional[Dict[str, Any]]: Information about the file or directory,
            or None when the entry can not be read (broken symlink, permissions).
        """
        try:
            # `os.DirEntry` caches its stat result, so `last_modified` and
            # `file_size` are read with a single system call. The previous
            # implementation called `stat()` up to three times per entry.
            stat_result = entry.stat()
            is_dir = entry.is_dir()
        except OSError as e:
            logger.warning("Skipping unreadable entry %s: %s", entry.path, e)
            return None

        file_type = FILE_TYPE_DIR if is_dir else FILE_TYPE_FILE
        info = {
            "type": file_type,
            "path": self._to_relative_path(entry.path),
            "visibility": VISIBILITY_PUBLIC,
            "last_modified": int(stat_result.st_mtime),
            "extra_metadata": [],
            "basename": entry.name,
            "extension": "" if is_dir else os.path.splitext(entry.name)[1][1:],
            "storage": STORAGE_LOCAL,
        }

        if file_type == FILE_TYPE_FILE:
            info["file_size"] = stat_result.st_size
            info["mime_type"] = self.get_mime_type(entry.name)

        return info