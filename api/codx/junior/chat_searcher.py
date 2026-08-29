"""
Chat search and filtering module.

Provides full-text search capabilities across chat data (name, messages, history,
files, model, etc.) with time-frame filtering and pagination support.

Supports granular field-level filtering via SearchFilters to restrict search scope
(similar to email filter dialogs).
"""
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from codx.junior.db import Chat, Message

logger = logging.getLogger(__name__)


@dataclass
class SearchFilters:
    """
    Specifies which fields to include in the search scope.

    When a flag is False, the corresponding field category is excluded from
    scoring. Allows fine-grained control over search scope (similar to email
    filter dialogs).

    All flags default to True (search everywhere) for backward compatibility.
    """

    search_name: bool = True
    """Include chat name in search scope."""

    search_description: bool = True
    """Include chat description in search scope."""

    search_messages: bool = True
    """Include message content and think field in search scope."""

    search_message_metadata: bool = True
    """Include message user, profiles, knowledge_topics in search scope."""

    search_history: bool = True
    """Include chat history summaries in search scope."""

    search_files: bool = True
    """Include file_list paths in search scope."""

    search_model: bool = True
    """Include LLM model name in search scope."""

    search_status: bool = True
    """Include chat status in search scope."""

    search_mode: bool = True
    """Include chat mode in search scope."""

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "SearchFilters":
        """
        Create a SearchFilters instance from a dictionary (e.g., from API payload).

        Unknown keys are silently ignored. Missing keys use class defaults (True).

        :param data: Optional dict with filter flag keys.
        :return: SearchFilters instance.
        """
        if not data:
            return cls()

        # Only accept known filter attributes
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {
            k: v for k, v in data.items()
            if k in valid_fields and isinstance(v, bool)
        }
        return cls(**filtered_data)


class SearchResult:
    """Represents a single chat search result with relevance metadata."""

    def __init__(self, chat: Chat, relevance_score: float, matched_fields: List[str]):
        """
        Initialize a search result.

        :param chat: The matched Chat object.
        :param relevance_score: Relevance score (0-100, higher is better).
        :param matched_fields: List of fields where matches were found.
        """
        self.chat: Chat = chat
        self.relevance_score: float = relevance_score
        self.matched_fields: List[str] = matched_fields


