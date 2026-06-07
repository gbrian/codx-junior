import os
import json
import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from codx.junior.analytics.model import TokenUsageEvent

logger = logging.getLogger(__name__)

# One file per day to keep individual files small
FILE_DATE_FORMAT = "%Y-%m-%d"


class AnalyticsStorage:
    """
    Incremental append-only storage for analytics events.

    Files are written under:
        <analytics_path>/<YYYY-MM-DD>_token_usage.jsonl

    The analytics path is a global directory shared across all projects,
    initialised from the ``CODX_JUNIOR_API_ANALYTICS_DATA_PATH`` environment
    variable (see ``codx.junior.globals.ANALYTICS_DATA_PATH``).

    Each line is a JSON-encoded ``TokenUsageEvent`` dict (JSONL format).
    A threading lock guards concurrent writes within the same process.

    Diagram:
    classDiagram
        class AnalyticsStorage {
            +str base_path
            +write(event: TokenUsageEvent)
            +read_events(start_date, end_date, username, project_name) List
            +list_available_dates() List[str]
        }
    """

    _lock = threading.Lock()

    def __init__(self, analytics_path: str):
        """
        Args:
            analytics_path: Global directory where all analytics JSONL files
                            are stored.  Typically set from
                            ``CODX_JUNIOR_API_ANALYTICS_DATA_PATH``.
        """
        self.base_path = analytics_path
        os.makedirs(self.base_path, exist_ok=True)
        logger.info("AnalyticsStorage initialised at: %s", self.base_path)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _file_path_for_date(self, iso_date: str) -> str:
        """Return the JSONL file path for a given ISO date string."""
        return os.path.join(self.base_path, f"{iso_date}_token_usage.jsonl")

    def _current_file_path(self) -> str:
        today = datetime.utcnow().strftime(FILE_DATE_FORMAT)
        return self._file_path_for_date(today)

    # ── Write ──────────────────────────────────────────────────────────────────

    def write(self, event: TokenUsageEvent) -> None:
        """
        Append a single ``TokenUsageEvent`` to today's JSONL file.

        Thread-safe via a module-level lock.

        Args:
            event: The analytics event to persist.
        """
        file_path = self._current_file_path()
        line = json.dumps(event.to_dict(), ensure_ascii=False)
        with self._lock:
            try:
                with open(file_path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
                logger.debug(
                    "Analytics: wrote event user=%s model=%s in=%d out=%d",
                    event.username,
                    event.model,
                    event.input_tokens,
                    event.output_tokens,
                )
            except Exception as ex:
                logger.error("AnalyticsStorage.write failed: %s", ex)

    # ── Read ───────────────────────────────────────────────────────────────────

    def read_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        username: Optional[str] = None,
        project_name: Optional[str] = None,
        project_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> List[TokenUsageEvent]:
        """
        Read and optionally filter stored events from JSONL files.

        Args:
            start_date:   Inclusive ISO date lower bound (``YYYY-MM-DD``).
            end_date:     Inclusive ISO date upper bound (``YYYY-MM-DD``).
            username:     Filter by exact username.
            project_name: Filter by exact project name.
            project_id:   Filter by exact project id.
            model:        Filter by exact model name.

        Returns:
            List of matching ``TokenUsageEvent`` objects ordered by timestamp.
        """
        available = self.list_available_dates()
        matching_files = []

        for date_str in available:
            if start_date and date_str < start_date:
                continue
            if end_date and date_str > end_date:
                continue
            matching_files.append(self._file_path_for_date(date_str))

        events: List[TokenUsageEvent] = []
        for file_path in matching_files:
            events.extend(self._read_file(file_path))

        # Apply filters
        if username:
            events = [e for e in events if e.username == username]
        if project_name:
            events = [e for e in events if e.project_name == project_name]
        if project_id:
            events = [e for e in events if e.project_id == project_id]
        if model:
            events = [e for e in events if e.model == model]

        events.sort(key=lambda e: e.timestamp)
        return events

    def _read_file(self, file_path: str) -> List[TokenUsageEvent]:
        """Parse a single JSONL file into a list of events, skipping bad lines."""
        events: List[TokenUsageEvent] = []
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        events.append(TokenUsageEvent.from_dict(data))
                    except Exception as ex:
                        logger.warning(
                            "Skipping malformed analytics line %d in %s: %s",
                            line_no,
                            file_path,
                            ex,
                        )
        except FileNotFoundError:
            pass
        except Exception as ex:
            logger.error("Error reading analytics file %s: %s", file_path, ex)
        return events

    def list_available_dates(self) -> List[str]:
        """
        Return sorted list of ISO date strings for which data files exist.

        Returns:
            Sorted list of ``YYYY-MM-DD`` strings.
        """
        dates: List[str] = []
        try:
            for fname in os.listdir(self.base_path):
                if fname.endswith("_token_usage.jsonl"):
                    date_part = fname.replace("_token_usage.jsonl", "")
                    # Basic sanity check — must be 10 chars YYYY-MM-DD
                    if len(date_part) == 10:
                        dates.append(date_part)
        except Exception as ex:
            logger.error("Error listing analytics directory: %s", ex)
        return sorted(dates)