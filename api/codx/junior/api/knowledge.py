import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from codx.junior.model.model import (
    CodxUser,
    KnowledgeReloadPath,
    KnowledgeSearch,
    KnowledgeDeleteSources,
    Document,
)

from codx.junior.knowledge.knowledge_ai_search import (
    KnowledgeAISearch,
    AISearchResult,
    AgentResourcePlan,
)
from codx.junior.api import require_admin
from codx.junior.engine.session import CODXJuniorSession
from codx.junior.engine.progress_callback import SocketProgressCallback, ProgressEventType
from codx.junior.sio.session_channel import SessionChannel
from codx.junior.sio.sio import sio
from codx.junior.sio.sio import sio_api_endpoint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

@router.get("/reload")
async def api_knowledge_reload(request: Request):
    """
    Trigger a knowledge base reload check for the current project.

    Returns:
        Knowledge status dict from the session.
    """
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.check_knowledge_status()


@router.post("/reload-path")
def api_knowledge_reload_path(
    knowledge_reload_path: KnowledgeReloadPath,
    request: Request,
):
    """
    Reload knowledge for a specific source path.

    Args:
        knowledge_reload_path: Object containing the path to reload.
        request: Incoming HTTP request carrying the session.
    """
    codx_junior_session = request.state.codx_junior_session
    logger.info("**** API:knowledge_reload_path %s", knowledge_reload_path)
    codx_junior_session.index_knowledge_source(sources=[knowledge_reload_path.path])


@router.post("/delete")
def api_knowledge_delete_path(
    knowledge_delete_sources: KnowledgeDeleteSources,
    request: Request,
):
    """
    Delete knowledge documents for specific source paths.

    Args:
        knowledge_delete_sources: Object containing the list of source paths to delete.
        request: Incoming HTTP request carrying the session.

    Returns:
        Result of the delete operation.
    """
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.delete_knowledge_source(
        sources=knowledge_delete_sources.sources
    )


@router.delete("/delete")
def api_knowledge_reload_all(request: Request):
    """
    Delete all knowledge documents for the current project.

    Returns:
        Result of the full-delete operation.
    """
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.delete_knowledge()


@router.post("/reload-search")
async def api_knowledge_search_endpoint(
    knowledge_search_params: KnowledgeSearch,
    request: Request,
):
    """
    Search the knowledge base using the provided parameters.

    Args:
        knowledge_search_params: Query and options for the knowledge search.
        request: Incoming HTTP request carrying the session.

    Returns:
        List of matching knowledge documents.
    """
    logger.info("API:knowledge_search_endpoint")
    codx_junior_session = request.state.codx_junior_session
    return await codx_junior_session.knowledge_search(
        knowledge_search=knowledge_search_params
    )


@router.get("/status")
def api_knowledge_status(request: Request):
    """
    Return the current knowledge base status for the project.

    Returns:
        Knowledge status dict.
    """
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.check_knowledge_status()

@router.get("/files")
def api_knowledge_files(request: Request):
    """
    Return the current knowledge base status for the project.

    Returns:
        Knowledge status dict.
    """
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.get_knowledge_files()


@router.get("/keywords")
def api_get_keywords(request: Request):
    """
    Retrieve knowledge-base keywords matching an optional query string.

    Query params:
        query (str): Optional search term to filter keywords.

    Returns:
        List of matching keyword strings.
    """
    codx_junior_session = request.state.codx_junior_session
    query = request.query_params.get("query")
    return codx_junior_session.get_keywords(query=query)


@router.post("/keywords")
def api_extract_tags(doc: Document, request: Request):
    """
    Extract and store keyword tags from the given document.

    Args:
        doc: Document whose content will be analysed for tags.
        request: Incoming HTTP request carrying the session.

    Returns:
        Updated document dict with populated keyword metadata.
    """
    codx_junior_session = request.state.codx_junior_session
    logger.info("Extract keywords from %s", doc)
    doc = codx_junior_session.extract_tags(doc=doc)
    return doc.__dict__


