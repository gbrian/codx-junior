import json
import logging
import os
import re
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from json import JSONDecodeError
from typing import List, Tuple, Optional, Dict, Any, Set

from langchain.messages import (
    AIMessage,
    HumanMessage,
)

from langchain_core.documents import Document

from engine.agent_runtime import AgentRunContext

from codx.junior.ai import AI
from codx.junior.ai.cancellation import CancellationToken, CancelledError, CANCELLATION_REGISTRY
from codx.junior.chat_manager import ChatManager
from codx.junior.chat.chat_event_bridge import ChatEventBridge
from codx.junior.context import AICodeGenerator
from codx.junior.db import Chat, Message, ChatHistoryEntry
from codx.junior.globals import AGENT_DONE_WORD
from codx.junior.project.project_discover import (
    find_project_by_id,
    get_project_dependencies,
)
from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.knowledge.knowledge_ai_search import KnowledgeAISearch
from codx.junior.knowledge.knowledge_ai_search_message import build_search_message
from codx.junior.profiles.profile_manager import ProfileManager
from codx.junior.profiling.profiler import profile_function
from codx.junior.settings import CODXJuniorSettings
from codx.junior.utils.chat_utils import ChatUtils, QueryMentions
from codx.junior.utils.utils import document_to_code_block
from codx.junior.model.model import CodxUser
from codx.junior.chat.chat_knowledge import ChatKnowledge
from codx.junior.analytics import Analytics

from codx.junior.globals import (
  LANGUAGE_PARSER_MAPPING,
)

# Set up logging
logger = logging.getLogger(__name__)

# Chat mode constants
CHAT_MODE_TASK = "task"
CHAT_MODE_AGENT = "agent"
CHAT_MODE_VIBE = "vibe"
TASK_ITEM_SEARCH = "search"
TASK_ITEM_ANALYSIS = "analysis"

# Prompt used to auto-initialize an auto_initialize chat's metadata
CHAT_INIT_PROMPT = """
Based on the conversation below, suggest values for the following chat metadata fields.
Return a JSON object with these keys (omit a key if you cannot determine a good value):
  - "name": a short, descriptive title for this chat (max 8 words)
  - "board": the high-level board/category this chat belongs to (e.g. "Backend", "Frontend", "DevOps", "Design", "General")
  - "column": the workflow column that best fits the current state (e.g. "To Do", "In Progress", "Done", "Backlog")

Return ONLY a valid JSON object, no extra text.
Example: {"name": "Fix login bug", "board": "Backend", "column": "In Progress"}
"""

def concat_content(arr):
    return "\n".join(filter(lambda el: True if el else False, arr))

