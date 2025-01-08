import os
import logging
import shutil

from slugify import slugify
from pathlib import Path
from pymilvus import MilvusClient
from langchain.schema.document import Document

from codx.junior.ai import AI
from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)

class DBDocument (Document):
  db_id: str = None
  def __init__(self, id, metadata, page_content=""):
    Document.__init__(self, id=id, page_content=page_content, metadata=metadata)
    self.db_id = id

class KnowledgeDB:
    db_path: str
    db_file_list: str
    index_name: str
    db: MilvusClient = None
    ai: AI
    db_file_list: str

    def __init__(self, settings: CODXJuniorSettings):
        self.ai = None
        self.settings = settings

        self.path = self.settings.project_path
        self.index_name = slugify(str(self.path))
        self.db_path = f"{settings.codx_path}/db/{self.index_name}"
        os.makedirs(self.db_path, exist_ok=True)
        
        self.db_file = f"{self.db_path}/milvus.db"
        self.db_file_list = f"{self.db_path}/{index_name}_file.json"
        self.embedding = None

        self.db = MilvusClient(self.db_file)
        self.init_collection()

    def init_collection(self):
        self.db.create_collection(
            collection_name=self.index_name,
            dimension=self.settings.get_ai_embeddings_vector_size()
        )

    def get_all_files(self):
        all_files = {}
        if os.path.isfile(self.self.db_file_list):
            with open(self.db_file_list, 'r') as f:
              all_files = json.loads(f.read())
        return all_files

    def save_all_files(self, all_files):
      with open(self.db_file_list, 'w') as f:
          f.write(json.dumps(all_files))

    def get_all_documents (self, include=[]) -> [Document]:
        all_files = self.get_all_files()
        documents = []
        for file, docs in all_files.items():
            documents = documents + [Document(**doc) for doc in docs] 
        return documents

    def update_documents (self, documents: [Document]):
        all_files = self.get_all_files()
        sources = [doc.metadata["source"] for doc in documents]

        for file in sources:
            all_files[file] = [doc.__dict__ for doc in documents if doc.metadata["source"] == file]

        self.save_all_files(all_files)

    def index_documents(self, documents: [Document]):
        data = []
        for doc in documents:
            vector = self.ai.embeddings(content=doc.page_content)
            data.append({
              "vector": vector,
              **doc.metadata
            })
        res = self.db.insert(data)
        for ix, _id in enumerate(res["ids"]):
            documents[ix].id = _id

        self.update_documents(documents=documents)
        
    def delete_documents (self, sources: [str]):
        logger.info('Removing old documents')
        ids_to_delete = []
        all_files = self.get_all_files()

        for _id, files in all_files.items:
            if [f for f in files if f["source"] in sources]:
                ids_to_delete.append(_id)
                
        logger.info(f"Document ids to delete: {ids_to_delete}: {sources}")
        
        self.db.delete(
            collection_name=self.index_name,
            filter=f"id in [{','.join(ids_to_delete)}]"
        )

        self.save_all_files(all_files)

    def reset(self):    
        self.db.drop_collection(
            collection_name=self.index_name
        )
        self.init_collection()

    def search(self, query: str):
      query_vector = self.ai.embeddings(content=query)
      res = self.db.search(
          collection_name=self.index_name,
          data=[query_vector],
          limit=20,
          output_fields=["id", "source"]
      )
      all_files = self.get_all_files()
      documents = []
      for hit in res:
          source = hit["source"]
          files = all_files[source]
          for file in files:
            doc = [Document(**_doc) for _doc in files if _doc["id"] == hit["id"]][0]
            documents.append(doc)

      return documents

    def get_all_sources(self):
        return self.get_all_files().keys()