@router.get("/metrics")
def api_knowledge_metrics(request: Request):
    """
    Return detailed collection-level metrics from the underlying Milvus store.

    Includes row count, load state, schema information, index metadata,
    and partition details.

    Returns:
        Metrics dict produced by ``KnowledgeDB.get_collection_metrics()``.

    Diagram:
    sequenceDiagram
        participant Client
        participant Router as KnowledgeRouter
        participant Session as CODXJuniorSession
        participant KDB as KnowledgeDB

        Client->>Router: GET /api/knowledge/metrics
        Router->>Session: get session from request state
        Session->>KDB: get_collection_metrics()
        KDB-->>Session: metrics dict
        Session-->>Router: metrics dict
        Router-->>Client: JSON metrics
    """
    codx_junior_session = request.state.codx_junior_session
    knowledge_db = codx_junior_session.get_knowledge_db()
    logger.info(
        "Fetching knowledge metrics for project '%s'",
        codx_junior_session.settings.project_name,
    )
    return knowledge_db.get_collection_metrics()


@router.get("/summary")
def api_knowledge_summary(request: Request):
    """
    Return the project summary as plain Markdown text.

    The summary is retrieved from the knowledge base via
    ``get_knowledge().get_project_summary()``.

    Returns:
        Plain-text Markdown content of the project summary,
        or an empty string when no summary is available yet.

    Diagram:
    sequenceDiagram
        participant Client
        participant Router as KnowledgeRouter
        participant Session as CODXJuniorSession
        participant KB as Knowledge

        Client->>Router: GET /api/knowledge/summary
        Router->>Session: get session from request state
        Session->>KB: get_knowledge()
        KB-->>Session: Knowledge instance
        Session->>KB: get_project_summary()
        KB-->>Session: markdown string
        Session-->>Router: markdown string
        Router-->>Client: text/markdown response
    """
    codx_junior_session = request.state.codx_junior_session
    logger.info(
        "Fetching project summary for project '%s'",
        codx_junior_session.settings.project_name,
    )
    knowledge = codx_junior_session.get_knowledge()
    summary: str = knowledge.get_project_summary() or ""
    return PlainTextResponse(content=summary, media_type="text/markdown")


@router.get("/summary/json")
def api_knowledge_summary_json(request: Request):
    """
    Return the project summary as a JSON object.

    Useful for clients that prefer a structured response over plain text.

    Returns:
        JSON object with a single ``summary`` key containing the Markdown
        content, e.g. ``{"summary": "# My Project\\n..."}``.

    Diagram:
    sequenceDiagram
        participant Client
        participant Router as KnowledgeRouter
        participant Session as CODXJuniorSession
        participant KB as Knowledge

        Client->>Router: GET /api/knowledge/summary/json
        Router->>Session: get session from request state
        Session->>KB: get_knowledge()
        KB-->>Session: Knowledge instance
        Session->>KB: get_project_summary()
        KB-->>Session: markdown string
        Session-->>Router: { summary: markdown string }
        Router-->>Client: JSON response
    """
    codx_junior_session = request.state.codx_junior_session
    logger.info(
        "Fetching project summary (JSON) for project '%s'",
        codx_junior_session.settings.project_name,
    )
    knowledge = codx_junior_session.get_knowledge()
    summary: str = knowledge.get_project_summary() or ""
    return JSONResponse(content={"summary": summary})


@router.post("/summary/rebuild")
def api_knowledge_summary_rebuild(
    request: Request,
    user: CodxUser = Depends(require_admin),
):
    """
    Trigger a full rebuild of the project summary (admin only).

    Forces ``Knowledge.build_project_summary`` to regenerate the summary
    document from scratch by reading all currently indexed sources.

    Returns:
        JSON object with:
          - ``summary``: The newly generated Markdown summary string.
          - ``project``: The project name for confirmation.

    Diagram:
    sequenceDiagram
        participant Client
        participant Router as KnowledgeRouter
        participant Auth as require_admin
        participant Session as CODXJuniorSession
        participant KB as Knowledge

        Client->>Router: POST /api/knowledge/summary/rebuild
        Router->>Auth: validate admin role
        Auth-->>Router: CodxUser (admin)
        Router->>Session: get session from request state
        Session->>KB: get_knowledge()
        KB-->>Session: Knowledge instance
        Session->>KB: build_project_summary()
        KB-->>Session: updated summary string
        Session-->>Router: updated summary string
        Router-->>Client: { summary, project }
    """
    codx_junior_session = request.state.codx_junior_session
    project_name = codx_junior_session.settings.project_name
    logger.info(
        "Admin '%s' triggered summary rebuild for project '%s'",
        user.username,
        project_name,
    )
    knowledge = codx_junior_session.get_knowledge()
    updated_summary: str = knowledge.build_project_summary() or ""
    return JSONResponse(content={"summary": updated_summary, "project": project_name})


