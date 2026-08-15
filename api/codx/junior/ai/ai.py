import json
import logging
import hashlib
import requests
from urllib.parse import urlparse
from typing import List, Optional, Union, Dict, Any, Callable

from langchain.chat_models.base import BaseChatModel
from langchain.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)

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
    Main class for managing AI interactions and routing.
    
    Mermaid Diagram:
    classDiagram
        AI --> OpenAI_AI : provider == "openai"
        AI --> AILogger : Logging operations
    """
    def __init__(
        self, 
        settings: CODXJuniorSettings,
        llm_model: Optional[str] = None,
        user: Optional[CodxUser] = None,
        system: Optional[str] = None,
    ):
        """
        Initialize the AI class.

        :param settings: Configuration settings.
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

        self.llm: Callable = self.create_chat_model(llm_model=llm_model)
        self.a_llm: Callable = self.create_a_chat_model(llm_model=llm_model)
        # Underlying embeddings client/model (created lazily-safe in constructor)
        self.embeddings_model: Any = None

    @profile_function
    def image(self, prompt: str) -> str:
        """
        Generate an image based on the provided prompt.

        :param prompt: The description of the image.
        :return: Generated image URL or data.
        """
        return self.llm.generate_image(prompt)

    def log(self, message: str, *args: Any) -> None:
        """
        Logs a message using the AI Logger if enabled.

        :param message: The message string.
        :param args: Optional arguments for lazy string formatting.
        """
        if self.settings.get_log_ai():
            self.ai_logger.info(message, *args)

    def _is_model_not_found_error(self, exc: Exception) -> bool:
        """
        Checks whether the exception indicates a model_not_found error.

        Handles multiple error formats including:
          - "model_not_found"
          - "model not found"
          - "model 'ollama/xxx' not found"
          - API error type: 'not_found_error' with a model-related message

        :param exc: The exception to inspect.
        :return: True if the error is a model_not_found error, False otherwise.
        """
        error_str = str(exc).lower()

        patterns = [
            "model_not_found",
            "model not found",
            "not found_error",
            "not_found_error",
        ]
        if any(p in error_str for p in patterns):
            return True

        # Handle the pattern: "model 'xxx' not found"
        if "not found" in error_str and "model" in error_str:
            return True

        return False

    def _pull_ollama_model(self) -> None:
        """
        Pulls the missing model from the Ollama API using the configured api_url.
        Streams the response and logs progress.

        The api_url may contain a path component (e.g. "http://localhost:11434/v1").
        We strip any path so that we always POST to <scheme>://<host>:<port>/api/pull.
        """
        model_name = self.llm_model or getattr(self.llm_settings, "model", None)
        api_url = getattr(self.llm_settings, "api_url", None)

        if not api_url or not model_name:
            logger.error(
                "Cannot pull Ollama model: missing api_url (%s) or model_name (%s)",
                api_url,
                model_name,
            )
            return

        # Strip the "ollama/" prefix if present, as Ollama API expects just the model name
        ollama_model_name = model_name.removeprefix("ollama/")

        # Strip any path from api_url (e.g. remove "/v1") so we build the correct
        # Ollama endpoint: <scheme>://<host>:<port>/api/pull
        parsed = urlparse(api_url)
        ollama_base_url = f"{parsed.scheme}://{parsed.netloc}"
        pull_url = f"{ollama_base_url}/api/pull"

        logger.info("Pulling Ollama model '%s' from %s", ollama_model_name, pull_url)

        try:
            with requests.post(
                pull_url,
                json={"name": ollama_model_name, "stream": True},
                stream=True,
                timeout=600,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            status = data.get("status", "")
                            logger.info("Ollama pull [%s]: %s", ollama_model_name, status)
                        except json.JSONDecodeError:
                            logger.debug("Ollama pull raw line: %s", line)
            logger.info("Successfully pulled Ollama model '%s'", ollama_model_name)
        except Exception as pull_exc:
            logger.exception(
                "Failed to pull Ollama model '%s' from %s: %s",
                ollama_model_name,
                pull_url,
                pull_exc,
            )
            raise RuntimeError(
                f"Failed to pull Ollama model '{ollama_model_name}': {pull_exc}"
            ) from pull_exc

    def _get_provider_type(self):
        return getattr(self.llm_settings, "provider_type", None)
    def _handle_model_not_found(self, exc: Exception) -> None:
        """
        Handles a model_not_found error. If the provider is Ollama, attempts to pull the model.

        :param exc: The original exception.
        :raises RuntimeError: If the provider is not Ollama or if the pull fails.
        """
        provider_type = self._get_provider_type()
        try:
            logger.warning(
                "Model not found for Ollama provider. Attempting to pull model '%s'.",
                self.llm_model,
            )
            self._pull_ollama_model()
        except Exception as ex:
            raise RuntimeError(
                f"Pull model failed: {ex}"
            ) from exc

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
    ) -> List[Message]:
        """
        Synchronous chat functionality that processes user inputs and returns AI responses.

        :param messages: History of messages.
        :param prompt: Prompt to append as a human message.
        :param max_response_length: The max tokens limit.
        :param callback: An optional callback function.
        :param tools: A list of tools for function calling.
        :param headers: Custom headers dict for the LLM request.
        :param cancellation_token: Optional token to cancel the ongoing completion.
        :return: A list of processed messages including the AI reply.
        """
        if messages is None:
            messages = []
        if tools is None:
            tools = []
        if headers is None:
            headers = {}

        if prompt:
            messages.append(HumanMessage(content=prompt))

        response_messages: List[Message] = []
        md5_key = messages_md5(messages) if self.cache else None
        
        if self.cache and isinstance(self.cache, dict) and md5_key in self.cache:
            cache_data = json.loads(self.cache[md5_key])
            response_messages.append(
                AIMessage(content=cache_data["content"])
            )
            if self.settings.get_log_ai():
                self.ai_logger.debug("Response from cache: %s %s", messages, cache_data["content"])

        else:
            callbacks = []
            if callback:
                callbacks.append(callback)
            
            try:
                self.log(
                    "Creating a new chat completion. Messages: %d words: %d",
                    len(messages), 
                    len("".join([str(m.content) for m in messages]))
                )
                
                response_messages = self.llm(
                    messages=messages, 
                    config={
                        "callbacks": callbacks,
                        "headers": headers,
                        "tools": tools,
                        "cancellation_token": cancellation_token,
                    }
                )
            except CancelledError:
                logger.info("chat: request was cancelled via CancellationToken")
                raise
            except Exception as exc:
                if self._is_model_not_found_error(exc):
                    logger.warning(
                        "model_not_found error detected for model '%s'. Attempting recovery.",
                        self.llm_model,
                    )
                    self._handle_model_not_found(exc)
                    # Retry after pulling the model
                    try:
                        response_messages = self.llm(
                            messages=messages,
                            config={
                                "callbacks": callbacks,
                                "headers": headers,
                                "tools": tools,
                                "cancellation_token": cancellation_token,
                            }
                        )
                    except CancelledError:
                        logger.info("chat (retry): request was cancelled via CancellationToken")
                        raise
                    except Exception as retry_exc:
                        logger.exception(
                            "Failed after pulling model. Non-retryable error: %s %s",
                            retry_exc,
                            self.llm_model,
                        )
                        raise RuntimeError(
                            f"Failed to process AI request after model pull. {retry_exc}"
                        ) from retry_exc
                else:
                    logger.exception(
                        "Failed to process AI. Non-retryable error processing AI request: %s %s",
                        exc,
                        self.llm_model,
                    )
                    raise RuntimeError(f"Failed to process AI request after retries. {exc}") from exc

            if self.cache and isinstance(self.cache, dict):
                self.cache[md5_key] = json.dumps(
                    {
                        "messages": serialize_messages(messages),
                        "content": response_messages[-1].content,
                    }
                )
      
        return response_messages

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
    ) -> List[Message]:
        """
        Asynchronous chat functionality that processes user inputs and returns AI responses.

        :param messages: History of messages.
        :param prompt: Prompt to append as a human message.
        :param max_response_length: The max tokens limit.
        :param callback: An optional callback function.
        :param tools: A list of tools for function calling.
        :param headers: Custom headers dict for the LLM request.
        :param cancellation_token: Optional token to cancel the ongoing completion.
        :return: A list of processed messages including the AI reply.
        """
        if messages is None:
            messages = []
        if tools is None:
            tools = []
        if headers is None:
            headers = {}

        if prompt:
            messages.append(HumanMessage(content=prompt))

        response_messages: List[Message] = []
        md5_key = messages_md5(messages) if self.cache else None
        
        if self.cache and isinstance(self.cache, dict) and md5_key in self.cache:
            cache_data = json.loads(self.cache[md5_key])
            response_messages.append(
                AIMessage(content=cache_data["content"])
            )
            if self.settings.get_log_ai():
                self.ai_logger.debug("Response from cache: %s %s", messages, cache_data["content"])

        else:
            callbacks = []
            if callback:
                callbacks.append(callback)
            
            try:
                self.log(
                    "Creating a new a_chat completion. Messages: %d words: %d",
                    len(messages), 
                    len("".join([str(m.content) for m in messages]))
                )
                
                response_messages = await self.a_llm(
                    messages=messages, 
                    config={
                        "callbacks": callbacks,
                        "headers": headers,
                        "tools": tools,
                        "cancellation_token": cancellation_token,
                    }
                )
            except CancelledError:
                logger.info("a_chat: request was cancelled via CancellationToken")
                raise
            except Exception as exc:
                if self._is_model_not_found_error(exc):
                    logger.warning(
                        "model_not_found error detected for model '%s'. Attempting recovery.",
                        self.llm_model,
                    )
                    self._handle_model_not_found(exc)
                    # Retry after pulling the model
                    try:
                        response_messages = await self.a_llm(
                            messages=messages,
                            config={
                                "callbacks": callbacks,
                                "headers": headers,
                                "tools": tools,
                                "cancellation_token": cancellation_token,
                            }
                        )
                    except CancelledError:
                        logger.info("a_chat (retry): request was cancelled via CancellationToken")
                        raise
                    except Exception as retry_exc:
                        logger.exception(
                            "Failed after pulling model. Non-retryable error: %s %s",
                            retry_exc,
                            self.llm_model,
                        )
                        raise RuntimeError(
                            f"Failed to process AI request after model pull. {retry_exc}"
                        ) from retry_exc
                else:
                    logger.exception(
                        "Failed to process AI. Non-retryable error processing AI request: %s %s",
                        exc,
                        self.llm_model,
                    )
                    raise RuntimeError(f"Failed to process AI request after retries. {exc}") from exc

            if self.cache and isinstance(self.cache, dict):
                self.cache[md5_key] = json.dumps(
                    {
                        "messages": serialize_messages(messages),
                        "content": response_messages[-1].content,
                    }
                )
      
        return response_messages

    @profile_function
    def embeddings(self, content: Union[str, List[str]]) -> Any:
        """
        Generate dense embedding vectors for the given content.

        Accepts either a single string or a list of strings and returns the
        embedding(s) produced by the configured embeddings model
        (resolved via ``settings.get_embeddings_settings``).

        Behaviour:
          - When ``content`` is a ``str``  → returns a single embedding vector
            (``List[float]``).
          - When ``content`` is a ``list`` → returns a list of embedding
            vectors (``List[List[float]]``), one per input string.

        This delegates to the underlying LangChain-style embeddings model
        created by ``create_embeddings_model`` (which exposes
        ``embed_query`` / ``embed_documents``).

        :param content: A single string or list of strings to embed.
        :return: A single vector, or a list of vectors, depending on input.
        """
        if self.embeddings_model is None:
            self.embeddings_model: Any = self.create_embeddings_model()

        # Batch input → embed_documents
        if isinstance(content, list):
            if hasattr(self.embeddings_model, "embed_documents"):
                return self.embeddings_model.embed_documents(content)
            # Fallback: embed one by one using embed_query
            return [self.embeddings_model.embed_query(text) for text in content]

        # Single string input → embed_query
        if hasattr(self.embeddings_model, "embed_query"):
            return self.embeddings_model.embed_query(content)

        # Fallback for clients exposing only embed_documents
        return self.embeddings_model.embed_documents([content])[0]

    def _get_provider(self) -> str:
        """
        Helper method to retrieve the LLM provider safely.

        :return: The string representing the designated AI provider.
        """
        if hasattr(self.llm_settings, "provider"):
            return getattr(self.llm_settings, "provider", "")
        if isinstance(self.llm_settings, dict):
            return self.llm_settings.get("provider", "")
        return ""

    def create_chat_model(self, llm_model: Optional[str]) -> Callable:
        """
        Initialize the correct synchronous chat completions target based on configuration.
        Routes to the appropriate provider implementation.
        """
        
        # Default to OpenAI_AI for "openai" or any other provider
        return OpenAI_AI(
            settings=self.settings, 
            llm_model=llm_model, 
            user=self.user, 
            system=self.system
        ).chat_completions

    def create_a_chat_model(self, llm_model: Optional[str]) -> Callable:
        """
        Initialize the correct asynchronous chat completions target based on configuration.
        Routes to the appropriate provider implementation.
        """
        # Default to OpenAI_AI for "openai" or any other provider
        return OpenAI_AI(
            settings=self.settings, 
            llm_model=llm_model, 
            user=self.user, 
            system=self.system
        ).a_chat_completions

    def get_openai_chat_client(self, llm_model: Optional[str] = None) -> Any:
        return OpenAI_AI(
            settings=self.settings, 
            llm_model=llm_model, 
            user=self.user, 
            system=self.system
        ).client

    def create_embeddings_model(self) -> Any:
        return OpenAI_AI(
            settings=self.settings, 
            user=self.user, 
            system=self.system
        ).embeddings()

def messages_md5(messages: List[Message]) -> str:
    """
    Creates an MD5 hash representing the conversation string array.
    """
    messages_str = "".join([str(msg.content) for msg in messages])
    return str(hashlib.md5(messages_str.encode("utf-8")).hexdigest())

def serialize_messages(messages: List[Message]) -> List[Dict[str, str]]:
    """
    Serialize messages to a JSON-compatible format.
    
    :param messages: List of message objects.
    :return: List of serialized message dicts.
    """
    return [
        {
            "type": type(msg).__name__,
            "content": str(msg.content),
        }
        for msg in messages
    ]

# Made with ❤️ by codx-junior