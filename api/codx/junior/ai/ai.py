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
from codx.junior.ai.openai_ai import OpenAI_AI
from codx.junior.ai.ai_logger import AILogger
from codx.junior.ai.cancellation import CancellationToken, CancelledError

from codx.junior.profiling.profiler import profile_function
from codx.junior.model.model import CodxUser

# Type hint for a chat message
Message = Union[AIMessage, HumanMessage, SystemMessage]

# Set up logging
logger = logging.getLogger(__name__)


class AI:
    """
    Main class for managing AI interactions with provider routing.

    Routes chat requests to either SmolAgent (async-native) or OpenAI_AI (legacy)
    based on global settings flag ``use_smol_agent``.

    Supports forwarding a ``chat_id`` (for analytics traceability) and a shared
    :class:`AgentRunContext` (for real-time tool/lifecycle event listeners and
    unified cancellation) down to the provider.

    Mermaid Diagram:
    ```mermaid
    classDiagram
        AI --> OpenAI_AI : use_smol_agent == False
        AI --> SmolAgent : use_smol_agent == True
        AI --> AILogger : Logging operations
        AI --> CancellationToken : Cancellation handling
        AI --> AgentRunContext : Event fan-out / run sharing
    ```
    """

    def __init__(
        self,
        settings: CODXJuniorSettings,
        llm_model: Optional[str] = None,
        user: Optional[CodxUser] = None,
        system: Optional[str] = None,
    ) -> None:
        """
        Initialize the AI class with provider routing.

        :param settings: Configuration settings (includes use_smol_agent flag).
        :param llm_model: The specific model to be used.
        :param user: The user interacting with the AI.
        :param system: System level parameters.
        """
        self.system: Optional[str] = system
        self.user: Optional[CodxUser] = user
        self.settings: CODXJuniorSettings = settings
        self.llm_model: Optional[str] = llm_model
        self.llm_settings: Any = settings.get_llm_settings(llm_model=llm_model)
        self.cache: Union[bool, Dict[str, str]] = False
        self.ai_logger: AILogger = AILogger(settings=settings)

        # Determine which provider to use
        self._use_smol_agent: bool = True

        # Initialize the appropriate chat model
        self.llm: Callable = self.create_chat_model(llm_model=llm_model)
        self.a_llm: Callable = self.create_a_chat_model(llm_model=llm_model)

        logger.info(
            "AI initialized with provider: %s (user=%s, model=%s)",
            "SmolAgent" if self._use_smol_agent else "OpenAI_AI",
            user.username if user else "NONE",
            llm_model,
        )

    def log(self, message: str, *args: Any) -> None:
        """
        Logs a message using the AI Logger if enabled.

        :param message: The message string.
        :param args: Optional arguments for lazy string formatting.
        """
        if self.settings.get_log_ai():
            self.ai_logger.info(message, *args)

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
    ) -> List[Message]:
        """
        Synchronous wrapper around asynchronous chat functionality.

        Processes user inputs and returns AI responses using the configured
        provider (SmolAgent or OpenAI_AI). The sync wrapper delegates to
        ``a_chat()`` to ensure consistent behavior across providers.

        Note: This method internally uses asyncio to bridge async code.
        For high-concurrency scenarios, prefer ``a_chat()`` directly.

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
    ) -> List[Message]:
        """
        Asynchronous chat functionality that processes user inputs and returns AI responses.

        Delegates to the configured provider (SmolAgent or OpenAI_AI) based on
        the ``use_smol_agent`` settings flag. The ``chat_id`` and
        ``run_context`` are forwarded in the provider config so tool and
        lifecycle events can be traced back to the chat and surfaced to any
        registered listeners in real time.

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
        :return: A list of processed messages including the AI reply.
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

        self.log(
            "Creating a new a_chat completion. Messages: %d, words: %d, provider: %s",
            len(messages),
            len("".join([str(m.content) for m in messages])),
            "SmolAgent" if self._use_smol_agent else "OpenAI_AI",
        )

        # Delegate to the appropriate provider's async method
        response_messages: List[Message] = await self.a_llm(
            messages=messages,
            config={
                "callbacks": [callback] if callback else [],
                "headers": headers,
                "tools": tools,
                "cancellation_token": cancellation_token,
                "chat_id": chat_id,
                "run_context": run_context,
            },
        )

        return response_messages

    def create_chat_model(self, llm_model: Optional[str]) -> Callable:
        """
        Initialize the correct chat completions target based on settings.

        Routes to SmolAgent or OpenAI_AI based on ``use_smol_agent`` flag.

        :param llm_model: Optional model override.
        :return: A callable chat model function (may be sync or async).
        """
        if self._use_smol_agent:
            from codx.junior.ai.smol.smol_agent import SmolAgent

            agent = SmolAgent(
                settings=self.settings,
                llm_model=llm_model,
                user=self.user,
                system=self.system,
            )
            logger.debug("SmolAgent chat model initialized")
            # Return a wrapper that bridges SmolAgent.chat (async) to sync interface
            return self._make_sync_wrapper(agent.chat)
        else:
            return OpenAI_AI(
                settings=self.settings,
                llm_model=llm_model,
                user=self.user,
                system=self.system,
            ).chat_completions

    def create_a_chat_model(self, llm_model: Optional[str]) -> Callable:
        """
        Initialize the correct asynchronous chat completions target based on settings.

        Routes to SmolAgent or OpenAI_AI based on ``use_smol_agent`` flag.

        :param llm_model: Optional model override.
        :return: An async callable chat model function.
        """
        if self._use_smol_agent:
            from codx.junior.ai.smol.smol_agent import SmolAgent

            agent = SmolAgent(
                settings=self.settings,
                llm_model=llm_model,
                user=self.user,
                system=self.system,
            )
            logger.debug("SmolAgent a_chat model initialized")
            return agent.chat
        else:
            return OpenAI_AI(
                settings=self.settings,
                llm_model=llm_model,
                user=self.user,
                system=self.system,
            ).a_chat_completions

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
        Get the underlying OpenAI client (only available with OpenAI_AI provider).

        :param llm_model: Optional model override.
        :return: The OpenAI client instance.
        :raises RuntimeError: If using SmolAgent provider (which uses generic client).
        """
        if self._use_smol_agent:
            logger.warning(
                "get_openai_chat_client called with SmolAgent provider. "
                "Returning generic OpenAI client from SmolAgent."
            )
            from codx.junior.ai.smol.smol_agent import SmolAgent

            agent = SmolAgent(
                settings=self.settings,
                llm_model=llm_model,
                user=self.user,
                system=self.system,
            )
            return agent.client
        else:
            return OpenAI_AI(
                settings=self.settings,
                llm_model=llm_model,
                user=self.user,
                system=self.system,
            ).client


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