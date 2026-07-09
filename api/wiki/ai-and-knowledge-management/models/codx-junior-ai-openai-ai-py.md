OpenAI_AI Class
================

Overview
--------

This class, `openai_ai`, is an implementation of the OpenAI API. It allows users to send requests to various models for different purposes.

Initialization
-------------

To initialize the class, you need to provide a settings object and optionally an LLM model to use:
```python
settings = CODXJuniorSettings()
llm_model = "some-model"
user_model = CodxUser(username="some_username", api_key="some_api_key")
ai = OpenAI_AI(settings=settings,llm_model=llm_model, user=user_model)
```
or
```python
settings = CODXJuniorSettings()
ai = OpenAI_AI(settings=settings)
```
Methods
---------

### `_preflight_limit_check`

This method checks the user's wallet before executing an AI request.

### `convert_message_to_openai`

Converting messages to a format compatible with the OpenAI API.

### `preparer_messages_to_openai`

Prepares messages to be sent to the OpenAI API by converting them to the correct format.

### `_raw_log_request`

Raw-logs the outgoing requests in the server log.

### `_raw_log_response`

Raw-logs the incoming responses from the API in the server log.

### `_raw_log_error`

Raw-logs any errors that occur when sending a request or receiving a response from the API in the server log.

### `log`

Logs messages to the AI logger.

### `chat_completions`

This method sends a chat-completion request to the OpenAI API.
```python
messages = [...]  # list of messages to send
config = {...}  # configuration for the request, e.g. cancellation token, tools used
response = ai.chat_completions(messages=messages, config=config)
```
### `a_chat_completions`

This method sends an asynchronous chat-completion request to the OpenAI API.
```python
messages = [...]  # list of messages to send
config = {...}  # configuration for the request, e.g. cancellation token, tools used
response = ai.aChatCompletitions(messages=messages, config=config)
```
### `process_tool_calls`

This method processes and executes a tool call with analytics recording.
```python
tool_call_data = {...}  # data for the tool call, e.g. function name, arguments
request_id = "..."  # traceability link to the LLM request that triggered this tool
chat_id = "..."  # chat/session identifier for tool usage tracking
response = ai.process_tool_calls(tool_call_data=tool_call_data, request_id=request_id, chat_id=chat_id)
```
### `generate_image`

This method uses the OpenAI Images API to generate an image.
```python
prompt = "..."  # prompt for the image generation
image_url = ai.generate_image(prompt=prompt)  # URL of the generated image
```

## Dependencies
**Imports from:** codx/junior/ai/ai_logger.py, codx/junior/ai/raw_logger.py, codx/junior/ai/cancellation.py, codx/junior/ai/wallet_check.py, codx/junior/settings.py, codx/junior/profiling/profiler.py, codx/junior/utils/utils.py, codx/junior/model/model.py, codx/junior/analytics/__init__.py, codx/junior/analytics/token_counter.py, codx/junior/tools/__init__.py
**Imported by:** codx/junior/ai/ai.py