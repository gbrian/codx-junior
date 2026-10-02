"""
Reader for raw AI JSONL log files produced by :class:`RawAILogger`.

Provides filtering, pagination helpers, and single-record lookup over the
per-day ``<YYYY-MM-DD>_raw_ai.jsonl`` files written by the logger.

Diagram:
---------
```mermaid
classDiagram
    class RawLogReader {
        +str base_path
        +list_log_files(start_date, end_date) List[Path]
        +read_events(start_date, end_date, username, project, model, provider, session_id) List[Dict]
        +read_event_by_id(log_id) Optional[Dict]
        +delete_event_by_id(log_id) bool
        +delete_events(start_date, end_date, username, project, model) int
    }
```
"""

import json
import logging
import os
import threading
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional

from codx.junior.globals import CODX_JUNIOR_AI_RAW_LOG_PATH

logger = logging.getLogger(__name__)

# Date format used in file names by RawAILogger
FILE_DATE_FORMAT = "%Y-%m-%d"
FILE_SUFFIX = "_raw_ai.jsonl"

_lock = threading.Lock()


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """
    Parse an ISO date string ``YYYY-MM-DD`` to a :class:`datetime.date`.

    Args:
        date_str: Date string to parse, or ``None``.

    Returns:
        Parsed :class:`datetime.date`, or ``None`` if input is falsy.
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, FILE_DATE_FORMAT).date()
    except ValueError:
        logger.warning("_parse_date: cannot parse date string %r", date_str)
        return None


def _file_date(file_path: Path) -> Optional[date]:
    """
    Extract the date from a JSONL log file name.

    Expected pattern: ``YYYY-MM-DD_raw_ai.jsonl``

    Args:
        file_path: Path to the JSONL file.

    Returns:
        Parsed :class:`datetime.date`, or ``None`` on failure.
    """
    stem = file_path.name.replace(FILE_SUFFIX, "")
    return _parse_date(stem)


def _record_matches_filters(
    record: Dict[str, Any],
    username: Optional[str],
    project: Optional[str],
    model: Optional[str],
    provider: Optional[str],
    session_id: Optional[str],
) -> bool:
    """
    Return ``True`` when *record* satisfies all provided filter criteria.

    ``None`` means "no filter on that field".

    Args:
        record:     A single JSONL log record dict.
        username:   Optional username filter.
        project:    Optional project name filter.
        model:      Optional model name filter.
        provider:   Optional provider name filter.
        session_id: Optional session id filter.

    Returns:
        Boolean match result.
    """
    if username and record.get("username") != username:
        return False
    if project and record.get("project") != project:
        return False
    if model and record.get("model") != model:
        return False
    if provider and record.get("provider") != provider:
        return False
    if session_id and record.get("session_id") != session_id:
        return False
    return True


class RawLogReader:
    """
    Read and filter raw AI JSONL log files produced by :class:`RawAILogger`.

    Each JSONL file is named ``<YYYY-MM-DD>_raw_ai.jsonl`` and lives under
    ``base_path``.  Each line in a file is a JSON object (one per AI
    request or response event).

    A synthetic ``log_id`` is assigned to every record using the pattern::

        <YYYY-MM-DD>:<line_index>

    This makes it possible to retrieve or delete individual records without
    a separate index.

    Args:
        base_path: Directory that contains the ``*_raw_ai.jsonl`` files.
    """

    def __init__(self) -> None:
        self.base_path = Path(CODX_JUNIOR_AI_RAW_LOG_PATH)
        logger.info("RawLogReader initialised at: %s", self.base_path)

    # ── Internal helpers ────────────────────────────────────────────────────

    def _jsonl_files(self) -> List[Path]:
        """Return all ``*_raw_ai.jsonl`` files sorted by name (chronological)."""
        if not self.base_path.exists():
            return []
        return sorted(self.base_path.glob(f"*{FILE_SUFFIX}"))

    def _read_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Parse every line of a JSONL file into a list of dicts.

        Malformed lines are skipped with a warning.

        Args:
            file_path: Path to the ``.jsonl`` file.

        Returns:
            List of parsed record dicts, each enriched with a ``log_id``.
        """
        records: List[Dict[str, Any]] = []
        file_date_str = file_path.name.replace(FILE_SUFFIX, "")

        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                for line_idx, raw_line in enumerate(fh):
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as exc:
                        logger.warning(
                            "RawLogReader: skipping malformed line %d in %s: %s",
                            line_idx,
                            file_path.name,
                            exc,
                        )
                        continue
                    # Assign a deterministic log_id based on file date + line index
                    record["log_id"] = f"{file_date_str}:{line_idx}"
                    records.append(record)
        except OSError as exc:
            logger.error("RawLogReader: cannot read %s: %s", file_path, exc)

        return records

    def _files_in_range(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> List[Path]:
        """
        Return JSONL files whose date falls within [start_date, end_date].

        Both bounds are inclusive.  ``None`` means "unbounded".

        Args:
            start_date: Inclusive lower bound ``YYYY-MM-DD``, or ``None``.
            end_date:   Inclusive upper bound ``YYYY-MM-DD``, or ``None``.

        Returns:
            Filtered list of :class:`Path` objects.
        """
        start = _parse_date(start_date)
        end = _parse_date(end_date)
        result: List[Path] = []

        for fp in self._jsonl_files():
            fd = _file_date(fp)
            if fd is None:
                continue
            if start and fd < start:
                continue
            if end and fd > end:
                continue
            result.append(fp)

        return result

    # ── Public API ──────────────────────────────────────────────────────────

    def read_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        username: Optional[str] = None,
        project: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Read and filter raw AI log events from JSONL files.

        Args:
            start_date: Inclusive start date ``YYYY-MM-DD``.
            end_date:   Inclusive end date ``YYYY-MM-DD``.
            username:   Filter by username.
            project:    Filter by project name.
            model:      Filter by model name.
            provider:   Filter by provider name.
            session_id: Filter by session/conversation id.

        Returns:
            A list of matching record dicts, each with a ``log_id`` field.
        """
        files = self._files_in_range(start_date, end_date)
        logger.debug(
            "RawLogReader.read_events: scanning %d file(s) "
            "(start=%s, end=%s, user=%s, project=%s, model=%s, provider=%s)",
            len(files),
            start_date,
            end_date,
            username,
            project,
            model,
            provider,
        )

        matching: List[Dict[str, Any]] = []
        for fp in files:
            for record in self._read_file(fp):
                if _record_matches_filters(
                    record,
                    username=username,
                    project=project,
                    model=model,
                    provider=provider,
                    session_id=session_id,
                ):
                    matching.append(record)

        logger.debug("RawLogReader.read_events: found %d matching records", len(matching))
        return matching

    def read_event_by_id(self, log_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single event by its ``log_id``.

        The ``log_id`` format is ``<YYYY-MM-DD>:<line_index>``.

        Args:
            log_id: Unique event identifier.

        Returns:
            The matching record dict (with ``log_id``), or ``None`` if not found.
        """
        try:
            date_part, line_part = log_id.rsplit(":", 1)
            line_idx = int(line_part)
        except ValueError:
            logger.warning("read_event_by_id: invalid log_id format %r", log_id)
            return None

        file_path = self.base_path / f"{date_part}{FILE_SUFFIX}"
        if not file_path.exists():
            logger.debug("read_event_by_id: file not found for log_id %s", log_id)
            return None

        records = self._read_file(file_path)
        for record in records:
            if record.get("log_id") == log_id:
                return record

        # Guard: line_idx might be out of range
        logger.debug("read_event_by_id: log_id %s not found in %s", log_id, file_path.name)
        return None

    def delete_event_by_id(self, log_id: str) -> bool:
        """
        Delete a single event from a JSONL file by rewriting it without
        the matching line.

        Args:
            log_id: Unique event identifier (``<YYYY-MM-DD>:<line_index>``).

        Returns:
            ``True`` if the record was found and deleted, ``False`` otherwise.
        """
        try:
            date_part, line_part = log_id.rsplit(":", 1)
            target_line_idx = int(line_part)
        except ValueError:
            logger.warning("delete_event_by_id: invalid log_id format %r", log_id)
            return False

        file_path = self.base_path / f"{date_part}{FILE_SUFFIX}"
        if not file_path.exists():
            logger.debug("delete_event_by_id: file not found for log_id %s", log_id)
            return False

        with _lock:
            try:
                with open(file_path, "r", encoding="utf-8") as fh:
                    lines = fh.readlines()

                if target_line_idx >= len(lines):
                    logger.warning(
                        "delete_event_by_id: line index %d out of range in %s",
                        target_line_idx,
                        file_path.name,
                    )
                    return False

                new_lines = [
                    line for idx, line in enumerate(lines) if idx != target_line_idx
                ]

                with open(file_path, "w", encoding="utf-8") as fh:
                    fh.writelines(new_lines)

                logger.info("delete_event_by_id: deleted log_id %s from %s", log_id, file_path.name)
                return True

            except OSError as exc:
                logger.error("delete_event_by_id: failed for log_id %s: %s", log_id, exc)
                return False

    def delete_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        username: Optional[str] = None,
        project: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> int:
        """
        Bulk delete events matching the provided filters by rewriting affected
        JSONL files without the matched lines.

        Args:
            start_date: Inclusive start date ``YYYY-MM-DD``.
            end_date:   Inclusive end date ``YYYY-MM-DD``.
            username:   Filter by username.
            project:    Filter by project name.
            model:      Filter by model name.
            provider:   Filter by provider name.

        Returns:
            Total number of deleted records.
        """
        files = self._files_in_range(start_date, end_date)
        total_deleted = 0

        for fp in files:
            deleted_in_file = self._delete_matching_lines(
                file_path=fp,
                username=username,
                project=project,
                model=model,
                provider=provider,
            )
            total_deleted += deleted_in_file

        logger.info(
            "RawLogReader.delete_events: deleted %d records across %d file(s)",
            total_deleted,
            len(files),
        )
        return total_deleted

    def _delete_matching_lines(
        self,
        file_path: Path,
        username: Optional[str],
        project: Optional[str],
        model: Optional[str],
        provider: Optional[str],
    ) -> int:
        """
        Rewrite a JSONL file, omitting lines that match the given filters.

        Args:
            file_path: Path to the JSONL file to rewrite.
            username:  Username filter.
            project:   Project name filter.
            model:     Model name filter.
            provider:  Provider name filter.

        Returns:
            Number of lines removed.
        """
        kept_lines: List[str] = []
        deleted_count = 0

        with _lock:
            try:
                with open(file_path, "r", encoding="utf-8") as fh:
                    raw_lines = fh.readlines()

                for raw_line in raw_lines:
                    line = raw_line.strip()
                    if not line:
                        kept_lines.append(raw_line)
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        # Keep malformed lines to avoid data loss
                        kept_lines.append(raw_line)
                        continue

                    if _record_matches_filters(
                        record,
                        username=username,
                        project=project,
                        model=model,
                        provider=provider,
                        session_id=None,
                    ):
                        deleted_count += 1
                    else:
                        kept_lines.append(raw_line)

                with open(file_path, "w", encoding="utf-8") as fh:
                    fh.writelines(kept_lines)

            except OSError as exc:
                logger.error(
                    "RawLogReader._delete_matching_lines: error processing %s: %s",
                    file_path,
                    exc,
                )

        return deleted_count