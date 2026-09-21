import logging
from typing import Optional, Union, Literal
from ddgs import DDGS

from .model import ToolResponse, ToolSettings

logger = logging.getLogger(__name__)

DUCKDUCKGO_SEARCH_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Perform a web search using DuckDuckGo. "
            "Returns search results with titles, URLs, and snippets. "
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
                }
            },
            "required": ["query"]
        }
    }
}


def duckduckgo_search(
    query: str,
    max_results: int = 5,
    search_type: Literal["web", "news", "images"] = "web"
) -> Union[str, ToolResponse]:
    """
    Perform a web search using DuckDuckGo with DDGS library.

    Args:
        query: The search query.
        max_results: Maximum number of search results to return.
        search_type: Type of search - 'web', 'news', or 'images' (default: 'web').

    Returns:
        A ToolResponse object containing the search results or an error message.
    """
    # Initialize response object for logging
    response_obj = ToolResponse(
        user_response="",
        llm_response=""
    )
    
    try:
        response_obj.add_log(
            f"Search initiated: query='{query}', max_results={max_results}, type='{search_type}'"
        )
        
        # Validate search type
        if search_type not in ["web", "news", "images"]:
            raise ValueError(f"Invalid search_type '{search_type}'. Must be 'web', 'news', or 'images'.")
        
        # Validate query
        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")
        
        # Initialize DDGS with timeout
        ddgs = DDGS(timeout=10)
        response_obj.add_log(f"DDGS instance initialized with 10s timeout")
        
        results = []
        
        # Perform search based on type
        if search_type == "web":
            response_obj.add_log(f"Executing web search...")
            search_results = ddgs.text(query, max_results=max_results)
            response_obj.add_log(f"Web search returned {len(search_results)} results")
            
            for idx, result in enumerate(search_results, 1):
                formatted_result = f"[{idx}] {result['title']}\n    URL: {result['href']}\n    {result['body'][:150]}..."
                results.append(formatted_result)
                response_obj.add_log(f"Result {idx}: {result['title'][:50]}...")
        
        elif search_type == "news":
            response_obj.add_log(f"Executing news search...")
            search_results = ddgs.news(query, max_results=max_results)
            response_obj.add_log(f"News search returned {len(search_results)} results")
            
            for idx, article in enumerate(search_results, 1):
                source = article.get('source', 'Unknown')
                date = article.get('date', 'Unknown')
                formatted_result = f"[{idx}] {article['title']}\n    Source: {source} | Date: {date}\n    URL: {article['url']}\n    {article.get('body', '')[:150]}..."
                results.append(formatted_result)
                response_obj.add_log(f"Article {idx}: {article['title'][:50]}... ({source})")
        
        elif search_type == "images":
            response_obj.add_log(f"Executing image search...")
            search_results = ddgs.images(query, max_results=max_results)
            response_obj.add_log(f"Image search returned {len(search_results)} results")
            
            for idx, image in enumerate(search_results, 1):
                title = image.get('title', 'Untitled')
                image_url = image['image']
                formatted_result = f"[{idx}] {title}\n    Image URL: {image_url[:80]}..."
                results.append(formatted_result)
                response_obj.add_log(f"Image {idx}: {title[:50]}...")
        
        # Handle empty results
        if not results:
            response_obj.add_log(f"No results found for query '{query}'", level="WARNING")
            response_obj.user_response = f"No results found for '{query}' on DuckDuckGo ({search_type} search)."
            response_obj.llm_response = f"DuckDuckGo {search_type.upper()} Search for '{query}': No results found."
            return response_obj
        
        # Format final response
        formatted_results = "\n\n".join(results)
        response_obj.user_response = f"DuckDuckGo {search_type.upper()} Search Results for '{query}':\n\n{formatted_results}"
        response_obj.llm_response = f"DuckDuckGo {search_type.upper()} Search for '{query}': Found {len(results)} results."
        response_obj.add_log(f"Search completed successfully with {len(results)} {search_type} results")
        
        return response_obj

    except ValueError as e:
        logger.error(f"Validation error during DuckDuckGo search: {e}")
        response_obj.add_log(f"Validation error: {e}", level="ERROR")
        response_obj.user_response = f"Search validation error: {e}"
        response_obj.llm_response = f"DuckDuckGo Search Validation Error: {e}"
        return response_obj
    
    except Exception as e:
        logger.error(f"Unexpected error during DuckDuckGo search: {e}")
        response_obj.add_log(f"Error: {type(e).__name__}: {e}", level="ERROR")
        response_obj.user_response = f"An error occurred during DuckDuckGo search: {e}"
        response_obj.llm_response = f"DuckDuckGo Search Error: {e}"
        return response_obj

# Made with ❤️ by codx-junior