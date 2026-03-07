# Knowledge Database

The `KnowledgeDB` class manages the interaction with a Milvus database for storing and retrieving document data. It's designed to index and search through documents, leveraging Milvus for efficient full-text search capabilities.

## Database Connection and Initialization

The module initializes a Milvus client connection at the module level.

```python
# /codx/junior/knowledge/knowledge_db.py
CODX_JUNIOR_MILVUS_URL = os.environ.get("CODX_JUNIOR_MILVUS_URL", "http://milvus:19530")

logger = logging.getLogger(__name__)

def connect_milvus_client():
    try:
        MILVUS["client"] = MilvusClient(
                        uri=CODX_JUNIOR_MILVUS_URL,
                        token="root:Milvus"
                    )
        return MILVUS["client"]
    except Exception as ex:
        logger.exception("Milvus not ready", ex)
    return None

MILVUS = {}
connect_milvus_client()

def get_milvus_client():
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
```

The `KnowledgeDB` class itself is initialized with project settings, which determine the database path and collection names.

```python
# /codx/junior/knowledge/knowledge_db.py
class KnowledgeDB:
    # ... (other attributes)

    def __init__(self, settings: CODXJuniorSettings):
        self.ai = None
        self.settings = settings

        self.path = self.settings.project_path
        self.index_name = re.sub('[^a-zA-Z0-9\._]', '', slugify(str(self.path))).strip()
        self.index_fulltext_name = f"{self.index_name}_full_text"

        self.db_path = f"{settings.codx_path}/db/{self.index_name}"
        os.makedirs(self.db_path, exist_ok=True)

        self.db_file = f"{self.db_path}/milvus.db"
        self.db_file_list = f"{self.db_path}/{self.index_name}_file.json"
        self.embedding = None

        self.connect_db()

        self.refresh_last_update()
    # ... (rest of the class)
```

## Database Schema and Fields

The `KNOWLEDGE_FIELDS` dictionary defines the schema for documents stored in Milvus. This includes fields for metadata, content, source, keywords, category, and last update timestamp.

```python
# /codx/junior/knowledge/knowledge_db.py
KNOWLEDGE_FIELDS = {
    "id":           { "datatype": DataType.INT64, "is_primary": True, "auto_id": True },
    "metadata":     { "datatype": DataType.JSON, "enable_analyzer": False },
    "page_content": { "datatype": DataType.VARCHAR, "max_length": 65535, "enable_analyzer": True },
    "source":       { "datatype": DataType.VARCHAR, "max_length": 200, "enable_analyzer": True },
    "keywords":     { "datatype": DataType.VARCHAR, "max_length": 5000, "enable_analyzer": True },
    "category":     { "datatype": DataType.VARCHAR, "max_length": 300, "enable_analyzer": True },
    "last_update":  { "datatype": DataType.INT32, "enable_analyzer": True },
}
```

A sparse vector field named `sparse` is also added for BM25 full-text search.

```python
# /codx/junior/knowledge/knowledge_db.py
    def create_db(self):
        # ... (other schema creation)
        schema.add_field(field_name="sparse", datatype=DataType.SPARSE_FLOAT_VECTOR)

        bm25_function = Function(
            name="text_bm25_emb",
            input_field_names=["page_content"],
            output_field_names=["sparse"],
            function_type=FunctionType.BM25,
        )

        schema.add_function(bm25_function)

        index_params = self.db.prepare_index_params()
        index_params.add_index(
            field_name="sparse",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="BM25",
            params={
                "inverted_index_algo": "DAAT_MAXSCORE",
                "bm25_k1": 1.2,
                "bm25_b": 0.75
            }
        )
        # ... (rest of collection creation)
```

## Document Indexing

The `index_documents` method takes a list of `Document` objects and prepares them for insertion into Milvus. It combines relevant fields into `page_content` for full-text indexing and sets the `last_update` timestamp.

```python
# /codx/junior/knowledge/knowledge_db.py
    @profile_function
    def index_documents(self, documents: [Document]):
        data_search = []
        for doc in documents:
            try:
                content = list(filter(lambda x: x,
                  [
                    doc.metadata["source"],
                    doc.page_content,
                    doc.metadata.get("summary"),
                    doc.metadata.get("tags")
                  ]
                ))
                page_content = "\n".join(content)
                search_doc = {
                  "metadata": doc.metadata,
                  "page_content": page_content,
                  "source": doc.metadata["source"],
                  "keywords": ",".join(doc.metadata.get("keywords",[])),
                  "category": doc.metadata.get("category",''),
                  "last_update": int(time.time())
                }
                data_search.append(search_doc)
                logger.info(f"Data processing document, len {len(doc.page_content)}, {doc.metadata}")

            except Exception as ex:
                logger.error(f"Error processing document, len {len(doc.page_content)}, {doc.metadata}: {ex}")


        try:
            res = self.db.insert(
                collection_name=self.index_fulltext_name,
                data=data_search
            )
            # logger.info(f"[Full text] Adding {data_search} documents: response {res}")

        except Exception as ex:
            if "float_vector" in str(ex):
                logger.error(f"Error inserting new documents for project {self.settings.project_name} - index {self.index_fulltext_name} {ex}, trying to restart index")
                self.reset()
            else:
                raise ex
```

