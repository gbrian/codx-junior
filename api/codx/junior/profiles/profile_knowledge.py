"""
Profile knowledge: semantic search over the profile ``knowledge`` folders.

Motivation
----------
A profile has a base definition shipped with codx-junior, but each project can
keep its own expertise for that profile: guidelines, conventions, reference
documents, examples... Those files live in a ``knowledge`` folder next to the
profile:

    <project .codx>/profiles/<Name>/knowledge/**   (one per project level)
    codx/junior/profiles/<Name>/knowledge/**       (built-in base profile)

:class:`~codx.junior.profiles.profile_manager.ProfileManager` already knows how
to resolve those folders (:meth:`ProfileManager.profile_knowledge_roots`); this
module turns them into a searchable index.

Design
------
Every knowledge folder gets its **own** :class:`KnowledgeDB` collection (a
"KnowledgeDB per knowledge folder"), so:

* a match is reported together with the profile/level it belongs to,
* indexing or resetting a folder never affects another one,
* base knowledge and project knowledge never mix.

``KnowledgeDB`` derives the collection name and the database folder from
``settings.abs_project_path`` (see ``KnowledgeDB.__init__``), so the folder is
isolated by handing the DB a copy of the project settings whose
``abs_project_path`` is the folder itself. ``codx_path`` is preserved, so every
database still lives under ``<project .codx>/db``.

The index is filesystem driven and incremental: a file is (re)indexed only when
it is new or its mtime is newer than the indexed version, and files removed
from disk are removed from the index. Nothing else in the project is affected.

Made with ❤️ by codx-junior
"""

import logging
import os
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document

from codx.junior.knowledge.knowledge_db import KnowledgeDB
from codx.junior.profiles.profile_manager import (
    MAX_KNOWLEDGE_FILE_SIZE,
    TEXT_KNOWLEDGE_EXTENSIONS,
    ProfileManager,
)
from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)

# Category stored in the documents metadata, so a profile knowledge document is
# recognizable inside its collection (and in logs / metrics).
KNOWLEDGE_CATEGORY = "profile_knowledge"

# ``page_content`` is a VARCHAR(65535) in the collection: a knowledge file is
# split into chunks before being indexed so a long document still fits.
CHUNK_SIZE = 4000
CHUNK_OVERLAP = 200

# Searching many profiles means opening many collections: keep it bounded.
MAX_SEARCH_PROFILES = 10


