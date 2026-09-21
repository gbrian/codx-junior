from fastapi import APIRouter, Request, Response
import logging

from codx.junior.ai.cancellation import CANCELLATION_REGISTRY
from codx.junior.chat_searcher import SearchFilters

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat/cancel")
async def chat_cancel(data: dict):
    """
    Cancel an in-flight chat request by chat_id or cancellation token UUID.

    Expected payload (at least one key must be provided):
        {
            "chat_id":  "<chat doc_id to cancel>",
            "token_id": "<cancellation token UUID>"
        }

    Returns:
        { "cancelled": true,  "method": "chat_id"|"token_id" }
        { "cancelled": false, "error": "..." }
    """
    if not data:
        logger.warning("chat_cancel: empty payload")
        return {"cancelled": False, "error": "missing chat_id or token_id"}

    chat_id = data.get("chat_id")
    token_id = data.get("token_id")

    if not chat_id and not token_id:
        logger.warning("chat_cancel: missing 'chat_id' and 'token_id' in payload")
        return {"cancelled": False, "error": "missing chat_id or token_id"}

    if chat_id:
        logger.info("chat_cancel: attempting cancel by chat_id='%s'", chat_id)
        cancelled = CANCELLATION_REGISTRY.cancel(chat_id)
        if cancelled:
            logger.info("chat_cancel: cancelled by chat_id='%s'", chat_id)
            return {"cancelled": True, "method": "chat_id"}

    if token_id:
        logger.info("chat_cancel: attempting cancel by token_id='%s'", token_id)
        cancelled = CANCELLATION_REGISTRY.cancel_by_token_id(token_id)
        if cancelled:
            logger.info("chat_cancel: cancelled by token_id='%s'", token_id)
            return {"cancelled": True, "method": "token_id"}

    logger.warning("chat_cancel: no in-flight token found for chat_id='%s' token_id='%s'", chat_id, token_id)
    return {"cancelled": False, "error": "no in-flight token found"}


@router.get("/chats/recent")
def api_get_recent_chats(request: Request):
    """
    Get recent chats with optional filtering and pagination.

    Query parameters:
        - user_id: Filter chats by user who created or participated (optional)
        - board: Filter chats by board name (optional)
        - column: Filter chats by column name (optional)
        - chat_type: Filter chats by type 'task' or 'chat' (optional)
        - page: Page number (1-indexed, default: 1)
        - page_size: Results per page (default: 10, max: 100)

    Returns:
        {
            "chats": [Chat objects],
            "total": total count,
            "page": current page,
            "page_size": page size,
            "total_pages": calculated total pages,
            "has_next": boolean,
            "has_prev": boolean
        }
    """
    try:
        codx_junior_session = request.state.codx_junior_session
        chat_manager = codx_junior_session.get_chat_manager()

        user_id = request.query_params.get("user_id")
        board = request.query_params.get("board")
        column = request.query_params.get("column")
        chat_type = request.query_params.get("chat_type")

        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = max(1, min(100, int(request.query_params.get("page_size", 10))))
        except (TypeError, ValueError) as ex:
            logger.error("api_get_recent_chats: invalid pagination params: %s", ex)
            return {
                "error": "Invalid page or page_size parameters",
                "chats": [],
                "total": 0,
                "page": 1,
                "page_size": 10,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
            }

        results = chat_manager.get_recent_chats(
            user_id=user_id,
            board=board,
            column=column,
            chat_type=chat_type,
            page=page,
            page_size=page_size,
        )

        logger.info(
            "api_get_recent_chats: user_id=%s board=%s column=%s chat_type=%s "
            "returned %d chats, page %d of %d",
            user_id or "all",
            board or "all",
            column or "all",
            chat_type or "all",
            results["total"],
            results["page"],
            results["total_pages"],
        )
        return results

    except Exception as ex:
        logger.error("api_get_recent_chats: unexpected error: %s", ex)
        return {
            "error": f"Failed to retrieve recent chats: {str(ex)}",
            "chats": [],
            "total": 0,
            "page": 1,
            "page_size": 10,
            "total_pages": 0,
            "has_next": False,
            "has_prev": False,
        }


