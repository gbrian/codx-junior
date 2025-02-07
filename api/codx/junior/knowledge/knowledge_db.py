import os
import re
import logging
import shutil
import json

from slugify import slugify
from pathlib import Path
from pymilvus import MilvusClient
from langchain.schema.document import Document

from codx.junior.ai import AI
from codx.junior.settings import CODXJuniorSettings

from codx.junior.utils import calculate_md5

logger = logging.getLogger(__name__)

CONNECTIONS_CACHE = {}

class DBDocument (Document):
  db_id: str = None
  def __init__(self, db_id, metadata, page_content=""):
    Document.__init__(self, page_content=page_content, metadata=metadata)
    self.db_id = db_id

class KnowledgeDB:
    db_path: str
    db_file_list: str
    index_name: str
    db: MilvusClient = None
    ai: AI
    last_update = None

    def __init__(self, settings: CODXJuniorSettings):
        self.ai = None
        self.settings = settings

        self.path = self.settings.project_path
        self.index_name = re.sub('[^a-zA-Z0-9\._]', '', slugify(str(self.path)))
        self.db_path = f"{settings.codx_path}/db/{self.index_name}"
        os.makedirs(self.db_path, exist_ok=True)
        
        self.db_file = f"{self.db_path}/milvus.db"
        self.db_file_list = f"{self.db_path}/{self.index_name}_file.json"
        self.embedding = None

        
        self.init_db()
        self.init_collection()
        self.refresh_last_update()

    def get_ai(self):
        if not self.ai:
            self.ai = AI(settings=self.settings)
        return self.ai

    def refresh_last_update(self):
        if os.path.isfile(self.db_file_list):
            self.last_update = os.path.getmtime(self.db_file_list)

    def init_db(self):
        global CONNECTIONS_CACHE
        self.db = CONNECTIONS_CACHE.get(self.index_name)
        if not self.db:
            self.db = MilvusClient(self.db_file)
            CONNECTIONS_CACHE[self.index_name] = self.db
    
    def init_collection(self):
        collections = self.db.list_collections()
        if self.index_name not in collections:
            self.db.create_collection(
                collection_name=self.index_name,
                dimension=self.settings.get_ai_embeddings_vector_size(),
                auto_id=True
            )

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

    def update_all_file (self, documents: [Document]):
        all_files = self.get_all_files()
        sources = [doc["metadata"]["source"] for doc in documents]

        for file in sources:
            all_files[file] = {
                "file_md5": calculate_md5(file),
                "documents": [doc for doc in documents if doc["metadata"]["source"] == file]
            }
        self.save_all_files(all_files)

    def index_documents(self, documents: [Document]):
        data = []
        for doc in documents:
            vector = self.get_ai().embeddings(content=doc.page_content)
            doc_data = {
              "vector": vector,
              "page_content": doc.page_content,
              "metadata": doc.metadata
            }
            data.append(doc_data)

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
                del all_files[source]
            self.save_all_files(all_files)

    def reset(self):    
        self.db.drop_collection(
            collection_name=self.index_name
        )
        if os.path.isfile(self.db_file_list):
            os.remove(self.db_file_list)
        self.last_update = None
        
        global CONNECTIONS_CACHE
        del CONNECTIONS_CACHE[self.index_name]
        self.init_db()
        self.init_collection()

    def search(self, query: str):
        query_vector = self.get_ai().embeddings(content=query)
        limit = int(self.settings.knowledge_search_document_count or "10")
        res = self.db.search(
            collection_name=self.index_name,
            data=[query_vector],
            limit=limit,
            output_fields=["id", "page_content", "metadata"]
        )
        documents = []
        # logger.info(f"search results: {list(res)}")
        for level0 in list(res):
            for level1 in level0:
                _id = level1["id"]
                entity = level1["entity"]
                metadata = entity["metadata"]
                distance = level1.get("distance")
                
                metadata["db_distance"] = float(distance)
                documents.append(
                    Document(id=_id,
                        page_content=entity["page_content"], 
                        metadata=metadata))
        return documents

    def get_all_sources(self):
        return self.get_all_files()