class ProfileKnowledge:
    """
    Semantic search over the profile knowledge folders of a project.

    A profile has one knowledge folder per level of the project inheritance
    chain (see :meth:`ProfileManager.profile_knowledge_roots`): the built-in
    base profile plus every parent project down to the current one.

    Diagram:
    flowchart TD
        A[ProfileKnowledge.search] --> B[ProfileManager.profile_knowledge_roots]
        B --> C[base knowledge folder]
        B --> D[parent project folders]
        B --> E[current project folder]
        C --> F[KnowledgeDB per folder]
        D --> F
        E --> F
        F --> G[index_folder - only changed files]
        G --> H[db.search query]
        H --> I[merge + sort by score]
    """

    def __init__(self, settings: CODXJuniorSettings) -> None:
        """
        Initialize the profile knowledge index for a project.

        Args:
            settings: Project settings (the knowledge folders of this project
                and of its parents are resolved from them).
        """
        self.settings = settings
        self.profile_manager = ProfileManager(settings=settings)
        # One DB per knowledge folder, reused while this instance lives.
        self._dbs: Dict[str, KnowledgeDB] = {}

    # -------------------------------------------------------------------------
    # One KnowledgeDB per knowledge folder
    # -------------------------------------------------------------------------
    def get_db(self, knowledge_path: str) -> KnowledgeDB:
        """
        Return the KnowledgeDB that indexes one knowledge folder.

        The DB uses a copy of the project settings whose ``abs_project_path``
        is the folder, which makes ``KnowledgeDB`` build its own collection and
        database folder for it. ``codx_path`` (and therefore the project
        identity) is kept.

        Args:
            knowledge_path: Absolute path of the knowledge folder.

        Returns:
            KnowledgeDB instance bound to that folder.
        """
        if knowledge_path not in self._dbs:
            logger.info("Opening profile knowledge DB for '%s'", knowledge_path)
            folder_settings = self.settings.model_copy(
                update={"abs_project_path": knowledge_path}
            )
            self._dbs[knowledge_path] = KnowledgeDB(settings=folder_settings)
        return self._dbs[knowledge_path]

    # -------------------------------------------------------------------------
    # Profile resolution
    # -------------------------------------------------------------------------
    def profile_names_with_knowledge(self) -> List[str]:
        """
        List the profiles that have at least one knowledge folder.

        Base profile names and project profile names are considered, then
        filtered by the existence of a ``knowledge`` folder in the project
        inheritance chain.

        Returns:
            Sorted profile names.
        """
        names = {
            os.path.basename(path)[:-len(".profile")]
            for path in self.profile_manager.base_profiles()
        }
        names.update(
            profile.name
            for profile in self.profile_manager.list_profiles()
            if profile and profile.name
        )
        return sorted(
            name
            for name in names
            if self.profile_manager.profile_knowledge_roots(profile_name=name)
        )

    # -------------------------------------------------------------------------
    # Indexing
    # -------------------------------------------------------------------------
    def index_profile(self, profile_name: str, force: bool = False) -> int:
        """
        Index every knowledge folder visible for a profile.

        Args:
            profile_name: Profile name.
            force: Reindex every file, even when it is already up to date.

        Returns:
            Number of documents indexed.
        """
        indexed = 0
        for root in self.profile_manager.profile_knowledge_roots(
            profile_name=profile_name
        ):
            try:
                indexed += self.index_folder(
                    root=root, profile_name=profile_name, force=force
                )
            except Exception as ex:
                logger.error(
                    "Error indexing profile knowledge '%s' (%s): %s",
                    profile_name,
                    root.get("path"),
                    ex,
                )
        return indexed

    def index_folder(
        self,
        root: Dict[str, str],
        profile_name: str,
        force: bool = False
    ) -> int:
        """
        Bring one knowledge folder index up to date.

        Only new/modified files are indexed (mtime newer than the indexed
        ``last_update``) and files that no longer exist are removed.

        Args:
            root: ``{"source", "path"}`` entry from
                :meth:`ProfileManager.profile_knowledge_roots`.
            profile_name: Profile the folder belongs to.
            force: Reindex every file.

        Returns:
            Number of documents indexed.
        """
        folder = root["path"]
        files = self._list_files(folder)
        db = self.get_db(folder)
        indexed_sources = db.get_all_sources() or {}

        documents: List[Document] = []
        for file_path in files:
            entry = indexed_sources.get(file_path)
            if entry and not force:
                last_update = int(entry.metadata.get("last_update") or 0)
                if last_update >= int(os.path.getmtime(file_path)):
                    continue

            text = self._read_text(file_path)
            if not text.strip():
                continue

            relative_file = os.path.relpath(file_path, folder)
            for chunk in self._split_text(text):
                documents.append(Document(
                    page_content=chunk,
                    metadata={
                        "source": file_path,
                        "category": KNOWLEDGE_CATEGORY,
                        "keywords": [profile_name, root.get("source", "")],
                        "profile": profile_name,
                        "knowledge_source": root.get("source", ""),
                        "file": relative_file,
                    },
                ))

        if documents:
            # A modified file must not keep its previous chunks.
            db.delete_documents(
                sources=sorted({doc.metadata["source"] for doc in documents})
            )
            db.index_documents(documents)

        removed = [source for source in indexed_sources if source not in files]
        if removed:
            db.delete_documents(sources=removed)

        if documents or removed:
            logger.info(
                "Profile knowledge '%s' [%s]: %d document(s) indexed, %d file(s) removed",
                profile_name,
                root.get("source", ""),
                len(documents),
                len(removed),
            )
        return len(documents)

    @staticmethod
    def _list_files(folder: str) -> List[str]:
        """
        List the text files of a knowledge folder.

        Args:
            folder: Absolute folder path.

        Returns:
            Sorted absolute file paths (text extensions only).
        """
        files: List[str] = []
        if not os.path.isdir(folder):
            return files
        for current, _, file_names in os.walk(folder):
            for name in file_names:
                if os.path.splitext(name)[1].lower() not in TEXT_KNOWLEDGE_EXTENSIONS:
                    continue
                files.append(os.path.join(current, name))
        return sorted(files)

    @staticmethod
    def _read_text(file_path: str) -> str:
        """
        Read a knowledge file as text.

        Delegates to ``ProfileManager`` so the size guard and the error
        handling are shared with the plain (non indexed) knowledge tools.

        Args:
            file_path: Absolute file path.

        Returns:
            File content, empty when it cannot be read.
        """
        return ProfileManager._read_text(file_path, max_size=MAX_KNOWLEDGE_FILE_SIZE)

    @staticmethod
    def _split_text(text: str) -> List[str]:
        """
        Split a document into overlapping chunks.

        Args:
            text: Document content.

        Returns:
            List of non-empty chunks.
        """
        if len(text) <= CHUNK_SIZE:
            return [text]

        chunks: List[str] = []
        step = CHUNK_SIZE - CHUNK_OVERLAP
        for start in range(0, len(text), step):
            chunk = text[start:start + CHUNK_SIZE]
            if chunk.strip():
                chunks.append(chunk)
            if start + CHUNK_SIZE >= len(text):
                break
        return chunks

    # -------------------------------------------------------------------------
    # Search
    # -------------------------------------------------------------------------
    def search(
        self,
        query: str,
        profile_names: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge of one or more profiles.

        Every knowledge folder of every requested profile is searched (base +
        every project level), results are merged and sorted by relevance.

        Args:
            query: Natural-language query.
            profile_names: Profiles to search. Defaults to every profile that
                has a knowledge folder.
            limit: Maximum number of results.

        Returns:
            List of result dicts with ``profile``, ``knowledge_source``,
            ``file``, ``source``, ``score`` and ``content``.

        Raises:
            ValueError: If the query is empty.
        """
        query = (query or "").strip()
        if not query:
            raise ValueError("query is required")

        names = profile_names or self.profile_names_with_knowledge()
        names = [name for name in names if name][:MAX_SEARCH_PROFILES]
        limit = max(1, min(int(limit or 10), 50))

        if not names:
            return []

        results: List[Dict[str, Any]] = []
        for profile_name in names:
            for root in self.profile_manager.profile_knowledge_roots(
                profile_name=profile_name
            ):
                try:
                    self.index_folder(root=root, profile_name=profile_name)
                    documents = self.get_db(root["path"]).search(
                        query=query, _limit=limit
                    )
                except Exception as ex:
                    logger.error(
                        "Error searching profile knowledge '%s' (%s): %s",
                        profile_name,
                        root.get("path"),
                        ex,
                    )
                    continue

                for document in documents:
                    metadata = document.metadata or {}
                    results.append({
                        "profile": profile_name,
                        "knowledge_source": metadata.get(
                            "knowledge_source", root.get("source", "")
                        ),
                        "file": metadata.get("file", ""),
                        "source": metadata.get("source", ""),
                        "score": metadata.get("score", 0.0),
                        "content": (document.page_content or "").strip(),
                    })

        results.sort(key=lambda result: result["score"], reverse=True)
        return results[:limit]

# Made with ❤️ by codx-junior