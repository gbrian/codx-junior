"""
Chat engine actions sub-module for codx-junior.
Handles chat interactions, summarization and AI messaging.

TASK CREATION IS NOT PART OF THIS MODULE (changed).
Sub-task generation (``generate_tasks`` and its ``SubTaskStatus`` /
``TaskGenerationStatus`` trackers) has been removed: tasks are only created with
all their information through the LLM tools (``create_task``,
``project_manager``) or the API (``POST /api/chats/tasks``), both delegating to
:class:`codx.junior.task_manager.TaskManager`.

Made with ❤️ by codx-junior
"""

import json
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional

import requests

from codx.junior.chat.chat_engine import ChatEngine
from codx.junior.db import Chat, Message, MessageTaskItem
from codx.junior.model.logs import (
    ChatLogSummary, 
    ChatLogStatusDistribution, 
    ChatLogTokenStats, 
    ChatLogModelUsage,
    ForensicArchivedMessageRecord,
    ForensicToolCallRecord,
)
from codx.junior.profiling.profiler import profile_function
from codx.junior.utils.utils import (
    document_to_code_block,
    extract_json_blocks,
)

try:
    from langchain.messages import AIMessage, HumanMessage
except ImportError:
    from langchain_core.messages import AIMessage, HumanMessage

if TYPE_CHECKING:
    from codx.junior.engine.session import CODXJuniorSession

logger = logging.getLogger(__name__)