@router.delete("/summary")
def api_knowledge_summary_delete(
    request: Request,
    user: CodxUser = Depends(require_admin),
):
    """
    Delete the persisted project summary file (admin only).

    Removes the on-disk summary so the next rebuild starts from a clean slate.

    Returns:
        JSON object with a confirmation ``message`` and the ``project`` name.

    Diagram:
    sequenceDiagram
        participant Client
        participant Router as KnowledgeRouter
        participant Auth as require_admin
        participant Session as CODXJuniorSession
        participant KB as Knowledge

        Client->>Router: DELETE /api/knowledge/summary
        Router->>Auth: validate admin role
        Auth-->>Router: CodxUser (admin)
        Router->>Session: get session from request state
        Session->>KB: get_knowledge()
        KB-->>Session: Knowledge instance
        Router->>KB: delete summary_file_path if exists
        KB-->>Router: done
        Router-->>Client: { message, project }
    """
    import os

    codx_junior_session = request.state.codx_junior_session
    project_name = codx_junior_session.settings.project_name
    knowledge = codx_junior_session.get_knowledge()

    summary_path = knowledge.summary_file_path
    if os.path.isfile(summary_path):
        os.remove(summary_path)
        logger.info(
            "Admin '%s' deleted summary file '%s' for project '%s'",
            user.username,
            summary_path,
            project_name,
        )
        message = f"Summary file deleted: {summary_path}"
    else:
        logger.info(
            "Admin '%s' requested summary deletion but no file found at '%s' for project '%s'",
            user.username,
            summary_path,
            project_name,
        )
        message = "No summary file found; nothing to delete."

    return JSONResponse(content={"message": message, "project": project_name})


@router.get("/ai-search")
async def api_knowledge_ai_search(
    request: Request,
):
    """
    Perform an iterative AI-driven search over the project knowledge base.

    The endpoint delegates to ``KnowledgeAISearch.ai_search`` which runs
    multiple search-and-check cycles until the AI determines that the
    retrieved documents are sufficient to answer the question, or until
    the maximum number of iterations is reached.

    Request body (``KnowledgeSearch``):
        - ``query`` (str): Natural-language question from the user.
        - ``max_iterations`` (int, optional): Maximum search cycles.
          Defaults to ``DEFAULT_AI_SEARCH_MAX_ITERATIONS`` (3).

    Returns:
        JSON-serialised ``AISearchResult`` containing:
          - ``user_query``: The original question.
          - ``max_iterations``: The configured iteration cap.
          - ``total_iterations``: Iterations actually performed.
          - ``answer``: AI-generated answer grounded in retrieved documents.
          - ``queries_used``: All search queries executed (initial + refined).
          - ``documents``: Supporting document chunks with metadata and scores.

    Raises:
        500: If an unexpected error occurs during the AI search pipeline.

    Diagram:
    sequenceDiagram
        participant Client
        participant Router as KnowledgeRouter
        participant KAIS as KnowledgeAISearch
        participant KB as Knowledge (KnowledgeDB)
        participant AI

        Client->>Router: POST /api/knowledge/ai-search { query, max_iterations }
        Router->>KAIS: ai_search(user_query, max_iterations)
        loop Until sufficient or max_iterations
            KAIS->>KB: search(current_queries)
            KB-->>KAIS: List[Document]
            KAIS->>AI: _check_sufficiency(query, documents)
            AI-->>KAIS: { is_sufficient, reasoning, refined_queries }
        end
        KAIS->>AI: _generate_final_answer(query, documents)
        AI-->>KAIS: answer string
        KAIS-->>Router: AISearchResult
        Router-->>Client: JSON AISearchResult
    """
    query = request.query_params.get("query")
    max_iterations: int = request.query_params.get("max_iterations")

    logger.info(
        "API:knowledge_ai_search | project='%s' | query='%s' | max_iterations=%d",
        request.state.codx_junior_session.settings.project_name,
        query,
        max_iterations,
    )

    settings = request.state.codx_junior_session.settings
    searcher = KnowledgeAISearch(settings=settings)

    result: AISearchResult = await searcher.ai_search(
        user_query=query,
        max_iterations=max_iterations,
    )

    logger.info(
        "API:knowledge_ai_search complete | total_iterations=%d | documents=%d | queries=%d",
        result.total_iterations,
        len(result.documents),
        len(result.queries_used),
    )

    return JSONResponse(content=result.to_dict())