@router.get("/chats/logs")
def api_get_chat_logs(request: Request):
    """
    Get complete AI log summary for a chat, including forensic audit trail.

    This endpoint aggregates all AI interactions (LLM requests, tool calls, token usage)
    for a single chat into a comprehensive summary with detailed metrics and complete
    forensic audit trail for debugging and compliance.

    ## Query Parameters
    - **chat_id** (required): UUID of the chat to retrieve logs for

    ## Response Structure: ChatLogSummary

    ### Summary Metrics
    - **chat_id**: The chat identifier used in query
    - **session_id**: Session identifier (if available from chat metadata)
    - **total_log_records**: Total count of all logged records (requests + responses + errors)
    - **total_requests**: Count of LLM completion requests sent
    - **total_responses**: Count of LLM completion responses received
    - **total_duration_seconds**: Aggregate wall-clock time for all AI calls
    - **average_request_duration_seconds**: Mean duration per LLM request

    ### Status Distribution
    - **status_distribution.success**: Count of successful requests/responses
    - **status_distribution.error**: Count of failed or errored requests
    - **status_distribution.cancelled**: Count of user-cancelled requests

    ### Token Usage (Estimated)
    - **token_stats.total_estimated_input_tokens**: Sum of prompt tokens across all requests
    - **token_stats.total_estimated_output_tokens**: Sum of completion tokens across all responses
    - **token_stats.total_estimated_tokens**: Grand total of input + output tokens

    ### Model Usage Breakdown
    - **model_usage**: Array of model usage statistics, each with:
      - **model**: Model name (e.g., "gpt-4o", "claude-3")
      - **provider**: Provider identifier (e.g., "openai", "anthropic")
      - **request_count**: Number of requests using this model/provider
      - **total_duration_seconds**: Cumulative duration for this model/provider

    ### Timestamp Range
    - **first_timestamp**: ISO-8601 timestamp of earliest log record
    - **last_timestamp**: ISO-8601 timestamp of latest log record

    ### Error Tracking
    - **has_errors**: Boolean indicating presence of error or cancelled records
    - **error_details**: Array of error messages (first 5 only, for readability)

    ### Fallback Status
    - **fallback_used**: Boolean indicating whether fallback query strategy was used
    - **fallback_reason**: Explanation if fallback was necessary (e.g., "no session_id available")

    ### Forensic Audit Trail (raw_log_records)
    **Complete forensic record of all AI interactions, suitable for audit compliance,
    debugging, and conversation replay.**

    - **raw_log_records**: Array of forensic records, sorted chronologically. Each record
      is either a ForensicArchivedMessageRecord or ForensicToolCallRecord:

    #### ForensicArchivedMessageRecord
    Represents a complete LLM request-response cycle with all model configuration:
    - **message_id**: Unique message identifier
    - **request_id**: Links to token usage event for cross-reference
    - **timestamp**: Unix timestamp of when recorded
    - **iso_date**: ISO date string (for partitioning)
    - **request_messages**: Complete OpenAI-format message array sent to model
      (includes all prior messages in conversation + system prompt)
    - **system_prompt**: The exact system message sent to the model
    - **temperature**: LLM temperature parameter (for reproducibility)
    - **max_tokens**: Maximum tokens limit enforced
    - **tools**: Complete JSON schema definitions of all tools available to model
    - **response_content**: Full text content of LLM response
    - **input_tokens**: Number of input tokens consumed
    - **output_tokens**: Number of output tokens generated
    - **duration_seconds**: Wall-clock duration of request
    - **error**: Error message if request failed (null if successful)
    - **cancelled**: Boolean indicating if request was user-cancelled
    - **model**: Model name used (e.g., "gpt-4o")
    - **provider**: Provider identifier (e.g., "openai")
    - **chat_id**: Parent chat identifier
    - **username**: User who triggered the request
    - **project_name**: Project context
    - **project_id**: Project identifier

    #### ForensicToolCallRecord
    Represents a complete tool execution with all invocation details:
    - **message_id**: Unique message identifier
    - **tool_call_id**: Tool call ID from LLM (uniquely identifies this tool invocation)
    - **timestamp**: Unix timestamp of when recorded
    - **iso_date**: ISO date string (for partitioning)
    - **tool_name**: Name of the tool function invoked
    - **tool_definition**: Complete JSON schema definition of the tool as sent to model
    - **request_args**: Parsed arguments sent to tool (dict with parameter values)
    - **result**: Raw result returned by tool (may be string, dict, list, or error message)
    - **result_sent_to_model**: Normalized result sent back to LLM (always string)
    - **duration_seconds**: Execution time in seconds
    - **success**: Boolean indicating if tool executed without exception
    - **error_message**: Error details if execution failed (null if successful)
    - **cached**: Boolean indicating if result was from in-conversation cache
    - **chat_id**: Parent chat identifier
    - **username**: User who triggered the tool
    - **project_name**: Project context
    - **project_id**: Project identifier

    ## Example Response (Simplified)

    ```json
    {
      "chat_id": "550e8400-e29b-41d4-a716-446655440000",
      "session_id": "sess_123456",
      "total_log_records": 12,
      "total_requests": 3,
      "total_responses": 3,
      "status_distribution": {
        "success": 11,
        "error": 1,
        "cancelled": 0
      },
      "token_stats": {
        "total_estimated_input_tokens": 2500,
        "total_estimated_output_tokens": 1200,
        "total_estimated_tokens": 3700
      },
      "total_duration_seconds": 15.4,
      "average_request_duration_seconds": 5.13,
      "model_usage": [
        {
          "model": "gpt-4o",
          "provider": "openai",
          "request_count": 3,
          "total_duration_seconds": 15.4
        }
      ],
      "first_timestamp": "2024-01-15T10:30:00+00:00",
      "last_timestamp": "2024-01-15T10:31:45+00:00",
      "has_errors": true,
      "error_details": [
        "Tool 'search_documents' timed out after 10 seconds"
      ],
      "fallback_used": false,
      "fallback_reason": null,
      "raw_log_records": [
        {
          "message_id": "msg_001",
          "request_id": "req_001",
          "timestamp": 1705315800.123,
          "iso_date": "2024-01-15",
          "request_messages": [
            {
              "role": "system",
              "content": "You are a helpful AI assistant..."
            },
            {
              "role": "user",
              "content": "Search for recent documentation"
            }
          ],
          "system_prompt": "You are a helpful AI assistant...",
          "temperature": 0.7,
          "max_tokens": 2000,
          "tools": [
            {
              "type": "function",
              "function": {
                "name": "search_documents",
                "description": "Search project documentation",
                "parameters": {...}
              }
            }
          ],
          "response_content": "I'll search the documentation for you...",
          "input_tokens": 850,
          "output_tokens": 420,
          "duration_seconds": 5.2,
          "error": null,
          "cancelled": false,
          "model": "gpt-4o",
          "provider": "openai",
          "chat_id": "550e8400-e29b-41d4-a716-446655440000",
          "username": "user@example.com",
          "project_name": "codx-junior",
          "project_id": "proj_789"
        },
        {
          "message_id": "msg_tool_001",
          "tool_call_id": "call_abc123",
          "timestamp": 1705315801.450,
          "iso_date": "2024-01-15",
          "tool_name": "search_documents",
          "tool_definition": {
            "type": "function",
            "function": {
              "name": "search_documents",
              "description": "Search project documentation",
              "parameters": {...}
            }
          },
          "request_args": {
            "query": "authentication",
            "limit": 10
          },
          "result": "[{\"title\": \"Auth Guide\", \"url\": \"...\"}]",
          "result_sent_to_model": "[{\"title\": \"Auth Guide\", \"url\": \"...\"}]",
          "duration_seconds": 0.8,
          "success": true,
          "error_message": null,
          "cached": false,
          "chat_id": "550e8400-e29b-41d4-a716-446655440000",
          "username": "user@example.com",
          "project_name": "codx-junior",
          "project_id": "proj_789"
        }
      ]
    }
    ```

    ## Use Cases

    ### Debugging
    Use raw_log_records to trace exact model inputs/outputs, tool definitions, and parameters.
    Each record contains complete payload for reproducing behavior.

    ### Compliance & Audit
    Complete forensic trail with timestamps, user attribution, and all model settings
    enables compliance with data governance and audit requirements.

    ### Performance Analysis
    Token counts and duration metrics per request/tool enable identification of
    bottlenecks and cost optimization opportunities.

    ### Conversation Replay
    Chronologically ordered records with complete system prompts, messages, and
    model parameters allow exact conversation replay for testing or debugging.

    ### Cost Attribution
    Token counts × provider pricing yields exact cost per conversation for
    billing and budget tracking.

    ## Error Responses

    **404 - Chat Not Found**
    ```json
    {
      "error": "Chat not found: <chat_id>",
      "chat_id": "<requested chat_id>"
    }
    ```

    **500 - Query or Processing Error**
    ```json
    {
      "error": "Failed to retrieve chat logs: <error details>"
    }
    ```

    ## HTTP Status Codes
    - **200**: Successfully retrieved logs
    - **404**: Chat not found
    - **500**: Unexpected error during query or aggregation
    """
    try:
        codx_junior_session = request.state.codx_junior_session
        chat_id = request.query_params.get("chat_id")

        if not chat_id:
            logger.error("api_get_chat_logs: missing chat_id")
            return {"error": "missing chat_id parameter"}

        logger.info("api_get_chat_logs: fetching logs for chat_id='%s'", chat_id)
        
        # Delegate to ChatEngineActions via the session
        summary = codx_junior_session._chat_engine_actions.get_chat_log_summary(chat_id=chat_id)

        logger.info(
            "api_get_chat_logs: completed for chat_id='%s' "
            "logs=%d requests=%d responses=%d errors=%d forensic_records=%d",
            chat_id,
            summary.total_log_records,
            summary.total_requests,
            summary.total_responses,
            summary.status_distribution.error,
            len(summary.raw_log_records),
        )
        return summary

    except ValueError as ex:
        logger.error("api_get_chat_logs: chat not found: %s", ex)
        return {"error": str(ex), "chat_id": request.query_params.get("chat_id")}
    except Exception as ex:
        logger.error("api_get_chat_logs: unexpected error: %s", ex)
        return {"error": f"Failed to retrieve chat logs: {str(ex)}"}


