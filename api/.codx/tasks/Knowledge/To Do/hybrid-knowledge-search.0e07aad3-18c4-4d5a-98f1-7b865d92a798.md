# [[{"id": "0e07aad3-18c4-4d5a-98f1-7b865d92a798", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": [], "profiles": [], "users": ["admin"], "name": "Hybrid knowledge search", "description": "The conversation discusses building a hybrid search engine using Milvus 2.5, which supports both semantic and full-text searches. The setup involves creating a data schema with fields for text and vectors, and using functions to convert text into sparse vectors based on BM25. Search indices are created for both dense and sparse vectors, enabling hybrid search capabilities. A Python class, `HybridSearchEngine`, is proposed to manage indexing and searching documents, utilizing Milvus clients for operations. The class facilitates document insertion and hybrid searching, ranking results using both semantic and full-text search criteria.", "created_at": "2025-07-05 15:09:47.604527", "updated_at": "2025-07-08T05:50:03.695034", "mode": "chat", "kanban_id": "", "column_id": "", "board": "Knowledge", "column": "To Do", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/Knowledge/To Do/hybrid-knowledge-search.0e07aad3-18c4-4d5a-98f1-7b865d92a798.md", "model": "", "visibility": "", "knowledge_topics": []}]]
## [[{"doc_id": "3ddece2f-90cd-42a2-bc4b-03be15438772", "role": "user", "task_item": "", "think": "", "hide": false, "improvement": false, "created_at": "2025-07-05 15:09:47.602508", "updated_at": "2025-07-05 15:09:47.602545", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true}]]
We must create a hybryd knowledge search engine for searching on project's files.
Summaryze and structurte this post. Create a class for managing a hybrid search engine, it will receive the collection name. Expose methods to pass documents to index/update and a search method.
Documents has: id, content, and a "metadata" dictionary. The content is what we must use for searching.
The search method will receive a query and a limit value and return a list of documents
```md

> https://milvus.io/blog/get-started-with-hybrid-semantic-full-text-search-with-milvus-2-5.md
Building the Data Schema and Search Indices
We import the required classes and functions:


from pymilvus import MilvusClient, DataType, Function, FunctionType, model


You may have noticed two new entries for Milvus 2.5, Function and FunctionType, which we will explain shortly.


Next we open the database with Milvus Standalone, that is, locally, and create the data schema. The schema comprises an integer primary key, a text string, a dense vector of dimension 384, and a sparse vector (of unlimited dimensionality). Note that Milvus Lite does not currently support full-text search, only Milvus Standalone and Milvus Distributed.


client = MilvusClient(uri="http://localhost:19530")


schema = client.create_schema()


schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True)
schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=1000, enable_analyzer=True)
schema.add_field(field_name="dense", datatype=DataType.FLOAT_VECTOR, dim=768),
schema.add_field(field_name="sparse", datatype=DataType.SPARSE_FLOAT_VECTOR)


{'auto_id': False, 'description': '', 'fields': [{'name': 'id', 'description': '', 'type': <DataType.INT64: 5>, 'is_primary': True, 'auto_id': True}, {'name': 'text', 'description': '', 'type': <DataType.VARCHAR: 21>, 'params': {'max_length': 1000, 'enable_analyzer': True}}, {'name': 'dense', 'description': '', 'type': <DataType.FLOAT_VECTOR: 101>, 'params': {'dim': 768}}, {'name': 'sparse', 'description': '', 'type': <DataType.SPARSE_FLOAT_VECTOR: 104>}], 'enable_dynamic_field': False}


You may have noticed the enable_analyzer=True parameter. This tells Milvus 2.5 to enable the lexical parser on this field and build a list of tokens and token frequencies, which are required for full-text search. The sparse field will hold a vector representation of the documentation as a bag-of-words produced from the parsing text.


But how do we connect the text and sparse fields, and tell Milvus how sparse should be calculated from text? This is where we need to invoke the Function object and add it to the schema:


bm25_function = Function(
    name="text_bm25_emb", # Function name
    input_field_names=["text"], # Name of the VARCHAR field containing raw text data
    output_field_names=["sparse"], # Name of the SPARSE_FLOAT_VECTOR field reserved to store generated embeddings
    function_type=FunctionType.BM25,
)


schema.add_function(bm25_function)


{'auto_id': False, 'description': '', 'fields': [{'name': 'id', 'description': '', 'type': <DataType.INT64: 5>, 'is_primary': True, 'auto_id': True}, {'name': 'text', 'description': '', 'type': <DataType.VARCHAR: 21>, 'params': {'max_length': 1000, 'enable_analyzer': True}}, {'name': 'dense', 'description': '', 'type': <DataType.FLOAT_VECTOR: 101>, 'params': {'dim': 768}}, {'name': 'sparse', 'description': '', 'type': <DataType.SPARSE_FLOAT_VECTOR: 104>, 'is_function_output': True}], 'enable_dynamic_field': False, 'functions': [{'name': 'text_bm25_emb', 'description': '', 'type': <FunctionType.BM25: 1>, 'input_field_names': ['text'], 'output_field_names': ['sparse'], 'params': {}}]}


The abstraction of the Function object is more general than that of applying full-text search. In the future, it may be used for other cases where one field needs to be a function of another field. In our case, we specify that sparse is a function of text via the function FunctionType.BM25. BM25 refers to a common metric in information retrieval used for calculating a query’s similarity to a document (relative to a collection of documents).


We use the default embedding model in Milvus, which is paraphrase-albert-small-v2:


embedding_fn = model.DefaultEmbeddingFunction()


The next step is to add our search indices. We have one for the dense vector and a separate one for the sparse vector. The index type is SPARSE_INVERTED_INDEX with BM25 since full-text search requires a different search method than those for standard dense vectors.


index_params = client.prepare_index_params()


index_params.add_index(
    field_name="dense",
    index_type="AUTOINDEX", 
    metric_type="COSINE"
)


index_params.add_index(
    field_name="sparse",
    index_type="SPARSE_INVERTED_INDEX", 
    metric_type="BM25"
)


Finally, we create our collection:


client.drop_collection('demo')
client.list_collections()


[]


client.create_collection(
    collection_name='demo', 
    schema=schema, 
    index_params=index_params
)


client.list_collections()


['demo']


And with that, we have an empty database set up to accept text documents and perform semantic and full-text searches!


Inserting Data and Performing Full-Text Search
Inserting data is no different than previous versions of Milvus:


docs = [
    'information retrieval is a field of study.',
    'information retrieval focuses on finding relevant information in large datasets.',
    'data mining and information retrieval overlap in research.'
]


embeddings = embedding_fn(docs)


client.insert('demo', [
    {'text': doc, 'dense': vec} for doc, vec in zip(docs, embeddings)
])


{'insert_count': 3, 'ids': [454387371651630485, 454387371651630486, 454387371651630487], 'cost': 0}


Let’s first illustrate a full-text search before we move on to hybrid search:


search_params = {
    'params': {'drop_ratio_search': 0.2},
}


results = client.search(
    collection_name='demo', 
    data=['whats the focus of information retrieval?'],
    output_fields=['text'],
    anns_field='sparse',
    limit=3,
    search_params=search_params
)


The search parameter drop_ratio_search refers to the proportion of lower-scoring documents to drop during the search algorithm.


Let’s view the results:


for hit in results[0]:
    print(hit)


{'id': 454387371651630485, 'distance': 1.3352930545806885, 'entity': {'text': 'information retrieval is a field of study.'}}
{'id': 454387371651630486, 'distance': 0.29726022481918335, 'entity': {'text': 'information retrieval focuses on finding relevant information in large datasets.'}}
{'id': 454387371651630487, 'distance': 0.2715056240558624, 'entity': {'text': 'data mining and information retrieval overlap in research.'}}


Performing Hybrid Semantic and Full-Text Search
Let’s now combine what we’ve learned to perform a hybrid search that combines separate semantic and full-text searches with a reranker:


from pymilvus import AnnSearchRequest, RRFRanker
query = 'whats the focus of information retrieval?'
query_dense_vector = embedding_fn([query])


search_param_1 = {
    "data": query_dense_vector,
    "anns_field": "dense",
    "param": {
        "metric_type": "COSINE",
    },
    "limit": 3
}
request_1 = AnnSearchRequest(**search_param_1)


search_param_2 = {
    "data": [query],
    "anns_field": "sparse",
    "param": {
        "metric_type": "BM25",
        "params": {"drop_ratio_build": 0.0}
    },
    "limit": 3
}
request_2 = AnnSearchRequest(**search_param_2)


reqs = [request_1, request_2]


ranker = RRFRanker()


res = client.hybrid_search(
    collection_name="demo",
    output_fields=['text'],
    reqs=reqs,
    ranker=ranker,
    limit=3
)
for hit in res[0]:
    print(hit)


{'id': 454387371651630485, 'distance': 0.032786883413791656, 'entity': {'text': 'information retrieval is a field of study.'}}
{'id': 454387371651630486, 'distance': 0.032258063554763794, 'entity': {'text': 'information retrieval focuses on finding relevant information in large datasets.'}}
{'id': 454387371651630487, 'distance': 0.0317460335791111, 'entity': {'text': 'data mining and information retrieval overlap in research.'}}


As you may have noticed, this is no different than a hybrid search with two separate semantic fields (available since Milvus 2.4). The results are identical to full-text search in this simple example, but for larger databases and keyword specific searches hybrid search typically has higher recall.
```
## [[{"doc_id": "dd7d163a-5995-454d-90d0-d860e398ed78", "role": "assistant", "task_item": "", "think": null, "hide": false, "improvement": false, "created_at": "2025-07-05 15:09:47.602508", "updated_at": "2025-07-05 15:09:47.602545", "images": [], "files": [], "meta_data": {"time_taken": 24.40639853477478, "first_chunk_time_taken": 0.00021147727966308594, "model": "gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false}]]
### Summary and Structure