@router.post("/agent-search")
async def api_knowledge_agent_search(
    request: Request,
):
    """
    Perform an AI-assisted agent search to generate a resource plan.

    The endpoint delegates to ``KnowledgeAISearch.agent_search`` which identifies
    all project files an agent needs to read, modify, or create to fulfil a user
    request.

    Unlike ``/ai-search`` which answers questions, this generates a structured
    **resource plan** optimized for agent task execution.

    Request query params:
        - ``request`` (str): Natural-language request from the user (e.g. "Add contacts section").
        - ``max_iterations`` (int, optional): Maximum search cycles (default 3).

    Returns:
        JSON-serialised ``AgentResourcePlan`` containing:
          - ``overview``: Narrative description of what needs doing.
          - ``files_to_read``: Files the agent should inspect for context.
          - ``files_to_modify``: Files to edit, with suggested actions and reasons.
          - ``files_to_create``: New files that should be created.
          - ``additional_context``: Caveats, dependencies, follow-up notes.
          - ``all_relevant_sources``: Flat deduplicated list of all file paths.
          - ``documents``: Supporting document chunks with metadata and scores.
          - ``queries_used``: All search queries executed (initial + refined).
          - ``projects_searched``: Names of all projects searched.
          - ``total_iterations``: Search+check cycles actually performed.

    Raises:
        500: If an unexpected error occurs during the agent search pipeline.

    Diagram:
    sequenceDiagram
        participant Client
        participant Router as KnowledgeRouter
        participant KAIS as KnowledgeAISearch
        participant KB as Knowledge
        participant AI

        Client->>Router: POST /api/knowledge/agent-search { request, max_iterations }
        Router->>KAIS: agent_search(user_request, max_iterations)
        loop Until sufficient or max_iterations
            KAIS->>KB: search(current_queries)
            KB-->>KAIS: List[Document]
            KAIS->>AI: _check_agent_sufficiency(request, documents, summary)
            AI-->>KAIS: { is_sufficient, reasoning, refined_queries }
        end
        KAIS->>AI: _generate_agent_resource_plan(request, documents, summary)
        AI-->>KAIS: AgentResourcePlan
        KAIS-->>Router: AgentResourcePlan
        Router-->>Client: JSON AgentResourcePlan
    """
    user_request = request.query_params.get("request")
    max_iterations: int = request.query_params.get("max_iterations")

    logger.info(
        "API:knowledge_agent_search | project='%s' | request='%s' | max_iterations=%d",
        request.state.codx_junior_session.settings.project_name,
        user_request,
        max_iterations,
    )

    settings = request.state.codx_junior_session.settings
    searcher = KnowledgeAISearch(settings=settings)

    plan = await searcher.agent_search(
        user_request=user_request,
        max_iterations=max_iterations,
    )

    logger.info(
        "API:knowledge_agent_search complete | total_iterations=%d | documents=%d | "
        "queries=%d | files_to_read=%d | files_to_modify=%d | files_to_create=%d",
        plan.total_iterations,
        len(plan.documents),
        len(plan.queries_used),
        len(plan.files_to_read),
        len(plan.files_to_modify),
        len(plan.files_to_create),
    )

    return JSONResponse(content=plan.to_dict())


