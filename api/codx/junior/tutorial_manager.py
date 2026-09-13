"""
Tutorial Management Module

Handles tutorial operations including definition retrieval, chapter creation,
modification, and deletion. Uses chat and message resources to create
learning content with nested hierarchies.

A tutorial is a chat with `mode='tutorial'` that can have child chats
(chapters) via parent_id references, ordered by child_index.

Made with ❤️ by codx-junior
"""

import logging
from typing import Dict, List, Optional, Any

from codx.junior.db import Chat, Message
from codx.junior.settings import CODXJuniorSettings
from codx.junior.chat_manager import ChatManager

logger = logging.getLogger(__name__)


class TutorialManager:
    """
    Manages tutorial chats and their nested chapter structure.
    
    A tutorial is a root chat with `mode='tutorial'` and child chats representing 
    chapters, ordered by `child_index`.
    
    All tutorial operations use the standard Chat and Message resources.
    """

    def __init__(self, settings: CODXJuniorSettings):
        """
        Initialize the tutorial manager with a chat manager instance.
        
        :param chat_manager: ChatManager instance for persistence operations.
        """
        self.settings = settings
        self.chat_manager = ChatManager(settings=settings)

    def tutorial_definition(self, tutorial_id: str) -> Dict[str, Any]:
        """
        Return a JSON object with the complete tutorial definition by recursively
        reading the chat hierarchy.
        
        Reads the root tutorial chat and all nested chapters in order (by child_index),
        building a hierarchical representation with messages and metadata.
        
        :param tutorial_id: ID of the root tutorial chat.
        :return: Dict with tutorial structure including chapters and content.
        :raises ValueError: If tutorial_id not found or not marked as tutorial mode.
        """
        tutorial_chat = self.chat_manager.find_by_id(tutorial_id)
        if not tutorial_chat:
            raise ValueError(f"Tutorial chat '{tutorial_id}' not found")
        
        if tutorial_chat.mode != 'tutorial':
            raise ValueError(
                f"Chat '{tutorial_id}' mode is '{tutorial_chat.mode}', not 'tutorial'"
            )
        
        logger.info("Building tutorial definition for '%s'", tutorial_chat.name)
        
        return {
            "id": tutorial_chat.id,
            "name": tutorial_chat.name,
            "description": tutorial_chat.description,
            "mode": tutorial_chat.mode,
            "tags": tutorial_chat.tags or [],
            "created_at": tutorial_chat.created_at,
            "updated_at": tutorial_chat.updated_at,
            "chapters": self._build_chapter_list(tutorial_id),
        }

    def _build_chapter_list(self, parent_id: str) -> List[Dict[str, Any]]:
        """
        Recursively build a list of chapters for a tutorial or parent chapter.
        
        Sorts children by child_index (ascending).
        
        :param parent_id: ID of the tutorial or parent chapter.
        :return: Ordered list of chapter dicts with content.
        """
        # Find all child chats sorted by child_index
        all_chats = self.chat_manager.list_chats()
        child_chats = sorted(
            [c for c in all_chats if c.parent_id == parent_id],
            key=lambda x: x.child_index or 0
        )
        
        chapters = []
        for child_chat in child_chats:
            chapter_dict = {
                "id": child_chat.id,
                "title": child_chat.name,
                "description": child_chat.description,
                "mode": child_chat.mode,
                "child_index": child_chat.child_index,
                "tags": child_chat.tags or [],
                "message_count": len(child_chat.messages),
                "created_at": child_chat.created_at,
                "updated_at": child_chat.updated_at,
                "messages": [
                    {
                        "id": msg.doc_id,
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at,
                    }
                    for msg in child_chat.messages if not msg.hide
                ],
                "nested_chapters": self._build_chapter_list(child_chat.id),
            }
            chapters.append(chapter_dict)
        
        return chapters

    def create_chapter(
        self,
        tutorial_id: str,
        name: str,
        description: str = "",
        content: str = "",
        tags: Optional[List[str]] = None,
        child_index: Optional[int] = None,
    ) -> Chat:
        """
        Create a new chapter (child chat) within a tutorial.
        
        :param tutorial_id: ID of the parent tutorial or chapter.
        :param name: Chapter title.
        :param description: Chapter description.
        :param content: Initial message content (optional).
        :param tags: Tags for the chapter.
        :param child_index: Position in siblings (auto-assigned if None).
        :return: The created chapter Chat.
        :raises ValueError: If tutorial_id not found.
        """
        parent_chat = self.chat_manager.find_by_id(tutorial_id)
        if not parent_chat:
            raise ValueError(f"Parent chat '{tutorial_id}' not found")
        
        # Auto-assign child_index if not provided
        if child_index is None:
            existing_chats = self.chat_manager.list_chats()
            sibling_chats = [
                c for c in existing_chats if c.parent_id == tutorial_id
            ]
            child_index = max(
                (c.child_index or 0 for c in sibling_chats),
                default=-1
            ) + 1
        
        # Create the chapter chat (mode defaults to 'chat', inherit from parent project)
        chapter_chat = Chat(
            name=name,
            description=description,
            parent_id=tutorial_id,
            child_index=child_index,
            tags=tags or [],
            mode="chat",
            owner_project_id=parent_chat.owner_project_id or parent_chat.project_id,
            board=parent_chat.board,
            column=parent_chat.column,
        )
        
        # Add initial content message if provided
        if content:
            message = Message(
                role="assistant",
                content=content,
            )
            chapter_chat.messages.append(message)
        
        # Save the chapter
        saved_chapter = self.chat_manager.save_chat(chapter_chat)
        
        logger.info(
            "Created chapter '%s' in tutorial '%s' at index %d",
            name,
            tutorial_id,
            child_index,
        )
        
        return saved_chapter

    def modify_chapter(
        self,
        chapter_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        child_index: Optional[int] = None,
        add_message: Optional[Message] = None,
    ) -> Chat:
        """
        Modify a chapter's metadata, content, or structure.
        
        Allows updating title, description, tags, ordering, and adding messages.
        
        :param chapter_id: ID of the chapter to modify.
        :param name: New chapter title (if provided).
        :param description: New description (if provided).
        :param tags: New tags list (if provided).
        :param child_index: New position in sibling order (if provided).
        :param add_message: Message to append to the chapter (if provided).
        :return: The modified chapter Chat.
        :raises ValueError: If chapter_id not found.
        """
        chapter_chat = self.chat_manager.find_by_id(chapter_id)
        if not chapter_chat:
            raise ValueError(f"Chapter '{chapter_id}' not found")
        
        # Update metadata
        if name is not None:
            chapter_chat.name = name
        if description is not None:
            chapter_chat.description = description
        if tags is not None:
            chapter_chat.tags = tags
        if child_index is not None:
            chapter_chat.child_index = child_index
        
        # Add message if provided
        if add_message:
            if not add_message.doc_id:
                import uuid
                add_message.doc_id = str(uuid.uuid4())
            chapter_chat.messages.append(add_message)
        
        # Persist changes
        updated_chapter = self.chat_manager.save_chat(chapter_chat)
        
        logger.info("Modified chapter '%s'", chapter_id)
        
        return updated_chapter

    def delete_chapter(self, chapter_id: str) -> None:
        """
        Delete a chapter from the tutorial.
        
        The main tutorial chat cannot be deleted (only mode='tutorial' chats with
        parent_id are considered chapters).
        
        :param chapter_id: ID of the chapter to delete.
        :raises ValueError: If chapter not found or is a tutorial root.
        """
        chapter_chat = self.chat_manager.find_by_id(chapter_id)
        if not chapter_chat:
            raise ValueError(f"Chapter '{chapter_id}' not found")
        
        if chapter_chat.mode == 'tutorial' and not chapter_chat.parent_id:
            raise ValueError(
                f"Cannot delete tutorial root chat '{chapter_id}'. "
                "Only child chapters can be deleted."
            )
        
        # Delete via chat_manager
        self.chat_manager.delete_chat(chat_id=chapter_id)
        
        logger.info("Deleted chapter '%s'", chapter_id)

    def move_chapter(
        self,
        chapter_id: str,
        new_parent_id: str,
        new_index: Optional[int] = None,
    ) -> Chat:
        """
        Move a chapter to a different parent (reorganize tutorial structure).
        
        :param chapter_id: ID of the chapter to move.
        :param new_parent_id: ID of the new parent tutorial/chapter.
        :param new_index: New position in parent's child list (auto-assigned if None).
        :return: The moved chapter Chat.
        :raises ValueError: If chapter or parent not found.
        """
        chapter_chat = self.chat_manager.find_by_id(chapter_id)
        if not chapter_chat:
            raise ValueError(f"Chapter '{chapter_id}' not found")
        
        parent_chat = self.chat_manager.find_by_id(new_parent_id)
        if not parent_chat:
            raise ValueError(f"New parent '{new_parent_id}' not found")
        
        # Update parent reference
        chapter_chat.parent_id = new_parent_id
        
        # Auto-assign index if not provided
        if new_index is None:
            existing_chats = self.chat_manager.list_chats()
            sibling_chats = [
                c for c in existing_chats if c.parent_id == new_parent_id
            ]
            new_index = max(
                (c.child_index or 0 for c in sibling_chats),
                default=-1
            ) + 1
        
        chapter_chat.child_index = new_index
        
        # Persist
        moved_chapter = self.chat_manager.save_chat(chapter_chat)
        
        logger.info(
            "Moved chapter '%s' to parent '%s' at index %d",
            chapter_id,
            new_parent_id,
            new_index,
        )
        
        return moved_chapter

# Made with ❤️ by codx-junior