**Title: Building a Hybrid Knowledge Search Engine Using Milvus 2.5**

The blog post explains how to create a hybrid search engine using Milvus 2.5 that can perform both semantic and full-text searches across project files. Below is a structured summary and a corresponding class implementation in Python for managing the hybrid search engine.

#### 1. Introduction
- Discusses the hybrid search capabilities of Milvus 2.5.
- Highlights the new features: Function and FunctionType.

#### 2. Constructing the Data Schema and Search Indices
- **Database Setup**: Connect to Milvus Standalone and create a schema.
- **Schema Design**: 
  - Integer primary key.
  - Text string with analyzer for full-text search.
  - Dense and sparse vectors for semantic embeddings.
- **Function Usage**: Defines sparse vectors as a function of text using BM25 for text similarity.
- **Indexing**: 
  - Dense vectors indexed with cosine similarity.
  - Sparse vectors indexed with SPARSE_INVERTED_INDEX for BM25.

#### 3. Inserting Data
- Example data inserted with embeddings generated using the default model.

#### 4. Performing Full-Text Search
- Full-text search is demonstrated with the collection, using drop ratio for search efficiency.

#### 5. Conducting Hybrid Semantic and Full-Text Search
- Explanation of combining semantic vector search with BM25 full-text search using RRF Ranker.

