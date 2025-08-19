import os
import re
import logging
import shutil
import json
import time
from datetime import datetime
from contextlib import contextmanager
from functools import reduce

from slugify import slugify
from pathlib import Path

from pymilvus import MilvusClient, DataType, Function, FunctionType

from langchain.schema.document import Document

from codx.junior.ai import AI
from codx.junior.settings import CODXJuniorSettings

from codx.junior.utils.utils import calculate_md5
from codx.junior.profiling.profiler import profile_function

CODX_JUNIOR_MILVUS_URL = os.environ.get("CODX_JUNIOR_MILVUS_URL", "http://milvus:19530")

logger = logging.getLogger(__name__)

MILVUS_CLIENT = MilvusClient(
                    uri=CODX_JUNIOR_MILVUS_URL,
                    token="root:Milvus"
                )

class DBDocument (Document):
  db_id: str = None
  def __init__(self, db_id, metadata, page_content=""):
    Document.__init__(self, page_content=page_content, metadata=metadata)
    self.db_id = db_id

KNOWLEDGE_FIELDS = {
    "id":           { "datatype": DataType.INT64, "is_primary": True, "auto_id": True },
    "metadata":     { "datatype": DataType.JSON, "enable_analyzer": False },
    "page_content": { "datatype": DataType.VARCHAR, "max_length": 10000, "enable_analyzer": True },
    "source":       { "datatype": DataType.VARCHAR, "max_length": 200, "enable_analyzer": True },
    "keywords":     { "datatype": DataType.VARCHAR, "max_length": 5000, "enable_analyzer": True },
    "category":     { "datatype": DataType.VARCHAR, "max_length": 300, "enable_analyzer": True },
    "last_update":  { "datatype": DataType.INT32, "enable_analyzer": True },
}

class KnowledgeDB:
    db: None
    db_path: str
    db_file_list: str
    index_name: str
    ai: AI
    last_update = None

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

    def __del__(self):
        #if hasattr(self, 'db') and self.db:
        #    self.db.close()
        pass

    def get_ai(self):
        if not self.ai:
            self.ai = AI(settings=self.settings)
        return self.ai

    def refresh_last_update(self):
        if os.path.isfile(self.db_file_list):
            self.last_update = os.path.getmtime(self.db_file_list)

    def connect_db(self):
        try:
            def connect():
                return MILVUS_CLIENT
            self.db = connect() 
            self.create_db()
            
        except Exception as ex:
            logger.error(f"Error connecting to milvus DB: {ex} -  settings: {self.settings}")
    
    def create_db(self):
        data_base_list = self.db.list_databases()
        if self.index_fulltext_name not in data_base_list:
            self.db.create_database(db_name=self.index_fulltext_name)
        
        collections = self.db.list_collections()
        if self.index_fulltext_name in collections:
            return

        schema = self.db.create_schema()
        for field_name, settings in KNOWLEDGE_FIELDS.items():
            schema.add_field(field_name=field_name, **settings)
        # Add sparse field
        schema.add_field(field_name="sparse", datatype=DataType.SPARSE_FLOAT_VECTOR)
        
        
        bm25_function = Function(
            name="text_bm25_emb", # Function name
            input_field_names=["page_content"], # Name of the VARCHAR field containing raw page_content data
            output_field_names=["sparse"], # Name of the SPARSE_FLOAT_VECTOR field reserved to store generated embeddings
            function_type=FunctionType.BM25, # Set to `BM25`
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

        self.db.create_collection(
            collection_name=self.index_fulltext_name, 
            schema=schema, 
            index_params=index_params
        )

        index_fulltext_name_view = self.db.describe_collection(
            collection_name=self.index_fulltext_name
        )

        logger.info(f"New full-text index collection created {index_fulltext_name_view}")

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

            except Exception as ex:
                logger.error(f"Error processing document, len {len(doc.page_content)}, {doc.metadata}: {ex}")

  
        try:
            self.db.insert(
                collection_name=self.index_fulltext_name,
                data=data_search
            )
            logger.info(f"[Full text] Adding {len(data_search)} documents")
            
        except Exception as ex:
            if "float_vector" in str(ex):
                logger.error(f"Error inserting new documents for project {self.settings.project_name} - index {self.index_fulltext_name} {ex}, trying to restart index")
                self.reset(index="fulltext")
            else:
                raise ex


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


    def raw_search(self, 
                  search_filter: str,
                  output_fields=None,
                  limit=None):
        if not output_fields:
            output_fields = list(KNOWLEDGE_FIELDS.keys())
        logger.info("raw_search: %s, %s", search_filter, output_fields)
        results = self.db.query(
            collection_name=self.index_fulltext_name,
            filter=search_filter,
            output_fields=output_fields,
            limit=limit
        )
        return self.db_results_to_documents(results)
      
    def get_db_info(self):
        return {
            "embeddings": {
                "index": self.index_fulltext_name,
                **self.db.get_collection_stats(
                          collection_name=self.index_fulltext_name, 
                          timeout=5)
            },
        }
        

    @profile_function
    def search(self, query: str):
        search_params = {
            'params': { 'drop_ratio_search': 0.2 },
        }
        logger.info(f"[Full text search] {query}")
        results = self.db.search(
            collection_name=self.index_fulltext_name, 
            data=[query],
            anns_field='sparse',
            output_fields=['page_content', 'metadata'], # Fields to return in search results; sparse field cannot be output
            limit=50,
            search_params=search_params
        )
        results = reduce(lambda x,y: x + y, results)
        
        return self.db_results_to_documents(results)

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

        # Fall back to returning an empty list if an error occurs.
        return {}

    def get_all_categoties(self):
        documents = self.raw_search(search_filter='source != ""', output_fields=["category"])
        return list(set([ doc.metadata.get("category", "Unknown") for doc in documents]))