@router.post("/chats/message")
async def api_add_message(request: Request):
    """
    Add a single message to a chat (merge-safe, idempotent).

    Expected JSON payload:
        {
            "chat_id": "<chat UUID>",
            "message": {
                "content": "...",
                "role": "user|assistant|system",
                "doc_id": "<optional UUID>",
                ...other Message fields
            }
        }

    Returns:
        The updated Chat object with merged messages.
    """
    from codx.junior.db import Message
    
    try:
        data = await request.json()
        codx_junior_session = request.state.codx_junior_session
        chat_manager = codx_junior_session.get_chat_manager()
        
        chat_id = data.get("chat_id")
        message_data = data.get("message")
        
        if not chat_id or not message_data:
            logger.error("api_add_message: missing chat_id or message")
            return {"error": "missing chat_id or message"}
        
        chat = chat_manager.find_by_id(chat_id=chat_id)
        if not chat:
            logger.error("api_add_message: chat not found: %s", chat_id)
            return {"error": f"chat '{chat_id}' not found"}
        
        message = Message(**message_data)
        updated_chat = chat_manager.add_message(chat=chat, message=message)
        
        return updated_chat
    except Exception as ex:
        logger.error("api_add_message: unexpected error: %s", ex)
        return {"error": f"Failed to add message: {str(ex)}"}


