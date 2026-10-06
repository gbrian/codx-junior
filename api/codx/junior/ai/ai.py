import json
import logging
import hashlib
from typing import List, Optional, Union, Dict, Any, Callable

from langchain.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)

from engine.agent_runtime import AgentRunContext

from codx.junior.settings import CODXJuniorSettings
from codx.junior.ai.ai_logger import AILogger
from codx.junior.ai.cancellation import CancellationToken, CancelledError

from codx.junior.model.agent import AgentRunResult
from codx.junior.profiling.profiler import profile_function
from codx.junior.model.model import CodxUser

# Type hint for a chat message
Message = Union[AIMessage, HumanMessage, SystemMessage]

# Set up logging
logger = logging.getLogger(__name__)


class AI:
    """
    Main class for managing AI interactions.

    All chat requests are handled by :class:`SmolAgent` (async-native). The
    legacy ``OpenAI_AI`` provider has been removed.

    ``a_chat_run`` returns the typed :class:`AgentRunResult` (including the
    cost/usage breakdown) so callers can register the cost of a run on the
    persisted message. ``a_chat`` / ``chat`` keep the historical
    ``List[Message]`` contract by returning ``result.messages``.

    Supports forwarding a ``chat_id`` (for analytics traceability) and a shared
    :class:`AgentRunContext` (for real-time tool/lifecycle event listeners and
    unified cancellation) down to the provider.

    Mermaid Diagram:
    ```mermaid
    classDiagram
        AI --> SmolAgent : all chat requests
        AI --> AILogger : Logging operations
        AI --> CancellationToken : Cancellation handling
        AI --> AgentRunContext : Event fan-out / run sharing
        AI --> AgentRunResult : typed run result (cost/usage)
    ```
    """

    def __init__(
        self,
        settings: CODXJuniorSettings,
        llm_model: Optional[str] = None,
        user: Optional[CodxUser] = None,
        system: Optional[str] = None,
        session: Optional[Any] = None,
    ) -> None:
        """
        Initialize the AI class.

        :param settings: Configuration settings.
        :param llm_model: The specific model to be used.
        :param user: The user interacting with the AI.
        :param system: System level parameters.
        :param session: Optional session context for tools that need access to current chat state.
        """
        self.system: Optional[str] = system
        self.user: Optional[CodxUser] = user
        self.settings: CODXJuniorSettings = settings
        self.llm_model: Optional[str] = llm_model
        self.llm_settings: Any = settings.get_llm_settings(llm_model=llm_model)
        self.cache: Union[bool, Dict[str, str]] = False
        self.ai_logger: AILogger = AILogger(settings=settings)
        self.session: Optional[Any] = session

        # Initialize the chat model (SmolAgent, async-native)
        self.llm: Callable = self.create_chat_model(llm_model=llm_model)
        self.a_llm: Callable = self.create_a_chat_model(llm_model=llm_model)

        logger.info(
            "AI initialized with provider: SmolAgent (user=%s, model=%s, session=%s)",
            user.username if user else "NONE",
            llm_model,
            "present" if session else "absent",
        )

    def log(self, message: str, *args: Any) -> None:
        """
        Logs a message using the AI Logger if enabled.

        :param message: The message string.
        :param args: Optional arguments for lazy string formatting.
        """
        if self.settings.get_log_ai():
            self.ai_logger.info(message, *args)

    @staticmethod
    def _extract_message_content(message: Any) -> str:
        """
        Extract content string from a message object or dict.

        Handles:
        - LangChain message objects with .content attribute
        - Dict objects with 'content' key (from convert_message for images)
        - Fallback to string representation

        :param message: Message object or dict to extract content from.
        :return: String content, or empty string if no content found.
        """
        # Handle LangChain message objects
        if hasattr(message, 'content'):
            return str(message.content)
        
        # Handle dict objects (e.g. image messages from convert_message)
        if isinstance(message, dict):
            content = message.get('content', '')
            return str(content) if content else ''
        
        # Fallback
        return str(message)

    @profile_function
    def chat(
        self,
        messages: Optional[List[Message]] = None,
        prompt: Optional[str] = None,
        *,
        max_response_length: Optional[int] = None,
        callback: Optional[Callable] = None,
        tools: Optional[List[str]] = None,
        headers: Optional[Dict[str, Any]] = None,
        cancellation_token: Optional[CancellationToken] = None,
        chat_id: Optional[str] = None,
        run_context: Optional[AgentRunContext] = None,
        current_chat: Optional[Any] = None,
        vision_content: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Message]:
        """
        Synchronous wrapper around asynchronous chat functionality.

        Returns the historical ``List[Message]`` contract. Callers that need the
        typed run result (cost/usage breakdown) should use ``a_chat_run``.

        :param messages: History of messages.
        :param prompt: Prompt to append as a human message.
        :param max_response_length: The max tokens limit.
        :param callback: An optional callback function.
        :param tools: A list of tools for function calling.
        :param headers: Custom headers dict for the LLM request.
        :param cancellation_token: Optional token to cancel the ongoing completion.
        :param chat_id: Optional chat identifier for analytics traceability.
        :param run_context: Optional shared AgentRunContext carrying event
                            listeners (e.g. ChatEventBridge) and cancellation.
        :param current_chat: Optional current chat object for tool context.
        :param vision_content: Optional list of vision content blocks (images, PDFs)
                               to pass to vision-capable models.
        :return: A list of processed messages including the AI reply.
        :raises CancelledError: If the request is cancelled.
        :raises RuntimeError: If AI processing fails.
        """
        import asyncio

        # Get or create the event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.a_chat(
                        messages=messages,
                        prompt=prompt,
                        max_response_length=max_response_length,
                        callback=callback,
                        tools=tools,
                        headers=headers,
                        cancellation_token=cancellation_token,
                        chat_id=chat_id,
                        run_context=run_context,
                        current_chat=current_chat,
                        vision_content=vision_content,
                    )
                )
            finally:
                loop.close()
        else:
            # We're already in an async context, create a task
            return loop.run_until_complete(
                self.a_chat(
                    messages=messages,
                    prompt=prompt,
                    max_response_length=max_response_length,
                    callback=callback,
                    tools=tools,
                    headers=headers,
                    cancellation_token=cancellation_token,
                    chat_id=chat_id,
                    run_context=run_context,
                    current_chat=current_chat,
                    vision_content=vision_content,
                )
            )

    @profile_function
    async def a_chat(
        self,
        messages: Optional[List[Message]] = None,
        prompt: Optional[str] = None,
        *,
        max_response_length: Optional[int] = None,
        callback: Optional[Callable] = None,
        tools: Optional[List[str]] = None,
        headers: Optional[Dict[str, Any]] = None,
        cancellation_token: Optional[CancellationToken] = None,
        chat_id: Optional[str] = None,
        run_context: Optional[AgentRunContext] = None,
        current_chat: Optional[Any] = None,
        vision_content: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Message]:
        """
        Asynchronous chat functionality that returns the conversation messages.

        Delegates to :meth:`a_chat_run` and returns ``result.messages`` so the
        historical ``List[Message]`` contract is preserved. Callers that need the
        typed run result (cost/usage breakdown) should call ``a_chat_run``
        directly.

        :return: A list of processed messages including the AI reply.
        :raises CancelledError: If the request is cancelled.
        :raises RuntimeError: If AI processing fails.
        """
        run_result = await self.a_chat_run(
            messages=messages,
            prompt=prompt,
            max_response_length=max_response_length,
            callback=callback,
            tools=tools,
            headers=headers,
            cancellation_token=cancellation_token,
            chat_id=chat_id,
            run_context=run_context,
            current_chat=current_chat,
            vision_content=vision_content,
        )
        return run_result.messages

    @profile_function
    async def a_chat_run(
        self,
        messages: Optional[List[Message]] = None,
        prompt: Optional[str] = None,
        *,
        max_response_length: Optional[int] = None,
        callback: Optional[Callable] = None,
        tools: Optional[List[str]] = None,
        headers: Optional[Dict[str, Any]] = None,
        cancellation_token: Optional[CancellationToken] = None,
        chat_id: Optional[str] = None,
        run_context: Optional[AgentRunContext] = None,
        current_chat: Optional[Any] = None,
        vision_content: Optional[List[Dict[str, Any]]] = None,
    ) -> AgentRunResult:
        """
        Asynchronous chat functionality returning the typed run result.

        Delegates to :class:`SmolAgent`, which returns an
        :class:`AgentRunResult` carrying the conversation messages, the per-run
        cost/usage breakdown and the tool/cache summaries. The ``chat_id`` and
        ``run_context`` are forwarded so tool and lifecycle events can be traced
        back to the chat and surfaced to registered listeners in real time.

        :return: The typed :class:`AgentRunResult` for this run.
        :raises CancelledError: If the request is cancelled.
        :raises RuntimeError: If AI processing fails.
        """
        if messages is None:
            messages = []
        if tools is None:
            tools = []
        if headers is None:
            headers = {}

        if prompt:
            messages.append(HumanMessage(content=prompt))

        # Safely extract content from messages that may be LangChain objects or dicts
        total_words = len("".join([self._extract_message_content(m) for m in messages]))

        self.log(
            "Creating a new a_chat_run completion. Messages: %d, words: %d, provider: SmolAgent",
            len(messages),
            total_words,
        )

        response = await self.a_llm(
            messages=messages,
            config={
                "callbacks": [callback] if callback else [],
                "headers": headers,
                "tools": tools,
                "cancellation_token": cancellation_token,
                "chat_id": chat_id,
                "run_context": run_context,
                "current_chat": current_chat,
                "vision_content": vision_content,
            },
        )

        # SmolAgent returns AgentRunResult. Any provider returning a plain
        # message list is wrapped into a typed result with zero-cost metadata so
        # callers always receive an AgentRunResult.
        if isinstance(response, AgentRunResult):
            return response

        response_messages: List[Message] = response or []
        return AgentRunResult(
            content=(
                self._extract_message_content(response_messages[-1])
                if response_messages else ""
            ),
            messages=response_messages,
        )

    def create_chat_model(self, llm_model: Optional[str]) -> Callable:
        """
        Create the synchronous chat callable.

        Bridges the async ``a_chat`` (which returns ``List[Message]``) to the
        legacy sync interface used by older callers.

        :param llm_model: Optional model override.
        :return: A sync callable returning ``List[Message]``.
        """
        logger.debug("SmolAgent sync chat model initialized")
        return self._make_sync_wrapper(self.a_chat)

    def create_a_chat_model(self, llm_model: Optional[str]) -> Callable:
        """
        Create the asynchronous chat callable.

        Returns :class:`SmolAgent.chat`, which yields an
        :class:`AgentRunResult`.

        :param llm_model: Optional model override.
        :return: An async callable returning :class:`AgentRunResult`.
        """
        from codx.junior.ai.smol.smol_agent import SmolAgent

        agent = SmolAgent(
            settings=self.settings,
            llm_model=llm_model,
            user=self.user,
            system=self.system,
            session=self.session,
        )
        logger.debug("SmolAgent a_chat model initialized")
        return agent.chat

    @staticmethod
    def _make_sync_wrapper(async_func: Callable) -> Callable:
        """
        Create a synchronous wrapper around an async function.

        Used to bridge SmolAgent's async-only interface to legacy sync callers.

        :param async_func: The async function to wrap.
        :return: A sync callable that internally handles asyncio.
        """
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            import asyncio

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(async_func(*args, **kwargs))
                finally:
                    loop.close()
            else:
                # Already in async context, this shouldn't happen for sync callers
                logger.warning(
                    "sync_wrapper called from within async context. "
                    "Consider using a_chat directly."
                )
                raise RuntimeError(
                    "Cannot use sync chat wrapper from within async context. "
                    "Use a_chat() instead."
                )

        return sync_wrapper

    def get_openai_chat_client(self, llm_model: Optional[str] = None) -> Any:
        """
        Get the underlying OpenAI-compatible client used by SmolAgent.

        :param llm_model: Optional model override.
        :return: The OpenAI client instance used by SmolAgent.
        """
        from codx.junior.ai.smol.smol_agent import SmolAgent

        agent = SmolAgent(
            settings=self.settings,
            llm_model=llm_model,
            user=self.user,
            system=self.system,
            session=self.session,
        )
        return agent.client


def messages_md5(messages: List[Message]) -> str:
    """
    Creates an MD5 hash representing the conversation string array.

    :param messages: List of message objects.
    :return: Hexadecimal MD5 digest of the concatenated message contents.
    """
    messages_str = "".join([str(msg.content) for msg in messages])
    return str(hashlib.md5(messages_str.encode("utf-8")).hexdigest())


def serialize_messages(messages: List[Message]) -> List[Dict[str, str]]:
    """
    Serialize messages to a JSON-compatible format.

    :param messages: List of message objects.
    :return: List of serialized message dicts with type and content.
    """
    return [
        {
            "type": type(msg).__name__,
            "content": str(msg.content),
        }
        for msg in messages
    ]

# Made with ❤️ by codx-junior