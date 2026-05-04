"""
knowledge_ai_search.py

Provides iterative AI-driven search over the knowledge base.
The AI determines whether the retrieved documents are sufficient to answer
the user's question or whether additional search iterations are required.

Key behaviours:
  - Multiple Document objects may share the same ``source`` (different chunks
    of the same file).  Deduplication is therefore performed on the full
    (source, page_content) pair rather than source alone.
  - Only documents with a BM25 ``score`` > MINIMUM_SCORE_THRESHOLD are kept,
    and from those only the top TOP_DOCUMENTS_LIMIT by score are used.
  - When the current document set is insufficient the AI may return up to
    ``MAX_REFINED_QUERIES`` search queries.  All queries are executed in
    parallel and their results are merged before the next sufficiency check.
  - Searches are run in parallel across the current project **and** all child
    projects returned by ``get_project_dependencies``.
  - Each document in the result carries a ``project_name`` metadata field
    identifying which project it originated from.

Diagram:
flowchart TD
    A[User Query] --> B[Resolve current + dependency projects]
    B --> C[Parallel Search: all projects x all queries]
    C --> D[Tag documents with project_name]
    D --> E[Filter: score > MINIMUM_SCORE_THRESHOLD]
    E --> F[Sort by score descending]
    F --> G[Keep top TOP_DOCUMENTS_LIMIT documents]
    G --> H[Merge & Deduplicate Documents]
    H --> I[AI: Is answer sufficient?]
    I -- Yes --> J[Generate Final Answer]
    I -- No --> K{Max iterations reached?}
    K -- No --> L[AI: Generate up-to-3 refined queries]
    L --> C
    K -- Yes --> J
    J --> M[Return AISearchResult with projects_searched]
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document

from codx.junior.ai import AI
from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.model.model import CodxUser
from codx.junior.settings import CODXJuniorSettings
from codx.junior.utils.utils import extract_json_blocks

logger = logging.getLogger(__name__)

# Default maximum number of search iterations
DEFAULT_MAX_ITERATIONS = 3

# Maximum number of refined queries the AI may return per iteration
MAX_REFINED_QUERIES = 3

# Only documents whose BM25 score exceeds this threshold are considered relevant
MINIMUM_SCORE_THRESHOLD = 4.0

# Maximum number of top-scoring documents to retain after filtering
TOP_DOCUMENTS_LIMIT = 4

# Separator used when building the chunk-level deduplication key
_DEDUP_KEY_SEP = "||"

# Metadata key used to carry the originating project name through the pipeline
METADATA_PROJECT_NAME = "project_name"

# Prompt templates
SUFFICIENCY_CHECK_PROMPT = """
You are a research assistant. A user asked the following question:

<user_query>
{user_query}
</user_query>

Based on the documents retrieved so far from multiple projects, determine if there is
enough information to answer the question fully and accurately.

<retrieved_documents>
{documents_text}
</retrieved_documents>

Respond with a JSON object:
{{
  "is_sufficient": true or false,
  "reasoning": "Brief explanation of why the documents are or are not sufficient",
  "refined_queries": [
    "First more specific search query to find missing information (omit if sufficient)",
    "Second alternative search query (omit if sufficient)",
    "Third alternative search query (omit if sufficient)"
  ]
}}

Notes:
- Set "is_sufficient" to true when the documents already contain enough information.
- When not sufficient, provide between 1 and {max_refined_queries} entries in
  "refined_queries" — each targeting a different aspect of the missing information.
- Leave "refined_queries" as an empty list when sufficient.
"""

FINAL_ANSWER_PROMPT = """
You are a knowledgeable assistant. Answer the following user question using ONLY the
provided documents. Be concise, accurate, and cite relevant sources where appropriate.

The documents may come from multiple related projects. When relevant, mention the
project each piece of information originates from.

<user_query>
{user_query}
</user_query>

<documents>
{documents_text}
</documents>

