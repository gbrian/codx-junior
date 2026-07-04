## DEPRECATED: Using vllm docker openai compatible

import os
import re
import logging
from typing import Union, Dict, List, Any, Optional
from urllib.parse import urlparse

from vllm import LLM, SamplingParams
from langchain.messages import AIMessage, HumanMessage

from codx.junior.ai.ai_logger import AILogger
from codx.junior.settings import CODXJuniorSettings
from codx.junior.model.model import CodxUser

# Module logger
logger = logging.getLogger(__name__)

# Constants to replace hardcoded values
DEFAULT_LLM_MODEL: str = "Qwen/Qwen3-8B"
DEFAULT_TEMPERATURE: float = 0.8
DEFAULT_TOP_P: float = 0.95

class VllmCPUAI:
    """
    Class to execute vllm models using CPU.

    This class provides methods similar to OpenAI_AI but targets vllm model execution
    constrained to CPU usage using vllm's offline batched inference API.
    """

    def __init__(
        self, 
        settings: CODXJuniorSettings, 
        llm_model: Optional[str] = None, 
        user: Optional[CodxUser] = None, 
        system: Optional[str] = None
    ):
        """
        Initialize VllmCPUAI with specific settings for CPU model execution.
        """
        self.tools: List[Any] = []
        self.settings: CODXJuniorSettings = settings
        self.model: str = llm_model or DEFAULT_LLM_MODEL
        self.user: Optional[CodxUser] = user
        self.system: Optional[str] = system
        self.ai_logger: AILogger = AILogger(settings=settings)

        try:
            self.llm: LLM = self.setup_vllm_client()
            username: str = self.user.username if self.user else "NONE"
            logger.info(
                "Vllm client initialized successfully for USER: %s with model: %s", 
                username,
                self.model
            )
        except (RuntimeError, ValueError) as ex:
            logger.error("Error initializing Vllm client: %s", ex)
            raise

    def _parse_hf_gguf_url(self, url: str) -> Optional[Dict[str, str]]:
        """
        Parses a Hugging Face blob URL to extract repo_id and filename.
        Returns a dict with 'repo_id' and 'filename' if matches, else None.
        """
        if not (url.startswith("http://") or url.startswith("https://")):
            return None
            
        parsed_url = urlparse(url)
        if "huggingface.co" not in parsed_url.netloc:
            return None

        # Regex to capture: /owner/repo/blob/branch/filename.gguf
        pattern = r"^/([^/]+/[^/]+)/blob/[^/]+/(.+\.gguf)$"
        match = re.match(pattern, parsed_url.path)
        
        if match:
            return {
                "repo_id": match.group(1),
                "filename": match.group(2)
            }
        return None

    def setup_vllm_client(self) -> LLM:
        """
        Setup and return the vllm LLM configured for the specified model on CPU.
        """
        logger.info("Initializing vllm LLM with model %s on device: %s", self.model, os.environ.get("VLLM_TARGET_DEVICE", "VLLM_TARGET_DEVICE NOT DEFINED"))
        
        # 1. Detect if the string is a Hugging Face GGUF URL
        url_info = self._parse_hf_gguf_url(self.model)
        
        if url_info:
            logger.info(
                "Detected HF GGUF URL. Extracting Repo: %s, File: %s", 
                url_info["repo_id"], 
                url_info["filename"]
            )
            
            # Setup specific rules for the massive 1M context Qwythos model to avoid CPU RAM failure
            max_len = 8192 if "Qwythos" in url_info["repo_id"] else 4096
            
            return LLM(
                model=url_info["repo_id"],
                quantization="gguf",
                gguf_file=url_info["filename"],
                max_model_len=max_len
            )
            
        # 2. Regular execution path if it's not a URL
        return LLM(model=self.model) 

    def log(self, msg: str) -> None:
        """
        Log messages if AI logging is enabled.
        """
        if self.settings.get_log_ai():
            self.ai_logger.info(msg)

    def convert_messages_to_prompt(self, messages: List[Union[AIMessage, HumanMessage]]) -> str:
        """
        Convert a list of LangChain messages to a single string prompt for vllm.
        """
        prompt_lines: List[str] = []
        for msg in messages:
            if msg.type == "ai":
                prompt_lines.append("Assistant: " + str(msg.content))
            else:
                prompt_lines.append("User: " + str(msg.content))
        prompt_lines.append("Assistant:")
        return "\n".join(prompt_lines)

    async def a_chat_completions(self, **kwargs) -> List[Union[AIMessage, HumanMessage]]:
        """
        Asynchronous wrapper for chat_completions.
        """
        return self.chat_completions(**kwargs)
        
    def chat_completions(
        self, 
        messages: List[Union[AIMessage, HumanMessage]], 
        config: Optional[Dict[str, Any]] = None
    ) -> List[Union[AIMessage, HumanMessage]]:
        """
        Handle synchronous chat completions for vllm models constrained to CPU.
        """
        if config is None:
            config = {}
        logger.info("Starting chat completion with vllm on CPU.")
        prompt: str = self.convert_messages_to_prompt(messages)
        
        temperature: float = config.get("temperature", DEFAULT_TEMPERATURE)
        top_p: float = config.get("top_p", DEFAULT_TOP_P)
        sampling_params = SamplingParams(temperature=temperature, top_p=top_p)

        try:
            outputs = self.llm.generate([prompt], sampling_params)
            collected_texts: List[str] = []
            for output in outputs:
                generated_text: str = output.outputs[0].text
                logger.info("Prompt: %r, Generated text: %r", output.prompt, generated_text)
                self.log("Generated text: %s" % generated_text)
                collected_texts.append(generated_text)

            full_response: str = "".join(collected_texts)
            messages.append(AIMessage(content=full_response))
            return messages
            
        except (RuntimeError, ValueError) as ex:
            logger.error("Error during vllm chat completions: %s", ex)
            raise

# Made with ❤️ by codx-junior