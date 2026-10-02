# VllmCPUAI

The `VllmCPUAI` class provides an interface for executing vLLM models while constraining usage to CPU resources. It mimics functionalities similar to OpenAI's AI endpoints but leverages vLLM for offline batched inference tailored for CPU mode.

## Class Structure and Initialization

### Purpose
This class is designed to manage the lifecycle of a local vLLM instance, particularly when running models on CPU hardware.

### Constructor (`__init__`)
The constructor initializes the client, handles model loading, and sets up logging.

#### Parameters:
*   **`settings`**: An instance of `CODXJuniorSettings`, required for global settings and AI logging management.
*   **`llm_model`** (Optional `str`): The specified LLM model identifier. If not provided, it defaults to `"Qwen/Qwen3-8B"` (`DEFAULT_LLM_MODEL`).
*   **`user`** (Optional `CodxUser`): An object representing the current user context. Used for logging purposes.
*   **`system`** (Optional `str`): A system message string.

#### Behavior:
1.  It calls `setup_vllm_client()` to initialize the vLLM backend (`self.llm`).
2.  Logs information upon successful initialization, noting the user and model used.
3.  Handles potential setup errors by catching `RuntimeError` or `ValueError`.

## Methods

### `_parse_hf_gguf_url(self, url: str)`
A private utility method responsible for parsing Hugging Face blob URLs.
*   **Description**: It checks if a given URL is a Hugging Face link and uses regex to extract the repository ID (`repo_id`) and the actual file name (`filename`), specifically targeting `.gguf` format files.
*   **Returns**: A dictionary containing `"repo_id"` and `"filename"`, or `None` if the URL does not match the expected structure.

### `setup_vllm_client(self) -> LLM`
Initializes and returns the vLLM object, configuring it for CPU execution based on the provided model name.
*   **Model Handling**: It first attempts to parse the model string as a GGUF URL using `_parse_hf_gguf_url()`.
    *   **GGUF URL Found**: If the model is found via a GGUF URL, it sets specific parameters (`quantization="gguf"`, passing `repo_id` and `filename`) and dynamically sets `max_model_len`. It includes special logic to handle large context models (e.g., "Qwythos") by detecting them in the `repo_id`.
    *   **Standard Model**: If it is not a GGUF URL, it initializes vLLM using the model name directly (`LLM(model=self.model)`).

### `log(self, msg: str) -> None`
Handles AI logging based on system settings.
*   **Description**: Logs an internal message (`msg`) only if the global AI logging setting (`self.settings.get_log_ai()`) is enabled.

### `convert_messages_to_prompt(self, messages: List[Union[AIMessage, HumanMessage]]) -> str`
Converts structures from LangChain's message format into a single string prompt suitable for vLLM.
*   **Functionality**: It iterates through the list of `HumanMessage` and `AIMessage` objects, prefixing their content with `"User: "` or `"Assistant: "`, respectively. Finally, it appends an initiating `"Assistant:"` marker to guide the model's expected output format.

### `chat_completions(self, messages: List[Union[AIMessage, HumanMessage]], config: Optional[Dict[str, Any]] = None) -> List[Union[AIMessage, HumanMessage]]`
The main method for synchronous chat completion execution.
*   **Parameters**:
    *   `messages`: A list of `AIMessage`/`HumanMessage` objects representing the conversation history.
    *   `config`: Optional dictionary containing generation parameters (e.g., `"temperature"`, `"top_p"`). Defaults are set to 0.8 and 0.95, respectively.
*   **Process**:
    1.  Converts the `messages` list into a single prompt string using `convert_messages_to_prompt()`.
    2.  Creates `vllm.SamplingParams` based on the temperature and top\_p provided in `config`.
    3.  Calls `self.llm.generate()` to receive model outputs.
    4.  Iterates through the generated outputs, logging them and accumulating the clean text content.
    5.  Combines all captured texts into a single response string (`full_response`).
    6.  Appends the final combined result as a new `AIMessage` object to the original `messages` list and returns the updated list.

### Asynchronous Accessors
*   **`a_chat_completions(**kwargs)`**: Provides an asynchronous wrapper calling `self.chat_completions()`.

## Dependencies
**Imports from:** codx/junior/ai/ai_logger.py, codx/junior/settings.py, codx/junior/model/model.py