import os
import json
import logging
import threading
from datetime import datetime, timedelta
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
            +rewrite_events_for_date_range(provider, model, start_date, end_date, input_k_tokens_cxjcoins, output_k_tokens_cxjcoins)
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

    # ── Rewrite ────────────────────────────────────────────────────────────────

    def rewrite_events_for_date_range(
        self,
        provider: str,
        model: str,
        start_date: str,
        end_date: str,
        input_k_tokens_cxjcoins: float,
        output_k_tokens_cxjcoins: float,
    ) -> int:
        """
        Recompute cxjcoins for matching events in a date range using new prices.

        Iterates over every day in ``[start_date, end_date]`` (inclusive),
        updates the ``input_k_tokens_cxjcoins``, ``output_k_tokens_cxjcoins``
        and ``total_cxjcoins`` fields for every event whose ``provider`` and
        ``model`` match the supplied values, and atomically replaces the
        original file.

        Each matching event is loaded via ``TokenUsageEvent.from_dict()``,
        the new pricing fields are applied and ``total_cxjcoins`` is forced to
        ``0.0`` so that ``TokenUsageEvent.__post_init__`` recalculates it
        correctly before the event is serialised back to disk.

        Args:
            provider:                  Provider name to match (e.g. ``"openai"``).
            model:                     Model name to match (e.g. ``"gpt-4o"``).
            start_date:                Inclusive start date in ``YYYY-MM-DD`` format.
            end_date:                  Inclusive end date in ``YYYY-MM-DD`` format.
            input_k_tokens_cxjcoins:   New price per 1 000 input tokens in cxjcoins.
            output_k_tokens_cxjcoins:  New price per 1 000 output tokens in cxjcoins.

        Returns:
            Total number of events that were updated across all files in the
            date range.
        """
        logger.info(
            "rewrite_events_for_date_range: starting rewrite for provider=%s model=%s "
            "date_range=[%s, %s] input_price=%.6f output_price=%.6f",
            provider,
            model,
            start_date,
            end_date,
            input_k_tokens_cxjcoins,
            output_k_tokens_cxjcoins,
        )

        start = datetime.strptime(start_date, FILE_DATE_FORMAT)
        end = datetime.strptime(end_date, FILE_DATE_FORMAT)
        current = start

        total_files_processed = 0
        total_events_updated = 0

        while current <= end:
            date_str = current.strftime(FILE_DATE_FORMAT)
            file_path = self._file_path_for_date(date_str)

            if not os.path.exists(file_path):
                logger.debug(
                    "rewrite_events_for_date_range: no file for date=%s, skipping",
                    date_str,
                )
                current += timedelta(days=1)
                continue

            logger.debug(
                "rewrite_events_for_date_range: processing file %s",
                file_path,
            )

            updated_lines: List[str] = []
            changed = False
            events_updated_in_file = 0
            events_skipped_in_file = 0

            try:
                with open(file_path, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            raw = json.loads(line)
                            if (
                                raw.get("provider") == provider
                                and raw.get("model") == model
                            ):
                                # Patch pricing fields and reset total so that
                                # TokenUsageEvent.__post_init__ recalculates it.
                                raw["input_k_tokens_cxjcoins"] = input_k_tokens_cxjcoins
                                raw["output_k_tokens_cxjcoins"] = output_k_tokens_cxjcoins
                                raw["total_cxjcoins"] = 0.0

                                # Deserialise → __post_init__ recomputes total_cxjcoins
                                event = TokenUsageEvent.from_dict(raw)

                                updated_lines.append(
                                    json.dumps(event.to_dict(), ensure_ascii=False)
                                )
                                changed = True
                                events_updated_in_file += 1
                                logger.debug(
                                    "rewrite_events_for_date_range: updated event "
                                    "user=%s timestamp=%s new_total_cxjcoins=%.6f",
                                    event.username,
                                    event.timestamp,
                                    event.total_cxjcoins,
                                )
                            else:
                                updated_lines.append(
                                    json.dumps(raw, ensure_ascii=False)
                                )
                                events_skipped_in_file += 1
                        except Exception as ex:
                            logger.warning(
                                "Skipping malformed line in %s during rewrite: %s",
                                file_path,
                                ex,
                            )
                            updated_lines.append(line)
            except Exception as ex:
                logger.error(
                    "Failed to read %s during rewrite_events_for_date_range: %s",
                    file_path,
                    ex,
                )
                current += timedelta(days=1)
                continue

            logger.info(
                "rewrite_events_for_date_range: file=%s events_updated=%d events_unchanged=%d",
                file_path,
                events_updated_in_file,
                events_skipped_in_file,
            )

            if changed:
                tmp_path = file_path + ".tmp"
                try:
                    with self._lock:
                        with open(tmp_path, "w", encoding="utf-8") as fh:
                            fh.write("\n".join(updated_lines) + "\n")
                        os.replace(tmp_path, file_path)
                    logger.info(
                        "Rewrote analytics file %s for provider=%s model=%s",
                        file_path,
                        provider,
                        model,
                    )
                    total_files_processed += 1
                    total_events_updated += events_updated_in_file
                except Exception as ex:
                    logger.error(
                        "Failed to write updated analytics file %s: %s",
                        file_path,
                        ex,
                    )
                    if os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
            else:
                logger.debug(
                    "rewrite_events_for_date_range: no matching events in %s, file unchanged",
                    file_path,
                )

            current += timedelta(days=1)

        logger.info(
            "rewrite_events_for_date_range: completed for provider=%s model=%s — "
            "files_rewritten=%d total_events_updated=%d",
            provider,
            model,
            total_files_processed,
            total_events_updated,
        )

        return total_events_updated