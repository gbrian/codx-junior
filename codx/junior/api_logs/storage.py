import json
import logging
import os
import threading
from datetime import datetime
from typing import List, Optional

from codx.junior.api_logs.model import ApiCallEvent

logger = logging.getLogger(__name__)

# One file per day to keep individual files small
FILE_DATE_FORMAT = "%Y-%m-%d"


class ApiLogStorage:
    """
    Incremental append-only storage for API call performance events.

    Files are written under:
        <logs_path>/<YYYY-MM-DD>_api_calls.jsonl

    The logs path is a global directory shared across all projects, initialised
    from the ``CODX_JUNIOR_API_LOGS_DATA_PATH`` environment variable (see
    ``codx.junior.globals.API_LOGS_DATA_PATH``).

    Each line is a JSON-encoded ``ApiCallEvent`` dict (JSONL format).
    A threading lock guards concurrent writes within the same process.

    Diagram:
    classDiagram
        class ApiLogStorage {
            +str base_path
            +write(event: ApiCallEvent) void
            +read_events(...) List[ApiCallEvent]
            +list_available_dates() List[str]
        }
    """

    _lock = threading.Lock()

    def __init__(self, logs_path: str) -> None:
        """
        Args:
            logs_path: Global directory where all API performance JSONL files
                       are stored. Typically set from
                       ``CODX_JUNIOR_API_LOGS_DATA_PATH``.
        """
        self.base_path = logs_path
        os.makedirs(self.base_path, exist_ok=True)
        logger.info("ApiLogStorage initialized at: %s", self.base_path)

    # ── Helpers ─────────────────────────────────────────────────────────────────

    def _file_path_for_date(self, iso_date: str) -> str:
        """Return the API call JSONL file path for a given ISO date."""
        return os.path.join(self.base_path, f"{iso_date}_api_calls.jsonl")

    def _current_file_path(self) -> str:
        """Get current API call file path for today."""
        today = datetime.utcnow().strftime(FILE_DATE_FORMAT)
        return self._file_path_for_date(today)

    # ── Write ───────────────────────────────────────────────────────────────────

    def write(self, event: ApiCallEvent) -> None:
        """
        Append an ApiCallEvent to today's JSONL file.

        Thread-safe via module-level lock. Logs on success and errors.

        Args:
            event: The API call event to persist.
        """
        file_path = self._current_file_path()
        line = json.dumps(event.to_dict(), ensure_ascii=False)
        with self._lock:
            try:
                with open(file_path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
                logger.debug(
                    "ApiLogStorage: wrote api call method=%s path=%s status=%s duration=%.3fs",
                    event.method,
                    event.path,
                    event.status_code,
                    event.duration_seconds,
                )
            except OSError as ex:
                logger.error("ApiLogStorage.write failed: %s", ex)

    # ── Read ────────────────────────────────────────────────────────────────────

    def read_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        path: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        username: Optional[str] = None,
        project_name: Optional[str] = None,
        project_id: Optional[str] = None,
        min_duration_seconds: Optional[float] = None,
        errors_only: bool = False,
    ) -> List[ApiCallEvent]:
        """
        Read and optionally filter stored API call events from JSONL files.

        Args:
            start_date:           Inclusive ISO date lower bound (YYYY-MM-DD).
            end_date:             Inclusive ISO date upper bound (YYYY-MM-DD).
            path:                 Filter by exact path (route template).
            method:               Filter by HTTP method (case-insensitive).
            status_code:          Filter by exact status code.
            username:             Filter by exact username.
            project_name:         Filter by exact project name.
            project_id:           Filter by exact project id.
            min_duration_seconds: Only include calls slower than this value.
            errors_only:          Only include failed calls (error or status >= 500).

        Returns:
            List of matching ApiCallEvent objects ordered by timestamp.
        """
        available = self.list_available_dates()
        matching_files = []

        for date_str in available:
            if start_date and date_str < start_date:
                continue
            if end_date and date_str > end_date:
                continue
            matching_files.append(self._file_path_for_date(date_str))

        events: List[ApiCallEvent] = []
        for file_path in matching_files:
            events.extend(self._read_file(file_path))

        # Apply filters
        if path:
            events = [e for e in events if e.path == path]
        if method:
            events = [e for e in events if e.method.upper() == method.upper()]
        if status_code is not None:
            events = [e for e in events if e.status_code == status_code]
        if username:
            events = [e for e in events if e.username == username]
        if project_name:
            events = [e for e in events if e.project_name == project_name]
        if project_id:
            events = [e for e in events if e.project_id == project_id]
        if min_duration_seconds is not None:
            events = [e for e in events if e.duration_seconds >= min_duration_seconds]
        if errors_only:
            events = [e for e in events if e.error or e.status_code >= 500]

        events.sort(key=lambda e: e.timestamp)
        return events

    # ── Internal Readers ───────────────────────────────────────────────────────

    def _read_file(self, file_path: str) -> List[ApiCallEvent]:
        """Parse single JSONL file into list of events, skipping bad lines."""
        events: List[ApiCallEvent] = []
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        events.append(ApiCallEvent.from_dict(data))
                    except (json.JSONDecodeError, TypeError, ValueError) as ex:
                        logger.warning(
                            "Skipping malformed api log line %d in %s: %s",
                            line_no,
                            file_path,
                            ex,
                        )
        except FileNotFoundError:
            pass
        except OSError as ex:
            logger.error("Error reading api log file %s: %s", file_path, ex)
        return events

    # ── Date Management ─────────────────────────────────────────────────────────

    def list_available_dates(self) -> List[str]:
        """
        Return sorted list of ISO date strings for which data files exist.

        Returns:
            Sorted list of YYYY-MM-DD strings in ascending order.
        """
        dates: List[str] = []
        try:
            for fname in os.listdir(self.base_path):
                if fname.endswith("_api_calls.jsonl"):
                    date_part = fname.replace("_api_calls.jsonl", "")
                    # Basic sanity check — must be 10 chars YYYY-MM-DD
                    if len(date_part) == 10:
                        dates.append(date_part)
        except OSError as ex:
            logger.error("Error listing api log directory: %s", ex)
        return sorted(dates)

# Made with ❤️ by codx-junior
