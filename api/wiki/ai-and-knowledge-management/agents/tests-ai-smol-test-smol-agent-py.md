# SmolAgent Basic Chat Tests

## Overview

This test suite covers Level 1 testing for SmolAgent, focusing on basic chat functionality without tool execution. The tests validate simple scenarios involving streaming responses, mocked OpenAI clients, cancellation handling, and usage recording.

## Test Structure

### Fixtures

The test suite provides several key fixtures for test setup:

- **mock_settings**: Mocks CODXJuniorSettings with LLM configuration including model, API key, and token cost settings
- **mock_user**: Mocks CodxUser with username and API key properties
- **mock_openai_client**: Provides a mocked OpenAI client for simulating API responses
- **smol_agent**: Creates a SmolAgent instance with mocked dependencies and no tools configured
- **mock_run_context**: Mocks AgentRunContext with token cancellation, event emission, and checkpoint capabilities
- **mock_analytics**: Mocks the Analytics singleton for token usage recording
- **sample_messages**: Provides sample conversation messages as HumanMessage objects
- **sample_config**: Provides default chat configuration with chat ID, tools list, and headers

### Helper Functions

**make_openai_chunk()**: Creates mock OpenAI streaming chunks with configurable content, finish reason, and token usage data. Supports simulating both content chunks and usage summary chunks.

## Test Cases

### Basic Streaming Response

Tests simple streaming completion returning text content across multiple chunks. Validates that:
- Multiple content chunks are properly concatenated
- The final response is returned as an AIMessage
- Finish reason is properly recognized

### Empty Chunk Handling

Validates graceful handling of empty chunks (null content) during streaming, ensuring they don't corrupt the final output.

### Preflight Wallet Check

Confirms that wallet validation is performed before initiating OpenAI streaming requests.

### Event Emissions

Verifies correct event types are emitted during successful completion:
- LLM_REQUEST events on chat initiation
- LLM_USAGE events after token counts are available

### Token Usage Recording

Validates that token usage data is properly recorded to analytics with correct parameters:
- Username extraction from user context
- Input token count from prompt tokens
- Output token count from completion tokens

### Runtime Context Creation

Tests automatic RunContext creation when not provided in configuration, validating that project-specific context is properly initialized.

### Cancellation Handling

Verifies that CancelledError is raised when cancellation token is set before streaming begins.

### OpenAI Request Parameters

Confirms that OpenAI API requests include correct configuration:
- Model specification (gpt-4)
- Stream flag enabled
- Stream options with usage inclusion enabled

### System Prompt Integration

Validates that system prompts are properly included in the messages sent to OpenAI with correct role designation.

### Callback Execution

Tests callback invocation with streamed content chunks, ensuring callbacks receive content fragments during streaming.

### Multiple Message History

Verifies that full conversation history is properly transmitted to OpenAI, including system prompt plus all user and assistant messages.

### Custom Headers

Confirms that custom headers from configuration are passed to OpenAI requests via extra_headers parameter with proper formatting (x-litellm-tags).

### Tool Parameter Handling

Validates that the tools parameter is excluded from OpenAI requests when no tools are configured.

### Temperature Configuration

Confirms that temperature settings are included in requests when set to non-zero values.

### Token Counting Fallback

Tests fallback token counting when OpenAI provider does not return usage information in response chunks.

### Cancellation Checkpoints

Validates that run_context checkpoint functionality is available for cancellation safe points.

## Key Testing Patterns

All tests follow consistent patterns:
- Arrange phase sets up mocks and configurable return values
- Act phase executes the chat method with prepared configuration
- Assert phase validates both direct return values and mock interaction calls

The suite uses pytest.mark.asyncio for all async test methods and patches external dependencies to ensure isolation and reproducibility.