@router.put("/chats/message")
async def api_update_message(request: Request):
    """
    Update an existing message in a chat (merge-safe).

    Matched by doc_id. If not found, the message is appended.

    Expected JSON payload:
        {
            "chat_id": "<chat UUID>",
            "message": {
                "doc_id": "<message UUID>",
                "content": "...",
                "role": "user|assistant|system",
                ...other Message fields
            }
        }

    Returns:
        The updated Chat object with merged messages.
    """
    from codx.junior.db import Message
    
    try:
        data = await request.json()
        codx_junior_session = request.state.codx_junior_session
        chat_manager = codx_junior_session.get_chat_manager()
        
        chat_id = data.get("chat_id")
        message_data = data.get("message")
        
        if not chat_id or not message_data:
            logger.error("api_update_message: missing chat_id or message")
            return {"error": "missing chat_id or message"}
        
        chat = chat_manager.find_by_id(chat_id=chat_id)
        if not chat:
            logger.error("api_update_message: chat not found: %s", chat_id)
            return {"error": f"chat '{chat_id}' not found"}
        
        message = Message(**message_data)
        updated_chat = chat_manager.update_message(chat=chat, message=message)
        
        return updated_chat
    except Exception as ex:
        logger.error("api_update_message: unexpected error: %s", ex)
        return {"error": f"Failed to update message: {str(ex)}"}