@sio.on("codx-junior-index-knowledge")
@sio_api_endpoint
async def sio_index_knowledge(
    sid, 
    data: dict, 
    codxjunior_session: CODXJuniorSession
):
    """
    Index knowledge files in the background via socket event with progress reporting.

    Expected data:
        - file_paths: List[str] - Absolute paths to files/folders to index
        - codx_path: str - Project path

    Emitted events:
        - ``codx-junior-index-progress-started``: Indexing started
        - ``codx-junior-index-progress-document-processing``: Processing document
        - ``codx-junior-index-progress-document-enriched``: Document enriched
        - ``codx-junior-index-progress-document-indexed``: Document indexed
        - ``codx-junior-index-progress-batch-complete``: Batch finished
        - ``codx-junior-index-progress-completed``: Full indexing done
        - ``codx-junior-index-error``: Error occurred

    Returns:
        Result of the indexing operation.
    """
    file_paths = data.get("file_paths", [])
    logger.info(
        "Socket: index_knowledge | files=%d | project=%s",
        len(file_paths),
        codxjunior_session.settings.project_name,
    )

    # Create progress callback for this session
    channel = SessionChannel(sio=sio, sid=sid)
    progress_callback = SocketProgressCallback(channel=channel)

    try:
        # Notify client that indexing started
        await progress_callback.on_progress(
            ProgressEventType.STARTED,
            {
                "total_files": len(file_paths),
                "message": f"Starting indexing of {len(file_paths)} file(s)",
            }
        )

        # Get knowledge instance with callback
        knowledge = codxjunior_session.get_knowledge()
        
        # Load documents with progress reporting
        all_documents = []
        for idx, file_path in enumerate(file_paths):
            await progress_callback.on_progress(
                ProgressEventType.DOCUMENT_PROCESSING,
                {
                    "file_index": idx,
                    "total_files": len(file_paths),
                    "current_file": file_path,
                    "message": f"Loading {file_path}...",
                }
            )
            
            try:
                documents = knowledge.loader.load(path=file_path)
                all_documents.extend(documents)
            except Exception as ex:
                await progress_callback.on_error(
                    ex,
                    {
                        "file_path": file_path,
                        "stage": "loading",
                    }
                )

        # Index all documents with progress reporting
        if all_documents:
            await knowledge.index_documents(
                documents=all_documents,
                raiseIfError=False,
                callback=progress_callback,
            )

        # Final success event
        await progress_callback.on_progress(
            ProgressEventType.COMPLETED,
            {
                "status": "success",
                "documents_indexed": len(all_documents),
                "files_indexed": len(file_paths),
                "message": f"Successfully indexed {len(file_paths)} file(s) ({len(all_documents)} documents)",
            }
        )

        logger.info(
            "Socket: index_knowledge complete | files=%d | documents=%d",
            len(file_paths),
            len(all_documents),
        )
        
        return {
            "status": "success",
            "files_indexed": len(file_paths),
            "documents_indexed": len(all_documents),
        }

    except Exception as ex:
        logger.exception("Error indexing knowledge via socket")
        await progress_callback.on_error(
            ex,
            {
                "files": len(file_paths),
                "stage": "overall",
            }
        )
        return {"error": str(ex)}


@sio.on("codx-junior-agent-search")
@sio_api_endpoint
async def sio_agent_search(
    sid,
    data: dict,
    codxjunior_session: CODXJuniorSession
):
    """
    Perform an AI-assisted agent search via socket event (background task).

    This allows long-running agent resource planning to happen asynchronously
    without blocking the client connection.

    Expected data:
        - request: str - Natural-language request describing the task
        - max_iterations: int - Maximum search cycles (optional, default 3)

    Emitted events:
        - ``codx-junior-agent-search-progress``: Search iteration updates
        - ``codx-junior-agent-search-complete``: Plan generation successful
        - ``codx-junior-agent-search-error``: Error occurred during search

    Progress event payload:
    {
        "iteration": int,
        "documents_found": int,
        "is_sufficient": bool,
        "message": str
    }

    Complete event payload:
    {
        "status": "success",
        "plan": AgentResourcePlan.to_dict(),
        "message": "Agent resource plan generated successfully"
    }

    Error event payload:
    {
        "status": "error",
        "message": str
    }
    """
    user_request = data.get("request", "")
    max_iterations = data.get("max_iterations", 3)

    logger.info(
        "Socket: agent_search | request='%s' | max_iterations=%d | project=%s",
        user_request,
        max_iterations,
        codxjunior_session.settings.project_name,
    )

    channel = SessionChannel(sio=sio, sid=sid)

    try:
        settings = codxjunior_session.settings
        searcher = KnowledgeAISearch(settings=settings)

        # Perform the agent search
        plan = await searcher.agent_search(
            user_request=user_request,
            max_iterations=max_iterations,
        )

        # Send completion event with the full plan
        channel.send_event("codx-junior-agent-search-complete", {
            "status": "success",
            "plan": plan.to_dict(),
            "message": f"Agent resource plan generated successfully "
                      f"({plan.total_iterations} iterations, "
                      f"{len(plan.documents)} documents, "
                      f"{len(plan.files_to_read)} files to read, "
                      f"{len(plan.files_to_modify)} files to modify, "
                      f"{len(plan.files_to_create)} files to create)",
        })

        logger.info(
            "Socket: agent_search complete | project=%s | iterations=%d | "
            "files_to_read=%d | files_to_modify=%d | files_to_create=%d",
            codxjunior_session.settings.project_name,
            plan.total_iterations,
            len(plan.files_to_read),
            len(plan.files_to_modify),
            len(plan.files_to_create),
        )

    except Exception as ex:
        logger.exception("Error during agent search via socket")
        channel.send_event("codx-junior-agent-search-error", {
            "status": "error",
            "message": str(ex),
        })

# Made with ❤️ by codx-junior