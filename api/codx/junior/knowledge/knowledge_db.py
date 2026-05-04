import os
import re
import logging
import shutil
import json
import time
from datetime import datetime
from contextlib import contextmanager
from functools import reduce
from typing import Any, Dict, List, Optional

from slugify import slugify
from pathlib import Path

from pymilvus import MilvusClient, DataType, Function, FunctionType
from pymilvus.exceptions import MilvusException

from langchain_core.documents import Document

from codx.junior.model.model import CodxUser

from codx.junior.ai import AI
from codx.junior.settings import CODXJuniorSettings

from codx.junior.utils.utils import calculate_md5
from codx.junior.profiling.profiler import profile_function

CODX_JUNIOR_MILVUS_URL = os.environ.get("CODX_JUNIOR_MILVUS_URL", "http://milvus:19530")

logger = logging.getLogger(__name__)

# Field names used in metrics queries
FIELD_SOURCE = "source"
FIELD_LAST_UPDATE = "last_update"
FIELD_CATEGORY = "category"
FIELD_KEYWORDS = "keywords"
FIELD_PAGE_CONTENT = "page_content"
FIELD_METADATA = "metadata"
FIELD_SPARSE = "sparse"

# Metadata key used to surface BM25 relevance score to callers
FIELD_SCORE = "score"

# Default search filter for non-empty sources
NON_EMPTY_SOURCE_FILTER = 'source != ""'


def connect_milvus_client() -> Optional[MilvusClient]:
    """
    Attempt to create and store a MilvusClient connection.

    Returns:
        MilvusClient instance on success, None on failure.
    """
    try:
        MILVUS["client"] = MilvusClient(
            uri=CODX_JUNIOR_MILVUS_URL,
            token="root:Milvus"
        )
        return MILVUS["client"]
    except Exception as ex:
        logger.exception("Milvus not ready: %s", ex)
    return None


MILVUS: Dict[str, Any] = {}
connect_milvus_client()


def get_milvus_client() -> MilvusClient:
    """
    Retrieve a healthy MilvusClient, reconnecting if necessary.

    Returns:
        A connected MilvusClient instance.

    Raises:
        Exception: If connection cannot be established.
    """
    client = MILVUS.get("client")
    if not client:
        if not connect_milvus_client():
            raise Exception("Couldn't connect to MILVUS server, check logs.")
    try:
        client.list_databases()
        return client
    except Exception as ex:
        logger.exception("Error connecting to MilvusDB: %s", ex)

    connect_milvus_client()
    return MILVUS["client"]


class DBDocument(Document):
    """Document subclass that carries an additional database identifier."""

    db_id: str = None

    def __init__(self, db_id: str, metadata: Dict[str, Any], page_content: str = ""):
        Document.__init__(self, page_content=page_content, metadata=metadata)
        self.db_id = db_id


KNOWLEDGE_FIELDS: Dict[str, Any] = {
    "id":           {"datatype": DataType.INT64, "is_primary": True, "auto_id": True},
    "metadata":     {"datatype": DataType.JSON, "enable_analyzer": False},
    "page_content": {"datatype": DataType.VARCHAR, "max_length": 65535, "enable_analyzer": True},
    "source":       {"datatype": DataType.VARCHAR, "max_length": 200, "enable_analyzer": True},
    "keywords":     {"datatype": DataType.VARCHAR, "max_length": 5000, "enable_analyzer": True},
    "category":     {"datatype": DataType.VARCHAR, "max_length": 300, "enable_analyzer": True},
    "last_update":  {"datatype": DataType.INT32, "enable_analyzer": True},
}