@router.delete("/chats/message")
async def api_remove_message(request: Request):
    """
    Remove a message from a chat (merge-safe).

    Expected query parameters:
        - chat_id: <chat UUID>
        - message_doc_id: <message doc_id to remove>

    Returns:
        The updated Chat object with the message removed.
    """
    try:
        codx_junior_session = request.state.codx_junior_session
        chat_manager = codx_junior_session.get_chat_manager()
        
        chat_id = request.query_params.get("chat_id")
        message_doc_id = request.query_params.get("message_doc_id")
        
        if not chat_id or not message_doc_id:
            logger.error("api_remove_message: missing chat_id or message_doc_id")
            return {"error": "missing chat_id or message_doc_id"}
        
        chat = chat_manager.find_by_id(chat_id=chat_id)
        if not chat:
            logger.error("api_remove_message: chat not found: %s", chat_id)
            return {"error": f"chat '{chat_id}' not found"}
        
        updated_chat = chat_manager.remove_message(chat=chat, message_doc_id=message_doc_id)
        
        return updated_chat
    except Exception as ex:
        logger.error("api_remove_message: unexpected error: %s", ex)
        return {"error": f"Failed to remove message: {str(ex)}"}


@router.post("/chats/metadata")
async def api_update_chat_metadata(request: Request):
    """
    Update chat metadata only (name, description, board, column, etc.)
    without touching messages.

    Expected JSON payload:
        {
            "chat_id": "<chat UUID>",
            "metadata": {
                "name": "...",
                "description": "...",
                "board": "...",
                "column": "...",
                ...other fields (excluding messages)
            }
        }

    Returns:
        The updated Chat object.
    """
    try:
        data = await request.json()
        codx_junior_session = request.state.codx_junior_session
        chat_manager = codx_junior_session.get_chat_manager()
        
        chat_id = data.get("chat_id")
        metadata = data.get("metadata", {})
        
        if not chat_id:
            logger.error("api_update_chat_metadata: missing chat_id")
            return {"error": "missing chat_id"}
        
        chat = chat_manager.find_by_id(chat_id=chat_id)
        if not chat:
            logger.error("api_update_chat_metadata: chat not found: %s", chat_id)
            return {"error": f"chat '{chat_id}' not found"}
        
        # Delegate metadata update to chat_manager
        updated_chat = chat_manager.update_chat_metadata(chat=chat, metadata=metadata)
        
        return updated_chat
    except Exception as ex:
        logger.error("api_update_chat_metadata: unexpected error: %s", ex)
        return {"error": f"Failed to update chat metadata: {str(ex)}"}


