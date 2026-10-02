"""
Tutorial Tools

Tools for managing tutorial content with nested chapter structure.
Provides operations for querying, creating, modifying, and deleting chapters.

Made with ❤️ by codx-junior
"""

import logging
from typing import TYPE_CHECKING, Optional, List

from .model import ToolResponse
from codx.junior.db import Message
from codx.junior.tutorial_manager import TutorialManager

if TYPE_CHECKING:
    from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)


def tutorial_definition(
    tutorial_id: str,
    settings: Optional["CODXJuniorSettings"] = None,
) -> dict:
    """
    Get the complete tutorial definition as JSON.
    
    Returns a hierarchical representation of the tutorial including all
    chapters, nested content, messages, and metadata.
    
    Args:
        tutorial_id: ID of the root tutorial chat (mode='tutorial').
        settings: CODXJuniorSettings instance.
    
    Returns:
        Dict with tutorial definition (chapters, content, metadata).
    
    Raises:
        ValueError: If tutorial not found or not marked as mode='tutorial'.
        RuntimeError: If chat manager is unavailable.
    
    Made with ❤️ by codx-junior
    """
    if not settings:
        raise ValueError("tutorial_definition requires settings parameter")
    
    try:
        tutorial_manager = TutorialManager(settings=settings)
        
        logger.info("Getting tutorial definition for '%s'", tutorial_id)
        definition = tutorial_manager.tutorial_definition(tutorial_id)
        
        return definition
    
    except Exception as ex:
        logger.exception("tutorial_definition error: %s", ex)
        raise RuntimeError(f"Failed to get tutorial definition: {ex}") from ex


def create_chapter(
    tutorial_id: str,
    name: str,
    description: str = "",
    content: str = "",
    tags: Optional[List[str]] = None,
    settings: Optional["CODXJuniorSettings"] = None,
) -> ToolResponse:
    """
    Create a new chapter in a tutorial.
    
    Args:
        tutorial_id: ID of parent tutorial/chapter.
        name: Chapter title.
        description: Chapter description.
        content: Initial message content.
        tags: Chapter tags.
        settings: CODXJuniorSettings instance.
    
    Returns:
        ToolResponse with creation status and chapter details.
    
    Made with ❤️ by codx-junior
    """
    if not settings:
        raise ValueError("create_chapter requires settings parameter")
    
    try:
        tutorial_manager = TutorialManager(settings=settings)

        chapter = tutorial_manager.create_chapter(
            tutorial_id=tutorial_id,
            name=name,
            description=description,
            content=content,
            tags=tags or [],
        )
        
        logger.info("Created chapter '%s' (id=%s)", name, chapter.id)
        
        return ToolResponse(
            user_response=f"✅ Chapter '{name}' created successfully.",
            llm_response=f"Chapter created: {chapter.name} (ID: {chapter.id}, Index: {chapter.child_index})",
        )
    
    except Exception as ex:
        logger.exception("create_chapter error: %s", ex)
        raise RuntimeError(f"Failed to create chapter: {ex}") from ex


def modify_chapter(
    chapter_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    content: Optional[str] = None,
    settings: Optional["CODXJuniorSettings"] = None,
) -> ToolResponse:
    """
    Modify a chapter's content or metadata.
    
    Args:
        chapter_id: ID of the chapter to modify.
        name: New chapter title.
        description: New description.
        tags: New tags.
        content: Message content to append.
        settings: CODXJuniorSettings instance.
    
    Returns:
        ToolResponse with modification status.
    
    Made with ❤️ by codx-junior
    """
    if not settings:
        raise ValueError("modify_chapter requires settings parameter")
    
    try:
        tutorial_manager = TutorialManager(settings=settings)

        # Build add_message if content provided
        add_message = None
        if content:
            add_message = Message(role="assistant", content=content)
        
        chapter = tutorial_manager.modify_chapter(
            chapter_id=chapter_id,
            name=name,
            description=description,
            tags=tags,
            add_message=add_message,
        )
        
        logger.info("Modified chapter '%s'", chapter_id)
        
        return ToolResponse(
            user_response=f"✅ Chapter updated successfully.",
            llm_response=f"Chapter modified: {chapter.name} (ID: {chapter.id})",
        )
    
    except Exception as ex:
        logger.exception("modify_chapter error: %s", ex)
        raise RuntimeError(f"Failed to modify chapter: {ex}") from ex


def delete_chapter(
    chapter_id: str,
    settings: Optional["CODXJuniorSettings"] = None,
) -> ToolResponse:
    """
    Delete a chapter from the tutorial.
    
    The main tutorial root (mode='tutorial' with no parent) cannot be deleted.
    
    Args:
        chapter_id: ID of the chapter to delete.
        settings: CODXJuniorSettings instance.
    
    Returns:
        ToolResponse with deletion status.
    
    Raises:
        ValueError: If chapter is tutorial root or not found.
    
    Made with ❤️ by codx-junior
    """
    if not settings:
        raise ValueError("delete_chapter requires settings parameter")
    
    try:
        tutorial_manager = TutorialManager(settings=settings)
        
        tutorial_manager.delete_chapter(chapter_id)
        
        logger.info("Deleted chapter '%s'", chapter_id)
        
        return ToolResponse(
            user_response=f"✅ Chapter deleted successfully.",
            llm_response=f"Chapter with ID {chapter_id} has been removed from the tutorial.",
        )
    
    except Exception as ex:
        logger.exception("delete_chapter error: %s", ex)
        raise RuntimeError(f"Failed to delete chapter: {ex}") from ex

# Made with ❤️ by codx-junior