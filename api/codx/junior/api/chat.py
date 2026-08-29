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
            "chat_id":  "<chat doc_id to cancel>",       # cancel by chat document ID
            "token_id": "<cancellation token UUID>"      # cancel by token UUID received
                                                         # in response message meta_data
        }

    When both keys are present ``chat_id`` is tried first; if no token is found
    for it the handler falls back to ``token_id``.

    Returns:
        { "cancelled": true,  "method": "chat_id"|"token_id" }
            — a token was found and cancelled
        { "cancelled": false, "error": "..." }
            — no in-flight token was found for either key

    flowchart TD
        A[Client POST /api/chat/cancel] --> B{chat_id present?}
        B -->|Yes| C[CANCELLATION_REGISTRY.cancel by chat_id]
        C -->|Token found| D[Return cancelled=true method=chat_id]
        C -->|No token| E{token_id present?}
        B -->|No| E
        E -->|Yes| F[CANCELLATION_REGISTRY.cancel_by_token_id]
        F -->|Token found| G[Return cancelled=true method=token_id]
        F -->|No token| H[Log warning]
        H --> I[Return cancelled=false]
        E -->|No| J[Log warning missing keys]
        J --> I
    """
    if not data:
        logger.warning("chat_cancel: empty payload")
        return {"cancelled": False, "error": "missing chat_id or token_id"}

    chat_id = data.get("chat_id")
    token_id = data.get("token_id")

    if not chat_id and not token_id:
        logger.warning(
            "chat_cancel: missing 'chat_id' and 'token_id' in payload"
        )
        return {"cancelled": False, "error": "missing chat_id or token_id"}

    # --- Try chat_id first ---
    if chat_id:
        logger.info(
            "chat_cancel: attempting cancel by chat_id='%s'", chat_id
        )
        cancelled = CANCELLATION_REGISTRY.cancel(chat_id)
        if cancelled:
            logger.info(
                "chat_cancel: cancelled by chat_id='%s'", chat_id
            )
            return {"cancelled": True, "method": "chat_id"}

    # --- Fall back to token_id ---
    if token_id:
        logger.info(
            "chat_cancel: attempting cancel by token_id='%s'", token_id
        )
        cancelled = CANCELLATION_REGISTRY.cancel_by_token_id(token_id)
        if cancelled:
            logger.info(
                "chat_cancel: cancelled by token_id='%s'", token_id
            )
            return {"cancelled": True, "method": "token_id"}

    logger.warning(
        "chat_cancel: no in-flight token found for "
        "chat_id='%s' token_id='%s'",
        chat_id, token_id,
    )
    return {"cancelled": False, "error": "no in-flight token found"}


@router.post("/chats/message")
async def api_add_message(request: Request):
    """
    Add a single message to a chat (merge-safe, idempotent).

    Used during AI turns to persist events (tool usage, streaming, etc.)
    without overwriting concurrent updates.

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
    from codx.junior.db import Chat, Message
    
    data = await request.json()
    codx_junior_session = request.state.codx_junior_session
    chat_manager = codx_junior_session.get_chat_manager()
    
    chat_id = data.get("chat_id")
    message_data = data.get("message")
    
    if not chat_id or not message_data:
        logger.error("api_add_message: missing chat_id or message")
        return {"error": "missing chat_id or message"}
    
    try:
        chat = chat_manager.find_by_id(chat_id=chat_id)
        if not chat:
            logger.error("api_add_message: chat not found: %s", chat_id)
            return {"error": f"chat '{chat_id}' not found"}
        
        message = Message(**message_data)
        updated_chat = chat_manager.add_message(chat=chat, message=message)
        
        logger.info(
            "api_add_message: added message '%s' to chat '%s'",
            message.doc_id, chat_id
        )
        return updated_chat
    except Exception as ex:
        logger.error("api_add_message: unexpected error: %s", ex)
        return {"error": f"Failed to add message: {str(ex)}"}


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
    codx_junior_session = request.state.codx_junior_session
    file_path = request.query_params.get("file_path")
    chat_id = request.query_params.get("id")
    export_format = request.query_params.get("export_format")
    from_date = request.query_params.get("from_date")

    if export_format:
        export = codx_junior_session.get_chat_manager().export_chat(chat_id=chat_id, export_format=export_format)
        return Response(
                  content=export.content,
                  media_type=export.content_type,
                  headers={"Content-Disposition": f"attachment; filename={export.file_name}"}
              )

    if chat_id:
        chat = codx_junior_session.get_chat_manager().find_by_id(chat_id=chat_id)
        if not chat:
            logger.error('Chat not found. chat_id: %s, project: %s', chat_id, codx_junior_session.settings.project_name)
        return chat

    if file_path:
        chat = codx_junior_session.get_chat_manager().load_chat_from_path(chat_file=file_path)
        if not chat:
            logger.error('Chat not found. file_path: %s, project: %s', file_path, codx_junior_session.settings.project_name)
        return chat

    return codx_junior_session.list_chats(from_date=from_date)


