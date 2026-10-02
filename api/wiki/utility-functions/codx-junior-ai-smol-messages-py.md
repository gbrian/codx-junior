# Message Helpers for SmolAgent

## Overview

This utility module provides functions to convert LangChain messages to the OpenAI Chat Completions format and manage tool-calling protocol messages. It includes support for streaming tool-call fragments through the `ToolCallAccumulator` class.

## Functions

### to_openai_message()

Converts a single LangChain message to an OpenAI message dictionary format.

**Parameters:**
- `message` (Union[AIMessage, HumanMessage]): A LangChain message object

**Returns:**
- Dict[str, Any]: A dictionary with `role` and `content` keys compatible with the OpenAI API

**Raises:**
- `json.JSONDecodeError`: If an image message contains invalid JSON

**Behavior:**
- Image messages are parsed from JSON and return with `role="user"`
- AI messages return with `role="assistant"`
- Human messages return with `role="user"`

### to_openai_messages()

Converts a complete LangChain message list to OpenAI format, optionally prepending a system prompt.

**Parameters:**
- `messages` (List[Union[AIMessage, HumanMessage]]): Conversation history as LangChain messages
- `system` (Optional[str]): Optional system prompt content

**Returns:**
- List[Dict[str, Any]]: List of OpenAI-compatible message dictionaries

**Behavior:**
- Converts each message using `to_openai_message()`
- Prepends system prompt as first message when provided and non-empty

### make_tool_message()

Builds an OpenAI tool result message required by the tool-calling protocol.

**Parameters:**
- `tool_call_id` (str): The `id` from the assistant's tool_call entry
- `content` (Any): Result returned by the tool

**Returns:**
- Dict[str, Any]: A message dict with `role="tool"` ready to append to the messages list

**Note:** Every tool invocation in the assistant's `tool_calls` array must be answered with a matching tool message, otherwise subsequent API requests are rejected.

### make_assistant_tool_calls_message()

Constructs the assistant message that records which tools were requested.

**Parameters:**
- `tool_calls` (Dict[str, Dict[str, Any]]): Mapping of tool_call_id → {id, function, arguments}
- `content` (str): Optional partial text content generated before tool calls (defaults to empty string)

**Returns:**
- Dict[str, Any]: A dictionary with `role="assistant"` and a `tool_calls` list

**Processing:**
- Converts argument dictionaries to JSON strings
- Structures each tool call with `id`, `type="function"`, and `function` metadata

## ToolCallAccumulator Class

Assembles fragmented tool-call data from OpenAI's streaming API into complete tool-call objects.

**Background:** The OpenAI streaming API sends tool-call information in fragments—the first chunk provides `id` and `function.name`, while subsequent chunks append characters to `function.arguments`.

### Methods

#### __init__()

Initializes an empty accumulator with no tool calls.

#### add()

Merges a list of streaming tool-call delta objects into the accumulator.

**Parameters:**
- `tool_calls_delta` (List[Any]): List of delta tool-call objects from a chunk

**Behavior:**
- Creates new tool-call entries for previously unseen IDs
- Appends function names and arguments to existing entries
- Logs warnings if a tool ID cannot be resolved

#### has_calls()

Checks whether at least one tool call has been accumulated.

**Returns:**
- bool: `True` if tool calls exist, `False` otherwise