import json
import logging
import os
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from codx.junior.analytics.model import (
    ArchivedMessage,
    ChatSessionEvent,
    ChatMetrics,
    ToolCallMessage,
    ToolUsageEvent,
    TokenUsageEvent,
)

logger = logging.getLogger(__name__)

# One file per day to keep individual files small
FILE_DATE_FORMAT = "%Y-%m-%d"


class AnalyticsStorage:
    """
    Incremental append-only storage for analytics events and archived messages.

    Organizes files by type under subdirectories with hybrid partitioning:
    - <base_path>/YYYY-MM-DD_token_usage.jsonl
    - <base_path>/tools/YYYY-MM-DD_tool_usage.jsonl
    - <base_path>/chat_sessions/YYYY-MM-DD_chat_sessions.jsonl
    - <base_path>/messages/YYYY-MM-DD/{request_id}_archived_messages.jsonl
    - <base_path>/messages/YYYY-MM-DD/{request_id}_tool_call_messages.jsonl

    Messages are partitioned by request_id to avoid huge single-day files.
    Each request gets its own small JSONL file for archived and tool call messages.

    Implements thread-safe append operations with a module-level lock.
    Provides filtering and querying capabilities across date ranges.
    
    Diagram:
    ```
    classDiagram
        class AnalyticsStorage {
            -str base_path
            -str tools_path
            -str chat_sessions_path
            -str messages_path
            -Lock _lock
            +__init__(analytics_path: str)
            +write(event: TokenUsageEvent) void
            +write_tool_event(event: ToolUsageEvent) void
            +write_chat_session(event: ChatSessionEvent) void
            +write_archived_message(event: ArchivedMessage) void
            +write_tool_call_message(event: ToolCallMessage) void
            +read_events(...) List[TokenUsageEvent]
            +read_tool_events(...) List[ToolUsageEvent]
            +read_chat_sessions(...) List[ChatSessionEvent]
            +read_archived_messages(chat_id, ...) List[ArchivedMessage]
            +read_tool_call_messages(chat_id, ...) List[ToolCallMessage]
            +list_available_dates() List[str]
            +rewrite_events_for_date_range(...) int
        }
    ```
    """

    _lock = threading.Lock()

    def __init__(self, analytics_path: str) -> None:
        """
        Initialize storage with base directory and create subdirectories.

        Args:
            analytics_path: Global directory where all analytics JSONL files
                          are stored. Typically set from environment variable
                          CODX_JUNIOR_API_ANALYTICS_DATA_PATH.
        """
        self.base_path = analytics_path
        self.tools_path = os.path.join(analytics_path, "tools")
        self.chat_sessions_path = os.path.join(analytics_path, "chat_sessions")
        self.messages_path = os.path.join(analytics_path, "messages")

        # Create all necessary directories
        os.makedirs(self.base_path, exist_ok=True)
        os.makedirs(self.tools_path, exist_ok=True)
        os.makedirs(self.chat_sessions_path, exist_ok=True)
        os.makedirs(self.messages_path, exist_ok=True)

        logger.info("AnalyticsStorage initialized at: %s", self.base_path)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _file_path_for_date(self, iso_date: str) -> str:
        """Return token usage JSONL file path for given ISO date."""
        return os.path.join(self.base_path, f"{iso_date}_token_usage.jsonl")

    def _tool_file_path_for_date(self, iso_date: str) -> str:
        """Return tool usage JSONL file path for given ISO date."""
        return os.path.join(self.tools_path, f"{iso_date}_tool_usage.jsonl")

    def _chat_session_file_path_for_date(self, iso_date: str) -> str:
        """Return chat session JSONL file path for given ISO date."""
        return os.path.join(
            self.chat_sessions_path, f"{iso_date}_chat_sessions.jsonl"
        )

    def _archived_message_file_path(self, iso_date: str, request_id: str) -> str:
        """Return archived message JSONL file path for request_id within date."""
        date_dir = os.path.join(self.messages_path, iso_date)
        return os.path.join(date_dir, f"{request_id}_archived_messages.jsonl")

    def _tool_call_message_file_path(self, iso_date: str, request_id: str) -> str:
        """Return tool call message JSONL file path for request_id within date."""
        date_dir = os.path.join(self.messages_path, iso_date)
        return os.path.join(date_dir, f"{request_id}_tool_call_messages.jsonl")

    def _current_file_path(self) -> str:
        """Get current token usage file path for today."""
        today = datetime.utcnow().strftime(FILE_DATE_FORMAT)
        return self._file_path_for_date(today)

    def _current_tool_file_path(self) -> str:
        """Get current tool usage file path for today."""
        today = datetime.utcnow().strftime(FILE_DATE_FORMAT)
        return self._tool_file_path_for_date(today)

    def _current_chat_session_file_path(self) -> str:
        """Get current chat session file path for today."""
        today = datetime.utcnow().strftime(FILE_DATE_FORMAT)
        return self._chat_session_file_path_for_date(today)

    # ── Write ──────────────────────────────────────────────────────────────────

    def write(self, event: TokenUsageEvent) -> None:
        """
        Append a TokenUsageEvent to today's JSONL file.

        Thread-safe via module-level lock. Logs on success and errors.

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
                    "Analytics: wrote event user=%s model=%s in=%d out=%d chat_id=%s",
                    event.username,
                    event.model,
                    event.input_tokens,
                    event.output_tokens,
                    event.chat_id,
                )
            except OSError as ex:
                logger.error("AnalyticsStorage.write failed: %s", ex)

    def write_tool_event(self, event: ToolUsageEvent) -> None:
        """
        Append a ToolUsageEvent to today's tool usage JSONL file.

        Thread-safe via module-level lock.

        Args:
            event: The tool usage event to persist.
        """
        file_path = self._current_tool_file_path()
        line = json.dumps(event.to_dict(), ensure_ascii=False)
        with self._lock:
            try:
                with open(file_path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
                logger.debug(
                    "Analytics: wrote tool event name=%s user=%s success=%s time_taken=%.3fs chat_id=%s",
                    event.name,
                    event.username,
                    event.success,
                    event.time_taken,
                    event.chat_id,
                )
            except OSError as ex:
                logger.error("AnalyticsStorage.write_tool_event failed: %s", ex)

    def write_chat_session(self, event: ChatSessionEvent) -> None:
        """
        Append a ChatSessionEvent to today's chat session JSONL file.

        Thread-safe via module-level lock. Allows incremental updates by
        appending multiple records for the same chat_id at different lifecycle points.

        Args:
            event: The chat session event to persist.
        """
        file_path = self._current_chat_session_file_path()
        line = json.dumps(event.to_dict(), ensure_ascii=False)
        with self._lock:
            try:
                with open(file_path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
                logger.debug(
                    "Analytics: wrote chat session chat_id=%s user=%s mode=%s profiles=%s files=%d",
                    event.chat_id,
                    event.username,
                    event.mode,
                    event.profiles,
                    len(event.files),
                )
            except OSError as ex:
                logger.error("AnalyticsStorage.write_chat_session failed: %s", ex)

    def write_archived_message(self, event: ArchivedMessage) -> None:
        """
        Append an ArchivedMessage to its request_id-specific JSONL file.

        Thread-safe via module-level lock. Stores complete request/response
        content for audit and debugging purposes. Each request_id gets its own
        file to avoid huge single-day files.

        Args:
            event: The archived message to persist.
        """
        if not event.request_id:
            logger.warning(
                "ArchivedMessage missing request_id: message_id=%s chat_id=%s",
                event.message_id,
                event.chat_id,
            )
            return

        iso_date = event.iso_date
        date_dir = os.path.join(self.messages_path, iso_date)
        file_path = self._archived_message_file_path(iso_date, event.request_id)

        line = json.dumps(event.to_dict(), ensure_ascii=False)
        with self._lock:
            try:
                os.makedirs(date_dir, exist_ok=True)
                with open(file_path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
                logger.debug(
                    "Analytics: wrote archived message message_id=%s chat_id=%s user=%s model=%s request_id=%s",
                    event.message_id,
                    event.chat_id,
                    event.username,
                    event.model,
                    event.request_id,
                )
            except OSError as ex:
                logger.error("AnalyticsStorage.write_archived_message failed: %s", ex)

    def write_tool_call_message(self, event: ToolCallMessage) -> None:
        """
        Append a ToolCallMessage to its request_id-specific JSONL file.

        Thread-safe via module-level lock. Stores tool invocation parameters,
        execution result, and any AI model interactions. Each request_id gets
        its own file to keep files small.

        Args:
            event: The tool call message to persist.
        """
        if not event.tool_call_id:
            logger.warning(
                "ToolCallMessage missing tool_call_id: message_id=%s chat_id=%s",
                event.message_id,
                event.chat_id,
            )
            return

        iso_date = event.iso_date
        # Use tool_call_id as the partition key for tool call messages
        date_dir = os.path.join(self.messages_path, iso_date)
        file_path = self._tool_call_message_file_path(iso_date, event.tool_call_id)

        line = json.dumps(event.to_dict(), ensure_ascii=False)
        with self._lock:
            try:
                os.makedirs(date_dir, exist_ok=True)
                with open(file_path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
                logger.debug(
                    "Analytics: wrote tool call message message_id=%s chat_id=%s tool_call_id=%s tool_name=%s user=%s",
                    event.message_id,
                    event.chat_id,
                    event.tool_call_id,
                    event.tool_name,
                    event.username,
                )
            except OSError as ex:
                logger.error(
                    "AnalyticsStorage.write_tool_call_message failed: %s", ex
                )

    # ── Read ───────────────────────────────────────────────────────────────────

    def read_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        username: Optional[str] = None,
        project_name: Optional[str] = None,
        project_id: Optional[str] = None,
        model: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> List[TokenUsageEvent]:
        """
        Read and optionally filter stored token usage events from JSONL files.

        Args:
            start_date:   Inclusive ISO date lower bound (YYYY-MM-DD).
            end_date:     Inclusive ISO date upper bound (YYYY-MM-DD).
            username:     Filter by exact username.
            project_name: Filter by exact project name.
            project_id:   Filter by exact project id.
            model:        Filter by exact model name.
            chat_id:      Filter by exact chat id.

        Returns:
            List of matching TokenUsageEvent objects ordered by timestamp.
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
        if chat_id:
            events = [e for e in events if e.chat_id == chat_id]

        events.sort(key=lambda e: e.timestamp)
        return events

    def read_tool_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        chat_id: Optional[str] = None,
        username: Optional[str] = None,
        project_name: Optional[str] = None,
        project_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> List[ToolUsageEvent]:
        """
        Read and optionally filter stored tool usage events from JSONL files.

        Args:
            start_date:   Inclusive ISO date lower bound (YYYY-MM-DD).
            end_date:     Inclusive ISO date upper bound (YYYY-MM-DD).
            chat_id:      Filter by exact chat/session id.
            username:     Filter by exact username.
            project_name: Filter by exact project name.
            project_id:   Filter by exact project id.
            tool_name:    Filter by exact tool function name.
            request_id:   Filter by exact request id.

        Returns:
            List of matching ToolUsageEvent objects ordered by timestamp.
        """
        available = self.list_available_dates()
        matching_files = []

        for date_str in available:
            if start_date and date_str < start_date:
                continue
            if end_date and date_str > end_date:
                continue
            matching_files.append(self._tool_file_path_for_date(date_str))

        events: List[ToolUsageEvent] = []
        for file_path in matching_files:
            events.extend(self._read_tool_file(file_path))

        # Apply filters
        if chat_id:
            events = [e for e in events if e.chat_id == chat_id]
        if username:
            events = [e for e in events if e.username == username]
        if project_name:
            events = [e for e in events if e.project_name == project_name]
        if project_id:
            events = [e for e in events if e.project_id == project_id]
        if tool_name:
            events = [e for e in events if e.name == tool_name]
        if request_id:
            events = [e for e in events if e.request_id == request_id]

        events.sort(key=lambda e: e.timestamp)
        return events

    def read_chat_sessions(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        chat_id: Optional[str] = None,
        username: Optional[str] = None,
        project_name: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[ChatSessionEvent]:
        """
        Read and optionally filter stored chat session events from JSONL files.

        Args:
            start_date:   Inclusive ISO date lower bound (YYYY-MM-DD).
            end_date:     Inclusive ISO date upper bound (YYYY-MM-DD).
            chat_id:      Filter by exact chat id.
            username:     Filter by exact username.
            project_name: Filter by exact project name.
            project_id:   Filter by exact project id.

        Returns:
            List of matching ChatSessionEvent objects ordered by timestamp.
        """
        available = self.list_available_dates()
        matching_files = []

        for date_str in available:
            if start_date and date_str < start_date:
                continue
            if end_date and date_str > end_date:
                continue
            matching_files.append(self._chat_session_file_path_for_date(date_str))

        events: List[ChatSessionEvent] = []
        for file_path in matching_files:
            events.extend(self._read_chat_session_file(file_path))

        # Apply filters
        if chat_id:
            events = [e for e in events if e.chat_id == chat_id]
        if username:
            events = [e for e in events if e.username == username]
        if project_name:
            events = [e for e in events if e.project_name == project_name]
        if project_id:
            events = [e for e in events if e.project_id == project_id]

        events.sort(key=lambda e: e.timestamp)
        return events

    def read_archived_messages(
        self,
        chat_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> List[ArchivedMessage]:
        """
        Read and optionally filter archived messages for a specific chat.

        Args:
            chat_id:    The chat identifier (required).
            start_date: Inclusive ISO date lower bound (YYYY-MM-DD).
            end_date:   Inclusive ISO date upper bound (YYYY-MM-DD).
            request_id: Filter by exact request id.

        Returns:
            List of matching ArchivedMessage objects ordered by timestamp.
        """
        # If request_id is provided, fetch directly from its file
        if request_id:
            available_dates = self.list_available_dates()
            matching_dates = []
            for date_str in available_dates:
                if start_date and date_str < start_date:
                    continue
                if end_date and date_str > end_date:
                    continue
                matching_dates.append(date_str)

            events: List[ArchivedMessage] = []
            for date_str in matching_dates:
                file_path = self._archived_message_file_path(date_str, request_id)
                events.extend(self._read_archived_message_file(file_path))

            # Filter by chat_id
            events = [e for e in events if e.chat_id == chat_id]
            events.sort(key=lambda e: e.timestamp)
            return events

        # Otherwise scan all request files in date range for this chat
        available_dates = self.list_available_dates()
        matching_dates = []
        for date_str in available_dates:
            if start_date and date_str < start_date:
                continue
            if end_date and date_str > end_date:
                continue
            matching_dates.append(date_str)

        events: List[ArchivedMessage] = []
        for date_str in matching_dates:
            date_dir = os.path.join(self.messages_path, date_str)
            if not os.path.isdir(date_dir):
                continue
            try:
                for fname in os.listdir(date_dir):
                    if fname.endswith("_archived_messages.jsonl"):
                        file_path = os.path.join(date_dir, fname)
                        events.extend(self._read_archived_message_file(file_path))
            except OSError as ex:
                logger.warning("Error listing messages directory %s: %s", date_dir, ex)

        # Filter by chat_id
        events = [e for e in events if e.chat_id == chat_id]
        events.sort(key=lambda e: e.timestamp)
        return events

    def read_tool_call_messages(
        self,
        chat_id: str,
        tool_call_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[ToolCallMessage]:
        """
        Read and optionally filter tool call messages for a specific chat.

        Args:
            chat_id:      The chat identifier (required).
            tool_call_id: Filter by exact tool call id.
            start_date:   Inclusive ISO date lower bound (YYYY-MM-DD).
            end_date:     Inclusive ISO date upper bound (YYYY-MM-DD).

        Returns:
            List of matching ToolCallMessage objects ordered by timestamp.
        """
        # If tool_call_id is provided, fetch directly from its file
        if tool_call_id:
            available_dates = self.list_available_dates()
            matching_dates = []
            for date_str in available_dates:
                if start_date and date_str < start_date:
                    continue
                if end_date and date_str > end_date:
                    continue
                matching_dates.append(date_str)

            events: List[ToolCallMessage] = []
            for date_str in matching_dates:
                file_path = self._tool_call_message_file_path(date_str, tool_call_id)
                events.extend(self._read_tool_call_message_file(file_path))

            # Filter by chat_id
            events = [e for e in events if e.chat_id == chat_id]
            events.sort(key=lambda e: e.timestamp)
            return events

        # Otherwise scan all tool call files in date range for this chat
        available_dates = self.list_available_dates()
        matching_dates = []
        for date_str in available_dates:
            if start_date and date_str < start_date:
                continue
            if end_date and date_str > end_date:
                continue
            matching_dates.append(date_str)

        events: List[ToolCallMessage] = []
        for date_str in matching_dates:
            date_dir = os.path.join(self.messages_path, date_str)
            if not os.path.isdir(date_dir):
                continue
            try:
                for fname in os.listdir(date_dir):
                    if fname.endswith("_tool_call_messages.jsonl"):
                        file_path = os.path.join(date_dir, fname)
                        events.extend(self._read_tool_call_message_file(file_path))
            except OSError as ex:
                logger.warning("Error listing messages directory %s: %s", date_dir, ex)

        # Filter by chat_id
        events = [e for e in events if e.chat_id == chat_id]
        events.sort(key=lambda e: e.timestamp)
        return events

    # ── Internal Readers ──────────────────────────────────────────────────────

    def _read_file(self, file_path: str) -> List[TokenUsageEvent]:
        """Parse single JSONL file into list of events, skipping bad lines."""
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
                    except (json.JSONDecodeError, TypeError, ValueError) as ex:
                        logger.warning(
                            "Skipping malformed analytics line %d in %s: %s",
                            line_no,
                            file_path,
                            ex,
                        )
        except FileNotFoundError:
            pass
        except OSError as ex:
            logger.error("Error reading analytics file %s: %s", file_path, ex)
        return events

    def _read_tool_file(self, file_path: str) -> List[ToolUsageEvent]:
        """Parse single tool usage JSONL file into list of events, skipping bad lines."""
        events: List[ToolUsageEvent] = []
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        events.append(ToolUsageEvent.from_dict(data))
                    except (json.JSONDecodeError, TypeError, ValueError) as ex:
                        logger.warning(
                            "Skipping malformed tool analytics line %d in %s: %s",
                            line_no,
                            file_path,
                            ex,
                        )
        except FileNotFoundError:
            pass
        except OSError as ex:
            logger.error("Error reading tool analytics file %s: %s", file_path, ex)
        return events

    def _read_chat_session_file(self, file_path: str) -> List[ChatSessionEvent]:
        """Parse single chat session JSONL file into list of events, skipping bad lines."""
        events: List[ChatSessionEvent] = []
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        events.append(ChatSessionEvent.from_dict(data))
                    except (json.JSONDecodeError, TypeError, ValueError) as ex:
                        logger.warning(
                            "Skipping malformed chat session line %d in %s: %s",
                            line_no,
                            file_path,
                            ex,
                        )
        except FileNotFoundError:
            pass
        except OSError as ex:
            logger.error("Error reading chat session file %s: %s", file_path, ex)
        return events

    def _read_archived_message_file(
        self, file_path: str
    ) -> List[ArchivedMessage]:
        """Parse single archived message JSONL file into list of events, skipping bad lines."""
        events: List[ArchivedMessage] = []
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        events.append(ArchivedMessage.from_dict(data))
                    except (json.JSONDecodeError, TypeError, ValueError) as ex:
                        logger.warning(
                            "Skipping malformed archived message line %d in %s: %s",
                            line_no,
                            file_path,
                            ex,
                        )
        except FileNotFoundError:
            pass
        except OSError as ex:
            logger.error("Error reading archived message file %s: %s", file_path, ex)
        return events

    def _read_tool_call_message_file(
        self, file_path: str
    ) -> List[ToolCallMessage]:
        """Parse single tool call message JSONL file into list of events, skipping bad lines."""
        events: List[ToolCallMessage] = []
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        events.append(ToolCallMessage.from_dict(data))
                    except (json.JSONDecodeError, TypeError, ValueError) as ex:
                        logger.warning(
                            "Skipping malformed tool call message line %d in %s: %s",
                            line_no,
                            file_path,
                            ex,
                        )
        except FileNotFoundError:
            pass
        except OSError as ex:
            logger.error("Error reading tool call message file %s: %s", file_path, ex)
        return events

    # ── Date Management ────────────────────────────────────────────────────────

    def list_available_dates(self) -> List[str]:
        """
        Return sorted list of ISO date strings for which data files exist.

        Inspects the base analytics path for token_usage JSONL files to
        determine which dates have data.

        Returns:
            Sorted list of YYYY-MM-DD strings in ascending order.
        """
        dates: List[str] = []
        try:
            for fname in os.listdir(self.base_path):
                if fname.endswith("_token_usage.jsonl"):
                    date_part = fname.replace("_token_usage.jsonl", "")
                    # Basic sanity check — must be 10 chars YYYY-MM-DD
                    if len(date_part) == 10:
                        dates.append(date_part)
        except OSError as ex:
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

        Iterates over every day in [start_date, end_date] (inclusive),
        updates pricing fields for every event whose provider and model match
        the supplied values, and atomically replaces the original file.

        Each matching event is loaded via TokenUsageEvent.from_dict(), the new
        pricing fields are applied and total_cxjcoins is forced to 0.0 so that
        TokenUsageEvent.__post_init__ recalculates it correctly.

        Args:
            provider:                  Provider name to match (e.g. "openai").
            model:                     Model name to match (e.g. "gpt-4o").
            start_date:                Inclusive start date in YYYY-MM-DD format.
            end_date:                  Inclusive end date in YYYY-MM-DD format.
            input_k_tokens_cxjcoins:   New price per 1000 input tokens.
            output_k_tokens_cxjcoins:  New price per 1000 output tokens.

        Returns:
            Total number of events updated across all files in date range.
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
                                # Patch pricing fields and reset total so
                                # __post_init__ recalculates it.
                                raw["input_k_tokens_cxjcoins"] = (
                                    input_k_tokens_cxjcoins
                                )
                                raw["output_k_tokens_cxjcoins"] = (
                                    output_k_tokens_cxjcoins
                                )
                                raw["total_cxjcoins"] = 0.0

                                # Deserialize → __post_init__ recomputes
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
                        except (json.JSONDecodeError, TypeError, ValueError) as ex:
                            logger.warning(
                                "Skipping malformed line in %s during rewrite: %s",
                                file_path,
                                ex,
                            )
                            updated_lines.append(line)
            except OSError as ex:
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
                except OSError as ex:
                    logger.error(
                        "Failed to write updated analytics file %s: %s",
                        file_path,
                        ex,
                    )
                    if os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except OSError:
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

# Made with ❤️ by codx-junior