Provide a thorough and helpful answer based solely on the documents above.
If the documents do not contain enough information, state that clearly.
"""


def _dedup_key(doc: Document) -> str:
    """
    Build a string key that uniquely identifies a document chunk.

    Multiple chunks from the same file are intentionally kept because they
    represent different portions of the source.  The key therefore combines
    the source path with the first 200 characters of the content so that
    genuinely identical chunks (returned by multiple queries) are collapsed
    while distinct chunks from the same file are retained.

    Args:
        doc: Document to key.

    Returns:
        Deduplication key string.
    """
    source = doc.metadata.get("source", "")
    content_prefix = doc.page_content[:200]
    return f"{source}{_DEDUP_KEY_SEP}{content_prefix}"


def _format_documents_for_prompt(documents: List[Document]) -> str:
    """
    Format a list of Document objects into a readable string for LLM prompts.

    Each document entry includes its originating project name so the AI can
    reason about cross-project context.

    Args:
        documents: List of LangChain Document objects.

    Returns:
        Formatted string representation of all documents.
    """
    parts = []
    for idx, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source", "Unknown")
        score = doc.metadata.get("score", "N/A")
        project_name = doc.metadata.get(METADATA_PROJECT_NAME, "Unknown")
        parts.append(
            f"[Document {idx}]\n"
            f"Project: {project_name}\n"
            f"Source: {source}\n"
            f"Score: {score}\n"
            f"Content:\n{doc.page_content}\n"
        )
    return "\n---\n".join(parts)


def _deduplicate_documents(documents: List[Document]) -> List[Document]:
    """
    Remove duplicate document chunks across search iterations and projects.

    Two chunks are considered duplicates when they share the same source path
    **and** the same leading content (first 200 characters).  When duplicates
    exist, the entry with the highest BM25 score is retained.

    Note: Multiple chunks from the same source file with *different* content
    are intentionally preserved — they represent different sections of the
    same file and may each contribute distinct information to the answer.

    Diagram:
    flowchart TD
        A[Input documents] --> B[Compute dedup key per document]
        B --> C{Key already seen?}
        C -- No --> D[Add to seen map]
        C -- Yes --> E{Current score higher?}
        E -- Yes --> F[Replace existing entry]
        E -- No  --> G[Discard current]
        D --> H[Return values of seen map]
        F --> H
        G --> H

    Args:
        documents: List of Document objects, potentially containing duplicates.

    Returns:
        Deduplicated list of Document objects.
    """
    seen: Dict[str, Document] = {}
    for doc in documents:
        key = _dedup_key(doc)
        existing = seen.get(key)
        if existing is None:
            seen[key] = doc
        else:
            existing_score = existing.metadata.get("score", 0.0)
            current_score = doc.metadata.get("score", 0.0)
            if current_score > existing_score:
                seen[key] = doc
    return list(seen.values())


def _filter_and_rank_documents(documents: List[Document]) -> List[Document]:
    """
    Filter documents by minimum BM25 score and return the top-scoring subset.

    Documents that lack a ``score`` in their metadata (e.g. path-matched files
    injected by ``Knowledge.search``) are assigned a score of 0.0 and therefore
    dropped by the threshold filter unless ``MINIMUM_SCORE_THRESHOLD`` is 0.

    Processing steps:
      1. Discard documents whose score is ≤ ``MINIMUM_SCORE_THRESHOLD``.
      2. Sort the survivors by score in descending order.
      3. Return the top ``TOP_DOCUMENTS_LIMIT`` documents.

    Diagram:
    flowchart TD
        A[Input documents] --> B[Filter: score > MINIMUM_SCORE_THRESHOLD]
        B --> C[Sort by score descending]
        C --> D[Slice top TOP_DOCUMENTS_LIMIT]
        D --> E[Return filtered documents]

    Args:
        documents: Raw list of Document objects, each optionally carrying a
                   ``score`` float in its metadata.

    Returns:
        At most ``TOP_DOCUMENTS_LIMIT`` Document objects with score above
        ``MINIMUM_SCORE_THRESHOLD``, ordered by descending score.
    """
    qualifying = [
        doc for doc in documents
        if doc.metadata.get("score", 0.0) > MINIMUM_SCORE_THRESHOLD
    ]

    sorted_docs = sorted(
        qualifying,
        key=lambda d: d.metadata.get("score", 0.0),
        reverse=True,
    )

    top_docs = sorted_docs[:TOP_DOCUMENTS_LIMIT]

    logger.info(
        "_filter_and_rank_documents: %d input → %d qualifying (score > %.1f) "
        "→ top %d returned.",
        len(documents),
        len(qualifying),
        MINIMUM_SCORE_THRESHOLD,
        len(top_docs),
    )

    return top_docs


def _document_to_dict(doc: Document) -> Dict[str, Any]:
    """
    Serialise a Document object to a plain dictionary for JSON output.

    Args:
        doc: LangChain Document to serialise.

    Returns:
        Dictionary with page_content and metadata fields.
    """
    return {
        "page_content": doc.page_content,
        "metadata": doc.metadata,
    }


def _tag_documents_with_project(
    documents: List[Document],
    project_name: str,
) -> List[Document]:
    """
    Stamp each document's metadata with the originating project name.

    This mutates the metadata in-place so that downstream consumers
    (prompt formatting, serialisation) can identify which project each
    chunk came from without additional bookkeeping.

    Args:
        documents:    Documents returned by a single project's search.
        project_name: Name of the project that produced these documents.

    Returns:
        The same list of documents with ``project_name`` set in metadata.
    """
    for doc in documents:
        doc.metadata[METADATA_PROJECT_NAME] = project_name
    return documents


class AISearchResult:
    """
    Structured result returned by the ai_search function.

    Attributes:
        user_query:        The original question posed by the user.
        max_iterations:    The maximum number of search iterations allowed.
        total_iterations:  The number of iterations actually performed.
        answer:            The AI-generated answer to the user's question.
        documents:         Documents used to construct the answer.
        queries_used:      All search queries executed (initial + refined).
        projects_searched: Names of all projects searched (current + children).
    """

    def __init__(
        self,
        user_query: str,
        max_iterations: int,
        total_iterations: int,
        answer: str,
        documents: List[Document],
        queries_used: Optional[List[str]] = None,
        projects_searched: Optional[List[str]] = None,
    ) -> None:
        self.user_query = user_query
        self.max_iterations = max_iterations
        self.total_iterations = total_iterations
        self.answer = answer
        self.documents = documents
        self.queries_used: List[str] = queries_used or []
        self.projects_searched: List[str] = projects_searched or []

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialise this result to a JSON-compatible dictionary.

        The ``documents`` list includes a ``project_name`` field in each
        document's metadata so callers can trace which project each piece
        of evidence originated from.

        Returns:
            Dictionary representation of the search result.
        """
        return {
            "user_query": self.user_query,
            "max_iterations": self.max_iterations,
            "total_iterations": self.total_iterations,
            "answer": self.answer,
            "queries_used": self.queries_used,
            "projects_searched": self.projects_searched,
            "documents": [_document_to_dict(doc) for doc in self.documents],
        }