@router.get("/chats")
def api_list_chats(request: Request):
    """
    List chats with optional filtering and export.

    Query parameters:
        - file_path: Load a specific chat by file path.
        - id: Load a specific chat by ID.
        - export_format: Export format (markdown, docx, pdf, excel, etc.).
        - from_date: ISO-format date for filtering (list_chats only).

    Returns:
        Single Chat object if id or file_path is provided.
        Export response if export_format is provided.
        List of Chat objects otherwise.
    """
    try:
        codx_junior_session = request.state.codx_junior_session
        chat_manager = codx_junior_session.get_chat_manager()
        file_path = request.query_params.get("file_path")
        chat_id = request.query_params.get("id")
        export_format = request.query_params.get("export_format")
        from_date = request.query_params.get("from_date")

        if export_format:
            export = chat_manager.export_chat(chat_id=chat_id, export_format=export_format)
            return Response(
                content=export.content,
                media_type=export.content_type,
                headers={"Content-Disposition": f"attachment; filename={export.file_name}"}
            )

        if chat_id:
            chat = chat_manager.find_by_id(chat_id=chat_id)
            if not chat:
                logger.error('Chat not found. chat_id: %s, project: %s', chat_id, codx_junior_session.settings.project_name)
            return chat

        if file_path:
            chat = chat_manager.load_chat_from_path(chat_file=file_path)
            if not chat:
                logger.error('Chat not found. file_path: %s, project: %s', file_path, codx_junior_session.settings.project_name)
            return chat

        return chat_manager.list_chats(from_date=from_date)
    except Exception as ex:
        logger.error("api_list_chats: unexpected error: %s", ex)
        return {"error": f"Failed to list chats: {str(ex)}"}


@router.post("/chats/search")
async def api_search_chats(request: Request):
    """
    Search chats with full-text search, field-level filtering, user filtering, and pagination.

    Expected JSON payload:
        {
            "query": "<search query string>",
            "user_id": "<optional user ID to filter by>",
            "from_date": "<ISO-format date, optional>",
            "to_date": "<ISO-format date, optional>",
            "page": 1,
            "page_size": 20,
            "filters": { ... }
        }

    Returns:
        Paginated search results with relevance scores.
    """
    try:
        data = await request.json()
        codx_junior_session = request.state.codx_junior_session
        chat_manager = codx_junior_session.get_chat_manager()

        query = data.get("query", "")
        user_id = data.get("user_id")
        from_date = data.get("from_date")
        to_date = data.get("to_date")
        page = data.get("page", 1)
        page_size = data.get("page_size", 20)
        filters_data = data.get("filters")

        # Validate inputs
        try:
            page = max(1, int(page))
            page_size = max(1, min(100, int(page_size)))
        except (TypeError, ValueError) as ex:
            logger.error("api_search_chats: invalid pagination params: %s", ex)
            return {
                "error": "Invalid page or page_size parameters",
                "results": [],
                "total": 0,
                "page": 1,
                "page_size": page_size,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
            }

        if not query:
            logger.warning("api_search_chats: empty query")
            return {
                "error": "Query parameter cannot be empty",
                "results": [],
                "total": 0,
                "page": 1,
                "page_size": page_size,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
            }

        # Delegate search to chat_manager with user_id filter
        results = chat_manager.search_chats(
            query=query,
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )

        logger.info(
            "api_search_chats: query='%s' user_id=%s returned %d results, page %d of %d",
            query,
            user_id or "all",
            results["total"],
            results["page"],
            results["total_pages"],
        )
        return results

    except ValueError as ex:
        logger.error("api_search_chats: invalid date format: %s", ex)
        return {
            "error": "Invalid date format (use ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
            "results": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
            "total_pages": 0,
            "has_next": False,
            "has_prev": False,
        }
    except Exception as ex:
        logger.error("api_search_chats: unexpected error: %s", ex)
        return {
            "error": f"Search failed: {str(ex)}",
            "results": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
            "total_pages": 0,
            "has_next": False,
            "has_prev": False,
        }


@router.post("/chats")
async def api_chat(request: Request):
    """
    Chat with the project. Delegates to session for AI turn execution.
    
    ADDED: Error responses now include response_message metadata
    (including cancellation_token_id) so frontend can display the error
    state and enable cancellation/retry UI.
    """
    from codx.junior.db import Chat
    
    try:
        data = await request.json()
        chat = Chat(**data)
        codx_junior_session = request.state.codx_junior_session
        
        codx_junior_session.chat_event(chat=chat, message="Chatting with project...")
        await codx_junior_session.chat_with_project(chat=chat)
        await codx_junior_session.save_chat(chat)
        
        return chat
    except Exception as ex:
        logger.error("api_chat: unexpected error: %s", ex)
        # ADDED: Return error response with proper structure so frontend
        # can extract error details and display cancellation UI if applicable
        return {
            "error": f"Failed to chat: {str(ex)}",
            "success": False,
            "chat_id": data.get("id"),
        }