class ChatEngineActions:
    """
    Handles chat interactions and AI messaging.

    ```mermaid
    flowchart TD
        CEA[ChatEngineActions]
        CEA --> chat_with_project
        CEA --> chat_search
        CEA --> api_chat_with_project
        CEA --> summarize_chat
        CEA --> init_chat_from_url
        CEA --> convert_message
        CEA --> get_chat_analysis_parents
        CEA --> get_chat_log_summary
    ```

    Task creation is deliberately absent: see
    :class:`codx.junior.task_manager.TaskManager`.
    """

    def __init__(self, session: "CODXJuniorSession") -> None:
        """Initialize with a reference to the parent session."""
        self.session = session

    @property
    def settings(self):
        """Shortcut to session settings."""
        return self.session.settings

    @property
    def event_manager(self):
        """Shortcut to session event manager."""
        return self.session.event_manager

    def init_chat_from_url(self, chat: Chat) -> None:
        """
        Initialize a chat by downloading and parsing a URL using AI.

        Args:
            chat: Chat object with a 'url' attribute to download.
        """
        ai_content = None
        try:
            response = requests.get(chat.url, timeout=30)
            response.raise_for_status()
            downloaded_content = response.text

            ai = self.session.get_ai()
            prompt = f"""
            Extract a concise title and all content from the following issue html page:
            {downloaded_content}

            Return the response in JSON format:
            {{
                "title": "Extracted title",
                "content": "Extracted content"
            }}
            """
            ai_responses = ai.chat(prompt=prompt)
            ai_content = ai_responses[0].content
            response_json = next(extract_json_blocks(ai_content))

            chat.name = response_json.get("title", "Untitled Chat")
            chat.messages.append(
                Message(role="user", content=response_json.get("content", ""))
            )
        except Exception as ex:
            self.session.log_exception(
                f"Error initializing chat from URL {chat.url}: {ex} - {ai_content}"
            )
            raise ex

    @profile_function
    async def chat_search(self, chat_id: str, query: str) -> tuple:
        """
        Search knowledge and respond within a chat context.

        Args:
            chat_id: ID of the chat to use as context.
            query: User's search query.

        Returns:
            Result of chat_with_project.
        """
        chat = self.session.get_chat_manager().find_by_id(chat_id=chat_id)
        description = chat.description

        query_search = f"""
        Create an accurate short free text search query to find resouces associated to this user query: '{query}'
        
        Conversation context:
        ```        
        {description}
        ```
        """

        ai = self.session.get_ai()
        run_result = await ai.a_chat_run(prompt=query_search)
        freetext_query = run_result.content

        documents = self.session.project_search(query=freetext_query)

        doc_blocks = "\n".join([document_to_code_block(d) for d in documents])
        document_analysis = f"""Based on the context below, answer user request: '{query}'.

        Context:
        {doc_blocks}
        """
        chat.messages.append(
            Message(role="user", content=document_analysis, task_item="search")
        )
        return await self.session.chat_with_project(chat=chat)

    @profile_function
    async def api_chat_with_project(
        self, profile_name: str, messages: list
    ) -> Chat:
        """
        Chat with the project via the API using a named profile.

        Args:
            profile_name: Profile to apply.
            messages: List of dicts with 'role' and 'content'.

        Returns:
            Updated Chat object.
        """
        chat = Chat(
            name="api-chat",
            profiles=[profile_name],
            messages=[
                Message(role=m["role"], content=m["content"]) for m in messages
            ],
        )
        await self.session.chat_with_project(chat=chat)
        return chat

    @profile_function
    async def chat_with_project(
        self,
        chat: Chat,
        disable_knowledge: bool = False,
        callback=None,
        append_references: bool = True,
        chat_mode: str = None,
        iteration: int = 0,
    ) -> tuple:
        """
        Core method: orchestrate a chat with the project using AI and knowledge.

        Args:
            chat: The chat to process.
            disable_knowledge: Skip knowledge retrieval if True.
            callback: Optional streaming callback.
            append_references: Whether to append document references.
            chat_mode: Override chat mode.
            iteration: Recursion depth tracker.

        Returns:
            Tuple of (updated_chat, documents).
        """
        if not chat:
            raise Exception("chat can't be None")
            
        chat_engine = ChatEngine(
            settings=self.settings,
            event_manager=self.event_manager,
            user=self.session.user,
        )
        try:
            chat, docs = await chat_engine.chat_with_project(
                chat=chat,
                disable_knowledge=disable_knowledge,
                callback=callback,
                append_references=append_references,
                chat_mode=chat_mode,
                iteration=iteration,
            )
            logger.info("chat_with_project save chat: %s", chat.name)
            await self.session.save_chat(chat)
            return chat, docs
        except Exception as ex:
            logger.exception("Error processing chat: %s", ex)

    @profile_function
    async def summarize_chat(self, chat: Chat, instructions: str = "") -> Message:
        """
        Summarize a chat conversation using AI.

        Args:
            chat: The chat to summarize.
            instructions: Additional instructions for the summary.

        Returns:
            The summary Message object.
        """
        if chat.messages[-1].task_item == MessageTaskItem.SUMMARY:
            return chat.messages[-1]

        org_messages = chat.messages
        summary_prompt = f"""
        Create a summary of the conversarion.
        Make sure to do not loose any important detail.
        Syntetize text, no need for verbosity
        Add keywords at the end
        { instructions }
        """
        chat.messages = chat.messages.copy() + [
            Message(role="user", content=summary_prompt)
        ]
        await self.session.chat_with_project(chat=chat)
        response_message = chat.messages[-1]
        response_message.task_item = MessageTaskItem.SUMMARY
        response_message.hide = True
        chat.messages = org_messages + [response_message]
        return response_message

    def get_chat_log_summary(self, chat_id: str) -> ChatLogSummary:
        """
        Find all AI logs associated with a chat and create a comprehensive summary.

        Given a chat_id, retrieves the chat, queries analytics storage for:
        - TokenUsageEvent records (LLM token consumption)
        - ArchivedMessage records (full request/response content)
        - ToolCallMessage records (tool execution details)
        - ToolUsageEvent records (tool performance metrics)

        Aggregates all events into a comprehensive summary with metrics,
        status distribution, token estimates, error tracking, and a complete
        forensic audit trail with raw request/response payloads.

        Args:
            chat_id: The unique identifier of the chat to summarize logs for.

        Returns:
            ChatLogSummary object containing aggregated log statistics and
            complete forensic audit trail (raw_log_records).

        Raises:
            ValueError: When chat is not found.
        """
        # ── Step 1: Fetch the chat ─────────────────────────────────────────
        chat_manager = self.session.get_chat_manager()
        chat = chat_manager.find_by_id(chat_id=chat_id)
        if not chat:
            raise ValueError(f"Chat not found: {chat_id}")
        
        logger.info(
            "get_chat_log_summary: chat_id='%s' session_id=%s created_at=%s",
            chat_id, chat.session_id, chat.created_at
        )

        # ── Step 2: Initialize Analytics reader ─────────────────────────────
        from codx.junior.analytics import Analytics
        analytics = Analytics()
        
        # Determine date range for queries
        start_date = None
        end_date = None
        try:
            created_dt = datetime.fromisoformat(str(chat.created_at).replace(" ", "T"))
            start_date = created_dt.strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
        except (ValueError, AttributeError) as ex:
            logger.warning("Could not parse chat.created_at: %s, using today only", chat.created_at)
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = end_date

        logger.debug(
            "get_chat_log_summary: querying analytics for date range [%s, %s]",
            start_date, end_date
        )

        # ── Step 3: Query all relevant log types by chat_id ──────────────────
        # Query token usage events
        token_events = analytics.storage.read_events(
            start_date=start_date,
            end_date=end_date,
            chat_id=chat_id,
        )

        # Query archived messages (full request/response content)
        archived_messages = analytics.storage.read_archived_messages(
            chat_id=chat_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Query tool call messages (tool execution details)
        tool_call_messages = analytics.storage.read_tool_call_messages(
            chat_id=chat_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Query tool usage events
        tool_usage_events = analytics.storage.read_tool_events(
            chat_id=chat_id,
            start_date=start_date,
            end_date=end_date,
        )

        logger.info(
            "get_chat_log_summary: retrieved %d token events, %d archived messages, "
            "%d tool call messages, %d tool usage events",
            len(token_events),
            len(archived_messages),
            len(tool_call_messages),
            len(tool_usage_events),
        )

        # ── Step 4: Build forensic audit trail ─────────────────────────────
        # Combine archived messages and tool call messages, sorted by timestamp
        forensic_records: List[tuple] = []  # (timestamp, record_dict)
        
        for message in archived_messages:
            try:
                forensic_record = ForensicArchivedMessageRecord(
                    message_id=message.message_id,
                    request_id=message.request_id or "",
                    timestamp=message.timestamp,
                    iso_date=message.iso_date,
                    request_messages=message.request_messages,
                    system_prompt=message.system_prompt,
                    temperature=message.temperature,
                    max_tokens=message.max_tokens,
                    tools=message.tools,
                    response_content=message.response_content,
                    input_tokens=message.input_tokens,
                    output_tokens=message.output_tokens,
                    duration_seconds=message.duration_seconds,
                    error=message.error,
                    cancelled=message.cancelled,
                    model=message.model,
                    provider=message.provider,
                    chat_id=message.chat_id,
                    username=message.username,
                    project_name=message.project_name,
                    project_id=message.project_id,
                )
                forensic_records.append(
                    (message.timestamp, forensic_record.dict())
                )
            except Exception as ex:
                logger.warning(
                    "get_chat_log_summary: failed to build forensic record for archived message %s: %s",
                    message.message_id, ex
                )

        for tool_msg in tool_call_messages:
            try:
                forensic_record = ForensicToolCallRecord(
                    message_id=tool_msg.message_id,
                    tool_call_id=tool_msg.tool_call_id,
                    timestamp=tool_msg.timestamp,
                    iso_date=tool_msg.iso_date,
                    tool_name=tool_msg.tool_name,
                    tool_definition=tool_msg.tool_definition,
                    request_args=tool_msg.request_args,
                    result=tool_msg.result,
                    result_sent_to_model=tool_msg.result_sent_to_model,
                    duration_seconds=tool_msg.duration_seconds,
                    success=tool_msg.success,
                    error_message=tool_msg.error_message,
                    cached=tool_msg.cached,
                    chat_id=tool_msg.chat_id,
                    username=tool_msg.username,
                    project_name=tool_msg.project_name,
                    project_id=tool_msg.project_id,
                )
                forensic_records.append(
                    (tool_msg.timestamp, forensic_record.dict())
                )
            except Exception as ex:
                logger.warning(
                    "get_chat_log_summary: failed to build forensic record for tool call %s: %s",
                    tool_msg.tool_call_id, ex
                )

        # Sort by timestamp (chronological order) and extract just the dicts
        forensic_records.sort(key=lambda x: x[0])
        raw_log_records = [record_dict for _, record_dict in forensic_records]

        logger.info(
            "get_chat_log_summary: built forensic audit trail with %d records",
            len(raw_log_records)
        )

        # ── Step 5: Aggregate all events into summary ──────────────────────
        summary = ChatLogSummary(
            chat_id=chat_id,
            session_id=chat.session_id,
            raw_log_records=raw_log_records,
        )

        # Track models and their usage
        model_usage_map = {}  # (model, provider) -> ChatLogModelUsage
        error_details = []
        total_duration = 0.0

        # ── Process Token Usage Events ────────────────────────────────────
        for event in token_events:
            summary.total_log_records += 1
            summary.token_stats.total_estimated_input_tokens += event.input_tokens
            summary.token_stats.total_estimated_output_tokens += event.output_tokens
            total_duration += event.duration_seconds

            # Track model usage
            key = (event.model, event.provider)
            if key not in model_usage_map:
                model_usage_map[key] = ChatLogModelUsage(
                    model=event.model,
                    provider=event.provider,
                )
            model_usage_map[key].request_count += 1
            model_usage_map[key].total_duration_seconds += event.duration_seconds

            # Track timestamps
            if event.timestamp:
                ts_iso = datetime.fromtimestamp(event.timestamp).isoformat()
                if not summary.first_timestamp or ts_iso < summary.first_timestamp:
                    summary.first_timestamp = ts_iso
                if not summary.last_timestamp or ts_iso > summary.last_timestamp:
                    summary.last_timestamp = ts_iso

        # ── Process Archived Messages ──────────────────────────────────────
        for message in archived_messages:
            summary.total_log_records += 1
            summary.total_requests += 1
            summary.status_distribution.success += 1
            summary.token_stats.total_estimated_input_tokens += message.input_tokens
            summary.token_stats.total_estimated_output_tokens += message.output_tokens
            total_duration += message.duration_seconds

            # Track model usage
            key = (message.model, message.provider)
            if key not in model_usage_map:
                model_usage_map[key] = ChatLogModelUsage(
                    model=message.model,
                    provider=message.provider,
                )
            model_usage_map[key].request_count += 1
            model_usage_map[key].total_duration_seconds += message.duration_seconds

            # Track error if present
            if message.error:
                summary.status_distribution.error += 1
                summary.status_distribution.success -= 1  # Undo success count
                if len(error_details) < 5:
                    error_details.append(message.error)

            if message.cancelled:
                summary.status_distribution.cancelled += 1
                summary.status_distribution.success -= 1  # Undo success count

            # Track timestamps
            if message.timestamp:
                ts_iso = datetime.fromtimestamp(message.timestamp).isoformat()
                if not summary.first_timestamp or ts_iso < summary.first_timestamp:
                    summary.first_timestamp = ts_iso
                if not summary.last_timestamp or ts_iso > summary.last_timestamp:
                    summary.last_timestamp = ts_iso

        # ── Process Tool Call Messages ────────────────────────────────────
        for tool_msg in tool_call_messages:
            summary.total_log_records += 1

            if tool_msg.success:
                summary.status_distribution.success += 1
            else:
                summary.status_distribution.error += 1
                if len(error_details) < 5:
                    error_details.append(tool_msg.error_message or "Tool execution failed")

            total_duration += tool_msg.duration_seconds

            # Track timestamps
            if tool_msg.timestamp:
                ts_iso = datetime.fromtimestamp(tool_msg.timestamp).isoformat()
                if not summary.first_timestamp or ts_iso < summary.first_timestamp:
                    summary.first_timestamp = ts_iso
                if not summary.last_timestamp or ts_iso > summary.last_timestamp:
                    summary.last_timestamp = ts_iso

        # ── Process Tool Usage Events ──────────────────────────────────────
        for tool_event in tool_usage_events:
            summary.total_log_records += 1

            if tool_event.success:
                summary.status_distribution.success += 1
            else:
                summary.status_distribution.error += 1
                if len(error_details) < 5:
                    error_details.append(tool_event.error_message or "Tool execution failed")

            total_duration += tool_event.time_taken

            # Track timestamps
            if tool_event.timestamp:
                ts_iso = datetime.fromtimestamp(tool_event.timestamp).isoformat()
                if not summary.first_timestamp or ts_iso < summary.first_timestamp:
                    summary.first_timestamp = ts_iso
                if not summary.last_timestamp or ts_iso > summary.last_timestamp:
                    summary.last_timestamp = ts_iso

        # ── Finalize aggregations ──────────────────────────────────────────
        summary.model_usage = list(model_usage_map.values())
        summary.has_errors = (
            summary.status_distribution.error > 0 or
            summary.status_distribution.cancelled > 0
        )
        summary.error_details = error_details
        summary.total_duration_seconds = total_duration
        summary.total_responses = len(archived_messages)

        # Calculate average request duration
        if len(archived_messages) > 0:
            summary.average_request_duration_seconds = (
                total_duration / len(archived_messages)
            )

        # Calculate total estimated tokens
        summary.token_stats.total_estimated_tokens = (
            summary.token_stats.total_estimated_input_tokens +
            summary.token_stats.total_estimated_output_tokens
        )

        logger.info(
            "get_chat_log_summary: completed for chat_id='%s' "
            "logs=%d requests=%d responses=%d duration=%.2fs errors=%d models=%d forensic_records=%d",
            chat_id,
            summary.total_log_records,
            summary.total_requests,
            summary.total_responses,
            summary.total_duration_seconds,
            summary.status_distribution.error,
            len(summary.model_usage),
            len(summary.raw_log_records),
        )

        return summary

    def get_chat_analysis_parents(self, chat: Chat) -> str:
        """
        Traverse all parent chats and collect their visible messages for context.

        Args:
            chat: Starting chat to traverse parents from.

        Returns:
            Concatenated parent message content string.
        """
        parent_content = []
        chat_manager = self.session.get_chat_manager()
        parent_chat = chat_manager.find_by_id(chat.parent_id)
        while parent_chat:
            messages = [m.content for m in parent_chat.messages if not m.hide]
            if messages:
                parent_content.append("\n".join(messages))
            parent_chat = chat_manager.find_by_id(parent_chat.parent_id)
        return "\n".join(parent_content)

    def convert_message(self, m: Message) -> object:
        """
        Convert a DB Message to a LangChain-compatible message object.

        Args:
            m: The DB Message to convert.

        Returns:
            HumanMessage, AIMessage, or image dict.
        """
        def parse_image(image: str) -> dict:
            try:
                return json.loads(image)
            except (json.JSONDecodeError, TypeError):
                return {"src": image, "alt": ""}

        if m.images:
            images = [parse_image(image) for image in m.images]
            text_content = {"type": "text", "text": m.content}
            content = [text_content] + [
                {"type": "image_url", "image_url": {"url": image["src"]}}
                for image in images
            ]
            return {"type": "image", "content": json.dumps(content)}

        if m.role == "user":
            return HumanMessage(content=m.content)

        return AIMessage(content=m.content)

# Made with ❤️ by codx-junior