class KnowledgeDB:
    """
    Manages a Milvus-backed full-text knowledge base for a project.

    Uses BM25 sparse vectors for full-text retrieval. Each project gets its
    own named collection derived from the project path.

    Diagram:
    classDiagram
        class KnowledgeDB {
            +str db_path
            +str index_name
            +str index_fulltext_name
            +AI ai
            +connect_db()
            +create_db()
            +reset()
            +index_documents(documents)
            +delete_documents(sources)
            +search(query, limit) List[Document]
            +raw_search(filter, output_fields, limit)
            +get_all_sources()
            +get_all_categories()
            +get_db_info()
            +get_collection_metrics()
        }

    Note: Documents returned by search() include a ``score`` key in their
    metadata containing the BM25 relevance score for the query.
    """

    db: Any
    db_path: str
    db_file_list: str
    index_name: str
    ai: Any
    last_update: Optional[float]

    def __init__(self, settings: CODXJuniorSettings):
        """
        Initialise KnowledgeDB for the given project settings.

        Args:
            settings: Project-level settings including paths and names.
        """
        self.ai = None
        self.settings = settings

        self.path = self.settings.abs_project_path
        self.index_name = re.sub(r'[^a-zA-Z0-9._]', '', slugify(str(self.path))).strip()
        self.index_fulltext_name = f"{self.index_name}_full_text"

        self.db_path = f"{settings.codx_path}/db/{self.index_name}"
        os.makedirs(self.db_path, exist_ok=True)

        self.db_file = f"{self.db_path}/milvus.db"
        self.db_file_list = f"{self.db_path}/{self.index_name}_file.json"
        self.embedding = None

        self.connect_db()
        self.refresh_last_update()

    def __del__(self):
        pass

    def get_ai(self) -> AI:
        """
        Lazily initialise and return the AI helper.

        Returns:
            AI instance bound to this project.
        """
        if not self.ai:
            self.ai = AI(settings=self.settings, user=CodxUser(username=__name__))
        return self.ai

    def refresh_last_update(self) -> None:
        """Refresh the cached last-update timestamp from the file-list file."""
        if os.path.isfile(self.db_file_list):
            self.last_update = os.path.getmtime(self.db_file_list)

    def connect_db(self) -> None:
        """Connect to the Milvus server and ensure the collection exists."""
        try:
            self.db = get_milvus_client()
            self.create_db()
        except Exception as ex:
            logger.error(
                "Error connecting to milvus DB: %s - settings: %s", ex, self.settings
            )

    def create_db(self) -> None:
        """
        Create the Milvus database and full-text collection if they don't exist.

        Sets up the BM25 sparse vector schema and SPARSE_INVERTED_INDEX.
        """
        data_base_list = self.db.list_databases()
        if self.index_fulltext_name not in data_base_list:
            self.db.create_database(db_name=self.index_fulltext_name)

        collections = self.db.list_collections()
        if self.index_fulltext_name in collections:
            return

        schema = self.db.create_schema()
        for field_name, settings in KNOWLEDGE_FIELDS.items():
            schema.add_field(field_name=field_name, **settings)

        # Sparse field stores BM25 embeddings generated by the built-in function
        schema.add_field(field_name=FIELD_SPARSE, datatype=DataType.SPARSE_FLOAT_VECTOR)

        bm25_function = Function(
            name="text_bm25_emb",
            input_field_names=[FIELD_PAGE_CONTENT],
            output_field_names=[FIELD_SPARSE],
            function_type=FunctionType.BM25,
        )
        schema.add_function(bm25_function)

        index_params = self.db.prepare_index_params()
        index_params.add_index(
            field_name=FIELD_SPARSE,
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="BM25",
            params={
                "inverted_index_algo": "DAAT_MAXSCORE",
                "bm25_k1": 1.2,
                "bm25_b": 0.75,
            },
        )

        self.db.create_collection(
            collection_name=self.index_fulltext_name,
            schema=schema,
            index_params=index_params,
        )

        collection_view = self.db.describe_collection(
            collection_name=self.index_fulltext_name
        )
        logger.info("New full-text index collection created: %s", collection_view)

    def reset(self) -> None:
        """Drop the collection and file-list, then recreate from scratch."""
        logger.info("Deleting index for project '%s'", self.settings.project_name)

        if os.path.isfile(self.db_file_list):
            os.remove(self.db_file_list)
        self.last_update = None

        self.db.drop_collection(collection_name=self.index_fulltext_name)
        self.create_db()

    @profile_function
    def index_documents(self, documents: List[Document]) -> None:
        """
        Insert or upsert a list of documents into the full-text collection.

        Args:
            documents: LangChain Document objects to index.
        """
        data_search: List[Dict[str, Any]] = []

        for doc in documents:
            try:
                content_parts = list(filter(
                    None,
                    [
                        doc.metadata.get("source"),
                        doc.page_content,
                        doc.metadata.get("summary"),
                        doc.metadata.get("tags"),
                    ],
                ))
                page_content = "\n".join(content_parts)

                search_doc = {
                    "metadata": doc.metadata,
                    "page_content": page_content,
                    "source": doc.metadata["source"],
                    "keywords": ",".join(doc.metadata.get("keywords", [])),
                    "category": doc.metadata.get("category", ""),
                    "last_update": int(time.time()),
                }
                data_search.append(search_doc)
                logger.info(
                    "Data processing document, len %d, %s",
                    len(doc.page_content),
                    doc.metadata,
                )
            except Exception as ex:
                logger.error(
                    "Error processing document, len %d, %s: %s",
                    len(doc.page_content),
                    doc.metadata,
                    ex,
                )

        try:
            res = self.db.insert(
                collection_name=self.index_fulltext_name,
                data=data_search,
            )
            logger.debug("Inserted %d documents, response: %s", len(data_search), res)
        except MilvusException as ex:
            if "float_vector" in str(ex):
                logger.error(
                    "Error inserting documents for project '%s' - index '%s': %s. "
                    "Attempting index reset.",
                    self.settings.project_name,
                    self.index_fulltext_name,
                    ex,
                )
                self.reset()
            else:
                raise

    @profile_function
    def delete_documents(self, sources: List[str]) -> None:
        """
        Remove all documents whose source field matches any of the given paths.

        Args:
            sources: List of source paths to delete.
        """
        logger.info("Removing old documents for sources: %s", sources)
        try:
            source_filter = 'source in ["' + '","'.join(sources) + '"]'
            self.db.delete(
                collection_name=self.index_fulltext_name,
                filter=source_filter,
            )
        except MilvusException as ex:
            logger.error("Error deleting sources %s: %s", sources, ex)

    def raw_search(
        self,
        search_filter: str,
        output_fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[Document]:
        """
        Execute a scalar filter query against the collection.

        Args:
            search_filter: Milvus filter expression string.
            output_fields: Fields to return; defaults to all KNOWLEDGE_FIELDS.
            limit: Maximum number of results.

        Returns:
            List of Document objects matching the filter.
        """
        if not output_fields:
            output_fields = list(KNOWLEDGE_FIELDS.keys())

        results = self.db.query(
            collection_name=self.index_fulltext_name,
            filter=search_filter,
            output_fields=output_fields,
            limit=limit,
        )
        return self.db_results_to_documents(results)

    def get_db_info(self) -> Dict[str, Any]:
        """
        Return basic collection statistics.

        Returns:
            Dictionary with embedding index name and collection stats.
        """
        return {
            "embeddings": {
                "index": self.index_fulltext_name,
                **self.db.get_collection_stats(
                    collection_name=self.index_fulltext_name,
                    timeout=5,
                ),
            },
        }

    def get_collection_metrics(self) -> Dict[str, Any]:
        """
        Aggregate key dashboard metrics for the project's full-text collection.

        Collects:
        - Row count from collection stats
        - Load state (whether the collection is in memory)
        - Schema description including field names and primary key
        - Index metadata for all indexes on the collection
        - Segment-level details when available

        Returns:
            Dictionary containing metrics, or an error dict on failure.

        Diagram:
        flowchart TD
            A[get_collection_metrics] --> B{Collection exists?}
            B -- No --> C[Return error dict]
            B -- Yes --> D[Fetch stats / row count]
            D --> E[Fetch load state]
            E --> F[Fetch schema description]
            F --> G[Fetch index info]
            G --> H[Fetch segment info]
            H --> I[Return metrics dict]
        """
        collection_name = self.index_fulltext_name

        # Verify the collection is present before querying
        existing_collections = self.db.list_collections()
        if collection_name not in existing_collections:
            logger.warning(
                "get_collection_metrics: collection '%s' not found", collection_name
            )
            return {"error": f"Collection '{collection_name}' not found"}

        try:
            # ── 1. Row count ─────────────────────────────────────────────────
            stats = self.db.get_collection_stats(
                collection_name=collection_name,
                timeout=5,
            )
            # MilvusClient returns {"row_count": N} as a string value
            row_count = int(stats.get("row_count", 0))
            logger.debug(
                "Collection '%s' row_count: %d", collection_name, row_count
            )

            # ── 2. Load state ─────────────────────────────────────────────────
            # get_load_state returns {"state": <LoadState>} in pymilvus v2.x
            load_state_response = self.db.get_load_state(
                collection_name=collection_name
            )
            load_state = str(load_state_response.get("state", "Unknown"))
            logger.debug(
                "Collection '%s' load_state: %s", collection_name, load_state
            )

            # ── 3. Schema description ─────────────────────────────────────────
            collection_description = self.db.describe_collection(
                collection_name=collection_name
            )
            fields_info: List[Dict[str, Any]] = collection_description.get("fields", [])
            field_names = [f.get("name", "") for f in fields_info]

            # Identify the primary key field
            primary_key_name = next(
                (f.get("name", "") for f in fields_info if f.get("is_primary")),
                "unknown",
            )
            collection_desc_text = collection_description.get("description", "")

            # ── 4. Index information ──────────────────────────────────────────
            index_infos: List[Dict[str, Any]] = []
            try:
                indexes = self.db.list_indexes(collection_name=collection_name)
                for index_name in indexes:
                    index_detail = self.db.describe_index(
                        collection_name=collection_name,
                        index_name=index_name,
                    )
                    index_infos.append({
                        "index_name": index_name,
                        "field": index_detail.get("field_name", ""),
                        "index_type": index_detail.get("index_type", ""),
                        "metric_type": index_detail.get("metric_type", ""),
                        "params": index_detail.get("params", {}),
                    })
                    logger.debug(
                        "Index info for '%s' on collection '%s': %s",
                        index_name,
                        collection_name,
                        index_detail,
                    )
            except MilvusException as index_ex:
                logger.warning(
                    "Could not fetch index info for collection '%s': %s",
                    collection_name,
                    index_ex,
                )

            # ── 5. Segment / partition info (best-effort) ─────────────────────
            partition_info: Dict[str, Any] = {}
            try:
                partitions = self.db.list_partitions(collection_name=collection_name)
                partition_info = {
                    "total_partitions": len(partitions),
                    "partition_names": partitions,
                }
                logger.debug(
                    "Partition info for collection '%s': %s",
                    collection_name,
                    partition_info,
                )
            except MilvusException as part_ex:
                logger.warning(
                    "Could not fetch partition info for collection '%s': %s",
                    collection_name,
                    part_ex,
                )

            metrics: Dict[str, Any] = {
                "collection": collection_name,
                "row_count": row_count,
                "status": {
                    "load_state": load_state,
                },
                "schema": {
                    "description": collection_desc_text,
                    "fields": field_names,
                    "primary_key": primary_key_name,
                },
                "indexes": index_infos,
                "partitions": partition_info,
            }

            logger.info(
                "get_collection_metrics for '%s': row_count=%d, load_state=%s, "
                "indexes=%d, partitions=%s",
                collection_name,
                row_count,
                load_state,
                len(index_infos),
                partition_info,
            )
            return metrics

        except MilvusException as ex:
            logger.error(
                "MilvusException in get_collection_metrics for '%s': %s",
                collection_name,
                ex,
            )
            return {"error": str(ex)}

    @profile_function
    def search(self, query: str, _limit: int = 50) -> List[Document]:
        """
        Full-text BM25 search against the sparse vector index.

        Each returned Document will have a ``score`` key in its ``metadata``
        containing the BM25 relevance score (higher is more relevant).

        Diagram:
        flowchart TD
            A[search query] --> B[MilvusClient.search BM25]
            B --> C[Flatten result list-of-lists]
            C --> D[db_results_to_documents with include_score=True]
            D --> E[Return List of Documents with score in metadata]

        Args:
            query:  Natural-language query string.
            _limit: Maximum number of results to return.

        Returns:
            List of matching Document objects ordered by descending BM25 score.
            Each document's metadata contains a ``score`` float field.
        """
        search_params = {
            "params": {"drop_ratio_search": 0.2},
        }
        results = self.db.search(
            collection_name=self.index_fulltext_name,
            data=[query],
            anns_field=FIELD_SPARSE,
            output_fields=[FIELD_PAGE_CONTENT, FIELD_METADATA],
            limit=_limit,
            search_params=search_params,
        )
        # Flatten the list-of-lists returned by MilvusClient.search
        flat_results = reduce(lambda x, y: x + y, results)
        logger.info(
            "[Full text search] '%s' returned %d results", query, len(flat_results)
        )
        # Pass include_score=True so the BM25 distance is surfaced in metadata
        return self.db_results_to_documents(flat_results, include_score=True)

    def db_results_to_documents(
        self,
        results: Any,
        include_score: bool = False,
    ) -> List[Document]:
        """
        Convert raw Milvus query/search result entries to LangChain Documents.

        When ``include_score`` is True the BM25 relevance distance returned by
        Milvus is stored as ``metadata["score"]`` on every document, allowing
        callers to rank or display results by relevance.

        Diagram:
        flowchart TD
            A[raw Milvus results] --> B[iterate entries]
            B --> C[extract entity / metadata]
            C --> D{include_score?}
            D -- Yes --> E[set metadata score = distance]
            D -- No  --> F[skip score]
            E --> G[build Document]
            F --> G
            G --> H[append to documents list]

        Args:
            results:       Iterable of result dicts from Milvus (query or search).
            include_score: When True, store the BM25 distance in
                           ``metadata[FIELD_SCORE]``.

        Returns:
            List of Document objects with populated metadata (and optionally score).
        """
        documents: List[Document] = []
        try:
            for entry in list(results):
                _id = entry.get("id", 0)
                entity = entry.get("entity") or entry
                # BM25 distance — higher value means more relevant
                distance = float(entry.get("distance", "0"))

                metadata = entity.get("metadata", {})
                for prop in [FIELD_SOURCE, FIELD_KEYWORDS, FIELD_CATEGORY, FIELD_LAST_UPDATE]:
                    value = entry.get(prop)
                    if value:
                        metadata[prop] = value

                if include_score:
                    # Expose the BM25 relevance score so callers can surface it
                    metadata[FIELD_SCORE] = distance
                    logger.debug(
                        "Document id=%s source=%s score=%.4f",
                        _id,
                        metadata.get(FIELD_SOURCE, ""),
                        distance,
                    )
                metadata["project_id"] = self.settings.project_id
                metadata["project_name"] = self.settings.project_name,
                
                documents.append(
                    Document(
                        id=_id,
                        page_content=entity.get(FIELD_PAGE_CONTENT, ""),
                        metadata=metadata,
                    )
                )
            return documents
        except Exception as ex:
            logger.exception(
                "ERROR db_results_to_documents: %s\n%s", ex, results[0]
            )
        return documents

    def get_all_sources(self) -> Dict[str, Document]:
        """
        Return a mapping of source path → most-recently-indexed Document.

        Returns:
            Dict keyed by source path, value is the freshest Document for that source.
        """
        try:
            documents = self.raw_search(
                search_filter=NON_EMPTY_SOURCE_FILTER,
                output_fields=[FIELD_SOURCE, FIELD_LAST_UPDATE],
            )
            result: Dict[str, Document] = {}

            for doc in documents:
                source = doc.metadata[FIELD_SOURCE]
                last_update = doc.metadata[FIELD_LAST_UPDATE]

                if source in result:
                    if result[source].metadata[FIELD_LAST_UPDATE] >= last_update:
                        continue

                result[source] = doc

            return result

        except Exception as ex:
            logger.error(
                "Error reading project '%s' sources: %s",
                self.settings.project_name,
                ex,
            )
            error = str(ex)
            if "field source not exist" in error or "field last_update not exist" in error:
                # Corrupted index — rebuild from scratch
                self.reset()

        return {}

    def get_all_categoties(self) -> List[str]:
        """
        Return a deduplicated list of all category values in the collection.

        Returns:
            List of unique category strings.
        """
        documents = self.raw_search(
            search_filter=NON_EMPTY_SOURCE_FILTER,
            output_fields=[FIELD_CATEGORY],
        )
        return list({doc.metadata.get("category", "Unknown") for doc in documents})

# Made with ❤️ by codx-junior