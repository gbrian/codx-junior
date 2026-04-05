import os
import logging
from typing import Union, Dict, List, Any, Optional

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
DEVICE_CPU: str = "cpu"


class VllmCPUAI:
    """
    Class to execute vllm models using CPU.

    This class provides methods similar to OpenAI_AI but targets vllm model execution
    constrained to CPU usage using vllm's offline batched inference API.

    Mermaid diagram of the generation flow:
    sequenceDiagram
        participant User
        participant VllmCPUAI
        participant vllm_LLM
        User->>VllmCPUAI: chat_completions(messages, config)
        VllmCPUAI->>VllmCPUAI: convert_messages_to_prompt()
        VllmCPUAI->>vllm_LLM: generate([prompt], SamplingParams)
        vllm_LLM-->>VllmCPUAI: outputs
        VllmCPUAI->>VllmCPUAI: collect all output texts
        VllmCPUAI->>VllmCPUAI: append single AIMessage(full_response)
        VllmCPUAI-->>User: updated messages list
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

        :param settings: Configuration settings.
        :param llm_model: The specific model to be used. Falls back to DEFAULT_LLM_MODEL if not provided.
        :param user: The user info.
        :param system: System level parameters.
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
            # Using lazy string formatting for logging
            logger.info(
                "Vllm client initialized successfully for USER: %s with model: %s", 
                username,
                self.model
            )
        except (RuntimeError, ValueError) as ex:
            logger.error("Error initializing Vllm client: %s", ex)
            raise

    def log(self, msg: str) -> None:
        """
        Log messages if AI logging is enabled.
        
        :param msg: Message to be logged.
        """
        if self.settings.get_log_ai():
            self.ai_logger.info(msg)

    def setup_vllm_client(self) -> LLM:
        """
        Setup and return the vllm LLM configured for the specified model on CPU.
        The first run will take about 3-5 mins (10 MB/s) to download models.

        :return: Initialized vllm LLM object.
        """
        logger.info("Initializing vllm LLM with model %s on device: %s", self.model, DEVICE_CPU)
        # Explicitly defining device="cpu" avoids torch.device errors when CUDA is missing 
        # or when we exclusively intend to run on the CPU.
        os.environ["VLLM_TARGET_DEVICE"] = DEVICE_CPU
        return LLM(model=self.model)

    def convert_messages_to_prompt(self, messages: List[Union[AIMessage, HumanMessage]]) -> str:
        """
        Convert a list of LangChain messages to a single string prompt for vllm.

        :param messages: List of message objects that needs conversion.
        :return: Formatted string prompt.
        """
        prompt_lines: List[str] = []
        
        for msg in messages:
            # Check message type to assign the correct speaker role
            if msg.type == "ai":
                prompt_lines.append("Assistant: " + str(msg.content))
            else:
                prompt_lines.append("User: " + str(msg.content))
        
        # Append final indicator for the model to start generating
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

        :param messages: List of message inputs.
        :param config: Additional configuration options like temperature or top_p.
        :return: List of message outputs appended with the AI's response.
        """
        if config is None:
            config = {}
            
        logger.info("Starting chat completion with vllm on CPU.")

        # Convert the message history into a single string prompt
        prompt: str = self.convert_messages_to_prompt(messages)
        
        # Setup SamplingParams using config or fallback to constants
        temperature: float = config.get("temperature", DEFAULT_TEMPERATURE)
        top_p: float = config.get("top_p", DEFAULT_TOP_P)
        sampling_params = SamplingParams(temperature=temperature, top_p=top_p)

        try:
            # Generate the text using the configured LLM and sampling parameters
            outputs = self.llm.generate([prompt], sampling_params)

            collected_texts: List[str] = []

            for output in outputs:
                generated_text: str = output.outputs[0].text
                
                # Log the generated output properties securely
                logger.info("Prompt: %r, Generated text: %r", output.prompt, generated_text)
                self.log("Generated text: %s" % generated_text)
                
                # Collect the text output
                collected_texts.append(generated_text)

            # Combine all outputs into a single full response
            full_response: str = "".join(collected_texts)
            
            # Append a single AIMessage containing the entire generated response
            messages.append(AIMessage(content=full_response))

            return messages
            
        except (RuntimeError, ValueError) as ex:
            logger.error("Error during vllm chat completions: %s", ex)
            raise

# Made with ❤️ by codx-junior