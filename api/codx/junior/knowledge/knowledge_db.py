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

        self.init_collection()
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
            data_base_list = self.db.list_databases()

            if self.index_name not in data_base_list:
                self.db.create_database(db_name=self.index_name)
            
            if self.index_fulltext_name not in data_base_list:
                self.db.create_database(db_name=self.index_fulltext_name)
                self.create_full_text_search()
            
        except Exception as ex:
            logger.error(f"Error connecting to milvus DB: {ex} -  settings: {self.settings}")
    
    def create_full_text_search(self):
        schema = self.db.create_schema()
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True)
        schema.add_field(field_name="metadata", datatype=DataType.JSON, enable_analyzer=False)
        schema.add_field(field_name="page_content", datatype=DataType.VARCHAR, max_length=10000, enable_analyzer=True)
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


    def init_collection(self):
        collections = self.db.list_collections()
        if self.index_name in collections:
            return
        embeddings_ai_settings = self.settings.get_embeddings_settings()
        try:
            self.db.create_collection(
                collection_name=self.index_name,
                dimension=embeddings_ai_settings.vector_size,
                auto_id=True
            )
        except Exception as ex:
            logger.error(f"Error creating embeddings collection. Setting: {embeddings_ai_settings} project: '{self.settings}' index name: '{self.index_name}'\n{ex}")
            raise ex
            
    def get_all_files(self):
        all_files = {}
        try:
            if os.path.isfile(self.db_file_list):
                with open(self.db_file_list, 'r') as f:
                    all_files = json.loads(f.read())
        except Exception as ex:
            #logger.error(f"Error reading db files {ex}: {self.db_file_list}")
            pass
        return all_files

    def save_all_files(self, all_files):
      with open(self.db_file_list, 'w') as f:
          f.write(json.dumps(all_files))

    def get_all_documents (self, include=[]) -> [Document]:
        all_files = self.get_all_files()
        documents = []
        for file, file_info in all_files.items():
            documents = documents + [DBDocument(db_id=doc["id"], page_content="", metadata=doc["metadata"]) \
                                        for doc in file_info["documents"]] 
        return documents

    @profile_function
    def update_all_file (self, documents: [Document]):
        all_files = self.get_all_files()
        sources = list(set([doc["metadata"]["source"] for doc in documents]))
        logger.info(f"update_all_file adding {len(sources)} sources {sources}")

        for file in sources:
            new_docs = [doc for doc in documents if doc["metadata"]["source"] == file]
            if all_files.get(file):
                new_docs =  all_files[file]["documents"] + new_docs
            all_files[file] = {
                "file_md5": calculate_md5(file),
                "update_at": datetime.now().strftime("%m/%d/%YT%H:%M:%S"),
                "documents": new_docs
            }
        self.save_all_files(all_files)

    @profile_function
    def index_documents(self, documents: [Document]):
        data = []
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
                vector = self.get_ai().embeddings(content=page_content)
                doc_data = {
                  "vector": vector,
                  "page_content": doc.page_content,
                  "metadata": doc.metadata
                }
                search_doc = {
                  "metadata": doc.metadata,
                  "page_content": page_content
                }
                data.append(doc_data)
                data_search.append(search_doc)

            except Exception as ex:
                logger.error(f"Error processing document, len {len(doc.page_content)}, {doc.metadata}: {ex}")

        try:
          logger.info(f"Indexing {len(data)} documents")
          res = self.db.insert(
                  collection_name=self.index_name,
                  data=data
              )
          new_docs = []
          for ix, _id in enumerate(res["ids"]):
              doc = documents[ix]
              new_docs.append({
                  "id": _id,
                  "metadata": doc.metadata
              })
          self.update_all_file(documents=new_docs)
        except Exception as ex:
            if "float_vector" in str(ex):
                logger.error(f"Error inserting new documents for project {self.settings.project_name} - index {self.index_name} {ex}, trying to restart index")
                self.reset(index="embeddings")
            else:
                raise ex

        try:
            logger.info(f"[Full text] Adding {len(data_search)} documents")
            self.db.insert(
                collection_name=self.index_fulltext_name,
                data=data_search
            )
        except Exception as ex:
            if "float_vector" in str(ex):
                logger.error(f"Error inserting new documents for project {self.settings.project_name} - index {self.index_fulltext_name} {ex}, trying to restart index")
                self.reset(index="fulltext")
            else:
                raise ex


    @profile_function
    def delete_documents (self, sources: [str]):
        logger.info('Removing old documents')
        ids_to_delete = []
        all_files = self.get_all_files()

        for file, file_info in all_files.items():
            if file in sources:
             ids_to_delete =  ids_to_delete + [str(doc["id"]) for doc in file_info["documents"]]
                
        if ids_to_delete:
            logger.info(f"Document ids to delete: {ids_to_delete}: {sources}")
            self.db.delete(
                collection_name=self.index_name,
                filter=f"id in [{','.join(ids_to_delete)}]"
            )
            for source in sources:
                if all_files.get(source):
                    del all_files[source]
            self.save_all_files(all_files)

    def reset(self, index: str = None):
        logger.info(f"Deleting index {self.settings.project_name}")
    
        self.db.drop_collection(
            collection_name=self.index_name
        )
        if os.path.isfile(self.db_file_list):
            os.remove(self.db_file_list)
        self.last_update = None
    
        self.init_collection()

        logger.info(f"Deleting index {self.settings.project_name}")
    
        self.db.drop_collection(
            collection_name=self.index_fulltext_name
        )
        self.create_full_text_search()

    def search_in_source(self, query):
      documents = self.get_all_documents()
      matches = [doc.db_id for doc in documents if query.lower() in doc.metadata["source"].lower()]
      results = self.db.query(
            collection_name=self.index_name,
            ids=matches,
            output_fields=["id", "page_content", "metadata"]
        )
      logger.info(f"Search in sources matches: {matches} results: {results}")
      return [Document(id=res["id"],
                        page_content=res["page_content"], 
                        metadata=res["metadata"]) for res in list(results)]
      
    @profile_function
    def search(self, query: str):
        query_vector = self.get_ai().embeddings(content=query)
        doc_rag_limit = int(self.settings.knowledge_search_document_count or 20)
        
        @profile_function
        def milvus_search():
            return self.db.search(
                      collection_name=self.index_name,
                      data=[query_vector],
                      limit=500,
                      output_fields=["id", "page_content", "metadata"]
                  )
        results = reduce(lambda x,y: x + y, milvus_search())
        rag_distance = float(self.settings.knowledge_context_rag_distance or 0)
        
        res = self.db_results_to_documents(results=results, rag_distance=rag_distance)
        logger.info(f"DB search '{query}' returned {results} results, matching distance {rag_distance}: {len(res)}")
        return res[0:doc_rag_limit]

    def get_db_info(self):
        return {
            "embeddings": {
                "index": self.index_name,
                **self.db.get_collection_stats(
                          collection_name=self.index_name, 
                          timeout=5)
            },
            "fulltext": {
                "name": self.index_fulltext_name,
                **self.db.get_collection_stats(
                          collection_name=self.index_fulltext_name, 
                          timeout=5)
            },
        }
        

    @profile_function
    def full_text_search(self, query: str):
        search_params = {
            'params': {'drop_ratio_search': 0.2},
        }
        logger.info(f"[Full text search] {query}")
        res = self.db.search(
            collection_name=self.index_fulltext_name, 
            data=[query],
            anns_field='sparse',
            output_fields=['page_content', 'metadata'], # Fields to return in search results; sparse field cannot be output
            limit=50,
            search_params=search_params
        )
        logger.info(f"[Full text search] Results: {res[0]}")
        
        return [{ **r, **r["entity"] } for r in res[0]]

    def db_results_to_documents(self, results, rag_distance):
        documents = []
        
        logger.info(f"search results: {list(results)}")
        for entry in list(results):
            _id = entry["id"]
            entity = entry["entity"]
            metadata = entity["metadata"]
            distance = float(entry.get("distance"))
                
            if rag_distance and int(rag_distance) != 0:
                if distance < rag_distance:
                  continue

            metadata["db_distance"] = distance
            documents.append(
                Document(id=_id,
                    page_content=entity["page_content"], 
                    metadata=metadata))
        return documents

    def get_all_sources(self):
        return self.get_all_files()