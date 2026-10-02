# AI Raw Log Models Documentation

## Overview

This module provides Pydantic models for AI raw log records that reflect the exact schema written by `RawAILogger` and read back by `RawLogReader`. The models are organized hierarchically to support request, response, and error logging scenarios.

## Core Models

### RawLogRecord

The top-level model representing a single complete log entry from a `*_raw_ai.jsonl` file.

**Key Fields:**
- `log_id` - Synthetic unique identifier in format `<YYYY-MM-DD>:<line_index>` (injected by RawLogReader)
- `timestamp` - ISO-8601 UTC timestamp of record creation
- `direction` - Either `'request'` for outgoing calls or `'response'` for replies/errors
- `status` - Outcome status with three possible values:
  - `"success"` – request completed normally
  - `"cancelled"` – request was cancelled before completion
  - `"error"` – request failed with an exception
- `request_id` - Unique UUID pairing request and response records
- `parent_request_id` - Optional UUID of parent call when spawned from tool-call response
- `provider` - Provider identifier (e.g., 'openai', 'litellm')
- `model` - Model name used for the completion call
- `base_url` - API endpoint base URL
- `username` - Requesting user identifier
- `project` - Associated project name
- `session_id` - Optional session or conversation identifier
- `tags` - Comma-separated tag string
- `duration_seconds` - Wall-clock duration in seconds (response/error records only)
- `payload` - Direction-specific payload object

### RawLogPayload

Union-like payload model that can represent request, response, or error data. All fields are optional to support deserialization without prior knowledge of direction or status.

**Request Fields:**
- `kwargs` - Keyword arguments passed to the completion call (excluding messages)
- `messages` - OpenAI-compatible messages array

**Response Fields:**
- `content` - Reconstructed full text content from streamed chunks
- `finish_reason` - Final completion reason (e.g., 'stop', 'tool_calls', 'length')
- `tool_calls` - Tool-call data dictionary keyed by tool-call ID

**Error Fields:**
- `error_type` - Exception class name
- `error_message` - String representation of the exception

## Specialized Payload Models

### RequestPayload

Payload for outgoing AI requests, written by `RawAILogger.log_request()`.

**Fields:**
- `kwargs` - Additional keyword arguments (temperature, stream, tools, etc.)
- `messages` - OpenAI-compatible messages array

### ResponsePayload

Payload for successful AI responses, written by `RawAILogger.log_response()`.

**Fields:**
- `content` - Full reconstructed text content
- `finish_reason` - Final finish_reason from last stream chunk
- `tool_calls` - Accumulated tool-call data

### ErrorPayload

Payload when requests fail or are cancelled, written by `RawAILogger.log_error()`.

**Fields:**
- `error_type` - Exception class name
- `error_message` - Exception string representation

## List and Pagination Models

### RawLogRecordSummary

Lightweight summary model suitable for list views, replacing full payload with a preview.

**Key Fields:**
- All fields from RawLogRecord except `payload`
- `payload_preview` - First 200 characters of payload string representation
- `tools` - Optional tool information

### RawLogListResponse

Paginated response wrapper for listing log records.

**Fields:**
- `items` - Array of RawLogRecordSummary objects
- `total` - Total number of matching records
- `page` - Current 1-based page number
- `page_size` - Items per page
- `has_more` - Boolean indicating if more pages exist

## Bulk Operations Models

### PurgeRequest

Request body for bulk log deletion with optional filtering.

**Fields:**
- `start_date` - Inclusive lower bound (YYYY-MM-DD format)
- `end_date` - Inclusive upper bound (YYYY-MM-DD format)
- `username` - Filter by username
- `project` - Filter by project name
- `model` - Filter by model name
- `provider` - Filter by provider name

### PurgeResponse

Response returned after a purge operation.

**Fields:**
- `ok` - Boolean success indicator
- `deleted` - Number of log records deleted

## Dependencies
**Imported by:** codx/junior/api/logs.py