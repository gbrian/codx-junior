"""``web_search`` tool: the configured search chain, formatted for the model.

The providers (SearXNG, Brave, Tavily, DuckDuckGo) live in
:mod:`codx.junior.web.search_backends`; this module keeps the tool contract and
the dual response (user facing text + short LLM feedback).

The module and the function keep their original names because the tool registry
imports them, but the behaviour is no longer DuckDuckGo-only: DuckDuckGo is the
last backend of the chain, used when nothing else is configured.

Made with ❤️ by codx-junior
"""

import logging
from typing import Optional, Union, Literal

from codx.junior.web.search_backends import search_web

from .model import ToolResponse

logger = logging.getLogger(__name__)

WEB_SEARCH_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web and return titles, URLs and snippets. "
            "The backend is chosen by the deployment (SearXNG, Brave or Tavily) "
            "and falls back to DuckDuckGo scraping, so an empty result set can "
            "mean the backend is unavailable: read the 'Errors' line before "
            "concluding that something does not exist. "
            "Supports multiple search types: web, news, images."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query."
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of search results to return (default: 5)."
                },
                "search_type": {
                    "type": "string",
                    "enum": ["web", "news", "images"],
                    "description": "Type of search: 'web' (default), 'news', or 'images'."
                },
                "provider": {
                    "type": "string",
                    "enum": ["searxng", "brave", "tavily", "ddgs"],
                    "description": (
                        "Optional: force one backend instead of the configured "
                        "chain (useful when a backend keeps failing)."
                    )
                }
            },
            "required": ["query"]
        }
    }
}

#: Backwards compatible alias: the tool registry imports this name.
DUCKDUCKGO_SEARCH_TOOL_JSON = WEB_SEARCH_TOOL_JSON


def _format_hits(response) -> str:
    """Render the hits as the numbered list the model expects."""
    blocks = []
    for index, hit in enumerate(response.hits, 1):
        lines = [f"[{index}] {hit.title}", f"    URL: {hit.url}"]
        meta = [value for value in (hit.engine, hit.published) if value]
        if meta:
            lines.insert(1, f"    Source: {' | '.join(meta)}")
        if hit.snippet:
            lines.append(f"    {hit.snippet}")
        if hit.image_url and response.search_type == "images":
            lines.append(f"    Image: {hit.image_url}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def web_search(
    query: str,
    max_results: int = 5,
    search_type: Literal["web", "news", "images"] = "web",
    provider: Optional[str] = None,
) -> Union[str, ToolResponse]:
    """Search the web with the configured provider chain.

    Args:
        query: The search query.
        max_results: Maximum number of search results to return.
        search_type: Type of search - 'web', 'news', or 'images' (default: 'web').
        provider: Optional backend name to bypass the configured chain.

    Returns:
        A ToolResponse object containing the search results or an error message.
    """
    response_obj = ToolResponse(user_response="", llm_response="")

    try:
        response_obj.add_log(
            f"Search initiated: query='{query}', max_results={max_results}, "
            f"type='{search_type}', provider='{provider or 'auto'}'"
        )

        if search_type not in ("web", "news", "images"):
            raise ValueError(
                f"Invalid search_type '{search_type}'. Must be 'web', 'news', or 'images'."
            )
        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        results = search_web(
            query,
            max_results=max_results,
            search_type=search_type,
            provider=provider,
        )

        for error in results.errors:
            response_obj.add_log(f"Backend failure: {error}", level="WARNING")

        if results.is_empty:
            errors = "; ".join(results.errors) or "no backend configured"
            response_obj.add_log(f"No results found for query '{query}'", level="WARNING")
            response_obj.user_response = (
                f"No results found for '{query}' ({search_type} search). Errors: {errors}"
            )
            response_obj.llm_response = (
                f"Web {search_type.upper()} search for '{query}': no results. "
                f"Attempts: {errors}. An empty answer is not proof that nothing exists."
            )
            return response_obj

        formatted = _format_hits(results)
        response_obj.user_response = (
            f"Web {search_type.upper()} Search Results for '{query}' "
            f"(backend: {results.backend}):\n\n{formatted}"
        )
        response_obj.llm_response = (
            f"Web {search_type.upper()} search for '{query}': "
            f"{len(results.hits)} results from {results.backend}."
        )
        if results.errors:
            response_obj.llm_response += f" Other backends failed: {'; '.join(results.errors)}"
        response_obj.add_log(
            f"Search completed with {len(results.hits)} results from {results.backend}"
        )
        return response_obj

    except ValueError as ex:
        logger.error(f"Validation error during web search: {ex}")
        response_obj.add_log(f"Validation error: {ex}", level="ERROR")
        response_obj.user_response = f"Search validation error: {ex}"
        response_obj.llm_response = f"Web Search Validation Error: {ex}"
        return response_obj

    except Exception as ex:
        logger.exception(f"Unexpected error during web search: {ex}")
        response_obj.add_log(f"Error: {type(ex).__name__}: {ex}", level="ERROR")
        response_obj.user_response = f"An error occurred during web search: {ex}"
        response_obj.llm_response = f"Web Search Error: {ex}"
        return response_obj


def duckduckgo_search(
    query: str,
    max_results: int = 5,
    search_type: Literal["web", "news", "images"] = "web",
    provider: Optional[str] = None,
) -> Union[str, ToolResponse]:
    """Deprecated alias of :func:`web_search`, kept for the tool registry."""
    return web_search(
        query=query,
        max_results=max_results,
        search_type=search_type,
        provider=provider,
    )

# Made with ❤️ by codx-junior