---

### Class Implementation: `HybridSearchEngine`

```python
from pymilvus import MilvusClient, DataType, Function, FunctionType, model, AnnSearchRequest, RRFRanker

class HybridSearchEngine:
    def __init__(self, collection_name):
        self.collection_name = collection_name
        self.client = MilvusClient(uri="http://localhost:19530")
        self.embedding_fn = model.DefaultEmbeddingFunction()
        self._setup_schema_and_indices()

    def _setup_schema_and_indices(self):
        # Create schema and add fields
        schema = self.client.create_schema()
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True)
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=1000, enable_analyzer=True)
        schema.add_field(field_name="dense", datatype=DataType.FLOAT_VECTOR, dim=768)
        schema.add_field(field_name="sparse", datatype=DataType.SPARSE_FLOAT_VECTOR)
        
        # Define function for sparse vectors
        bm25_function = Function(
            name="text_bm25_emb",
            input_field_names=["text"],
            output_field_names=["sparse"],
            function_type=FunctionType.BM25,
        )
        schema.add_function(bm25_function)
        
        # Prepare index parameters
        index_params = self.client.prepare_index_params()
        index_params.add_index(field_name="dense", index_type="AUTOINDEX", metric_type="COSINE")
        index_params.add_index(field_name="sparse", index_type="SPARSE_INVERTED_INDEX", metric_type="BM25")
        
        # Create collection
        self.client.drop_collection(self.collection_name)
        self.client.create_collection(collection_name=self.collection_name, schema=schema, index_params=index_params)

    def index_documents(self, documents):
        if not isinstance(documents, list):
            documents = [documents]
        
        embeddings = self.embedding_fn([doc['content'] for doc in documents])
        indexed_data = [{'text': doc['content'], 'dense': vec} for doc, vec in zip(documents, embeddings)]
        
        return self.client.insert(self.collection_name, indexed_data)

    def search(self, query, limit=3):
        query_dense_vector = self.embedding_fn([query])
        
        # Prepare dense vector search
        search_param_1 = {
            "data": query_dense_vector,
            "anns_field": "dense",
            "param": {"metric_type": "COSINE"},
            "limit": limit
        }
        request_1 = AnnSearchRequest(**search_param_1)
        
        # Prepare sparse vector search (BM25)
        search_param_2 = {
            "data": [query],
            "anns_field": "sparse",
            "param": {"metric_type": "BM25", "params": {"drop_ratio_build": 0.0}},
            "limit": limit
        }
        request_2 = AnnSearchRequest(**search_param_2)
        
        reqs = [request_1, request_2]
        ranker = RRFRanker()
        
        # Perform hybrid search
        res = self.client.hybrid_search(
            collection_name=self.collection_name,
            output_fields=['text'],
            reqs=reqs,
            ranker=ranker,
            limit=limit
        )
        
        return [{'id': hit.id, 'distance': hit.distance, 'content': hit.entity['text']} for hit in res[0]]
```

### Explanation

- **Class `HybridSearchEngine`**: Manages the hybrid search operations using Milvus.
  - **Initialization**: Creates a Milvus client and calls the setup function for schema and indices.
  - **Method `_setup_schema_and_indices`**: Sets up the schema, functions, and indexing mechanism for the collection.
  - **Method `index_documents`**: Embeds the documents and inserts them into the collection.
  - **Method `search`**: Performs hybrid search using semantic and full-text searches, returning ranked results based on combined criteria.