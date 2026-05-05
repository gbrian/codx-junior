"""
Knowledge sub-engine for codx-junior.
Handles all knowledge base operations including search, indexing, and document management.

Made with ❤️ by codx-junior
"""

import logging
import os
import time
from typing import TYPE_CHECKING, Optional

from codx.junior.context import (
    find_relevant_documents,
    validate_search_documents,
)
from codx.junior.db import Chat, Message
from codx.junior.globals import (
    MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS,
    MAX_OUTDATED_TIME_TO_PROVESS_FILE_MENTIONS_IN_SECS,
)
from codx.junior.knowledge.knowledge_keywords import KnowledgeKeywords
from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.model.model import KnowledgeSearch
from codx.junior.profiling.profiler import profile_function
from codx.junior.project.project_discover import find_project_by_name
from codx.junior.utils.utils import document_to_code_block

if TYPE_CHECKING:
    from codx.junior.engine.session import CODXJuniorSession
    from codx.junior.ai import AI

logger = logging.getLogger(__name__)


class KnowledgeEngine:
    """
    Handles all knowledge-related operations for a CODXJuniorSession.

    ```mermaid
    flowchart TD
        KE[KnowledgeEngine]
        KE --> reload_knowledge
        KE --> knowledge_search
        KE --> project_search
        KE --> select_affected_documents
        KE --> process_project_changes
        KE --> process_project_mentions
    ```
    """

    def __init__(self, session: "CODXJuniorSession") -> None:
        """Initialize with a reference to the parent session."""
        self.session = session

    @property
    def settings(self):
        """Shortcut to session settings."""
        return self.session.settings

    @property
    def event_manager(self):
        """Shortcut to session event manager."""
        return self.session.event_manager

    def reload_knowledge(self, path: str = None) -> dict:
        """
        Reload knowledge for the project, optionally scoped to a path.

        Args:
            path: Optional file/dir path to reload.

        Returns:
            Dict with doc_count of reloaded documents.
        """
        knowledge = self.session.get_knowledge()
        self.session.log_info("***** reload_knowledge: %s", path)
        documents = None
        if path:
            documents = knowledge.reload_path(path)
            self.session.log_info("reload_knowledge: %s - Docs: %d", path, len(documents))
        else:
            documents = knowledge.reload()
        return {"doc_count": len(documents) if documents else 0}

    async def knowledge_search(self, knowledge_search: KnowledgeSearch) -> dict:
        """
        Perform a knowledge search with the given parameters.

        Args:
            knowledge_search: Search parameters model.

        Returns:
            Dict with response, documents and settings used.
        """
        self.settings.knowledge_search_type = knowledge_search.document_search_type
        self.settings.knowledge_search_document_count = knowledge_search.document_count
        self.settings.knowledge_context_cutoff_relevance_score = knowledge_search.document_cutoff_score
        self.settings.knowledge_context_rag_distance = knowledge_search.document_cutoff_rag

        logger.info(
            "knowledge_search: knowledge_search_type=%s, doc_count=%s, cutoff=%s, rag=%s",
            self.settings.knowledge_search_type,
            self.settings.knowledge_search_document_count,
            self.settings.knowledge_context_cutoff_relevance_score,
            self.settings.knowledge_context_rag_distance,
        )

        documents = []
        response = ""

        search_type = knowledge_search.search_type
        llm_model = self.settings.get_wiki_model()

        if search_type == "raw":
            documents = validate_search_documents(
                query=knowledge_search.search_term,
                documents=documents,
                settings=self.settings,
            )
            chat = Chat(
                messages=[
                    Message(
                        role="user",
                        content=f"Answer user query: {knowledge_search.search_term}",
                    )
                ],
                llm_model=llm_model,
            )
            chat, docs = await self.session.chat_with_project(chat=chat)
            response_message = chat.messages[-1]
            response = response_message.content
            llm_model = response_message.meta_data["model"]
            documents = docs
        else:
            documents = Knowledge(settings=self.settings).search(
                knowledge_search.search_term,
                search_type=search_type,
                limit=knowledge_search.document_count,
            )

        return {
            "response": response,
            "documents": documents,
            "settings": {
                "llm_model": llm_model,
                "knowledge_search_type": self.settings.knowledge_search_type,
                "knowledge_search_document_count": self.settings.knowledge_search_document_count,
                "knowledge_context_cutoff_relevance_score": self.settings.knowledge_context_cutoff_relevance_score,
                "knowledge_context_rag_distance": self.settings.knowledge_context_rag_distance,
            },
        }

    def delete_knowledge_source(self, sources: list) -> dict:
        """
        Delete knowledge documents by source paths.

        Args:
            sources: List of source paths to delete.

        Returns:
            Dict with ok status.
        """
        Knowledge(settings=self.settings).delete_documents(sources=sources)
        return {"ok": 1}

    def index_knowledge_source(self, sources: list) -> dict:
        """
        Index knowledge documents by source paths.

        Args:
            sources: List of source paths to index.

        Returns:
            Dict with ok status.
        """
        knowledge = Knowledge(settings=self.settings)
        for path in sources:
            knowledge.reload_path(path=path)
        return {"ok": 1}

    def delete_knowledge(self) -> dict:
        """
        Reset (delete) all knowledge for the project.

        Returns:
            Dict with ok status.
        """
        Knowledge(settings=self.settings).reset()
        return {"ok": 1}

    def get_project_dependencies(self) -> tuple:
        """
        Return all projects related with this project (child and dependency projects).

        Returns:
            Tuple of (child_projects, dependency_projects).
        """
        def not_none(col: list) -> list:
            return [e for e in col if e]

        project_child_projects = self.settings.get_sub_projects()
        project_dependencies = [
            find_project_by_name(project_name)
            for project_name in self.settings.get_project_dependencies()
        ]
        return not_none(project_child_projects), not_none(project_dependencies)

    def get_all_search_projects(self) -> list:
        """
        Return all projects relevant for knowledge search (self + children + deps).

        Returns:
            List of settings objects.
        """
        project_child_projects, project_dependencies = self.get_project_dependencies()
        return [self.settings] + project_child_projects + project_dependencies

    def check_knowledge_status(self) -> dict:
        """
        Return detailed knowledge status including pending files and metrics.

        Returns:
            Dict with status information.
        """
        knowledge = self.session.get_knowledge()
        status = knowledge.status()
        current_sources_and_updates = knowledge.get_db().get_all_sources()
        pending_files, _ = knowledge.detect_changes(
            current_sources_and_updates=current_sources_and_updates
        )
        total_pending = len(pending_files)

        # Cap the list for display
        if total_pending > 1000:
            pending_files = pending_files[:1000]

        pending_files = [
            f for f in pending_files if f not in list(current_sources_and_updates.keys())
        ]
        collection_metrics = knowledge.get_db().get_collection_metrics()

        return {
            "current_sources_and_updates": current_sources_and_updates,
            "pending_files": pending_files,
            "total_pending_changes": len(pending_files),
            "total_pending": total_pending,
            "collection_metrics": collection_metrics,
            **status,
        }

    @profile_function
    def find_project_documents(self, query: str) -> list:
        """
        Find project documents relevant to a query.

        Args:
            query: Free text query.

        Returns:
            List of matching documents.
        """
        documents, _ = self.select_afefcted_documents_from_knowledge(
            chat=None, ai=self.session.get_ai(), query=query, search_projects=[]
        )
        return documents

    @profile_function
    def project_search(self, query: str) -> list:
        """
        Search knowledge for a query string.

        Args:
            query: Free text query.

        Returns:
            List of matching documents.
        """
        return self.session.get_knowledge().search(query=query)

    @profile_function
    def select_afefcted_documents_from_knowledge(
        self,
        chat: Optional[Chat],
        ai: "AI",
        query: str,
        ignore_documents: list = None,
        search_projects: list = None,
    ) -> tuple:
        """
        Select documents from knowledge base relevant to a query across projects.

        Args:
            chat: Optional active chat for event messaging.
            ai: AI instance for query processing.
            query: The search query.
            ignore_documents: Documents to exclude.
            search_projects: Projects to search within.

        Returns:
            Tuple of (documents, file_list).
        """
        ignore_documents = ignore_documents or []
        search_projects = search_projects or []

        for search_project in search_projects:
            query = query.replace(f"@{search_project.project_name}", "")

        @profile_function
        def process_rag_query(rag_query: str) -> tuple:
            docs = []
            file_list = []

            self.session.log_info(
                "select_afefcted_documents_from_knowledge search subprojects: %s in %s",
                rag_query,
                [p.project_name for p in search_projects],
            )

            for search_project in search_projects:
                if chat:
                    self.event_manager.chat_event(
                        chat=chat,
                        message=f"Search knowledge in {search_project.project_name}: {search_project.abs_project_path}",
                    )
                knowledge_documents = Knowledge(settings=search_project).search(query)
                project_docs, project_file_list = find_relevant_documents(
                    query=rag_query,
                    settings=search_project,
                    knowledge_documents=knowledge_documents,
                    ignore_documents=ignore_documents,
                )
                project_file_list = [
                    os.path.join(search_project.abs_project_path, file_path)
                    for file_path in project_file_list
                ]
                if project_docs:
                    docs = docs + project_docs
                if project_file_list:
                    file_list = file_list + project_file_list

            self.session.log_info(
                "select_afefcted_documents_from_knowledge doc length: %d - cutoff score %s",
                len(docs),
                self.settings.knowledge_context_cutoff_relevance_score,
            )
            return docs, file_list

        return process_rag_query(rag_query=query)

    def extract_tags(self, doc) -> object:
        """
        Extract tags/keywords from a document.

        Args:
            doc: Document object.

        Returns:
            Updated document with tags.
        """
        knowledge = Knowledge(settings=self.settings)
        knowledge.extract_doc_keywords(doc)
        return doc

    def get_keywords(self, query: str) -> list:
        """
        Get keywords for a query using KnowledgeKeywords.

        Args:
            query: Free text query.

        Returns:
            List of keywords.
        """
        return KnowledgeKeywords(settings=self.settings).get_keywords(query)

    def create_knowledge_search_query(self, query: str) -> str:
        """
        Create an optimized knowledge base search query from free text.

        Args:
            query: Raw query text.

        Returns:
            Optimized search string.
        """
        ai = self.session.get_ai()
        return ai.chat(
            prompt=f"""
        <text>
        {query}
        </text>

        Extract keywords from the text to help searching in the knowledge base.
        Return just the search string without further decoration or comments.
        """
        )[-1].content

    async def process_project_changes(self) -> None:
        """
        Process pending project file changes for knowledge indexing.
        Only processes files that are not too recent (to avoid partial writes).
        """
        if not self.settings.is_valid_project():
            return

        knowledge = Knowledge(settings=self.settings)
        knowledge.clean_deleted_documents()
        current_sources_and_updates = self.session.get_knowledge().get_db().get_all_sources()
        new_files, _ = knowledge.detect_changes(current_sources_and_updates)
        if not new_files:
            return

        def find_changed_file() -> Optional[str]:
            """Return the first file that has been modified recently enough."""
            for file_path in new_files:
                age_secs = int(time.time()) - int(os.stat(file_path).st_mtime)
                if age_secs < MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS:
                    return file_path
            return None

        file_path = find_changed_file()
        if not file_path:
            return

        mention_manager = self.session.get_mention_manager()

        # Don't index files with mentions
        if not self.settings.watching or mention_manager.check_if_file_has_mentions(
            file_path=file_path
        ):
            return

        file_has_mentions = mention_manager.check_if_file_has_mentions(file_path=file_path)
        if file_has_mentions:
            return

        is_media_file = self.session.audio_manager.is_valid_media_file(file_path=file_path)
        self.session.log_info(
            "Reload knowledge file %s - is media: %s", file_path, is_media_file
        )

        if is_media_file:
            logger.info("Converting media file %s", file_path)
            transcript_info = self.session.audio_manager.transcribe_from_file(
                file_path=file_path
            )
            file_path = transcript_info["transcript_file_path"]

        knowledge.reload_path(path=file_path)
        self.event_manager.send_knowled_event(type="loaded", file_path=file_path)

        self.session.get_wiki().process_file_change(file_path=file_path)

    async def process_project_mentions(self) -> None:
        """
        Process pending project file mention checks.
        Only processes files that are not too recent.
        """
        if not self.settings.is_valid_project():
            return

        knowledge = Knowledge(settings=self.settings)
        knowledge.clean_deleted_documents()
        current_sources_and_updates = self.session.get_knowledge().get_db().get_all_sources()
        new_files, _ = knowledge.detect_changes(current_sources_and_updates)
        if not new_files:
            return

        def find_changed_file() -> Optional[str]:
            """Return the first file modified within the mention processing window."""
            for file_path in new_files:
                age_secs = int(time.time()) - int(os.stat(file_path).st_mtime)
                if age_secs < MAX_OUTDATED_TIME_TO_PROVESS_FILE_MENTIONS_IN_SECS:
                    return file_path
            return None

        file_path = find_changed_file()
        if not file_path:
            return

        mention_manager = self.session.get_mention_manager()
        await mention_manager.check_file_for_mentions(file_path=file_path)