@router.post("/chats/from-url")
async def api_chat_from_url(request: Request):
    """
    Initialize chat from URL. Delegates to session.
    """
    from codx.junior.db import Chat
    
    try:
        data = await request.json()
        chat = Chat(**data)
        codx_junior_session = request.state.codx_junior_session
        
        codx_junior_session.chat_event(chat=chat, message="Loading chat...")
        codx_junior_session.init_chat_from_url(chat=chat)
        await codx_junior_session.save_chat(chat)
        
        return chat
    except Exception as ex:
        logger.error("api_chat_from_url: unexpected error: %s", ex)
        return {"error": f"Failed to load chat from URL: {str(ex)}"}


@router.post("/chats/sub-tasks")
async def api_chat_subtasks(request: Request):
    """
    Generate subtasks from chat. Delegates to session.
    """
    from codx.junior.db import Chat
    
    try:
        data = await request.json()
        chat = Chat(**data)
        codx_junior_session = request.state.codx_junior_session
        
        return await codx_junior_session.generate_tasks(chat=chat)
    except Exception as ex:
        logger.error("api_chat_subtasks: unexpected error: %s", ex)
        return {"error": f"Failed to generate tasks: {str(ex)}"}


@router.put("/chats")
async def api_save_chat(request: Request):
    """
    Save chat. Delegates to chat_manager.
    """
    from codx.junior.db import Chat
    
    try:
        data = await request.json()
        chat = Chat(**data)
        codx_junior_session = request.state.codx_junior_session
        chat_manager = codx_junior_session.get_chat_manager()
        
        chat_only = request.query_params.get("chat_only") == "1"
        saved_chat = chat_manager.save_chat(chat=chat, chat_only=chat_only)
        
        return saved_chat
    except Exception as ex:
        logger.error("api_save_chat: unexpected error: %s", ex)
        return {"error": f"Failed to save chat: {str(ex)}"}


@router.delete("/chats")
def api_delete_chat(request: Request):
    """
    Delete a chat. Delegates to chat_manager.
    """
    try:
        codx_junior_session = request.state.codx_junior_session
        chat_manager = codx_junior_session.get_chat_manager()
        chat_id = request.query_params.get("chat_id")
        
        chat_manager.delete_chat(chat_id=chat_id)
        
        return {"deleted": True}
    except Exception as ex:
        logger.error("api_delete_chat: unexpected error: %s", ex)
        return {"error": f"Failed to delete chat: {str(ex)}"}


@router.get("/kanban")
def api_kanban(request: Request):
    """
    Load kanban. Delegates to chat_manager.
    """
    try:
        codx_junior_session = request.state.codx_junior_session
        chat_manager = codx_junior_session.get_chat_manager()
        
        return chat_manager.load_kanban()
    except Exception as ex:
        logger.error("api_kanban: unexpected error: %s", ex)
        return {"error": f"Failed to load kanban: {str(ex)}"}


@router.post("/kanban")
async def api_set_kanban(request: Request):
    """
    Save kanban. Delegates to chat_manager.
    """
    try:
        codx_junior_session = request.state.codx_junior_session
        chat_manager = codx_junior_session.get_chat_manager()
        kanban = await request.json()
        
        chat_manager.save_kanban(kanban)
        
        return {"saved": True}
    except Exception as ex:
        logger.error("api_set_kanban: unexpected error: %s", ex)
        return {"error": f"Failed to save kanban: {str(ex)}"}


@router.delete("/kanban")
def api_delete_kanban(request: Request):
    """
    Delete kanban board. Delegates to chat_manager.
    """
    try:
        codx_junior_session = request.state.codx_junior_session
        chat_manager = codx_junior_session.get_chat_manager()
        kanban_title = request.query_params.get("kanban_title")
        
        chat_manager.delete_kanban(kanban_title=kanban_title)
        
        return {"deleted": True}
    except Exception as ex:
        logger.error("api_delete_kanban: unexpected error: %s", ex)
        return {"error": f"Failed to delete kanban: {str(ex)}"}

# Made with ❤️ by codx-junior