class ChatEngine:
    """
    Core engine for managing chat interactions with AI models.

    Handles message processing, knowledge search, context building,
    and AI response generation for various chat modes.

    Integrates comprehensive analytics tracking for chat sessions, token usage,
    and tool executions to enable full request-response traceability.

    CHANGED: Tool and run-lifecycle events emitted by the agent runtime are
    ASSOCIATED with the assistant response message (``tool_events`` /
    ``lifecycle_events`` typed lists) via :class:`ChatEventBridge`. The
    response message is created BEFORE the AI call and passed to the bridge.

    CRASH-SAFETY: the bridge persists the response message on EVERY event
    change (merge-safe ``add_message``/``update_message``), and the engine
    persists it immediately on error and cancellation paths, so as much
    information as possible survives a crash or kill mid-run. Because the
    bridge may have already inserted the response message, the engine uses
    :meth:`_append_message_if_missing` to avoid duplicating it in memory.

    ADDED — streamed-chunk crash-safety: the streaming callback
    (``send_message_event``) calls :meth:`ChatEventBridge.maybe_persist_stream`
    on every flush, persisting partial streamed content at most once per
    throttle interval. A hard kill loses at most a few seconds of text.

    ADDED — hidden reasoning crash-safety: intermediate reasoning messages
    produced during the AI call are persisted IMMEDIATELY via
    :meth:`ChatEventBridge.persist_message` instead of waiting for the
    end-of-turn chat save.


    flowchart TD
        A[User Message] --> B{Chat Mode?}
        B -->|vibe| C[AI Search Context]
        B -->|search| C
        C --> D[Build Context]
        B -->|task| E[Refine Document]
        B -->|agent| F[Agent Iteration]
        B -->|chat| G[Standard Chat]
        D --> G
        E --> H{Add parent messages?}
        F --> H
        G --> H
        H -->|ignore_parent_knowledge=False| H1[Prepend parent messages]
        H -->|ignore_parent_knowledge=True| H2[Skip parent messages]
        H1 --> H3[Record Chat Session Start]
        H2 --> H3
        H3 --> I[Create response_message]
        I --> J[ChatEventBridge - persists on every event]
        J --> K[AI Response]
        K -->|stream flush| K5[Throttled persist of partial content]
        K -->|hidden reasoning| K6[persist_message - immediate]
        K -->|tool events| K3[Events on response_message persisted + streamed]
        K -->|model param error| K7[Catch + inform user]
        K -->|error/cancel| K4[bridge.publish - error persisted immediately]
        K --> L[Record Chat Session End]
        L --> M[Return Chat + Documents]
    """

    def __init__(
        self,
        settings: CODXJuniorSettings,
        event_manager,
        user: CodxUser = None
    ) -> None:
        """
        Initialize the ChatEngine with project settings, event manager, and optional user.

        :param settings: The current project's settings.
        :param event_manager: Event manager for emitting chat/search events.
        :param user: Optional authenticated user for the session.
        """
        self.settings = settings
        self.event_manager = event_manager
        self.knowledge = Knowledge(settings=settings)
        self.chat_knowledge = ChatKnowledge(
            settings=settings,
            event_manager=event_manager
        )
        self.user = user
        # ADDED: Initialize analytics instance for chat session tracking
        self.analytics = Analytics()

    def get_profile_manager(self) -> ProfileManager:
        """Return a ProfileManager instance for the current settings."""
        return ProfileManager(settings=self.settings)

    def get_chat_manager(self, project_id: str = None) -> ChatManager:
        """
        Return a ChatManager, optionally scoped to a specific project.

        :param project_id: Optional project ID to scope the manager.
        :return: A ChatManager instance.
        """
        if not project_id:
            return ChatManager(settings=self.settings)
        return ChatManager(settings=find_project_by_id(project_id=project_id))

    @contextmanager
    def chat_action(self, chat: Chat, event: str):
        """
        Context manager that emits start/done/error events around a chat action.

        :param chat: The chat being processed.
        :param event: Human-readable event name for logging and notifications.
        """
        self.event_manager.chat_event(chat=chat, message=f"{event} starting")
        logger.info("Start chat %s", chat.name)
        try:
            yield
        except OSError as ex:
            self.event_manager.chat_event(
                chat=chat,
                message=f"{event} error: {ex}",
                event_type="error"
            )
            logger.exception("Chat %s %s error: %s", chat.name, event, ex)
        finally:
            self.event_manager.chat_event(
                chat=chat,
                message=f"{event} done",
                event_type="done"
            )
            logger.info("Chat done %s", chat.name)

    # -------------------------------------------------------------------------
    # Helper: new message factory
    # -------------------------------------------------------------------------
    @staticmethod
    def _new_chat_message(role: str, content: str = "") -> Message:
        """
        Create a new Message with a generated doc_id.

        :param role: The message role ('user', 'assistant', etc.).
        :param content: Optional initial content string.
        :return: A new Message instance.
        """
        return Message(
            role=role,
            content=content,
            files=[],
            doc_id=str(uuid.uuid4())
        )

    # -------------------------------------------------------------------------
    # Helper: append message avoiding duplicates (ADDED for crash-safety)
    # -------------------------------------------------------------------------
    @staticmethod
    def _append_message_if_missing(chat: Chat, message: Message) -> None:
        """
        Append *message* to ``chat.messages`` only if not already present.

        Needed because the :class:`ChatEventBridge` persists (and may append)
        the response message BEFORE the turn finishes; a blind append would
        duplicate it. Lookup is by ``doc_id``.

        :param chat: The chat to append to.
        :param message: The message to append.
        """
        if any(m.doc_id == message.doc_id for m in chat.messages):
            logger.debug(
                "Message '%s' already present in chat '%s', skipping append",
                message.doc_id,
                chat.doc_id,
            )
            return
        chat.messages.append(message)

    # -------------------------------------------------------------------------
    # Helper: resolve chat mode flags
    # -------------------------------------------------------------------------
    def _resolve_chat_mode_flags(
        self,
        chat: Chat,
        chat_mode: Optional[str],
        task_item: Optional[str]
    ) -> Dict[str, Any]:
        """
        Resolve boolean flags that drive branching logic from the chat mode and task item.

        :param chat: The current chat object.
        :param chat_mode: Explicit mode override (may be None).
        :param task_item: Task item from the latest user message.
        :return: Dict with keys: chat_mode, is_refine, is_agent, is_vibe,
                 is_search, needs_pre_search.
        """
        resolved_mode = chat_mode or chat.mode or "chat"
        is_refine: bool = resolved_mode == CHAT_MODE_TASK
        is_agent: bool = resolved_mode == CHAT_MODE_AGENT
        is_vibe: bool = resolved_mode == CHAT_MODE_VIBE
        is_search: bool = task_item == TASK_ITEM_SEARCH
        needs_pre_search: bool = is_vibe or is_search

        logger.info(
            "Resolved chat mode flags: mode=%s is_refine=%s is_agent=%s "
            "is_vibe=%s is_search=%s needs_pre_search=%s",
            resolved_mode, is_refine, is_agent, is_vibe, is_search, needs_pre_search
        )

        return {
            "chat_mode": resolved_mode,
            "is_refine": is_refine,
            "is_agent": is_agent,
            "is_vibe": is_vibe,
            "is_search": is_search,
            "needs_pre_search": needs_pre_search,
        }

    # -------------------------------------------------------------------------
    # Helper: build LangChain message history with optional parent messages
    # -------------------------------------------------------------------------
    def _build_message_history(
        self,
        chat: Chat,
        include_parent_messages: bool = True
    ) -> List:
        """
        Convert all non-hidden, non-improvement chat messages (excluding the
        last) into LangChain message objects.

        If include_parent_messages is True and chat has a parent and
        ignore_parent_knowledge is False, prepends parent chat history.

        Tool and lifecycle events live on the response messages themselves
        (``tool_events`` / ``lifecycle_events``) and are never converted to
        prompt content, so no role-based filtering is needed.

        FIXED: Now includes parent visible messages respecting the
        ignore_parent_knowledge flag.

        :param chat: The chat whose history to convert.
        :param include_parent_messages: Whether to include parent messages
                                        (default True).
        :return: List of LangChain message objects.
        """
        messages = []

        # FIXED: Add parent messages if applicable
        if include_parent_messages and chat.parent_id and not chat.ignore_parent_knowledge:
            chat_manager = self.get_chat_manager(project_id=chat.owner_project_id)
            parent_chat = chat_manager.find_by_id(chat.parent_id)

            if parent_chat:
                logger.info(
                    "Including parent chat messages for chat '%s' "
                    "(parent_id='%s', ignore_parent_knowledge=%s)",
                    chat.doc_id,
                    chat.parent_id,
                    chat.ignore_parent_knowledge,
                )
                # Recursively include parent's parent messages
                parent_messages = self._build_message_history(
                    chat=parent_chat,
                    include_parent_messages=True
                )
                messages.extend(parent_messages)
            else:
                logger.warning(
                    "Parent chat '%s' not found for chat '%s' "
                    "(owner_project_id='%s')",
                    chat.parent_id,
                    chat.doc_id,
                    chat.owner_project_id,
                )
        elif chat.parent_id and chat.ignore_parent_knowledge:
            logger.info(
                "Skipping parent chat messages for chat '%s' "
                "(ignore_parent_knowledge=True)",
                chat.doc_id,
            )

        # Add current chat messages (excluding the last one, which is the
        # current user message)
        for message in chat.messages[0:-1]:
            if message.hide or message.improvement:
                continue
            messages.append(self.convert_message(message))

        return messages

    # -------------------------------------------------------------------------
    # Helper: collect all files referenced across visible messages
    # -------------------------------------------------------------------------
    @staticmethod
    def _collect_files_from_visible_messages(
        valid_messages: List[Message],
        chat_base_files: List[str]
    ) -> List[str]:
        """
        Collect and deduplicate all file references from visible (non-hidden,
        non-improvement) messages plus the chat-level base file list.

        This ensures that files attached to *any* prior message are included in
        the working context, not just those on the most recent user message.

        flowchart TD
            A[chat.file_list] --> D[Union]
            B[Each visible message .files] --> D
            C[Deduplicate] --> E[Sorted list]
            D --> C

        :param valid_messages: All non-hidden, non-improvement messages for the turn.
        :param chat_base_files: Files already present on ``chat.file_list``.
        :return: Deduplicated, sorted list of file paths.
        """
        all_files: Set[str] = set(chat_base_files)
        for message in valid_messages:
            if message.files:
                all_files.update(message.files)
        # Sort for deterministic ordering
        return sorted(all_files)

    # -------------------------------------------------------------------------
    # Helper: resolve profiles, model and tools
    # -------------------------------------------------------------------------
    def _resolve_profiles_and_model(
        self,
        chat: Chat,
        query_mentions: QueryMentions,
        chat_files: List[str],
        is_refine: bool
    ) -> Dict[str, Any]:
        """
        Derive the active profiles, LLM model, tool list, and profile content string
        from the query mentions and chat state.

        Profiles are sorted by name and their content is formatted to be passed
        as part of the AI system prompt, including the current date/time.

        flowchart TD
            A[Query mentions profiles] --> B{Any profiles?}
            B -->|Yes| C[Sort profiles by name]
            C --> D[Build system prompt content]
            D --> E[Collect tools]
            E --> F{Profile has model?}
            F -->|Yes| G[Set chat_model from profile]
            F -->|No| H[Keep existing model]
            B -->|No| I{Any chat_files?}
            I -->|Yes| J[Set default profile content]
            I -->|No| K[Empty profile content]

        :param chat: The current chat object.
        :param query_mentions: Resolved mentions from the user query.
        :param chat_files: List of files attached to the chat.
        :param is_refine: Whether we are in task/refine mode.
        :return: Dict with keys: chat_profiles_system_content, chat_profile_names,
                 chat_model, chat_tools, is_refine.
        """
        all_profiles = query_mentions.profiles
        chat_profiles_system_content = ""
        chat_profile_names: List[str] = []
        chat_model: Optional[str] = chat.llm_model
        chat_tools: List[str] = []

        if all_profiles:
            # Sort profiles by name for consistent ordering
            sorted_profiles = sorted(all_profiles, key=lambda p: p.name)
            
            profile_blocks = []
            for profile in sorted_profiles:
                block = f"### PROFILE: {profile.name}\n"
                block += profile.parsed_content
                profile_blocks.append(block)
            
            chat_profiles_system_content = "\n\n".join(profile_blocks)
            chat_profile_names = [profile.name for profile in sorted_profiles]

            for profile in sorted_profiles:
                chat_tools = chat_tools + profile.tools
                logger.info("Profile '%s (%s)' tools: '%s'", profile.name, profile.project_id, profile.tools)
            chat_tools = list(set(chat_tools))
            

            if not chat_model:
                profile_models = [p for p in sorted_profiles if p.llm_model]
                if profile_models:
                    profile_model = profile_models[0]
                    chat_model = profile_model.llm_model
                    logger.info(
                        "chat_model '%s' from profile: '%s'",
                        profile_model.llm_model,
                        profile_model.name
                    )

            if next((p for p in sorted_profiles if p.chat_mode == CHAT_MODE_TASK), None):
                is_refine = True

        elif chat_files:
            chat_profiles_system_content = (
                "Focus on the changes required by the task "
                "and keep all other content as it is."
            )

        return {
            "chat_profiles_system_content": chat_profiles_system_content,
            "chat_profile_names": chat_profile_names,
            "chat_model": chat_model,
            "chat_tools": chat_tools,
            "is_refine": is_refine,
        }

    # -------------------------------------------------------------------------
    # Helper: evaluate knowledge-disable conditions
    # -------------------------------------------------------------------------
    def _evaluate_knowledge_flags(
        self,
        chat: Chat,
        disable_knowledge: bool,
        search_projects: List[CODXJuniorSettings],
        user_message: Message
    ) -> bool:
        """
        Determine whether knowledge search should be disabled, emitting events as needed.

        :param chat: The current chat object.
        :param disable_knowledge: Incoming disable flag.
        :param search_projects: Resolved search projects.
        :param user_message: The latest user message.
        :return: True if knowledge should be disabled, False otherwise.
        """
        if disable_knowledge:
            self.event_manager.chat_event(
                chat=chat,
                message="Knowledge search is disabled: Disabled by invocation"
            )
            return True

        if not search_projects:
            self.event_manager.chat_event(
                chat=chat,
                message="Knowledge search is disabled: No search projects found"
            )
            return True

        if not self.settings.use_knowledge:
            self.event_manager.chat_event(
                chat=chat,
                message="Knowledge search is disabled: Project settings disabled"
            )
            return True

        if user_message.disable_knowledge:
            self.event_manager.chat_event(
                chat=chat,
                message="Knowledge search is disabled: Disabled by user message"
            )
            return True

        return False

    # -------------------------------------------------------------------------
    # Helper: load content for explicitly attached chat files
    # -------------------------------------------------------------------------
    def _load_chat_files_content(
        self,
        chat_files: List[str],
        already_in_messages: Set[str]
    ) -> str:
        """
        Read and format the content of files explicitly attached to the chat.

        Files already embedded as code blocks in the message history are skipped
        to avoid duplication.

        :param chat_files: List of file paths to load.
        :param already_in_messages: Set of file paths already present in message bodies.
        :return: Concatenated formatted file content string.
        """
        chat_files_content = ""
        for chat_file in chat_files:
            if chat_file in already_in_messages:
                continue

            chat_file_full_path = self._resolve_chat_file_path(chat_file)
            if not chat_file_full_path:
                continue

            try:
                with open(chat_file_full_path, "r", encoding="utf-8") as fh:
                    source = chat_file_full_path.replace(
                        self.settings.abs_project_path + "/", ""
                    )
                    logger.info(
                        "Loading chat_file content from '%s' with source: '%s'",
                        chat_file_full_path,
                        source
                    )
                    doc_context = self._document_to_context(
                        Document(
                            page_content=fh.read(),
                            metadata={"source": source}
                        )
                    )
                    chat_files_content += doc_context + "\n"
            except OSError as ex:
                logger.error("Error adding context file to chat: %s", ex)

        return chat_files_content

    def _document_to_context(self, doc: Document) -> str:
        """
        Convert a Document to a formatted context string with language-specific code fence.

        :param doc: The Document to convert.
        :return: Formatted context string with file metadata and code fence.
        """
        content = doc.page_content
        source = doc.metadata['source']
        language = doc.metadata.get('language')
        extension = source.split(".")[-1] if "." in source else ""

        language = language or extension
        language = LANGUAGE_PARSER_MAPPING.get(language, language)
        
        return concat_content([
            "### FILE CONTEXT",
            f"This is the actual project's file content for '{source}', use same file path in your response.",
            "This content represent the current file, use it as a base for changes.",
            "",
            f"```{language} {source}",
            content,
            "```",
            ""
        ])

    def _resolve_chat_file_path(self, chat_file: str) -> Optional[str]:
        """
        Resolve the full filesystem path of a chat-attached file.

        Returns None and logs a warning if the file cannot be found.

        :param chat_file: Relative or absolute file path.
        :return: Resolved absolute path, or None if unresolvable.
        """
        if chat_file.startswith(self.settings.abs_project_path) or os.path.isfile(chat_file):
            return chat_file

        logger.info(
            "Normalizing chat_file '%s' for project path: '%s'",
            chat_file,
            self.settings.abs_project_path
        )
        normalized = chat_file.lstrip("/")
        full_path = os.path.join(self.settings.abs_project_path, normalized)
        return full_path

    # -------------------------------------------------------------------------
    # Helper: pre-search (vibe / search modes)
    # -------------------------------------------------------------------------
    async def _run_pre_search(
        self,
        chat: Chat,
        messages: List,
        query: str,
        chat_files: List[str]
    ) -> Tuple[List[Document], List[str], str]:
        """
        Execute the AI-driven pre-search used in vibe and search modes.

        Combines conversation history with the current query to build a richer
        search query, then delegates to ChatKnowledge.

        :param chat: The current chat object.
        :param messages: Existing LangChain messages (history).
        :param query: The raw user query string.
        :param chat_files: Files already attached to the chat.
        :return: Tuple of (documents, file_list, context_string).
        """
        history_context = concat_content([m.content for m in messages])
        pre_search_query = f"{history_context}\n{query}".strip()

        pre_docs, pre_file_list, pre_context = (
            await self.chat_knowledge.ai_search_for_context(
                chat=chat,
                query=pre_search_query,
                existing_chat_files=chat_files
            )
        )
        logger.info("Pre-search added %d documents to context", len(pre_docs))
        return pre_docs, pre_file_list, pre_context

    # -------------------------------------------------------------------------
    # Helper: standard RAG knowledge search
    # -------------------------------------------------------------------------
    def _run_rag_knowledge_search(
        self,
        chat: Chat,
        messages: List,
        query: str,
        ignore_documents: List[str],
        search_projects: List[CODXJuniorSettings]
    ) -> Tuple[List[Document], List[str], str]:
        """
        Perform the standard RAG document search across the given search projects.

        :param chat: The current chat object.
        :param messages: Existing LangChain message history.
        :param query: The raw user query string.
        :param ignore_documents: File paths to exclude from search results.
        :param search_projects: Projects to search within.
        :return: Tuple of (documents, file_list, context_string).
        """
        rag_documents: List[Document] = []
        file_list: List[str] = []
        context = ""

        chat.messages.append(
            self._new_chat_message(
                "assistant",
                content=f"Searching in {[p.project_name for p in search_projects]}"
            )
        )
        logger.info("chat_with_project start project search %s", search_projects)

        try:
            if query:
                query_context = concat_content([message.content for message in messages])
                search_query = self.chat_knowledge.create_knowledge_search_query(
                    query=f"{query_context}\n{query}"
                )
                self.event_manager.chat_event(
                    chat=chat,
                    message=f"Knowledge searching for: {search_query}"
                )

                rag_documents, file_list = (
                    self.chat_knowledge.select_documents_from_knowledge(
                        chat=chat,
                        query=search_query,
                        ignore_documents=ignore_documents,
                        search_projects=search_projects
                    )
                )
                for doc in rag_documents:
                    doc_context = document_to_code_block(doc)
                    context += f"{doc_context}\n"

            self.event_manager.chat_event(
                chat=chat,
                message=f"Knowledge search found {len(rag_documents)} relevant documents"
            )
        except (OSError, ValueError, RuntimeError) as ex:
            self.event_manager.chat_event(
                chat=chat,
                message=f"!!Error searching in knowledge {ex}",
                event_type="error"
            )
            logger.exception("!!Error searching in knowledge: %s", ex)

        return rag_documents, file_list, context

    # -------------------------------------------------------------------------
    # Helper: build the final AI prompt messages list
    # -------------------------------------------------------------------------
    def _build_ai_prompt_messages(
        self,
        chat: Chat,
        messages: List,
        user_message: Message,
        last_ai_message: Optional[Message],
        context: str,
        chat_files_content: str,
        is_refine: bool,
        is_agent: bool,
        iterations_left: int
    ) -> List:
        """
        Assemble the final list of LangChain messages to send to the AI.

        This appends context, working-file content, and the mode-specific prompt
        (refine / agent / standard) to the history. Profile instructions are now
        handled via the system prompt.

        flowchart TD
            A[Start] --> B{Context?}
            B -->|Yes| C[Append context message]
            B -->|No| D{is_refine?}
            C --> D
            D -->|Yes| E[Build refine message]
            D -->|No| F{is_agent?}
            F -->|Yes| G[Build agent message]
            F -->|No| H[Append user message directly]
            E --> I{chat_files_content?}
            G --> I
            H --> I
            I -->|Yes| J[Prepend working files header]
            I -->|No| K[Return messages]
            J --> K

        :param chat: The current chat object.
        :param messages: LangChain message history (will be mutated by appending).
        :param user_message: The latest user message.
        :param last_ai_message: The most recent AI message in history, or None.
        :param context: RAG / pre-search context string.
        :param chat_files_content: Content of explicitly attached files.
        :param is_refine: Whether we are in task/refine mode.
        :param is_agent: Whether we are in agent mode.
        :param iterations_left: Remaining agent iterations.
        :return: Mutated messages list ready for AI invocation.
        """
        if context:
            messages.append(
                self.convert_message(
                    self._new_chat_message(
                        role="user",
                        content=f"<project_files>{context}</project_files>"
                    )
                )
            )

        if is_refine:
            messages = self._append_refine_message(
                chat=chat,
                messages=messages,
                user_message=user_message,
                last_ai_message=last_ai_message
            )
        elif is_agent:
            messages = self._append_agent_message(
                chat=chat,
                messages=messages,
                user_message=user_message,
                iterations_left=iterations_left
            )
        else:
            messages.append(self.convert_message(user_message))

        if chat_files_content:
            messages[-1].content = (
                f"\n## Working Files:\n"
                f"{chat_files_content}\n"
                f"\n## User request\n"
                f"{messages[-1].content}"
            )

        return messages

    def _append_refine_message(
        self,
        chat: Chat,
        messages: List,
        user_message: Message,
        last_ai_message: Optional[Message]
    ) -> List:
        """
        Append a task-refinement prompt to the message list.

        If a previous AI document exists, it asks the model to apply comments to it.
        Otherwise it simply uses the raw user message content.

        Incorporates parent context if available and not ignored.

        :param chat: The current chat object.
        :param messages: Existing message list.
        :param user_message: The latest user message.
        :param last_ai_message: The most recent AI message, or None.
        :return: Updated messages list.
        """
        existing_document = last_ai_message.content if last_ai_message else ""
        parent_task = ""
        
        # FIXED: Resolve parent context internally based on ignore_parent_knowledge flag
        if not chat.ignore_parent_knowledge:
            parent_task = self.get_chat_analysis_parents(chat=chat)
        
        task_content = ""

        answer_messages = [
            message.content for message in chat.messages if message.is_answer
        ]
        if answer_messages:
            task_content += "Task Document Header:\n"
            task_content += concat_content(answer_messages)
            task_content += "\n\n"

        if parent_task:
            task_content += (
                f"\nYou are writing a child document.\n"
                f"This information comes from the parent document for your information:\n"
                f"<parent_document>\n{parent_task}\n</parent_document>\n"
            )

        if existing_document:
            task_content += (
                f"\n<document>\n{existing_document}\n</document>\n\n"
                f"<comments>\n{user_message.content}\n</comments>\n\n"
                f"INSTRUCTIONS:\n"
                f" * Read comments and update document content based on them\n"
                f" * Leave all parts of the document not affected by the comments untouched\n"
                f" * Output the final document content\n"
            )
        else:
            task_content += user_message.content

        refine_message = self._new_chat_message(role="user", content=task_content)
        messages.append(self.convert_message(refine_message))
        return messages

    def _append_agent_message(
        self,
        chat: Chat,
        messages: List,
        user_message: Message,
        iterations_left: int
    ) -> List:
        """
        Append an agent-style prompt that instructs the model to complete a task.

        Incorporates parent context if available and not ignored.

        :param chat: The current chat object.
        :param messages: Existing message list.
        :param user_message: The latest user message.
        :param iterations_left: How many iterations remain.
        :return: Updated messages list.
        """
        parent_context = ""
        
        # FIXED: Resolve parent context internally based on ignore_parent_knowledge flag
        if not chat.ignore_parent_knowledge:
            parent_context = self.get_chat_analysis_parents(chat=chat)
        
        agent_content = (
            f"You are responsible to end this task.\n"
            f"Follow instructions and try to solve it with the minimum iterations needed.\n"
            f"<task>\n{chat.name}\n</task>\n\n"
        )

        if parent_context:
            agent_content += (
                f"You are writing a child document based on prior context:\n"
                f"<parent_context>\n{parent_context}\n</parent_context>\n\n"
            )

        agent_content += (
            f"<user_request>\n{user_message.content}\n</user_request>\n\n"
            f"You still have {iterations_left} attempts more to finish the task.\n"
            f"Return {AGENT_DONE_WORD} when the task is done.\n"
        )
        
        agent_message = self._new_chat_message(role="user", content=agent_content)
        messages.append(self.convert_message(agent_message))
        return messages

    # -------------------------------------------------------------------------
    # Helper: extract code blocks with filenames from response content
    # -------------------------------------------------------------------------
    def _extract_files_from_response(self, content: str) -> List[Dict[str, str]]:
        """
        Extract code blocks with filenames from the AI response content.

        Parses markdown code blocks in the format:
        ```language filename
        code content here
        ```

        Returns a list of dicts with keys: language, file_path, content

        :param content: The response content string to parse.
        :return: List of file dicts extracted from code blocks.
        """
        files: List[Dict[str, str]] = []
        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]
            # Match opening code fence with language and filename
            open_match = re.match(r'^```(\w+)\s+(.+)$', line)

            if open_match:
                language = open_match.group(1)
                file_path = open_match.group(2).strip()
                code_lines: List[str] = []
                i += 1
                nesting_depth = 1

                # Collect code content until closing fence
                while i < len(lines) and nesting_depth > 0:
                    current_line = lines[i]

                    # Check for nested code fences
                    if re.match(r'^```(\w+)', current_line):
                        nesting_depth += 1
                        code_lines.append(current_line)
                    elif current_line == '```':
                        nesting_depth -= 1
                        if nesting_depth > 0:
                            code_lines.append(current_line)
                    else:
                        code_lines.append(current_line)

                    i += 1

                # Only add if we have a filename
                if file_path:
                    files.append({
                        "language": language,
                        "file_path": file_path,
                        "content": '\n'.join(code_lines)
                    })
            else:
                i += 1

        logger.info("Extracted %d files from response content", len(files))
        return files

    # -------------------------------------------------------------------------
    # ADDED: Helper to build user-friendly error message from API response
    # -------------------------------------------------------------------------
    @staticmethod
    def _build_friendly_error_message(error: Exception) -> str:
        """
        Extract and format API error details for user consumption.

        Handles OpenAI BadRequestError with parameter constraints, falling back
        to a generic message for other error types.

        :param error: The exception to extract details from.
        :return: User-friendly error message.
        """
        error_str = str(error)
        
        try:
            # BadRequestError contains response with error details
            if hasattr(error, 'response') and error.response:
                error_body = error.response.json() if hasattr(error.response, 'json') else {}
                if isinstance(error_body, dict):
                    error_info = error_body.get('error', {})
                    if isinstance(error_info, dict):
                        msg = error_info.get('message', '')
                        param = error_info.get('param', '')
                        
                        if msg and param:
                            return (
                                f"⚠️ **Model Configuration Issue**\n\n"
                                f"Parameter: `{param}`\n\n"
                                f"Error: {msg}\n\n"
                                f"*Suggestion: Check your model settings or try with different parameters.*"
                            )
                        elif msg:
                            return f"⚠️ **API Error**: {msg}"
        except Exception:
            pass
        
        # Generic fallback
        return f"⚠️ **Request Error**: {error_str}"

    # -------------------------------------------------------------------------
    # Helper: execute AI response
    # -------------------------------------------------------------------------
    async def _execute_ai_response(
        self,
        chat: Chat,
        messages: List,
        is_search: bool,
        ai,
        ai_headers: Dict[str, str],
        chat_tools: List[str],
        response_message: Message,
        task_item: Optional[str],
        callback,
        send_message_event,
        cancellation_token: Optional[CancellationToken] = None,
        run_context: Optional[AgentRunContext] = None,
        event_bridge: Optional[ChatEventBridge] = None,
    ) -> Tuple[Optional[str], str, List[str], Any]:
        """
        Invoke the appropriate AI or search handler and extract the response parts.

        Returns a tuple of (think_content, response_content, extra_files, ai_chat_fn).

        CRASH-SAFETY: when an error occurs, ``response_message.error`` is set
        and the response message is persisted IMMEDIATELY via the event bridge
        so the error survives even if a later step crashes.

        ADDED CRASH-SAFETY: hidden reasoning messages produced by multi-step
        runs are persisted the moment they are appended (via
        ``event_bridge.persist_message``) instead of waiting for the
        end-of-turn chat save.

        FIX Issue 3: The ``is_thinking`` / ``think_content`` detection block
        has been removed. ``message_parts`` is always a single-element list so
        ``is_thinking`` was always ``False`` and ``think_content`` always
        ``None``. The ``think`` field is already populated correctly during
        streaming via ``send_message_event`` → ``response_message.think``;
        overwriting it here would erase the streamed think content.

        flowchart TD
            A{is_search?} -->|Yes| B[KnowledgeAISearch]
            A -->|No| C[AI Chat with run_context]
            B --> D[Build search message]
            C --> E[Extract last message content]
            C -->|hidden reasoning| F4[persist_message - immediate]
            C -->|tool events| F2[Events persisted on response_message]
            C -->|error| F3[response_message.error persisted immediately]
            D --> F[Return think, content, files]
            E --> F

        :param chat: The current chat.
        :param messages: Assembled prompt messages.
        :param is_search: Whether this is a pure knowledge search request.
        :param ai: Configured AI instance.
        :param ai_headers: HTTP-style headers forwarded to the AI provider.
        :param chat_tools: Tool names available to the AI.
        :param response_message: The response message being assembled; the
                                 run_context listeners attach tool/lifecycle
                                 events to it during the AI call.
        :param task_item: The task item type of the current user message.
        :param callback: Streaming callback for partial content.
        :param send_message_event: Callable to emit partial response events.
        :param cancellation_token: Optional token to cancel the ongoing request.
        :param run_context: Optional AgentRunContext with the ChatEventBridge
                            listener bound to *response_message* (used only
                            for the main chat request).
        :param event_bridge: Optional bridge used to persist the response
                             message immediately on error and to persist
                             hidden reasoning messages as they are produced.
        :return: Tuple of (think_content, main_content, extra_file_list, ai_chat_fn).
        """
        # FIX Issue 3: think_content is NOT derived here — it is set on
        # response_message.think during streaming via send_message_event.
        # Returning None here preserves whatever was already streamed.
        think_content: Optional[str] = None
        main_content = ""
        extra_files: List[str] = []

        async def ai_chat(messages=None, prompt="", tags="", callback=None, run_context=None):
            """Invoke the AI with the assembled messages and optional prompt."""
            if messages is None:
                messages = []
            headers = ai_headers
            if tags:
                headers = {**ai_headers, "tags": ai_headers["tags"] + "," + tags}
            return await ai.a_chat(
                messages=messages,
                prompt=prompt,
                callback=callback,
                headers=headers,
                tools=chat_tools,
                cancellation_token=cancellation_token,
                chat_id=chat.id,
                run_context=run_context,
                current_chat=chat,
            )

        try:
            input_messages_count = len(messages)

            if is_search:
                self.event_manager.chat_event(
                    chat=chat,
                    message=f"Knowledge search for: {chat.name}"
                )
                send_message_event("* Searching...", False)
                combined_query = concat_content([m.content for m in messages])
                ai_search_results = await KnowledgeAISearch(
                    settings=self.settings
                ).ai_search(user_query=combined_query)
                search_message = build_search_message(ai_search_results)
                main_content = search_message.content
                extra_files = search_message.files or []
            else:
                # The run_context (with the ChatEventBridge listener bound to
                # response_message) is only forwarded for the MAIN chat request
                # so tool / lifecycle events are attached to the response.
                # Auxiliary calls (summary, auto-init) reuse ai_chat without a
                # run_context.
                response_messages = await ai_chat(
                    messages=messages,
                    callback=callback,
                    run_context=run_context,
                )
                new_message_count = len(response_messages) - input_messages_count

                if new_message_count > 1:
                    for reasoning_message in response_messages[input_messages_count + 1:-1]:
                        hidden_msg = self._new_chat_message(
                            role=reasoning_message.type,
                            content=reasoning_message.content
                        )
                        hidden_msg.hide = True
                        chat.messages.append(hidden_msg)
                        # ADDED CRASH-SAFETY: persist each hidden reasoning
                        # message IMMEDIATELY so it survives a crash before
                        # the end-of-turn chat save.
                        if event_bridge:
                            event_bridge.persist_message(hidden_msg)

                # FIX Issue 3: message_parts was always a single-element list
                # so is_thinking was always False and think_content always None.
                # Read only the final answer from the last message directly.
                # response_message.think is already set correctly by
                # send_message_event during streaming — do not touch it here.
                main_content = response_messages[-1].content

        except Exception as ex:
            logger.exception(
                "Ops, sorry! Error chatting with project: %s %s", ex, chat.id
            )
            main_content = f"Ops, sorry! There was an error with latest request: {ex}"
            response_message.error = str(ex)
            response_message.content = concat_content([response_message.content, main_content])
            # CRASH-SAFETY: persist the error state IMMEDIATELY so it is not
            # lost if any later step (summary, metadata, save) fails.
            if event_bridge:
                event_bridge.publish()

        return think_content, main_content, extra_files, ai_chat

    # -------------------------------------------------------------------------
    # Helper: finalize response metadata
    # -------------------------------------------------------------------------
    @staticmethod
    def _finalize_response_metadata(
        response_message: Message,
        user_message: Message,
        timing_info: Dict[str, Any],
        ai_model: str,
        chat_profile_names: List[str],
        extracted_files: List[Dict[str, str]] = None
    ) -> None:
        """
        Stamp the response message with timing, model metadata, and extracted files.

        Merges ``user_message.meta_data`` into the existing
        ``response_message.meta_data`` so that fields already present on the
        response message (e.g. ``cancellation_token_id`` stamped in step 6 or
        ``analytics`` set by the ChatEventBridge) are **not** overwritten.

        :param response_message: The message to annotate.
        :param user_message: The originating user message (provides base meta_data).
        :param timing_info: Dict containing 'start_time' and 'first_response'.
        :param ai_model: Name of the model that generated the response.
        :param chat_profile_names: Names of profiles active during this turn.
        :param extracted_files: List of file dicts extracted from code blocks.
        """
        # Start from the user message's meta_data (may contain client-side fields),
        # then overlay with whatever was already on the response message so that
        # fields like ``cancellation_token_id`` and ``analytics`` that were
        # stamped before/during the AI call are preserved.
        base_meta: Dict[str, Any] = dict(user_message.meta_data or {})
        base_meta.update(response_message.meta_data or {})

        base_meta["time_taken"] = time.time() - timing_info["start_time"]
        base_meta["first_chunk_time_taken"] = timing_info["first_response"]
        base_meta["model"] = ai_model

        # Add extracted files to metadata
        if extracted_files:
            base_meta["files"] = extracted_files
            logger.info("Added %d extracted files to response metadata", len(extracted_files))

        response_message.meta_data = base_meta

    # -------------------------------------------------------------------------
    # Helper: build clean message history for description (ADDED)
    # -------------------------------------------------------------------------
    @staticmethod
    def _build_clean_message_history_for_description(chat: Chat) -> List:
        """
        Build a message history that excludes system prompts, profile content,
        and file content details.

        This creates a cleaner conversation history suitable for generating
        concise summaries without the technical implementation details.

        Only includes the natural user and assistant messages from the chat,
        excluding hidden and improvement messages.

        :param chat: The chat whose clean history to build.
        :return: List of clean message content strings (user and assistant only).
        """
        clean_messages = []
        
        for message in chat.messages:
            # Skip hidden and improvement messages
            if message.hide or message.improvement:
                continue
            
            # Only include actual user and assistant messages
            if message.role not in ("user", "assistant"):
                continue
            
            # Clean the content by removing file content markers and system prompts
            content = message.content.strip()
            
            # Skip context/file markers added during processing
            if content.startswith("<project_files>") or content.startswith("## Working Files:"):
                # Extract just the user request part if it exists
                if "## User request" in content:
                    parts = content.split("## User request")
                    if len(parts) > 1:
                        content = parts[1].strip()
                    else:
                        continue
                else:
                    continue
            
            # Skip processing messages
            if content.startswith("* Processing"):
                continue
            
            # Skip search messages
            if content.startswith("Searching in") or content.startswith("Knowledge search"):
                continue
            
            if content:
                clean_messages.append(content)
        
        logger.info(
            "Built clean message history for description: %d messages",
            len(clean_messages)
        )
        return clean_messages

    # -------------------------------------------------------------------------
    # Helper: generate chat description and history entry
    # -------------------------------------------------------------------------
    async def _generate_chat_description(
        self,
        chat: Chat,
        messages: List,
        is_refine: bool,
        ai_chat_fn
    ) -> None:
        """
        Generate and store a short summary of the conversation.

        The summary includes only the core conversation content, excluding:
        - Profile content and instructions
        - File contents (only file paths are considered)
        - Processing/system messages

        Maintains a timestamped history of descriptions as the chat evolves,
        allowing review of context changes over time.

        :param chat: The chat to annotate with a description.
        :param messages: Message list used for the conversation.
        :param is_refine: Whether we are in task/refine mode (uses only last message).
        :param ai_chat_fn: Async callable matching the ai_chat signature.
        """
        try:
            # Build clean messages without file contents and profile information
            clean_messages = self._build_clean_message_history_for_description(chat)
            
            if not clean_messages:
                logger.warning(
                    "No clean messages available for description generation in chat '%s'",
                    chat.doc_id
                )
                return
            
            # Convert clean message strings back to LangChain format
            desc_messages = []
            for i, content in enumerate(clean_messages):
                # Alternate between user and assistant, starting with user
                role = "user" if i % 2 == 0 else "assistant"
                if role == "user":
                    desc_messages.append(HumanMessage(content=content))
                else:
                    desc_messages.append(AIMessage(content=content))
            
            # If in refine mode, use only the last message for context
            if is_refine and desc_messages:
                desc_messages = [desc_messages[-1]]
            
            logger.info(
                "Generating chat description from %d clean messages for chat '%s'",
                len(desc_messages),
                chat.doc_id
            )
            
            description_response = await ai_chat_fn(
                messages=desc_messages,
                prompt="Create a 5 lines summary of the conversation",
                tags="chat-summary"
            )
            
            new_description = description_response[-1].content.strip()
            
            # Update current description
            chat.description = new_description
            
            # Create and append history entry
            history_entry = ChatHistoryEntry(
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
                summary=new_description,
                message_ids=[m.doc_id for m in chat.messages]
            )
            
            # Initialize history if needed
            if not hasattr(chat, 'history') or chat.history is None:
                chat.history = []
            
            chat.history.append(history_entry)
            
            logger.info(
                "Chat description updated (history entries: %d) for chat '%s'",
                len(chat.history),
                chat.doc_id
            )
        except (ValueError, RuntimeError, OSError) as ex:
            logger.exception(
                "Error generating chat description: %s %s", ex, chat.doc_id
            )

    # -------------------------------------------------------------------------
    # Helper: auto-initialize auto_initialize chat metadata
    # -------------------------------------------------------------------------
    async def _auto_initialize_chat_metadata(
        self,
        chat: Chat,
        messages: List,
        ai_chat_fn
    ) -> None:
        """
        Use AI to auto-fill missing chat metadata for auto_initialize chats.

        When a chat is marked as ``auto_initialize``, this method asks the AI to
        suggest values for ``name``, ``board``, and ``column`` based on the
        conversation content.  Only fields that are currently empty/blank will
        be overwritten.  On success the ``auto_initialize`` flag is cleared.

        flowchart TD
            A{chat.auto_initialize?} -->|No| Z[Skip]
            A -->|Yes| B[Build init messages from history]
            B --> C[Call AI with CHAT_INIT_PROMPT]
            C --> D[Parse JSON response]
            D --> E{name missing?}
            E -->|Yes| F[Set chat.name]
            E -->|No| G{board missing?}
            F --> G
            G -->|Yes| H[Set chat.board]
            G -->|No| I{column missing?}
            H --> I
            I -->|Yes| J[Set chat.column]
            J --> K[Clear auto_initialize flag]
            I -->|No| K

        :param chat: The chat whose metadata may be auto-filled.
        :param messages: The assembled message list for the current turn.
        :param ai_chat_fn: Async callable matching the ai_chat signature.
        """
        if not chat.auto_initialize:
            return

        logger.info(
            "Chat '%s' is auto_initialize — attempting AI metadata auto-fill",
            chat.doc_id
        )

        try:
            init_messages = messages.copy()
            init_response = await ai_chat_fn(
                messages=init_messages,
                prompt=CHAT_INIT_PROMPT,
                tags="chat-init"
            )
            raw = init_response[-1].content.strip()

            # Strip possible markdown code fences
            if raw.startswith("```"):
                raw = concat_content(
                    line for line in raw.splitlines()
                    if not line.startswith("```")
                ).strip()

            suggestions: Dict[str, str] = json.loads(raw)
            logger.info(
                "Chat init suggestions for '%s': %s", chat.doc_id, suggestions
            )

            if suggestions.get("name"):
                chat.name = suggestions["name"]
                logger.info("Auto-set chat.name = '%s'", chat.name)

            if not chat.board and suggestions.get("board"):
                chat.board = suggestions["board"]
                logger.info("Auto-set chat.board = '%s'", chat.board)

            if not chat.column and suggestions.get("column"):
                chat.column = suggestions["column"]
                logger.info("Auto-set chat.column = '%s'", chat.column)

            chat.auto_initialize = False
            logger.info(
                "Chat '%s' metadata initialized: name='%s' board='%s' column='%s'",
                chat.doc_id, chat.name, chat.board, chat.column
            )

        except (ValueError, RuntimeError, JSONDecodeError, OSError) as ex:
            logger.exception(
                "Error auto-initializing chat metadata for '%s': %s", chat.doc_id, ex
            )

    # -------------------------------------------------------------------------
    # Helper: handle post-task mode cleanup
    # -------------------------------------------------------------------------
    @staticmethod
    def _hide_non_answer_messages(chat: Chat) -> None:
        """
        In task mode, hide all prior messages that are not marked as answers.

        :param chat: The chat to process.
        """
        for message in chat.messages[:-1]:
            if not message.is_answer:
                message.hide = True

    # -------------------------------------------------------------------------
    # Helper: Record chat session START (ADDED)
    # -------------------------------------------------------------------------
    def _record_chat_session_start(
        self,
        chat: Chat,
        mode: str,
        profiles: List[str],
        files: List[str],
        iteration: int,
        max_iterations: int,
        llm_model: str,
        parent_chat_id: Optional[str] = None
    ) -> None:
        """
        Record the start of a chat session with initial context.

        Called at the beginning of chat processing to capture chat metadata
        and context information. Additional calls during the session can update
        this record with new information as it becomes available.

        :param chat: The chat object being processed.
        :param mode: Chat mode ('task', 'agent', 'vibe', 'chat').
        :param profiles: List of active profile names.
        :param files: List of files associated with the chat.
        :param iteration: Current iteration number (for agent mode).
        :param max_iterations: Maximum iterations allowed.
        :param llm_model: LLM model being used.
        :param parent_chat_id: Parent chat ID if nested.
        """
        try:
            self.analytics.record_chat_session(
                chat_id=chat.id,
                chat_name=chat.name or "Unnamed Chat",
                username=self.user.username if self.user else "anonymous",
                project_name=self.settings.project_name or "",
                project_id=getattr(self.settings, "project_id", "") or "",
                mode=mode,
                profiles=profiles,
                files=files,
                parent_chat_id=parent_chat_id,
                iteration=iteration,
                max_iterations=max_iterations,
                llm_model=llm_model,
                input_message_count=len(chat.messages),
                output_message_count=0,
            )
            logger.info(
                "Chat session start recorded: chat_id=%s mode=%s profiles=%s files=%d",
                chat.id, mode, profiles, len(files)
            )
        except OSError as ex:
            logger.warning("Failed to record chat session start: %s", ex)

    # -------------------------------------------------------------------------
    # Helper: Record chat session END (ADDED)
    # -------------------------------------------------------------------------
    def _record_chat_session_end(
        self,
        chat: Chat,
        mode: str,
        profiles: List[str],
        files: List[str],
        iteration: int,
        max_iterations: int,
        llm_model: str,
        start_time: float,
        parent_chat_id: Optional[str] = None,
        cancelled: bool = False,
        error: Optional[str] = None,
    ) -> None:
        """
        Record the end of a chat session with final metrics.

        Called after chat processing completes (or errors). Captures final duration,
        message counts, and error state.

        :param chat: The chat object being processed.
        :param mode: Chat mode ('task', 'agent', 'vibe', 'chat').
        :param profiles: List of active profile names.
        :param files: List of files associated with the chat.
        :param iteration: Final iteration number.
        :param max_iterations: Maximum iterations allowed.
        :param llm_model: LLM model being used.
        :param start_time: Timestamp when chat processing started.
        :param parent_chat_id: Parent chat ID if nested.
        :param cancelled: Whether the chat was cancelled.
        :param error: Error message if chat failed.
        """
        try:
            duration_seconds = time.time() - start_time
            output_message_count = len([m for m in chat.messages if m.role == "assistant"])

            self.analytics.record_chat_session(
                chat_id=chat.id,
                chat_name=chat.name or "Unnamed Chat",
                username=self.user.username if self.user else "anonymous",
                project_name=self.settings.project_name or "",
                project_id=getattr(self.settings, "project_id", "") or "",
                mode=mode,
                profiles=profiles,
                files=files,
                parent_chat_id=parent_chat_id,
                iteration=iteration,
                max_iterations=max_iterations,
                llm_model=llm_model,
                duration_seconds=duration_seconds,
                input_message_count=len([m for m in chat.messages if m.role == "user"]),
                output_message_count=output_message_count,
                cancelled=cancelled,
                error=error,
            )
            logger.info(
                "Chat session end recorded: chat_id=%s duration=%.2fs cancelled=%s error=%s",
                chat.id, duration_seconds, cancelled, error
            )
        except OSError as ex:
            logger.warning("Failed to record chat session end: %s", ex)

    # -------------------------------------------------------------------------
    # Main entry point
    # -------------------------------------------------------------------------
    @profile_function
    async def chat_with_project(
        self,
        chat: Chat,
        disable_knowledge: bool = False,
        callback=None,
        append_references: bool = True,
        chat_mode: str = None,
        iteration: int = 0,
        system: str = None
    ):
        """
        Main entry point for processing a chat interaction with a project.

        Handles context gathering, knowledge search, AI response generation,
        and agent iteration logic.

        A CancellationToken is registered in the global CANCELLATION_REGISTRY
        for the duration of this call (keyed by ``chat.doc_id``).  Each token
        also carries a unique ``token_id`` (UUID4) that is stamped into the
        response message's ``meta_data`` immediately so clients receive it via
        streaming events.

        CHANGED: The assistant response message is created BEFORE the AI call
        and passed to :class:`ChatEventBridge`; tool executions and run
        lifecycle events emitted during the run are attached to it as typed
        ``tool_events`` / ``lifecycle_events`` lists.

        CRASH-SAFETY: the bridge persists the response message on EVERY event
        change (merge-safe ChatManager methods) and the engine persists it
        immediately on error / cancellation, so tool results, run errors,
        analytics and partial content survive a crash mid-run.

        ADDED CRASH-SAFETY:
          * Streamed partial content is persisted (throttled) from the
            streaming callback via ``event_bridge.maybe_persist_stream``.
          * Hidden reasoning messages are persisted the moment they are
            appended via ``event_bridge.persist_message``.

        FIXED: Parent chat messages are now properly included in the message
        history when `ignore_parent_knowledge` flag is False, enabling proper
        context inheritance across chat hierarchy.

        External callers can cancel the in-flight request via:
          - ``CANCELLATION_REGISTRY.cancel(chat.doc_id)``          — by chat ID
          - ``CANCELLATION_REGISTRY.cancel_by_token_id(token_id)`` — by token UUID

        When cancellation occurs the response message's ``meta_data`` will
        contain a ``"cancelled_at"`` key with an ISO-8601 UTC timestamp.

        flowchart TD
            A[Start] --> A1[Register CancellationToken]
            A1 --> A2[Create response_message + stamp token_id]
            A2 --> A3[ChatEventBridge created EARLY - persists on every event]
            A3 --> B{Project match?}
            B -->|No| C[Switch project context]
            B -->|Yes| D[Resolve chat mode & profiles]
            D --> E{vibe or search?}
            E -->|Yes| F[AI Search for context]
            F --> G[Build context string]
            E -->|No| G
            G --> H{Knowledge enabled?}
            H -->|Yes| I[RAG document search]
            I --> J[Add docs to context]
            H -->|No| J
            J --> K{chat_mode?}
            K -->|task| L[Refine document]
            K -->|agent| M[Agent prompt]
            K -->|chat| N[Standard user message]
            L --> O[Record Chat Session START]
            M --> O
            N --> O
            O --> P[AI Chat]
            P -->|stream flush| P4[Throttled persist of partial content]
            P -->|hidden reasoning| P5[persist_message - immediate]
            P -->|tool events| P2[Events persisted + streamed]
            P -->|BadRequestError| P6[Catch param error + inform user]
            P --> Q{Cancelled or Error?}
            Q -->|Yes| R[bridge.publish - state persisted immediately]
            R --> S[Record Chat Session END]
            Q -->|No| T[Parse response + bridge.publish final state]
            T --> U{Agent done?}
            U -->|No, iterations left| V[Recurse]
            U -->|Yes| S[Record Chat Session END success]
            S --> W[Unregister CancellationToken]
            W --> X[Return chat + docs]

        :param chat: The Chat object containing messages and metadata.
        :param disable_knowledge: If True, skip knowledge base search.
        :param callback: Optional streaming callback for partial responses.
        :param append_references: Whether to append document references to the response.
        :param chat_mode: Override for the chat mode ('chat', 'task', 'agent', 'vibe').
        :param iteration: Current agent iteration count.
        :param system: Optional system prompt override.
        :return: Tuple of (updated Chat, list of Documents).
        """
        # --- Delegate to sibling engine if chat belongs to a different project ---
        if chat.project_id and chat.project_id != self.settings.project_id:
            logger.info(
                "chat project_id is not the same as current project, switching contexts:"
                " '%s' -> '%s'",
                self.settings.project_id,
                chat.project_id
            )
            return await self.switch_project(chat.project_id).chat_with_project(
                chat=chat,
                disable_knowledge=disable_knowledge,
                callback=callback,
                append_references=append_references,
                chat_mode=chat_mode,
                iteration=iteration
            )

        # ------------------------------------------------------------------
        # Register a cancellation token for this chat turn.
        # Only register at the outermost iteration to avoid replacing an
        # already-registered (and potentially cancelled) token mid-flight.
        # ------------------------------------------------------------------
        cancellation_token: Optional[CancellationToken] = None
        is_root_iteration = iteration == 0
        if is_root_iteration:
            cancellation_token = CANCELLATION_REGISTRY.register(chat.doc_id)
            logger.info(
                "CancellationToken registered for chat '%s' token_id='%s'",
                chat.doc_id,
                cancellation_token.token_id,
            )
        else:
            # Re-use the token that was registered at iteration 0
            cancellation_token = CANCELLATION_REGISTRY.get(chat.doc_id)

        try:
            return await self._chat_with_project_inner(
                chat=chat,
                disable_knowledge=disable_knowledge,
                callback=callback,
                append_references=append_references,
                chat_mode=chat_mode,
                iteration=iteration,
                system=system,
                cancellation_token=cancellation_token,
            )
        finally:
            if is_root_iteration:
                CANCELLATION_REGISTRY.unregister(chat.doc_id)
                logger.info(
                    "CancellationToken unregistered for chat '%s'", chat.doc_id
                )

    async def _chat_with_project_inner(
        self,
        chat: Chat,
        disable_knowledge: bool = False,
        callback=None,
        append_references: bool = True,
        chat_mode: str = None,
        iteration: int = 0,
        system: str = None,
        cancellation_token: Optional[CancellationToken] = None,
    ):
        """
        Internal implementation of chat_with_project.

        Separated from the public entry-point so that the cancellation token
        can be registered / unregistered exactly once around the full
        (possibly recursive) call tree.

        See ``chat_with_project`` for full parameter documentation.
        """
        with self.chat_action(chat=chat, event=f"Processing AI request {chat.name}"):
            logger.info(
                "Processing chat '%s'. Current project: '%s' target project '%s'",
                chat.name,
                self.settings.project_name,
                chat.project_id
            )

            # ------------------------------------------------------------------
            # 1. Collect timing information
            # ------------------------------------------------------------------
            timing_info: Dict[str, Any] = {
                "start_time": time.time(),
                "first_response": None
            }
            session_start_time = timing_info["start_time"]

            # ------------------------------------------------------------------
            # 2. Extract user message and basic query context
            # ------------------------------------------------------------------
            valid_messages = [
                message for message in chat.messages
                if not message.hide and not message.improvement
            ]
            all_messages_content_lines = "".join(
                [m.content for m in valid_messages]
            ).split("\n")
            all_messages_content_code_block_file_paths: Set[str] = {
                line.split()[-1]
                for line in all_messages_content_lines
                if line.startswith("```") and len(line.split()) >= 3
            }

            last_ai_messages = [m for m in valid_messages if m.role == "assistant"]
            last_ai_message = last_ai_messages[-1] if last_ai_messages else None

            user_message = valid_messages[-1] if valid_messages else Message(content="")
            query = user_message.content
            task_item = user_message.task_item

            # ------------------------------------------------------------------
            # 3. Resolve chat mode flags
            # ------------------------------------------------------------------
            mode_flags = self._resolve_chat_mode_flags(
                chat=chat,
                chat_mode=chat_mode,
                task_item=task_item
            )
            chat_mode = mode_flags["chat_mode"]
            is_refine: bool = mode_flags["is_refine"]
            is_agent: bool = mode_flags["is_agent"]
            is_vibe: bool = mode_flags["is_vibe"]
            is_search: bool = mode_flags["is_search"]
            needs_pre_search: bool = mode_flags["needs_pre_search"]

            # ------------------------------------------------------------------
            # 4. Agent iteration accounting
            # ------------------------------------------------------------------
            max_iterations = self.settings.get_agent_max_iterations()
            iterations_left = max_iterations - iteration

            # ------------------------------------------------------------------
            # 5. Resolve parent chat
            # ------------------------------------------------------------------
            parent_chat = None
            if chat.parent_id:
                chat_manager = self.get_chat_manager(project_id=chat.owner_project_id)
                parent_chat = chat_manager.find_by_id(chat.parent_id)

            # ------------------------------------------------------------------
            # 6. Initialise response message BEFORE the AI call and stamp the
            #    cancellation token_id immediately so clients receive it in the
            #    very first streaming event. All tool / lifecycle events of the
            #    upcoming run will be attached to this message and persisted on
            #    every change.
            # ------------------------------------------------------------------
            response_message = self._new_chat_message("assistant")
            response_message.meta_data = {"start_time": timing_info["start_time"]}
            if cancellation_token:
                response_message.meta_data["cancellation_token_id"] = cancellation_token.token_id
                logger.debug(
                    "Stamped cancellation_token_id='%s' into response meta_data "
                    "for chat '%s'",
                    cancellation_token.token_id,
                    chat.doc_id,
                )

            # ------------------------------------------------------------------
            # 6.5 CHANGED: Bind the ChatEventBridge to the response message
            #      EARLY (before the streaming callback is defined) so it can:
            #      * attach tool / lifecycle events during the AI call,
            #      * persist streamed partial content (throttled) from
            #        send_message_event — a hard kill loses at most a few
            #        seconds of text,
            #      * persist hidden reasoning messages immediately.
            #      CRASH-SAFETY: the bridge PERSISTS the response message on
            #      every event change (merge-safe ChatManager methods, with a
            #      defensive save_chat fallback) and streams it.
            # ------------------------------------------------------------------
            event_bridge = ChatEventBridge(
                chat=chat,
                response_message=response_message,
                chat_manager=self.get_chat_manager(project_id=chat.owner_project_id),
                event_manager=self.event_manager,
            )
            run_context = AgentRunContext(
                project_id=self.settings.project_id or "",
                listeners=[event_bridge.on_event],
            )
            logger.info(
                "AgentRunContext '%s' created for chat '%s' bound to response "
                "message '%s' (iteration %d)",
                run_context.run_id,
                chat.doc_id,
                response_message.doc_id,
                iteration,
            )

            # ------------------------------------------------------------------
            # 7. Resolve query mentions (profiles, files, projects)
            # ------------------------------------------------------------------
            query_mentions: QueryMentions = self.get_query_mentions(
                chat=chat, user_message=user_message
            )

            # ------------------------------------------------------------------
            # 8. Resolve chat files list
            #
            #    Collect files from ALL visible messages (not just the current
            #    user_message) to ensure context from earlier turns is included.
            #    Files referenced in query_mentions and parent_chat are also
            #    merged in. Duplicates are removed via set union in the helper.
            # ------------------------------------------------------------------
            chat_files: List[str] = self._collect_files_from_visible_messages(
                valid_messages=valid_messages,
                chat_base_files=chat.file_list or []
            )
            # Merge in files from query mentions (e.g. @file references)
            if query_mentions.files:
                chat_files = sorted(set(chat_files + query_mentions.files))
            # Merge in parent chat file list if present and not ignored
            if parent_chat and parent_chat.file_list and not chat.ignore_parent_files:
                chat_files = sorted(set(chat_files + parent_chat.file_list))
                logger.info(
                    "Merged parent chat files into context for chat '%s'",
                    chat.doc_id,
                )
            elif parent_chat and chat.ignore_parent_files:
                logger.info(
                    "Skipping parent chat files for chat '%s' (ignore_parent_files=True)",
                    chat.doc_id,
                )

            logger.info(
                "Resolved %d unique chat files for chat '%s': %s",
                len(chat_files),
                chat.doc_id,
                chat_files,
            )

            # ------------------------------------------------------------------
            # 9. Resolve profiles, model, and tools
            # ------------------------------------------------------------------
            profile_result = self._resolve_profiles_and_model(
                chat=chat,
                query_mentions=query_mentions,
                chat_files=chat_files,
                is_refine=is_refine
            )
            chat_profiles_system_content: str = profile_result["chat_profiles_system_content"]
            chat_profile_names: List[str] = profile_result["chat_profile_names"]
            chat_model: Optional[str] = profile_result["chat_model"]
            chat_tools: List[str] = profile_result["chat_tools"]
            is_refine = profile_result["is_refine"]

            if chat_profile_names:
                self.event_manager.chat_event(
                    chat=chat,
                    message=f"Chat profiles: {chat_profile_names}"
                )

            response_message.profiles = chat_profile_names
            
            # ------------------------------------------------------------------
            # 9.5 ADDED: Record chat session START with initial context
            # ------------------------------------------------------------------
            if iteration == 0:
                self._record_chat_session_start(
                    chat=chat,
                    mode=chat_mode,
                    profiles=chat_profile_names,
                    files=chat_files,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    llm_model=chat_model or (self.settings.get_llm_settings().model),
                    parent_chat_id=chat.parent_id if parent_chat else None,
                )
            
            # ------------------------------------------------------------------
            # 10. Resolve search projects
            # ------------------------------------------------------------------
            query_mention_projects: List[CODXJuniorSettings] = [
                p for p in query_mentions.projects
                if p and hasattr(p, "codx_path")
            ]
            search_projects: List[CODXJuniorSettings] = list(
                {s.codx_path: s for s in query_mention_projects}.values()
            )

            # ------------------------------------------------------------------
            # 11. Evaluate knowledge disable conditions
            # ------------------------------------------------------------------
            if is_refine:
                task_item = TASK_ITEM_ANALYSIS

            disable_knowledge = self._evaluate_knowledge_flags(
                chat=chat,
                disable_knowledge=disable_knowledge,
                search_projects=search_projects,
                user_message=user_message
            )

            # ------------------------------------------------------------------
            # 12. Build message history from prior turns (FIXED)
            #
            #     Now includes parent chat messages if ignore_parent_knowledge
            #     is False. Parent messages are prepended to ensure proper
            #     context hierarchy.
            # ------------------------------------------------------------------
            messages = self._build_message_history(
                chat=chat,
                include_parent_messages=True
            )

            ignore_documents = chat_files.copy()
            if chat.name:
                ignore_documents.append(f"/{chat.name}")

            # ------------------------------------------------------------------
            # 13. Load explicitly attached chat files
            # ------------------------------------------------------------------
            chat_files_content = self._load_chat_files_content(
                chat_files=chat_files,
                already_in_messages=all_messages_content_code_block_file_paths
            )

            # ------------------------------------------------------------------
            # 14. Prepare AI instance with merged system prompt
            # ------------------------------------------------------------------
            ai_settings = self.settings.get_llm_settings()
            logger.info("[chat_model] %s", chat_model)
            if chat_model:
                ai_settings.model = chat_model
            
            # Merge profile system content with any provided system prompt
            final_system_prompt = ""
            if chat_profiles_system_content:
                final_system_prompt = chat_profiles_system_content
            if system:
                if final_system_prompt:
                    final_system_prompt += "\n\n" + system
                else:
                    final_system_prompt = system
            
            ai = self.get_ai(llm_model=ai_settings.model, system=final_system_prompt)

            self.event_manager.chat_event(
                chat=chat, message=f"Chatting with {ai_settings.model}"
            )
            response_message.meta_data["model"] = ai_settings.model

            # ------------------------------------------------------------------
            # 15. Build AI request headers and tags
            # ------------------------------------------------------------------
            tags = [f"{chat.mode}"] + [p.name for p in query_mentions.profiles]
            if is_agent:
                tags.append("agent")
            if is_vibe:
                tags.append(CHAT_MODE_VIBE)
            ai_headers = {
                "tags": ",".join(list(set(tags + chat_tools + chat_profile_names)))
            }

            # ------------------------------------------------------------------
            # 16. Define streaming event emitter
            # ------------------------------------------------------------------
            def send_message_event(content: str, done: bool, documents=None) -> None:
                """
                Emit a message event with the current response state.

                Handles think/content separation for models that emit reasoning blocks.
                The ``cancellation_token_id`` present in ``response_message.meta_data``
                is forwarded to the client in every event so they can cancel at any time.

                ADDED CRASH-SAFETY: after streaming, a THROTTLED persist of the
                response message is triggered via the event bridge so streamed
                partial content survives a hard kill (bounded disk I/O).
                """
                if not response_message.is_thinking:
                    if content and content.startswith("") \
                            and not response_message.content:
                        response_message.is_thinking = True
                elif response_message.is_thinking and "" in content:
                    response_message.is_thinking = False

                content = content.replace("", "").replace("", "")

                if not timing_info.get("first_response"):
                    timing_info["first_response"] = (
                        time.time() - timing_info["start_time"]
                    )

                if response_message.is_thinking:
                    response_message.think = content
                else:
                    response_message.content = content

                sources: List[str] = []
                if documents:
                    sources = list({
                        d.metadata["source"].replace(self.settings.abs_project_path, "")
                        for d in documents
                    })
                response_message.files = list(set(response_message.files + sources))
                response_message.task_item = task_item
                response_message.done = done
                self.event_manager.message_event(chat=chat, message=response_message)
                # ADDED CRASH-SAFETY: throttled persist of streamed partial
                # content — a hard kill loses at most the throttle interval
                # of streamed text (never raises, bounded disk I/O).
                event_bridge.maybe_persist_stream()

            send_message_event("* Processing request, please wait...\n", False)

            # ------------------------------------------------------------------
            # 17. Document accumulator (shared across search steps)
            # ------------------------------------------------------------------
            context = ""
            documents: List[Document] = []

            # ------------------------------------------------------------------
            # 18. Pre-search (vibe / search modes)
            # ------------------------------------------------------------------
            if needs_pre_search:
                logger.info(
                    "Pre-search triggered. is_vibe=%s, is_search=%s",
                    is_vibe, is_search
                )
                pre_docs, pre_file_list, pre_context = await self._run_pre_search(
                    chat=chat,
                    messages=messages,
                    query=query,
                    chat_files=chat_files
                )
                if pre_docs:
                    documents.extend(pre_docs)
                    context += pre_context
                    response_message.files = list(
                        set(response_message.files + pre_file_list)
                    )

            # ------------------------------------------------------------------
            # 19. Standard RAG knowledge search
            # ------------------------------------------------------------------
            if not disable_knowledge and search_projects and not is_search:
                rag_docs, rag_file_list, rag_context = self._run_rag_knowledge_search(
                    chat=chat,
                    messages=messages,
                    query=query,
                    ignore_documents=ignore_documents,
                    search_projects=search_projects
                )
                documents.extend(rag_docs)
                context += rag_context
                response_message.files = list(
                    set(response_message.files + rag_file_list)
                )

            # ------------------------------------------------------------------
            # 20. Assemble final prompt messages
            # ------------------------------------------------------------------
            if not callback:
                def callback(content: str) -> None:
                    """Default streaming callback that emits partial response events."""
                    send_message_event(content=content, done=False)

            messages = self._build_ai_prompt_messages(
                chat=chat,
                messages=messages,
                user_message=user_message,
                last_ai_message=last_ai_message,
                context=context,
                chat_files_content=chat_files_content,
                is_refine=is_refine,
                is_agent=is_agent,
                iterations_left=iterations_left
            )

            # ------------------------------------------------------------------
            # 21. Execute AI / search response
            # ------------------------------------------------------------------
            try:
                think_content, main_content, extra_files, ai_chat_fn = (
                    await self._execute_ai_response(
                        chat=chat,
                        messages=messages,
                        is_search=is_search,
                        ai=ai,
                        ai_headers=ai_headers,
                        chat_tools=chat_tools,
                        response_message=response_message,
                        task_item=task_item,
                        callback=callback,
                        send_message_event=send_message_event,
                        cancellation_token=cancellation_token,
                        run_context=run_context,
                        event_bridge=event_bridge,
                    )
                )
            except CancelledError as cancel_exc:
                logger.info(
                    "chat_with_project: CancelledError for chat '%s': %s",
                    chat.doc_id, cancel_exc
                )
                cancelled_at = (
                    cancellation_token.cancelled_at
                    if cancellation_token and cancellation_token.cancelled_at
                    else datetime.now(tz=timezone.utc)
                )
                response_message.meta_data = response_message.meta_data or {}
                response_message.meta_data["cancelled_at"] = (
                    cancelled_at.isoformat()
                )
                response_message.content = concat_content([
                    response_message.content, 
                    (
                        response_message.content
                        or "*(Request was cancelled)*"
                    )
                ])

                response_message.done = True
                # CRASH-SAFETY: persist the cancelled state (and any events
                # collected so far) immediately; append only if the bridge
                # did not already register the message on the chat.
                self._append_message_if_missing(chat=chat, message=response_message)
                event_bridge.publish()
                self.event_manager.chat_event(chat=chat, message="cancelled")
                
                # ADDED: Record chat session END with cancellation
                if iteration == 0:
                    self._record_chat_session_end(
                        chat=chat,
                        mode=chat_mode,
                        profiles=chat_profile_names,
                        files=chat_files,
                        iteration=iteration,
                        max_iterations=max_iterations,
                        llm_model=chat_model or (self.settings.get_llm_settings().model),
                        start_time=session_start_time,
                        parent_chat_id=chat.parent_id if parent_chat else None,
                        cancelled=True,
                        error="User cancelled the request",
                    )
                
                return chat, documents

            # FIX Issue 3: think_content returned from _execute_ai_response is
            # always None (detection was removed). response_message.think is
            # already set correctly during streaming via send_message_event.
            # Do NOT overwrite it here — doing so would erase streamed think content.
            # Only set main_content and clear is_thinking flag.
            response_message.content = main_content
            
            response_message.is_thinking = False
            if extra_files:
                response_message.files = list(
                    set(response_message.files + extra_files)
                )
            send_message_event(content=response_message.content, done=True)

            # ------------------------------------------------------------------
            # 22. Extract files from response and finalize response metadata
            # ------------------------------------------------------------------
            extracted_files = self._extract_files_from_response(
                content=response_message.content
            )

            self._finalize_response_metadata(
                response_message=response_message,
                user_message=user_message,
                timing_info=timing_info,
                ai_model=ai_settings.model,
                chat_profile_names=chat_profile_names,
                extracted_files=extracted_files
            )

            # CRASH-SAFETY: persist the FINAL response state (content, error,
            # events, metadata) immediately — before summary/auto-init steps
            # that could still fail. The bridge may have already inserted the
            # message during the run, so guard the in-memory append by doc_id.
            self._append_message_if_missing(chat=chat, message=response_message)
            event_bridge.publish()
            logger.info("Chat done, adding message to chat. %s", chat.messages[-1])

            # ------------------------------------------------------------------
            # 23. Generate conversation summary and auto-initialize if needed
            # ------------------------------------------------------------------
            if not is_search:
                await self._generate_chat_description(
                    chat=chat,
                    messages=messages,
                    is_refine=is_refine,
                    ai_chat_fn=ai_chat_fn
                )

                # Auto-initialize auto_initialize chats on their first response
                await self._auto_initialize_chat_metadata(
                    chat=chat,
                    messages=messages,
                    ai_chat_fn=ai_chat_fn
                )

                if chat_mode == CHAT_MODE_TASK or is_vibe:
                    self._hide_non_answer_messages(chat=chat)

            # ------------------------------------------------------------------
            # 24. Agent iteration recursion
            # ------------------------------------------------------------------
            is_agent_done = AGENT_DONE_WORD in response_message.content
            if is_agent and not is_agent_done and iterations_left:
                self.event_manager.chat_event(
                    chat=chat, message=f"Agent iteration {iteration + 1}"
                )
                return await self._chat_with_project_inner(
                    chat=chat,
                    disable_knowledge=disable_knowledge,
                    callback=callback,
                    append_references=append_references,
                    chat_mode=chat_mode,
                    iteration=iteration + 1,
                    system=system,
                    cancellation_token=cancellation_token,
                )

            # ADDED: Record chat session END on success
            if iteration == 0:
                self._record_chat_session_end(
                    chat=chat,
                    mode=chat_mode,
                    profiles=chat_profile_names,
                    files=chat_files,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    llm_model=chat_model or (self.settings.get_llm_settings().model),
                    start_time=session_start_time,
                    parent_chat_id=chat.parent_id if parent_chat else None,
                    cancelled=False,
                    error=None,
                )

            self.event_manager.chat_event(chat=chat, message="done")
            return chat, documents

    def cancel_chat(self, chat_doc_id: str) -> bool:
        """
        Cancel an in-flight chat request identified by *chat_doc_id*.

        Delegates to ``CANCELLATION_REGISTRY.cancel``.

        :param chat_doc_id: The ``doc_id`` of the chat to cancel.
        :returns: True if a token was found and cancelled, False otherwise.
        """
        result = CANCELLATION_REGISTRY.cancel(chat_doc_id)
        logger.info(
            "cancel_chat called for chat_id='%s': token_found=%s",
            chat_doc_id,
            result,
        )
        return result

    def cancel_chat_by_token_id(self, token_id: str) -> bool:
        """
        Cancel an in-flight chat request identified by the cancellation *token_id*.

        This is the preferred method when the client received the ``token_id``
        from the response message ``meta_data`` and wants to cancel without
        knowing the chat ``doc_id``.

        Delegates to ``CANCELLATION_REGISTRY.cancel_by_token_id``.

        :param token_id: The UUID string of the CancellationToken to cancel.
        :returns: True if a token was found and cancelled, False otherwise.
        """
        result = CANCELLATION_REGISTRY.cancel_by_token_id(token_id)
        logger.info(
            "cancel_chat_by_token_id called for token_id='%s': token_found=%s",
            token_id,
            result,
        )
        return result

    def switch_project(self, project_id: str) -> "ChatEngine":
        """
        Switch to another project based on the provided project ID.

        :param project_id: The ID of the project to switch to.
        :return: The ChatEngine instance after switching the project.
        """
        if not project_id or project_id == self.settings.project_id:
            logger.debug("Already in project %s", project_id)
            return self

        settings = find_project_by_id(project_id=project_id)
        if settings:
            self.settings = settings
            self.chat_knowledge = ChatKnowledge(
                settings=self.settings,
                event_manager=self.event_manager
            )
            logger.info("Switched to project ID %s", project_id)
        else:
            logger.warning("No settings found for project ID %s", project_id)

        return self

    def get_ai(self, llm_model: Optional[str] = None, system: str = None) -> AI:
        """
        Get an AI instance configured for a specific model.

        :param llm_model: The name of the large language model.
        :param system: Optional system prompt override.
        :return: An AI instance.
        """
        ai_instance = AI(
            settings=self.settings,
            llm_model=llm_model,
            user=self.user,
            system=system,
            session=self,
        )
        logger.debug("AI instance created with model %s", llm_model)
        return ai_instance

    def get_ai_code_generator_changes(self, response: str) -> AICodeGenerator:
        """
        Process the response string to generate AI code generator changes.

        :param response: The string output from the AI model.
        :return: An instance of AICodeGenerator containing the parsed changes.
        """
        code_generator = AICodeGenerator.from_response(response)
        for change in code_generator.code_changes:
            file_path = change.file_path
            if not file_path.startswith(self.settings.abs_project_path):
                change.file_path = os.path.join(
                    self.settings.abs_project_path, file_path
                )
        logger.info("Code generator changes retrieved from response")
        return code_generator

    def get_query_mentions(self, chat: Chat, user_message: Message) -> QueryMentions:
        """
        Extract mentions of profiles and projects from the given query.

        :param chat: The current chat object.
        :param user_message: The latest user message.
        :return: A QueryMentions object with resolved profiles, projects, and files.
        """
        profile_manager = self.get_profile_manager()
        content = user_message.content
        profiles = (
            user_message.profiles if user_message.profiles else chat.profiles
        ) or []

        chat_files = list(set(chat.file_list + user_message.files))
        for chat_file in chat_files:
            file_profiles = [
                p.name
                for p in profile_manager.get_file_profiles_by_file_path(file_path=chat_file)
            ]
            profiles = profiles + file_profiles

        chat_profiles = [f"@{name}" for name in profiles]
        chat_utils = ChatUtils(profile_manager=profile_manager)
        query = f"{content} {chat_profiles} @project"
        query_mentions: QueryMentions = chat_utils.get_query_mentions(query=query)
        logger.debug(
            "Query mentions extracted for '%s...': %s",
            query[0:10],
            {
                "projects": [p.name for p in query_mentions.projects],
                "profiles": [p.name for p in query_mentions.profiles]
            }
        )
        return query_mentions

    def get_chat_analysis_parents(self, chat: Chat) -> str:
        """
        Traverse all parent chats and return concatenated non-hidden message content.

        Respects the ignore_parent_knowledge flag at each level during traversal.

        :param chat: The child chat whose parents to traverse.
        :return: Concatenated content string from all ancestor chats.
        """
        parent_content: List[str] = []
        chat_manager = self.get_chat_manager(project_id=chat.owner_project_id)
        parent_chat = chat_manager.find_by_id(chat.parent_id)

        if chat.parent_id and not parent_chat:
            logger.warning(
                "[parent_chat] parent_id: '%s' parent_project_id: '%s', "
                "Not found for chat: %s",
                chat.parent_id,
                chat.owner_project_id,
                chat.name
            )
            return ""

        while parent_chat:
            if parent_chat.ignore_parent_knowledge:
                logger.info(
                    "Parent chat '%s' has ignore_parent_knowledge=True, "
                    "stopping parent traversal",
                    parent_chat.doc_id,
                )
                break

            messages = [
                message.content
                for message in parent_chat.messages
                if not message.hide
            ]
            if messages:
                parent_content.append(concat_content(messages))
                logger.info(
                    "Collected %d messages from parent chat '%s'",
                    len(messages),
                    parent_chat.doc_id,
                )

            parent_chat = chat_manager.find_by_id(parent_chat.parent_id)

        result = concat_content(parent_content)
        logger.info(
            "get_chat_analysis_parents collected %d chars from %d parent levels",
            len(result),
            len(parent_content),
        )
        return result

    @staticmethod
    def convert_message(message: Message):
        """
        Convert a DB Message object into a LangChain message type.

        Handles text-only messages, image messages, and role-based conversion.

        :param message: The Message object to convert.
        :return: A LangChain HumanMessage, AIMessage, or image dict.
        """
        def parse_image(image: str) -> dict:
            """Parse an image string into a dict with src and alt fields."""
            try:
                return json.loads(image)
            except JSONDecodeError:
                return {"src": image, "alt": ""}

        if message.images:
            images = [parse_image(image) for image in message.images]
            text_content = {
                "type": "text",
                "text": message.content
            }
            content = [text_content] + [
                {
                    "type": "image_url",
                    "image_url": {"url": image["src"]}
                }
                for image in images
            ]
            msg = {"type": "image", "content": json.dumps(content)}
        elif message.role == "user":
            msg = HumanMessage(content=message.content)
        else:
            msg = AIMessage(content=message.content)

        return msg

    def get_all_search_projects(self) -> List[CODXJuniorSettings]:
        """
        Return all projects including child projects and dependencies.

        :return: List of CODXJuniorSettings for the current project and its relations.
        """
        project_child_projects, project_dependencies = get_project_dependencies(
            settings=self.settings
        )
        all_projects = [self.settings] + project_child_projects + project_dependencies
        return all_projects

    def index_chat(self, chat: Chat) -> None:
        """
        Index the chat as a Document in the knowledge system.

        Converts valid chat messages into a single Document with appropriate
        metadata.

        :param chat: The chat to index.
        """
        valid_messages = [
            message.content
            for message in chat.messages
            if not message.hide and not message.improvement
        ]

        page_content = concat_content(valid_messages)
        metadata = {
            "source": chat.file_path,
            "parser": "chat",
            "loader_type": "chat"
        }

        try:
            self.knowledge.index_document(page_content, metadata)
            logger.info("Chat indexed successfully: %s", chat.file_path)
        except (OSError, ValueError, RuntimeError) as ex:
            logger.exception("Failed to index chat: %s, error: %s", chat.file_path, ex)

# Made with ❤️ by codx-junior