## Document Deletion

The `delete_documents` method allows for the removal of documents based on their `source` field.

```python
# /codx/junior/knowledge/knowledge_db.py
    @profile_function
    def delete_documents (self, sources: [str]):
        logger.info('Removing old documents')
        try:
            logger.info(f"Document ids to delete: {sources}")
            source_filters = "".join([
              'source in ["',
              '","'.join(sources),
             '"]'
            ])
            self.db.delete(
                collection_name=self.index_fulltext_name,
                filter=source_filters
            )
        except Exception as ex:
            logger.error("Error deleting sources: %s", sources)
```

## Searching Documents

### Raw Search

The `raw_search` method performs a direct query to the Milvus collection using a provided filter string.

```python
# /codx/junior/knowledge/knowledge_db.py
    def raw_search(self,
                  search_filter: str,
                  output_fields=None,
                  limit=None):
        if not output_fields:
            output_fields = list(KNOWLEDGE_FIELDS.keys())
        # logger.info("raw_search: %s, %s", search_filter, output_fields)
        results = self.db.query(
            collection_name=self.index_fulltext_name,
            filter=search_filter,
            output_fields=output_fields,
            limit=limit
        )
        return self.db_results_to_documents(results)
```

### Full-Text Search

The `search` method utilizes Milvus's search capabilities, specifically the sparse vector field, for full-text queries.

```python
# /codx/junior/knowledge/knowledge_db.py
    @profile_function
    def search(self, query: str, _limit: int = 50):
        search_params = {
            'params': { 'drop_ratio_search': 0.2 },
        }
        results = self.db.search(
            collection_name=self.index_fulltext_name,
            data=[query],
            anns_field='sparse',
            output_fields=['page_content', 'metadata'], # Fields to return in search results; sparse field cannot be output
            limit=_limit,
            search_params=search_params
        )
        results = reduce(lambda x,y: x + y, results)
        logger.info(f"[Full text search] '{query}' returned {len(results)} results")

        return self.db_results_to_documents(results)
```

The `db_results_to_documents` helper function converts the raw Milvus search results into a list of `Document` objects.

```python
# /codx/junior/knowledge/knowledge_db.py
    def db_results_to_documents(self, results):
        documents = []
        try:
            for entry in list(results):
                _id = entry.get("id", 0)
                entity = entry.get("entity") or entry
                distance = float(entry.get("distance", "0"))
                entity["db_distance"] = distance

                metadata = entity.get("metadata", { })
                for prop in ["source", "keywords", "category", "last_update"]:
                    value = entry.get(prop)
                    if value:
                        metadata[prop] = value

                documents.append(
                    Document(id=_id,
                        page_content=entity.get("page_content", ""),
                        metadata=metadata))
            return documents
        except Exception as ex:
            logger.exception("ERROR db_results_to_documents: %s\n%s", ex, results[0])
```

## Utility Methods

### Get Database Information

The `get_db_info` method retrieves statistics about the Milvus collection.

```python
# /codx/junior/knowledge/knowledge_db.py
    def get_db_info(self):
        return {
            "embeddings": {
                "index": self.index_fulltext_name,
                **self.db.get_collection_stats(
                          collection_name=self.index_fulltext_name,
                          timeout=5)
            },
        }
```

### Get All Sources

The `get_all_sources` method retrieves all unique sources present in the database, along with their last update timestamp. If the index is corrupted (e.g., missing fields), it will attempt to reset it.

```python
# /codx/junior/knowledge/knowledge_db.py
    def get_all_sources(self):
        try:
            documents = self.raw_search(search_filter='source != ""', output_fields=["source", "last_update"])
            result = {}

            for doc in documents:
                source = doc.metadata["source"]
                last_update = doc.metadata["last_update"]

                if source in result:
                    if result[source].metadata["last_update"] >= last_update:
                        continue

                result[source] = doc

            return result

        # Log any exceptions encountered during execution.
        except Exception as ex:
            logger.error("Error reading project '%s' sources: %s", self.settings.project_name, ex)
            error = str(ex)
            if "field source not exist" in error or \
                "field last_update not exist" in error:
                # Corrupted index
                self.reset()

        # Fall back to returning an empty list if an error occurs.
        return {}
```

### Get All Categories

The `get_all_categories` method returns a list of all unique categories found in the documents.

```python
# /codx/junior/knowledge/knowledge_db.py
    def get_all_categoties(self):
        documents = self.raw_search(search_filter='source != ""', output_fields=["category"])
        return list(set([ doc.metadata.get("category", "Unknown") for doc in documents]))
```

## Resetting the Database

The `reset` method drops the current Milvus collection and recreates it, effectively clearing all indexed data.

```python
# /codx/junior/knowledge/knowledge_db.py
    def reset(self):
        logger.info(f"Deleting index {self.settings.project_name}")

        if os.path.isfile(self.db_file_list):
            os.remove(self.db_file_list)
        self.last_update = None

        logger.info(f"Deleting index {self.settings.project_name}")

        self.db.drop_collection(
            collection_name=self.index_fulltext_name
        )
        self.create_db()
```