@router.post("/chats/search")
async def api_search_chats(request: Request):
    """
    Search chats with full-text search, field-level filtering, and pagination.

    Expected JSON payload:
        {
            "query": "<search query string>",
            "from_date": "<ISO-format date, optional>",
            "to_date": "<ISO-format date, optional>",
            "page": 1,
            "page_size": 20,
            "filters": {
                "search_name": true,
                "search_description": true,
                "search_messages": true,
                "search_message_metadata": true,
                "search_history": true,
                "search_files": true,
                "search_model": true,
                "search_status": true,
                "search_mode": true
            }
        }

    The search looks across (subject to filter flags):
        - Chat name, description, status, mode
        - Message content and thinking field
        - Message user, profiles, knowledge topics
        - File list, LLM model
        - Chat history summaries

    Filter flags:
        - All flags default to ``true`` (search everywhere) when omitted.
        - Set to ``false`` to exclude that field category from search scope.
        - Allows fine-grained control similar to email filter dialogs.

    Returns:
        {
            "results": [
                {
                    "chat": { ... },
                    "relevance_score": 15.5,
                    "matched_fields": ["name", "message_content"]
                },
                ...
            ],
            "total": 42,
            "page": 1,
            "page_size": 20,
            "total_pages": 3,
            "has_next": true,
            "has_prev": false
        }
    """
    from codx.junior.chat_searcher import ChatSearcher

    data = await request.json()
    codx_junior_session = request.state.codx_junior_session
    chat_manager = codx_junior_session.get_chat_manager()

    query = data.get("query", "")
    from_date = data.get("from_date")
    to_date = data.get("to_date")
    page = data.get("page", 1)
    page_size = data.get("page_size", ChatSearcher.DEFAULT_PAGE_SIZE)
    filters_data = data.get("filters")

    # Validate inputs
    try:
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))  # Cap at 100 items per page
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

    try:
        # Load all chats for the project
        all_chats = chat_manager.list_chats()
        logger.info(
            "api_search_chats: loaded %d chats for searching", len(all_chats)
        )

        # Parse filter flags from request (defaults to all enabled if not provided)
        filters = SearchFilters.from_dict(filters_data)

        # Perform search with filters
        searcher = ChatSearcher()
        results = searcher.search(
            chats=all_chats,
            query=query,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
            filters=filters,
        )

        logger.info(
            "api_search_chats: query='%s' returned %d results, page %d of %d",
            query,
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
            "page_size": page_size,
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
            "page_size": page_size,
            "total_pages": 0,
            "has_next": False,
            "has_prev": False,
        }


@router.post("/chats")
async def api_chat(request: Request):
    from codx.junior.db import Chat
    from codx.junior.profiling.profiler import profile_function
    data = await request.json()
    chat = Chat(**data)
    codx_junior_session = request.state.codx_junior_session
    codx_junior_session.chat_event(chat=chat, message="Chatting with project...")
    await codx_junior_session.chat_with_project(chat=chat)
    await codx_junior_session.save_chat(chat)
    return chat


@router.post("/chats/from-url")
async def api_chat_form_url(request: Request):
    from codx.junior.db import Chat
    data = await request.json()
    chat = Chat(**data)
    codx_junior_session = request.state.codx_junior_session
    codx_junior_session.chat_event(chat=chat, message="Loading chat...")
    codx_junior_session.init_chat_from_url(chat=chat)
    await codx_junior_session.save_chat(chat)
    return chat


@router.post("/chats/sub-tasks")
async def api_chat_subtasks(request: Request):
    from codx.junior.db import Chat
    data = await request.json()
    chat = Chat(**data)
    codx_junior_session = request.state.codx_junior_session
    return await codx_junior_session.generate_tasks(chat=chat)


@router.put("/chats")
async def api_save_chat(request: Request):
    from codx.junior.db import Chat
    data = await request.json()
    chat = Chat(**data)
    codx_junior_session = request.state.codx_junior_session
    chat_only = request.query_params.get("chatonly") == "1"
    await codx_junior_session.save_chat(chat, chat_only=chat_only)


@router.delete("/chats")
def api_delete_chat(request: Request):
    codx_junior_session = request.state.codx_junior_session
    chat_id = request.query_params.get("chat_id")
    codx_junior_session.delete_chat(chat_id)


@router.get("/kanban")
def api_kanban(request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.get_chat_manager().load_kanban()


@router.post("/kanban")
async def api_set_kanban(request: Request):
    codx_junior_session = request.state.codx_junior_session
    kanban = await request.json()
    codx_junior_session.get_chat_manager().save_kanban(kanban)


@router.delete("/kanban")
def api_delete_kanban(request: Request):
    codx_junior_session = request.state.codx_junior_session
    kanban_title = request.query_params.get("kanban_title")
    return codx_junior_session.get_chat_manager().delete_kanban(kanban_title=kanban_title)

# Made with ❤️ by codx-junior