class KnowledgeAISearch:
    """
    Performs iterative AI-driven search over the project knowledge base,
    including all child/dependency projects searched in parallel.

    Each document in the result carries a ``project_name`` metadata key
    that identifies which project it was retrieved from, enabling the AI
    to provide cross-project context in its final answer.

    Only documents with a BM25 score above ``MINIMUM_SCORE_THRESHOLD`` are
    considered; from those, only the top ``TOP_DOCUMENTS_LIMIT`` by score
    are passed to the AI sufficiency check and final answer generation.

    The search loop works as follows:
      1. Resolve current project + all dependency projects via
         ``get_project_dependencies``.
      2. Run full-text searches for each current query across ALL projects
         in parallel.
      3. Tag every returned document with the originating ``project_name``.
      4. Filter to documents with score > MINIMUM_SCORE_THRESHOLD and
         keep only the top TOP_DOCUMENTS_LIMIT by score.
      5. Merge and deduplicate all retrieved documents across iterations.
      6. Ask the AI whether the retrieved documents are sufficient.
      7. If sufficient (or max iterations reached), generate a final answer.
      8. Otherwise, use up to ``MAX_REFINED_QUERIES`` AI-suggested queries
         and repeat.

    Diagram:
    classDiagram
        class KnowledgeAISearch {
            +CODXJuniorSettings settings
            +Knowledge knowledge
            +List~Knowledge~ child_knowledges
            +AI ai
            +ai_search(user_query, max_iterations) AISearchResult
            -_build_child_knowledges() List~Knowledge~
            -_search_queries(queries) List[Document]
            -_search_single_knowledge(knowledge, query) List[Document]
            -_check_sufficiency(user_query, documents) Dict
            -_generate_final_answer(user_query, documents) str
        }
    """

    def __init__(self, settings: CODXJuniorSettings) -> None:
        """
        Initialise the AI search with project settings.

        Child project Knowledge instances are lazily resolved on first search
        so that the constructor remains fast even for large dependency trees.

        Args:
            settings: Project-level configuration including model and path info.
        """
        self.settings = settings
        self.knowledge = Knowledge(settings=settings)
        self.ai: Optional[AI] = None
        # Resolved lazily on first call to _build_child_knowledges
        self._child_knowledges: Optional[List[Knowledge]] = None

    def _get_ai(self) -> AI:
        """
        Lazily initialise and return the AI helper.

        Returns:
            AI instance bound to this project.
        """
        if not self.ai:
            self.ai = AI(
                settings=self.settings,
                llm_model=self.settings.get_rag_model(),
                user=CodxUser(username=__name__),
            )
        return self.ai

    def _build_child_knowledges(self) -> List[Knowledge]:
        """
        Resolve child/dependency project settings and build a Knowledge instance
        for each one.

        Uses ``get_project_dependencies`` from the project discovery module.
        Any project that cannot be resolved is skipped with a warning.

        Diagram:
        flowchart TD
            A[_build_child_knowledges] --> B[get_project_dependencies]
            B --> C{dependency settings valid?}
            C -- Yes --> D[Instantiate Knowledge for dependency]
            C -- No  --> E[Log warning and skip]
            D --> F[Append to child list]
            F --> G[Return child Knowledge list]

        Returns:
            List of Knowledge instances for each resolved child project.
        """
        if self._child_knowledges is not None:
            return self._child_knowledges

        # Deferred import to avoid circular dependencies at module load time
        from codx.junior.project.project_discover import get_project_dependencies

        child_knowledges: List[Knowledge] = []

        try:
            dependencies = get_project_dependencies(self.settings)
        except Exception as exc:
            logger.warning(
                "Could not resolve project dependencies for '%s': %s",
                self.settings.project_name,
                exc,
            )
            self._child_knowledges = child_knowledges
            return child_knowledges

        for dep_settings in dependencies:
            if dep_settings is None:
                logger.warning(
                    "Skipping None dependency settings for project '%s'.",
                    self.settings.project_name,
                )
                continue
            try:
                child_knowledges.append(Knowledge(settings=dep_settings))
                logger.info(
                    "Registered child knowledge for project '%s'.",
                    dep_settings.project_name,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to build Knowledge for child project '%s': %s",
                    getattr(dep_settings, "project_name", dep_settings),
                    exc,
                )

        self._child_knowledges = child_knowledges
        logger.info(
            "Resolved %d child knowledge bases for project '%s'.",
            len(child_knowledges),
            self.settings.project_name,
        )
        return self._child_knowledges

    async def _search_single_knowledge(
        self,
        knowledge: Knowledge,
        query: str,
    ) -> List[Document]:
        """
        Run a single search query against a single Knowledge instance
        in a thread-pool executor so the synchronous call does not block
        the async event loop.

        The originating project name is stamped onto every returned document
        via ``_tag_documents_with_project`` so cross-project provenance is
        preserved through deduplication and prompt formatting.

        Args:
            knowledge: The Knowledge instance to search.
            query:     The query string.

        Returns:
            List of Document objects tagged with the originating project name.
        """
        loop = asyncio.get_event_loop()
        project_name = getattr(knowledge.settings, "project_name", "unknown")
        logger.info(
            "Searching project '%s' with query: %s", project_name, query
        )
        try:
            results: List[Document] = await loop.run_in_executor(
                None, knowledge.search, query
            )
            # Tag each document with its originating project so callers can
            # trace cross-project provenance in the final answer.
            tagged = _tag_documents_with_project(results, project_name)
            logger.info(
                "Project '%s' query '%s' returned %d documents.",
                project_name,
                query,
                len(tagged),
            )
            return tagged
        except Exception as exc:
            logger.warning(
                "Search failed for project '%s' query '%s': %s",
                project_name,
                query,
                exc,
            )
            return []

    async def _search_queries(self, queries: List[str]) -> List[Document]:
        """
        Execute one or more search queries concurrently across ALL knowledge
        bases (current project + all child/dependency projects).

        Each (query, knowledge) combination is dispatched as an independent
        asyncio task.  Results from all tasks are merged, filtered by minimum
        BM25 score, ranked, and capped to the top ``TOP_DOCUMENTS_LIMIT``
        documents before being returned.

        Filtering guarantees that only high-confidence results (score >
        ``MINIMUM_SCORE_THRESHOLD``) influence the AI sufficiency check and
        final answer generation, preventing low-quality path-matched files
        from diluting the context window.

        Diagram:
        flowchart TD
            A[queries list] --> B[Build all_knowledges: current + children]
            B --> C[Cartesian product: query x knowledge]
            C --> D[asyncio.gather all _search_single_knowledge tasks]
            D --> E[Flatten results - each doc tagged with project_name]
            E --> F[_deduplicate_documents]
            F --> G[_filter_and_rank_documents]
            G --> H[Return top TOP_DOCUMENTS_LIMIT documents]

        Args:
            queries: One or more search query strings.

        Returns:
            At most ``TOP_DOCUMENTS_LIMIT`` Document objects with BM25 score
            above ``MINIMUM_SCORE_THRESHOLD``, each tagged with its originating
            ``project_name``, deduplicated and sorted by descending score.
        """
        # Current project + all child/dependency projects
        all_knowledges: List[Knowledge] = [
            self.knowledge,
            *self._build_child_knowledges(),
        ]

        # Build one task per (query, knowledge) combination
        tasks = [
            self._search_single_knowledge(knowledge=kb, query=q)
            for q in queries
            for kb in all_knowledges
        ]

        logger.info(
            "Dispatching %d search tasks (%d queries x %d projects).",
            len(tasks),
            len(queries),
            len(all_knowledges),
        )

        gathered: List[List[Document]] = await asyncio.gather(
            *tasks,
            return_exceptions=False,
        )

        all_retrieved: List[Document] = []
        for docs in gathered:
            all_retrieved.extend(docs)

        # Deduplicate first so score comparisons during filtering are meaningful
        deduplicated = _deduplicate_documents(all_retrieved)
        logger.info(
            "After deduplication: %d unique document chunks from %d raw results.",
            len(deduplicated),
            len(all_retrieved),
        )

        # Filter to high-confidence results and cap to the top N by score
        filtered = _filter_and_rank_documents(deduplicated)
        logger.info(
            "After score filtering (> %.1f) and ranking: %d documents kept "
            "(limit=%d).",
            MINIMUM_SCORE_THRESHOLD,
            len(filtered),
            TOP_DOCUMENTS_LIMIT,
        )

        return filtered

    async def _check_sufficiency(
        self,
        user_query: str,
        documents: List[Document],
    ) -> Dict[str, Any]:
        """
        Ask the AI whether the current document set is sufficient to answer the query.

        Uses ``a_chat`` (async) so the call does not block the event loop.

        The AI may return up to ``MAX_REFINED_QUERIES`` alternative search
        queries in the ``refined_queries`` list when the current documents are
        not sufficient.

        Args:
            user_query: The original or refined search query.
            documents:  Documents retrieved so far (tagged with project_name).

        Returns:
            Dictionary with keys:
              - ``is_sufficient`` (bool): True if documents are enough.
              - ``reasoning`` (str): Explanation from the AI.
              - ``refined_queries`` (List[str]): Up to 3 queries to try next
                when not sufficient.
        """
        documents_text = _format_documents_for_prompt(documents)
        prompt = SUFFICIENCY_CHECK_PROMPT.format(
            user_query=user_query,
            documents_text=documents_text,
            max_refined_queries=MAX_REFINED_QUERIES,
        )

        logger.info("Checking sufficiency for query: %s", user_query)
        messages = await self._get_ai().a_chat(prompt=prompt)
        response_content = messages[-1].content.strip()

        # Extract the JSON block from the AI response
        json_blocks = list(extract_json_blocks(response_content))
        if json_blocks:
            result = json_blocks[0]
            # Normalise: ensure refined_queries is always a list of strings
            refined = result.get("refined_queries", [])
            if isinstance(refined, str):
                # Gracefully handle AI returning a plain string instead of a list
                refined = [refined] if refined.strip() else []
            result["refined_queries"] = [q for q in refined if q and q.strip()]
            logger.debug("Sufficiency check result: %s", result)
            return result

        # Fallback: if JSON parsing fails, treat as sufficient to avoid infinite loop
        logger.warning(
            "Could not parse sufficiency JSON from AI response; treating as sufficient. "
            "Response: %s",
            response_content,
        )
        return {
            "is_sufficient": True,
            "reasoning": "Could not parse AI response; defaulting to sufficient.",
            "refined_queries": [],
        }

    async def _generate_final_answer(
        self,
        user_query: str,
        documents: List[Document],
    ) -> str:
        """
        Generate the final answer to the user's question from the collected documents.

        Uses ``a_chat`` (async) so the call does not block the event loop.
        The prompt instructs the AI to mention the originating project when
        referencing specific pieces of information.

        Args:
            user_query: The original question from the user.
            documents:  All documents gathered across iterations and projects,
                        each tagged with a ``project_name`` metadata field.

        Returns:
            AI-generated answer string.
        """
        documents_text = _format_documents_for_prompt(documents)
        prompt = FINAL_ANSWER_PROMPT.format(
            user_query=user_query,
            documents_text=documents_text,
        )

        logger.info("Generating final answer for query: %s", user_query)
        messages = await self._get_ai().a_chat(prompt=prompt)
        return messages[-1].content.strip()

    async def ai_search(
        self,
        user_query: str,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ) -> AISearchResult:
        """
        Run an iterative AI-assisted search to answer the user's question.

        Searches span the current project **and** all dependency projects
        returned by ``get_project_dependencies``.  Each document in the result
        carries a ``project_name`` field in its metadata identifying its origin.

        Only documents with BM25 score > ``MINIMUM_SCORE_THRESHOLD`` are
        considered at each iteration; from those only the top
        ``TOP_DOCUMENTS_LIMIT`` by score are passed to the AI.  This keeps the
        context window focused on the highest-quality evidence and avoids
        polluting the prompt with low-relevance path-matched files.

        Each iteration fans out to all (query × project) combinations in
        parallel so that both multiple refined queries and multiple child
        projects are searched simultaneously.  All results are accumulated
        and deduplicated before the next sufficiency check.

        All AI calls are made via ``a_chat`` (async) to avoid blocking the
        event loop.

        Diagram:
        flowchart TD
            A[Start: user_query] --> B[Resolve child knowledges via get_project_dependencies]
            B --> C[Search current + dependency projects with current queries]
            C --> D[Tag docs with project_name]
            D --> E[Filter: score > MINIMUM_SCORE_THRESHOLD, keep top TOP_DOCUMENTS_LIMIT]
            E --> F[Accumulate and deduplicate documents across iterations]
            F --> G{Any documents?}
            G -- No --> H[Generate final answer]
            G -- Yes --> I[AI: sufficient?]
            I -- Yes --> H
            I -- No and iterations left --> J[Collect up-to-3 refined_queries]
            J --> C
            I -- No and max iterations --> H
            H --> K[Return AISearchResult with projects_searched]

        Args:
            user_query:     The user's natural-language question.
            max_iterations: Maximum number of search+check cycles allowed.

        Returns:
            An AISearchResult containing the answer, supporting documents
            (each tagged with ``project_name``), and the names of all
            projects that were searched.
        """
        effective_max_iterations = max_iterations or DEFAULT_MAX_ITERATIONS
        logger.info(
            "ai_search started | query=%s | max_iterations=%d",
            user_query,
            effective_max_iterations,
        )

        # Resolve child knowledges once upfront so the log message is clear
        child_knowledges = self._build_child_knowledges()
        all_project_names: List[str] = [self.settings.project_name] + [
            getattr(kb.settings, "project_name", "unknown")
            for kb in child_knowledges
        ]
        logger.info(
            "ai_search will span %d project(s): %s",
            len(all_project_names),
            all_project_names,
        )

        # Track all queries issued throughout the search
        queries_used: List[str] = [user_query]
        current_queries: List[str] = [user_query]
        all_documents: List[Document] = []
        total_iterations = 0

        for iteration in range(1, effective_max_iterations + 1):
            total_iterations = iteration
            logger.info(
                "Iteration %d/%d | queries=%s",
                iteration,
                effective_max_iterations,
                current_queries,
            )

            # ── Search all projects in parallel for all current queries ───────
            # _search_queries already applies score filtering and top-N ranking
            retrieved = await self._search_queries(current_queries)
            logger.info(
                "Iteration %d: %d high-quality documents (score > %.1f, top %d) "
                "across %d queries and %d project(s).",
                iteration,
                len(retrieved),
                MINIMUM_SCORE_THRESHOLD,
                TOP_DOCUMENTS_LIMIT,
                len(current_queries),
                len(all_project_names),
            )

            # Accumulate and deduplicate across iterations
            all_documents = _deduplicate_documents(all_documents + retrieved)
            logger.debug(
                "Accumulated %d unique document chunks after iteration %d.",
                len(all_documents),
                iteration,
            )

            # ── Early exit when no documents have been found at all ───────────
            if not all_documents:
                logger.warning(
                    "No qualifying documents found for queries %s across any project; "
                    "stopping early.",
                    current_queries,
                )
                break

            # ── Check sufficiency ─────────────────────────────────────────────
            sufficiency = await self._check_sufficiency(
                user_query=user_query,
                documents=all_documents,
            )

            is_sufficient: bool = sufficiency.get("is_sufficient", True)
            refined_queries: List[str] = sufficiency.get("refined_queries", [])

            logger.info(
                "Sufficiency check iteration %d: is_sufficient=%s, reasoning=%s",
                iteration,
                is_sufficient,
                sufficiency.get("reasoning", ""),
            )

            if is_sufficient or iteration == effective_max_iterations:
                logger.info(
                    "Stopping search after iteration %d "
                    "(sufficient=%s, max_reached=%s).",
                    iteration,
                    is_sufficient,
                    iteration == effective_max_iterations,
                )
                break

            if refined_queries:
                # Cap to the maximum allowed number of parallel queries
                capped_queries = refined_queries[:MAX_REFINED_QUERIES]
                logger.info(
                    "Using %d refined queries for next iteration: %s",
                    len(capped_queries),
                    capped_queries,
                )
                queries_used.extend(capped_queries)
                current_queries = capped_queries
            else:
                # No refinement provided; stop iterating to avoid spinning
                logger.info(
                    "No refined queries provided; stopping after iteration %d.",
                    iteration,
                )
                break

        # ── Generate the final answer ─────────────────────────────────────────
        answer = await self._generate_final_answer(
            user_query=user_query,
            documents=all_documents,
        )

        result = AISearchResult(
            user_query=user_query,
            max_iterations=effective_max_iterations,
            total_iterations=total_iterations,
            answer=answer,
            documents=all_documents,
            queries_used=queries_used,
            projects_searched=all_project_names,
        )

        logger.info(
            "ai_search complete | total_iterations=%d | documents=%d | "
            "queries=%d | projects=%d",
            total_iterations,
            len(all_documents),
            len(queries_used),
            len(all_project_names),
        )

        return result

# Made with ❤️ by codx-junior