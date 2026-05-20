import json
import logging
import os
import time
import uuid
from contextlib import contextmanager
from json import JSONDecodeError
from typing import List, Tuple, Optional, Dict, Any

from langchain.messages import (
    AIMessage,
    HumanMessage,
)

from langchain_core.documents import Document

from codx.junior.ai import AI
from codx.junior.chat_manager import ChatManager
from codx.junior.context import AICodeGenerator
from codx.junior.db import Chat, Message
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

# Set up logging
logger = logging.getLogger(__name__)

# Chat mode constants
CHAT_MODE_TASK = "task"
CHAT_MODE_AGENT = "agent"
CHAT_MODE_VIBE = "vibe"
TASK_ITEM_SEARCH = "search"
TASK_ITEM_ANALYSIS = "analysis"


class ChatEngine:
    """
    Core engine for managing chat interactions with AI models.

    Handles message processing, knowledge search, context building,
    and AI response generation for various chat modes.

    flowchart TD
        A[User Message] --> B{Chat Mode?}
        B -->|vibe| C[AI Search Context]
        B -->|search| C
        C --> D[Build Context]
        B -->|task| E[Refine Document]
        B -->|agent| F[Agent Iteration]
        B -->|chat| G[Standard Chat]
        D --> G
        E --> H[AI Response]
        F --> H
        G --> H
        H --> I[Return Chat + Documents]
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
        except Exception as ex:
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
    # Helper: build LangChain message history
    # -------------------------------------------------------------------------
    def _build_message_history(self, chat: Chat) -> List:
        """
        Convert all non-hidden, non-improvement chat messages (excluding the last)
        into LangChain message objects.

        :param chat: The chat whose history to convert.
        :return: List of LangChain message objects.
        """
        messages = []
        for message in chat.messages[0:-1]:
            if message.hide or message.improvement:
                continue
            messages.append(self.convert_message(message))
        return messages

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

        flowchart TD
            A[Query mentions profiles] --> B{Any profiles?}
            B -->|Yes| C[Build profile content]
            C --> D[Collect tools]
            D --> E{Profile has model?}
            E -->|Yes| F[Set chat_model from profile]
            E -->|No| G[Keep existing model]
            B -->|No| H{Any chat_files?}
            H -->|Yes| I[Set default profile content]
            H -->|No| J[Empty profile content]

        :param chat: The current chat object.
        :param query_mentions: Resolved mentions from the user query.
        :param chat_files: List of files attached to the chat.
        :param is_refine: Whether we are in task/refine mode.
        :return: Dict with keys: chat_profiles_content, chat_profile_names,
                 chat_model, chat_tools, is_refine.
        """
        all_profiles = query_mentions.profiles
        chat_profiles_content = ""
        chat_profile_names: List[str] = []
        chat_model: Optional[str] = chat.llm_model
        chat_tools: List[str] = []

        if all_profiles:
            chat_profiles_content = "\n".join([
                f"###PROFILE: {profile.name}\n{profile.parsed_content}"
                for profile in all_profiles
            ])
            chat_profile_names = [profile.name for profile in all_profiles]

            for profile in all_profiles:
                chat_tools = chat_tools + profile.tools
            chat_tools = list(set(chat_tools))
            logger.info("Profile tools: '%s'", chat_tools)

            if not chat_model:
                profile_models = [p for p in all_profiles if p.llm_model]
                if profile_models:
                    profile_model = profile_models[0]
                    chat_model = profile_model.llm_model
                    logger.info(
                        "chat_model '%s' from profile: '%s'",
                        profile_model.llm_model,
                        profile_model.name
                    )

            if next((p for p in all_profiles if p.chat_mode == CHAT_MODE_TASK), None):
                is_refine = True

        elif chat_files:
            chat_profiles_content = (
                "Focus on the changes required by the task "
                "and keep all other content as it is."
            )

        return {
            "chat_profiles_content": chat_profiles_content,
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
        already_in_messages: set
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
                    doc_context = document_to_code_block(
                        Document(
                            page_content=fh.read(),
                            metadata={"source": source}
                        )
                    )
                    chat_files_content += doc_context + "\n"
            except OSError as ex:
                logger.error("Error adding context file to chat: %s", ex)

        return chat_files_content

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
        history_context = "\n".join([m.content for m in messages])
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
                query_context = "\n".join([message.content for message in messages])
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
        chat_profiles_content: str,
        is_refine: bool,
        is_agent: bool,
        iterations_left: int
    ) -> List:
        """
        Assemble the final list of LangChain messages to send to the AI.

        This appends context, working-file content, profile instructions, and
        the mode-specific prompt (refine / agent / standard) to the history.

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
            I -->|No| K{chat_profiles_content?}
            J --> K
            K -->|Yes| L[Append profile instructions]
            K -->|No| M[Return messages]
            L --> M

        :param chat: The current chat object.
        :param messages: LangChain message history (will be mutated by appending).
        :param user_message: The latest user message.
        :param last_ai_message: The most recent AI message in history, or None.
        :param context: RAG / pre-search context string.
        :param chat_files_content: Content of explicitly attached files.
        :param chat_profiles_content: Concatenated profile instruction strings.
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

        if chat_profiles_content:
            messages[-1].content += f"\nInstructions:\n{chat_profiles_content}"

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

        :param chat: The current chat object.
        :param messages: Existing message list.
        :param user_message: The latest user message.
        :param last_ai_message: The most recent AI message, or None.
        :return: Updated messages list.
        """
        existing_document = last_ai_message.content if last_ai_message else ""
        parent_task = self.get_chat_analysis_parents(chat=chat)
        task_content = ""

        answer_messages = [
            message.content for message in chat.messages if message.is_answer
        ]
        if answer_messages:
            task_content += "Task Document Header:\n"
            task_content += "\n".join(answer_messages)
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

        :param chat: The current chat object.
        :param messages: Existing message list.
        :param user_message: The latest user message.
        :param iterations_left: How many iterations remain.
        :return: Updated messages list.
        """
        parent_context = self.get_chat_analysis_parents(chat=chat)
        agent_content = (
            f"\nYou are responsible to end this task.\n"
            f"Follow instructions and try to solve it with the minimum iterations needed.\n"
            f"<task>\n{chat.name}\n</task>\n\n"
            f"<parent_context>\n{parent_context}\n</parent_context>\n\n"
            f"<user_request>\n{user_message.content}\n</user_request>\n\n"
            f"You still have {iterations_left} attempts more to finish the task.\n"
            f"Return {AGENT_DONE_WORD} when the task is done.\n"
        )
        agent_message = self._new_chat_message(role="user", content=agent_content)
        messages.append(self.convert_message(agent_message))
        return messages

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
        send_message_event
    ) -> Tuple[Optional[str], Optional[str], List[str]]:
        """
        Invoke the appropriate AI or search handler and extract the response parts.

        Returns a tuple of (think_content, response_content, extra_files).

        flowchart TD
            A{is_search?} -->|Yes| B[KnowledgeAISearch]
            A -->|No| C[AI Chat]
            B --> D[Build search message]
            C --> E[Extract last message content]
            D --> F[Return think, content, files]
            E --> F

        :param chat: The current chat.
        :param messages: Assembled prompt messages.
        :param is_search: Whether this is a pure knowledge search request.
        :param ai: Configured AI instance.
        :param ai_headers: HTTP-style headers forwarded to the AI provider.
        :param chat_tools: Tool names available to the AI.
        :param response_message: The response message being assembled.
        :param task_item: The task item type of the current user message.
        :param callback: Streaming callback for partial content.
        :param send_message_event: Callable to emit partial response events.
        :return: Tuple of (think_content, main_content, extra_file_list).
        """
        think_content: Optional[str] = None
        main_content = ""
        extra_files: List[str] = []

        async def ai_chat(messages=None, prompt="", tags="", callback=None):
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
                tools=chat_tools
            )

        try:
            input_messages_count = len(messages)

            if is_search:
                self.event_manager.chat_event(
                    chat=chat,
                    message=f"Knowledge search for: {chat.name}"
                )
                send_message_event("* Searching...", False)
                combined_query = "\n".join([m.content for m in messages])
                ai_search_results = await KnowledgeAISearch(
                    settings=self.settings
                ).ai_search(user_query=combined_query)
                search_message = build_search_message(ai_search_results)
                message_parts = [search_message.content]
                extra_files = search_message.files or []
            else:
                response_messages = await ai_chat(messages=messages, callback=callback)
                new_message_count = len(response_messages) - input_messages_count

                if new_message_count > 1:
                    for reasoning_message in response_messages[input_messages_count + 1:-1]:
                        hidden_msg = self._new_chat_message(
                            role=reasoning_message.type,
                            content=reasoning_message.content
                        )
                        hidden_msg.hide = True
                        chat.messages.append(hidden_msg)

                message_parts = [response_messages[-1].content]

            is_thinking = len(message_parts) == 2
            think_content = message_parts[0] if is_thinking else None
            main_content = message_parts[-1]

        except (ValueError, RuntimeError, OSError) as ex:
            logger.exception(
                "Ops, sorry! Error chatting with project: %s %s", ex, chat.id
            )
            main_content = f"Ops, sorry! There was an error with latest request: {ex}"
            response_message.error = str(ex)

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
        chat_profile_names: List[str]
    ) -> None:
        """
        Stamp the response message with timing and model metadata.

        :param response_message: The message to annotate.
        :param user_message: The originating user message (provides base meta_data).
        :param timing_info: Dict containing 'start_time' and 'first_response'.
        :param ai_model: Name of the model that generated the response.
        :param chat_profile_names: Names of profiles active during this turn.
        """
        response_message.meta_data = user_message.meta_data or {}
        response_message.meta_data["time_taken"] = (
            time.time() - timing_info["start_time"]
        )
        response_message.meta_data["first_chunk_time_taken"] = timing_info["first_response"]
        response_message.meta_data["model"] = ai_model
        response_message.profiles = chat_profile_names

    # -------------------------------------------------------------------------
    # Helper: generate chat description
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

        :param chat: The chat to annotate with a description.
        :param messages: Message list used for the conversation.
        :param is_refine: Whether we are in task/refine mode (uses only last message).
        :param ai_chat_fn: Async callable matching the ai_chat signature.
        """
        try:
            desc_messages = messages.copy()
            if is_refine:
                desc_messages = [desc_messages[-1]]
            description_response = await ai_chat_fn(
                messages=desc_messages,
                prompt="Create a 5 lines summary of the conversation",
                tags="chat-summary"
            )
            chat.description = description_response[-1].content
        except (ValueError, RuntimeError) as ex:
            logger.exception(
                "Error generating chat description: %s %s", ex, chat.id
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

        flowchart TD
            A[Start] --> B{Project match?}
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
            L --> O[AI Chat]
            M --> O
            N --> O
            O --> P[Parse response]
            P --> Q{Agent done?}
            Q -->|No, iterations left| R[Recurse]
            Q -->|Yes| S[Return chat + docs]

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
            all_messages_content_code_block_file_paths = {
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
            # 6. Initialise response message
            # ------------------------------------------------------------------
            response_message = self._new_chat_message("assistant")
            response_message.meta_data = {"start_time": timing_info["start_time"]}

            # ------------------------------------------------------------------
            # 7. Resolve query mentions (profiles, files, projects)
            # ------------------------------------------------------------------
            query_mentions: QueryMentions = self.get_query_mentions(
                chat=chat, user_message=user_message
            )

            # ------------------------------------------------------------------
            # 8. Resolve chat files list
            # ------------------------------------------------------------------
            chat_files = list(
                set((chat.file_list or []) + (user_message.files or []))
            ) + query_mentions.files
            if parent_chat and parent_chat.file_list:
                chat_files = list(set(chat_files + parent_chat.file_list))

            # ------------------------------------------------------------------
            # 9. Resolve profiles, model, and tools
            # ------------------------------------------------------------------
            profile_result = self._resolve_profiles_and_model(
                chat=chat,
                query_mentions=query_mentions,
                chat_files=chat_files,
                is_refine=is_refine
            )
            chat_profiles_content: str = profile_result["chat_profiles_content"]
            chat_profile_names: List[str] = profile_result["chat_profile_names"]
            chat_model: Optional[str] = profile_result["chat_model"]
            chat_tools: List[str] = profile_result["chat_tools"]
            is_refine = profile_result["is_refine"]

            if chat_profile_names:
                self.event_manager.chat_event(
                    chat=chat,
                    message=f"Chat profiles: {chat_profile_names}"
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
            # 12. Build message history from prior turns
            # ------------------------------------------------------------------
            messages = self._build_message_history(chat=chat)

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
            # 14. Prepare AI instance
            # ------------------------------------------------------------------
            ai_settings = self.settings.get_llm_settings()
            logger.info("[chat_model] %s", chat_model)
            if chat_model:
                ai_settings.model = chat_model
            ai = self.get_ai(llm_model=ai_settings.model, system=system)

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
            def send_message_event(content: str, done: bool, documents = None) -> None:
                """
                Emit a message event with the current response state.

                Handles think/content separation for models that emit reasoning blocks.
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
                chat_profiles_content=chat_profiles_content,
                is_refine=is_refine,
                is_agent=is_agent,
                iterations_left=iterations_left
            )

            # ------------------------------------------------------------------
            # 21. Execute AI / search response
            # ------------------------------------------------------------------
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
                    send_message_event=send_message_event
                )
            )

            response_message.think = think_content
            response_message.content = main_content
            response_message.is_thinking = False
            if extra_files:
                response_message.files = list(
                    set(response_message.files + extra_files)
                )
            send_message_event(content=response_message.content, done=True)

            # ------------------------------------------------------------------
            # 22. Finalize response metadata
            # ------------------------------------------------------------------
            self._finalize_response_metadata(
                response_message=response_message,
                user_message=user_message,
                timing_info=timing_info,
                ai_model=ai_settings.model,
                chat_profile_names=chat_profile_names
            )

            chat.messages.append(response_message)
            logger.info("Chat done, adding message to chat. %s", chat.messages[-1])

            # ------------------------------------------------------------------
            # 23. Generate conversation summary (non-search modes)
            # ------------------------------------------------------------------
            if not is_search:
                await self._generate_chat_description(
                    chat=chat,
                    messages=messages,
                    is_refine=is_refine,
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
                return self.chat_with_project(
                    chat=chat,
                    disable_knowledge=disable_knowledge,
                    callback=callback,
                    append_references=append_references,
                    chat_mode=chat_mode,
                    iteration=iteration + 1
                )

            self.event_manager.chat_event(chat=chat, message="done")
            return chat, documents

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
            system=system
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
            "Query mentions extracted for '%s...': %s", query[0:10], query_mentions
        )
        return query_mentions

    def get_chat_analysis_parents(self, chat: Chat) -> str:
        """
        Traverse all parent chats and return concatenated non-hidden message content.

        :param chat: The child chat whose parents to traverse.
        :return: Concatenated content string from all ancestor chats.
        """
        parent_content: List[str] = []
        chat_manager = self.get_chat_manager(project_id=chat.owner_project_id)
        parent_chat = chat_manager.find_by_id(chat.parent_id)
        if chat.parent_id and not parent_chat:
            logger.error(
                "[parent_chat] parent_id: '%s' parent_project_id: '%s', Not found for chat: %s",
                chat.parent_id,
                chat.owner_project_id,
                chat.name
            )
        while parent_chat:
            messages = [
                message.content
                for message in parent_chat.messages
                if not message.hide
            ]
            if messages:
                parent_content.append("\n".join(messages))
            parent_chat = chat_manager.find_by_id(parent_chat.parent_id)
        return "\n".join(parent_content)

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

        Converts valid chat messages into a single Document with appropriate metadata.

        :param chat: The chat to index.
        """
        valid_messages = [
            message.content
            for message in chat.messages
            if not message.hide and not message.improvement
        ]

        page_content = "\n".join(valid_messages)
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