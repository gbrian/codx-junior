"""
Module for knowledge search and context gathering in chat interactions.

Provides utilities for:
- AI-powered search context gathering (vibe/search modes)
- RAG-based document selection from knowledge base
- Knowledge search query creation

flowchart TD
    A[User Query] --> B{Search Type}
    B -->|AI Search| C[KnowledgeAISearch]
    B -->|RAG Search| D[Knowledge Base]
    C --> E[Build Context Documents]
    D --> F[Find Relevant Documents]
    E --> G[Return Documents + Context]
    F --> G
"""

import logging
import os
from typing import List, Tuple, Optional

from langchain_core.documents import Document

from codx.junior.ai import AI
from codx.junior.context import find_relevant_documents
from codx.junior.db import Chat
from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.knowledge.knowledge_ai_search import KnowledgeAISearch
from codx.junior.knowledge.knowledge_ai_search_message import build_search_message
from codx.junior.settings import CODXJuniorSettings
from codx.junior.utils.utils import document_to_code_block

logger = logging.getLogger(__name__)


class ChatKnowledge:
    """
    Handles all knowledge search and context gathering operations for chat interactions.

    Wraps both AI-powered search (KnowledgeAISearch) and traditional RAG search
    (Knowledge/Milvus) behind a unified interface used by ChatEngine.

    flowchart TD
        A[ChatKnowledge] --> B[ai_search_for_context]
        A --> C[select_documents_from_knowledge]
        A --> D[create_knowledge_search_query]
        B --> E[KnowledgeAISearch]
        C --> F[Knowledge Milvus]
        C --> G[find_relevant_documents]
        D --> H[AI keyword extraction]
    """

    def __init__(self, settings: CODXJuniorSettings, event_manager) -> None:
        """
        Initialize ChatKnowledge with project settings and an event manager.

        :param settings: The current project's settings.
        :param event_manager: Event manager for emitting chat/search events.
        """
        self.settings = settings
        self.event_manager = event_manager
        self.knowledge = Knowledge(settings=settings)

    async def ai_search_for_context(
        self,
        chat: Chat,
        query: str,
        existing_chat_files: List[str]
    ) -> Tuple[List[Document], List[str], str]:
        """
        Perform an AI-powered search to gather context documents and file references.

        Used for 'vibe' chat mode and 'search' task items to pre-load relevant
        context before the main AI processing step.

        sequenceDiagram
            participant CK as ChatKnowledge
            participant KAS as KnowledgeAISearch
            participant EM as EventManager

            CK->>EM: Emit "Searching for context..."
            CK->>KAS: ai_search(user_query)
            KAS-->>CK: ai_search_results
            CK->>CK: build_search_message(results)
            CK->>CK: Extract documents + file paths
            CK->>EM: Emit "Found N context documents"
            CK-->>CK: Return (documents, file_list, context_str)

        :param chat: The current chat object for event emission.
        :param query: The combined user query to search with.
        :param existing_chat_files: Already-loaded file paths to avoid duplicates.
        :return: Tuple of (documents, file_list, context_string).
        """
        documents: List[Document] = []
        file_list: List[str] = []
        context: str = ""

        self.event_manager.chat_event(
            chat=chat,
            message="Searching for context using AI search..."
        )
        logger.info(
            "Performing AI search for vibe/search context. Query length: %d",
            len(query)
        )

        try:
            ai_search_results = await KnowledgeAISearch(
                settings=self.settings
            ).ai_search(user_query=query)

            search_message = build_search_message(ai_search_results)

            documents, file_list, context = self._extract_documents_from_search_message(
                search_message=search_message,
                existing_chat_files=existing_chat_files
            )

            # Prepend AI search summary content to the context if available
            if search_message.content:
                context = f"{search_message.content}\n\n{context}"

            self.event_manager.chat_event(
                chat=chat,
                message=f"AI search found {len(documents)} context documents"
            )
            logger.info("AI search context gathered: %d documents", len(documents))

        except (OSError, ValueError, RuntimeError) as search_ex:
            self.event_manager.chat_event(
                chat=chat,
                message=f"AI search context error: {search_ex}",
                event_type="error"
            )
            logger.exception("Error during AI search for context: %s", search_ex)

        return documents, file_list, context

    def _extract_documents_from_search_message(
        self,
        search_message,
        existing_chat_files: List[str]
    ) -> Tuple[List[Document], List[str], str]:
        """
        Extract Document objects and file paths from a search message result.

        Reads file contents from disk for each file referenced in the search message
        that is not already present in the chat's existing files.

        :param search_message: The search message containing file references.
        :param existing_chat_files: File paths already present in the chat context.
        :return: Tuple of (documents, file_list, context_string).
        """
        documents: List[Document] = []
        file_list: List[str] = []
        context: str = ""

        if not (hasattr(search_message, "files") and search_message.files):
            return documents, file_list, context

        for file_path in search_message.files:
            if file_path in existing_chat_files:
                continue

            file_list.append(file_path)
            full_path = self._resolve_full_path(file_path)

            if not os.path.isfile(full_path):
                logger.warning("Search result file not found on disk: %s", full_path)
                continue

            doc, doc_context = self._read_document_from_path(full_path)
            if doc is not None:
                documents.append(doc)
                context += doc_context + "\n"
                logger.debug("Added AI search context file: %s", doc.metadata.get("source"))

        return documents, file_list, context

    def _resolve_full_path(self, file_path: str) -> str:
        """
        Resolve a potentially relative file path to an absolute path.

        :param file_path: The file path, possibly relative to the project root.
        :return: The resolved absolute file path.
        """
        if os.path.isabs(file_path):
            return file_path
        return os.path.join(
            self.settings.abs_project_path,
            file_path.lstrip("/")
        )

    def _read_document_from_path(
        self,
        full_path: str
    ) -> Tuple[Optional[Document], str]:
        """
        Read a file from disk and return a Document and its code block representation.

        :param full_path: The absolute path to the file to read.
        :return: Tuple of (Document or None, code_block_string).
        """
        try:
            with open(full_path, "r", encoding="utf-8") as file_handle:
                source = full_path.replace(
                    self.settings.abs_project_path + "/", ""
                )
                doc = Document(
                    page_content=file_handle.read(),
                    metadata={"source": source}
                )
                doc_context = document_to_code_block(doc)
                return doc, doc_context
        except OSError as file_ex:
            logger.error(
                "Error reading context file '%s': %s",
                full_path,
                file_ex
            )
            return None, ""

    def select_documents_from_knowledge(
        self,
        chat: Chat,
        query: str,
        ignore_documents: Optional[List[str]] = None,
        search_projects: Optional[List[CODXJuniorSettings]] = None
    ) -> Tuple[List[Document], List[str]]:
        """
        Select documents from the knowledge base relevant to a given query.

        Searches across all provided search projects using RAG (Retrieval-Augmented
        Generation) and returns deduplicated, relevant documents.

        flowchart TD
            A[Query] --> B[For each search_project]
            B --> C[knowledge.search]
            C --> D[find_relevant_documents]
            D --> E[Accumulate docs + file_list]
            E --> F[Return all docs + file_list]

        :param chat: Current chat object for event emission.
        :param query: Search query for selecting documents.
        :param ignore_documents: List of document paths to exclude from results.
        :param search_projects: List of project settings to search within.
        :return: Tuple of (list of Documents, list of file paths).
        """
        resolved_search_projects: List[CODXJuniorSettings] = search_projects or []
        resolved_ignore_documents: List[str] = ignore_documents or []

        all_documents: List[Document] = []
        all_file_paths: List[str] = []

        logger.debug("Starting document selection with query: %s", query)

        for search_project in resolved_search_projects:
            self.event_manager.chat_event(
                chat=chat,
                message=f"Searching knowledge in {search_project.project_name}"
            )
            project_docs, project_file_list = self._search_single_project(
                query=query,
                search_project=search_project,
                ignore_documents=resolved_ignore_documents
            )
            all_documents.extend(project_docs)
            all_file_paths.extend(project_file_list)

        logger.info("Documents selected from knowledge: %d", len(all_documents))
        return all_documents, all_file_paths

    def _search_single_project(
        self,
        query: str,
        search_project: CODXJuniorSettings,
        ignore_documents: List[str]
    ) -> Tuple[List[Document], List[str]]:
        """
        Execute RAG search for a single project and return matching documents.

        :param query: The search query string.
        :param search_project: Project settings defining the knowledge base to search.
        :param ignore_documents: Document paths to exclude from results.
        :return: Tuple of (documents, absolute file paths).
        """
        logger.debug(
            "Searching project '%s' for query: %s",
            search_project.project_name,
            query
        )

        knowledge_documents = self.knowledge(settings=search_project).search(query)

        project_docs, project_file_list = find_relevant_documents(
            query=query,
            settings=search_project,
            knowledge_documents=knowledge_documents,
            ignore_documents=ignore_documents
        )

        # Resolve file paths to absolute paths within the project
        absolute_file_list = [
            os.path.join(search_project.abs_project_path, fp)
            for fp in project_file_list
        ]

        return project_docs, absolute_file_list

    def create_knowledge_search_query(self, query: str) -> str:
        """
        Enhance a raw query into a more effective knowledge base search string.

        Uses the AI to extract and expand keywords from the input text for
        improved document retrieval accuracy.

        :param query: The initial user query or combined conversation context.
        :return: A processed query string optimized for knowledge base search.
        """
        ai = AI(settings=self.settings)
        enhanced_query = ai.chat(
            prompt=(
                f"<text>\n"
                f"{query}\n"
                f"</text>\n\n"
                "Extract keywords from the text to help searching in the knowledge base.\n"
                "Return just the search string without further decoration or comments."
            )
        )[-1].content.strip()

        logger.debug("Knowledge search query created: %s", enhanced_query)
        return enhanced_query

# Made with ❤️ by codx-junior