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
    Search chats with full-text search, field-level filtering, and pagination.

    Expected JSON payload:
        {
            "query": "<search query string>",
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

        # Delegate search to chat_manager
        results = chat_manager.search_chats(
            query=query,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
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
        return {"error": f"Failed to chat: {str(ex)}"}


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