class ChatSearcher:
    """
    Performs full-text search and filtering on chats with pagination.

    Supports time-frame filtering, field-level search scope control via
    SearchFilters, and searches across multiple fields:

    - Chat metadata: name, description, status, mode
    - Messages: content, think field
    - Message metadata: user, profiles, knowledge_topics
    - Files: file_list
    - Model: llm_model
    - History: summary text in chat_history entries
    """

    # Field weights for relevance scoring (higher = more important match)
    FIELD_WEIGHTS: Dict[str, float] = {
        "name": 3.0,
        "description": 2.0,
        "message_content": 2.5,
        "message_think": 1.5,
        "history_summary": 2.0,
        "user": 1.0,
        "file_list": 1.0,
        "llm_model": 0.5,
        "status": 1.0,
        "mode": 0.5,
    }

    DEFAULT_PAGE_SIZE: int = 20

    def __init__(self):
        """Initialize the chat searcher."""
        logger.debug("ChatSearcher initialized")

    def search(
        self,
        chats: List[Chat],
        query: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        filters: Optional[SearchFilters] = None,
    ) -> Dict[str, Any]:
        """
        Search chats with time-frame filtering, field-level scope control, and pagination.

        :param chats: List of Chat objects to search within.
        :param query: Search query string (case-insensitive substring matching).
        :param from_date: ISO-format date string; only include chats updated
            after this date (inclusive).
        :param to_date: ISO-format date string; only include chats updated
            before this date (inclusive).
        :param page: Page number (1-indexed).
        :param page_size: Number of results per page.
        :param filters: Optional SearchFilters to restrict search scope. If not
            provided, all fields are searched (default behavior).
        :return: Dict with keys:
            - ``results``: List of SearchResult dicts (matched chats).
            - ``total``: Total number of matching chats (across all pages).
            - ``page``: Current page number.
            - ``page_size``: Results per page.
            - ``total_pages``: Total number of pages.
            - ``has_next``: Whether a next page exists.
            - ``has_prev``: Whether a previous page exists.
        """
        # Use default filters (all fields enabled) if not provided
        if filters is None:
            filters = SearchFilters()

        # Filter by time frame
        filtered_chats = self._filter_by_time_frame(chats, from_date, to_date)
        logger.info(
            "search: time-frame filter reduced %d chats to %d",
            len(chats),
            len(filtered_chats),
        )

        # Normalize query for case-insensitive matching
        query_lower = query.lower() if query else ""

        # Score and filter by search query
        scored_results: List[SearchResult] = []
        for chat in filtered_chats:
            score, matched_fields = self._score_chat(chat, query_lower, filters)
            if score > 0:
                scored_results.append(
                    SearchResult(
                        chat=chat,
                        relevance_score=score,
                        matched_fields=matched_fields,
                    )
                )
        logger.info(
            "search: query '%s' matched %d chats with filters=%s",
            query,
            len(scored_results),
            self._filters_summary(filters),
        )

        # Sort by relevance (descending) and then by updated_at (descending).
        # Convert datetime to timestamp for proper numeric sorting.
        scored_results.sort(
            key=lambda x: (
                -x.relevance_score,
                -self._parse_timestamp(x.chat.updated_at).timestamp(),
            )
        )

        # Apply pagination
        return self._paginate_results(scored_results, page, page_size)

    def _filter_by_time_frame(
        self,
        chats: List[Chat],
        from_date: Optional[str],
        to_date: Optional[str],
    ) -> List[Chat]:
        """
        Filter chats by updated_at time frame.

        :param chats: Input list of chats.
        :param from_date: ISO-format start date (inclusive), or None.
        :param to_date: ISO-format end date (inclusive), or None.
        :return: Filtered list of chats.
        """
        if not from_date and not to_date:
            return chats

        from_dt = datetime.fromisoformat(from_date) if from_date else datetime.min
        to_dt = datetime.fromisoformat(to_date) if to_date else datetime.max

        filtered = [
            chat for chat in chats
            if from_dt <= self._parse_timestamp(chat.updated_at) <= to_dt
        ]
        return filtered

    def _score_chat(
        self,
        chat: Chat,
        query_lower: str,
        filters: SearchFilters,
    ) -> tuple:
        """
        Score a chat's relevance to the query, respecting filter scope.

        Searches across multiple fields and weights them by importance.
        Returns both a cumulative score and the list of matched fields.

        Skips field categories disabled in filters.

        :param chat: The chat to score.
        :param query_lower: Normalized (lowercase) search query.
        :param filters: SearchFilters controlling which fields to search.
        :return: Tuple of (score: float, matched_fields: List[str]).
        """
        if not query_lower:
            return 0.0, []

        score: float = 0.0
        matched_fields: set = set()

        # Search chat name (if enabled)
        if filters.search_name and query_lower in chat.name.lower():
            score += self.FIELD_WEIGHTS["name"]
            matched_fields.add("name")

        # Search chat description (if enabled)
        if filters.search_description and query_lower in chat.description.lower():
            score += self.FIELD_WEIGHTS["description"]
            matched_fields.add("description")

        # Search messages: content and think field (if enabled)
        if filters.search_messages:
            for message in chat.messages:
                if query_lower in message.content.lower():
                    score += self.FIELD_WEIGHTS["message_content"]
                    matched_fields.add("message_content")
                    # Count additional hits in same message to boost relevance
                    count = message.content.lower().count(query_lower)
                    if count > 1:
                        score += (count - 1) * 0.5

                if message.think and query_lower in message.think.lower():
                    score += self.FIELD_WEIGHTS["message_think"]
                    matched_fields.add("message_think")

        # Search message metadata: user, profiles, knowledge_topics (if enabled)
        if filters.search_message_metadata:
            for message in chat.messages:
                if message.user and query_lower in message.user.lower():
                    score += self.FIELD_WEIGHTS["user"]
                    matched_fields.add("user")

                for profile in message.profiles:
                    if query_lower in profile.lower():
                        score += 0.3  # Small boost for profile matches
                        matched_fields.add("profiles")

                for topic in message.knowledge_topics:
                    if query_lower in topic.lower():
                        score += 0.3
                        matched_fields.add("knowledge_topics")

        # Search chat history summaries (if enabled)
        if filters.search_history:
            for history_entry in chat.history:
                if query_lower in history_entry.summary.lower():
                    score += self.FIELD_WEIGHTS["history_summary"]
                    matched_fields.add("history_summary")

        # Search files (if enabled)
        if filters.search_files:
            for file_path in chat.file_list:
                if query_lower in file_path.lower():
                    score += self.FIELD_WEIGHTS["file_list"]
                    matched_fields.add("file_list")
                    break  # Count all file matches as one match

        # Search model (if enabled)
        if filters.search_model and chat.llm_model:
            if query_lower in chat.llm_model.lower():
                score += self.FIELD_WEIGHTS["llm_model"]
                matched_fields.add("llm_model")

        # Search status (if enabled)
        if filters.search_status and query_lower in chat.status.lower():
            score += self.FIELD_WEIGHTS["status"]
            matched_fields.add("status")

        # Search mode (if enabled)
        if filters.search_mode and query_lower in chat.mode.lower():
            score += self.FIELD_WEIGHTS["mode"]
            matched_fields.add("mode")

        return score, list(matched_fields)

    @staticmethod
    def _parse_timestamp(value: Optional[str]) -> datetime:
        """
        Parse a timestamp string that may be in either historical format.

        Handles both ``datetime.isoformat()`` and ``str(datetime.now())`` formats.
        Returns datetime.min for unparseable values (sorts oldest).

        :param value: Raw timestamp string (may be None/empty/invalid).
        :return: Parsed datetime, or ``datetime.min`` when unparseable.
        """
        if not value:
            return datetime.min
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            logger.debug("Unparseable timestamp: '%s'", value)
            return datetime.min

    @staticmethod
    def _paginate_results(
        results: List[SearchResult],
        page: int,
        page_size: int,
    ) -> Dict[str, Any]:
        """
        Apply pagination to search results.

        :param results: Sorted list of SearchResult objects.
        :param page: Page number (1-indexed).
        :param page_size: Results per page.
        :return: Paginated response dict.
        """
        total = len(results)
        total_pages = (total + page_size - 1) // page_size  # Ceiling division

        # Validate page number
        if page < 1:
            page = 1
        if page > max(1, total_pages):
            page = max(1, total_pages)

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_results = results[start_idx:end_idx]

        return {
            "results": [
                {
                    "chat": result.chat.model_dump(),
                    "relevance_score": result.relevance_score,
                    "matched_fields": result.matched_fields,
                }
                for result in page_results
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    @staticmethod
    def _filters_summary(filters: SearchFilters) -> str:
        """
        Generate a concise string summary of active filters for logging.

        :param filters: The SearchFilters to summarize.
        :return: String listing disabled fields (e.g. "[!files, !model]").
        """
        disabled = []
        if not filters.search_name:
            disabled.append("!name")
        if not filters.search_description:
            disabled.append("!description")
        if not filters.search_messages:
            disabled.append("!messages")
        if not filters.search_message_metadata:
            disabled.append("!message_metadata")
        if not filters.search_history:
            disabled.append("!history")
        if not filters.search_files:
            disabled.append("!files")
        if not filters.search_model:
            disabled.append("!model")
        if not filters.search_status:
            disabled.append("!status")
        if not filters.search_mode:
            disabled.append("!mode")
        return f"[{', '.join(disabled)}]" if disabled else "[all]"


# Made with ❤️ by codx-junior