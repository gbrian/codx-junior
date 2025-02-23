import logging
import os
import shutil
import json
from slugify import slugify
from datetime import datetime
from functools import reduce
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.llms import OpenAI
from langchain.schema.document import Document

from codx.junior.utils import calculate_md5
from codx.junior.utils import extract_blocks
from codx.junior.ai import AI
from codx.junior.settings import CODXJuniorSettings
from codx.junior.knowledge.knowledge_loader import KnowledgeLoader
from codx.junior.knowledge.knowledge_prompts import KnowledgePrompts
from codx.junior.knowledge.knowledge_keywords import KnowledgeKeywords

from codx.junior.profiling.profiler import profile_function

logger = logging.getLogger(__name__)

class DBDocument (Document):
  db_id: str = None
  def __init__(self, id, metadata, page_content=""):
    Document.__init__(self, id=id, page_content=page_content, metadata=metadata)
    self.db_id = id

class Knowledge:
    db_path: str
    db_file_list: str
    index_name: str
    db: Chroma = None
    ai: AI

    def __init__(self, settings: CODXJuniorSettings):
        self.ai = None
        self.settings = settings

        self.path = self.settings.project_path
        self.knowledge_prompts = KnowledgePrompts(settings=settings)
        self.index_name = slugify(str(self.path))
        self.db_path = f"{settings.codx_path}/db/{self.index_name}"
        self.db_file = f"{self.db_path}/chroma.sqlite3"
        self.db_file_list = f"{self.db_path}/file_list"
        self.knowledge_keywords = KnowledgeKeywords(settings=settings)
        self.loader = KnowledgeLoader(settings=settings)
        self.last_update = None
        self.refresh_last_update()        
        self.last_changed_file_paths = []
        self.embedding = None

    def get_embedding(self):
        if not self.embedding:
            self.embedding = OpenAIEmbeddings(
                openai_api_key=self.settings.get_ai_api_key(),
                openai_api_base=self.settings.get_ai_api_url(),
                disallowed_special=())
        return self.embedding

    def get_ai(self):
      from codx.junior import build_ai
      if not self.ai:
        self.ai = build_ai(settings=self.settings)
      return self.ai

    def get_db(self):
      try:
          if not self.db:
              os.makedirs(self.db_path, exist_ok=True)
              db_file = f"{self.db_path}/chroma.sqlite3"
              db_exists = os.path.isfile(db_file)
              if db_exists:
                  self.db = Chroma(
                          persist_directory=self.db_path, 
                          embedding_function=self.get_embedding())
          return self.db
      except Exception as ex:
          logger.exception(f"Error opening Knowledge DB: {self.db_path}")

    def refresh_last_update(self):
      if os.path.isfile(self.db_file):
          self.last_update = os.path.getmtime(self.db_file)

    def get_sub_projects_paths(self):
        sub_projects = self.settings.get_sub_projects()
        return [project.project_path for project in sub_projects]


    @profile_function
    def detect_changes(self):
      current_sources = self.get_all_sources()
      changes = self.loader.list_repository_files(
                          last_update=self.last_update if current_sources else None,
                          current_sources=current_sources,
                          ignore_paths=self.get_sub_projects_paths())
      
      def is_empty(file_path):
          return False if os.stat(file_path).st_size else True
      return [file_path for file_path in changes if not is_empty(file_path)]

    def reload(self, full: bool = False):
        if not self.settings.use_knowledge:
            return
        self.refresh_last_update()
        if full:
          self.reset()
        try:
            logger.info('Reloading knowledge')
            # Load the knowledge from the filesystem
            current_sources = self.get_all_sources()
            documents = self.loader.load(
                                last_update=self.last_update if current_sources else None,
                                current_sources=current_sources,
                                ignore_paths=self.get_sub_projects_paths())
            if documents:
                self.index_documents(documents)

            self.last_changed_file_paths = list(dict.fromkeys([d.metadata["source"] for d in documents]))
            self.build_summary()
            logger.info('Knowledge reloaded')
            self.refresh_last_update()
            return documents
        except Exception as ex:
            logger.error(f"Error loading knowledge {ex}")
            pass

    @profile_function
    def reload_path(self, path: str):
        documents = self.loader.load(last_update=None, path=path)
        logger.info(f"reload_path {path}: {documents}")
        if documents:
            self.index_documents(documents, raiseIfError=True)
        logger.info(f"reload_path DONE {path} {len(documents)} documents")
        return documents

    def get_all_documents (self, include=[]):
        collection = self.get_db()._collection
        collection_docs = collection.get(include=include + ['metadatas'])
        documents = []
        ids = collection_docs["ids"]
        metadatas = collection_docs["metadatas"]
        page_contents = collection_docs.get("documents", [])
        for ix, _id in enumerate(ids):
          page_content = ""
          if page_contents:
            page_content = page_contents[ix]
          documents.append(DBDocument(id=_id, page_content=page_content, metadata=metadatas[ix]))
        return documents
        
    def clean_deleted_documents(self):
        if not self.get_db():
          return False
        ids_to_delete = []
        collection = self.get_db()._collection
        documents = self.get_all_documents()
        
        sources = []
        for doc in documents:
          source = doc.metadata["source"]
          if not self.loader.is_valid_file(source):
            sources.append(source)
            ids_to_delete.append(doc.db_id)

        if len(ids_to_delete):
          logger.info(f'Documents to delete: {sources} {ids_to_delete}')
          collection.delete(ids=ids_to_delete)
          return True
        return False

    @profile_function
    def enrich_document (self, doc, metadata):
      if doc.metadata.get("indexed"):
        raise Exception(f"Doc already indexed {doc.metadata}")
      for k in metadata.keys():
        doc.metadata[k] = metadata[k]
      language = doc.metadata.get('language', '')
      source = doc.metadata.get('source')
      summary = ""

      if self.settings.knowledge_enrich_documents:
        try:
          prompt, system = self.knowledge_prompts.enrich_document_prompt(doc)
          messages = self.get_ai().start(system, prompt)
          summary = messages[-1].content.strip()
        except Exception as ex:
          logger.info(f"Error enriching document {source}: {ex}")
          pass
      if self.settings.knowledge_extract_document_tags:
          self.extract_doc_keywords(doc)
       
      doc.metadata["indexed"] = 1
      return doc

    def extract_doc_keywords(self, doc):
      keywords = doc.metadata.get("keywords")
      try:
        if not keywords:
            prompt, system = self.knowledge_prompts.extract_document_tags(doc)
            messages = self.get_ai().chat(messages=[system], prompt=prompt)
            response = messages[-1].content.strip()
            
            blocks = list(extract_blocks(response))
            keywords = blocks[0]["content"] if blocks else respone

            doc.metadata["keywords"] = keywords
        source = doc.metadata['source']
        logger.info(f"Extracted keywords from {source}: {keywords}")
        self.knowledge_keywords.add_keywords(source, keywords)
      except Exception as ex:
        logger.exception(f"Error extracting document keywords {doc.metadata}: {ex}")
        pass

    @profile_function
    def parallel_enrich(self, documents, metadata):
      with ThreadPoolExecutor() as executor:
        futures = {
          executor.submit(
            self.enrich_document,
            doc=doc,
            metadata=metadata): doc for doc in documents
        }
        valid_documents = []
        for future in as_completed(futures):
          result = future.result()
          if result is not None:
              valid_documents.append(result)
        return valid_documents
  
    @profile_function
    def index_documents (self, documents, raiseIfError=False):
        self.delete_documents(documents)
        # logger.info(f"Indexing documents. {documents}")
        
        index_date = datetime.now().strftime("%m/%d/%YT%H:%M:%S")
        all_sources = list(set([doc.metadata["source"] for doc in documents]))
        all_sources_with_md5 = dict([(source, calculate_md5(source)) for source in all_sources])
        
        metadata = {
          "index_date": f"{index_date}"
        }

        """
        CHUNK_SIZE = 10
        for doc_chunk in [documents[i:i+CHUNK_SIZE] for i in range(len(documents))[::CHUNK_SIZE]]:
          enriched_docs = self.parallel_enrich(doc_chunk, metadata=metadata)
          for enriched_doc in enriched_docs:
            try:
                self.db = Chroma.from_documents([self.doc_and_summary(enriched_doc)],
                  self.embedding,
                  persist_directory=self.db_path,
                )
                logger.info(f"Stored document from {enriched_doc.metadata['source']}")
            except Exception as ex:
                logger.exception(f"Error indexing document {enriched_doc.metadata['source']}: {ex}")
                if raiseIfError:
                    raise ex
        """
        for enriched_doc in documents:
            source = enriched_doc.metadata["source"]
            try:
                #if self.settings.knowledge_extract_document_tags:
                #    self.extract_doc_keywords(enriched_doc)
                enriched_doc.metadata["index_date"] = index_date
                enriched_doc.metadata["file_md5"] = all_sources_with_md5[source]
                # logger.info(f"Indexing document: {enriched_doc}")
                self.db = Chroma.from_documents([enriched_doc],
                  self.get_embedding(),
                  persist_directory=self.db_path,
                )
                # logger.info(f"Indexing document DONE: {enriched_doc}")
                
            except Exception as ex:
                logger.exception(f"Error indexing document {enriched_doc.metadata['source']}: {ex}")
                if raiseIfError:
                    raise ex

    def get_last_changed_file_paths (self):
      return self.last_changed_file_paths

    def build_summary(self):
        try:
          os.makedirs(self.db_path, exist_ok=True)
        except:
          pass
        current_files = [f"{doc.metadata['source']} {doc.metadata.get('language')}" for doc in self.get_all_documents()]
        db_files = list(dict.fromkeys(current_files))
        # Save all files
        with open(self.db_file_list, "w") as db_file_list:
          db_file_list.write("\n".join(db_files))
        

    def delete_documents (self, documents=None, sources=None):
        if not self.get_db():
            return

        logger.info('Removing old documents')
        ids_to_delete = []
        collection = self.get_db()._collection
        collection_docs = collection.get(include=['metadatas'])
        
        def delete_doc_ids (source_doc):
          for ix, metadata in enumerate(collection_docs["metadatas"]):
              if metadata.get('source') == source_doc:
                  id_to_delete = collection_docs["ids"][ix]
                  logger.info(f"Document to delete: {id_to_delete}: {source_doc}")
                  ids_to_delete.append(id_to_delete)
        if not sources:
          sources = list(dict.fromkeys([doc.metadata["source"] for doc in documents]))
        for source in sources:
          delete_doc_ids(source_doc=source)
          self.knowledge_keywords.remove_keywords(source)

        if len(ids_to_delete):
          logger.info(f'Documents to delete: {sources} {ids_to_delete}')
          collection.delete(ids=ids_to_delete)

    def reset(self):
        logger.info('Reseting retriever')
        self.last_update = None
        if os.path.exists(self.db_path):
            shutil.rmtree(self.db_path)

    def as_retriever(self):
        return self.get_db().as_retriever(
            search_type=self.settings.knowledge_search_type,
            search_kwargs={
              "k": int(self.settings.knowledge_search_document_count)
            },
        )

    @profile_function
    def search(self, query):
      if not self.settings.use_knowledge:
        logging.error(f"Knowledge::search use_knowledge is DISABLED {self.settings.use_knowledge}")
        return []
      attemps = 3
      while attemps >= 0:
          try:
              retriever = self.as_retriever()
              HNSW_M = self.settings.knowledge_hnsw_M
              documents = retriever.get_relevant_documents(query, **{ "M": HNSW_M })
              logger.debug(f"[Knowledge::search] {query} docs: {len(documents)}")
              return documents
          except Exception as ex:
              logger.exception(f"Error knowledge search {ex}")
          attemps -= 1
      return []

    def search_in_source(self, query):
      if not self.get_db():
          return []
      collection = self.get_db()._collection
      collection_docs = collection.get(include=['metadatas', 'documents'])      
      ids = collection_docs["ids"]
      metadatas = collection_docs["metadatas"]
      page_contents = collection_docs.get("documents", [])
      documents = []
      search_query = query.lower()
      for ix, _id in enumerate(ids):
        if search_query in metadatas[ix]["source"].lower():
          documents.append(Document(id=ids[ix], page_content=page_contents[ix], metadata=metadatas[ix]))
      
      # logger.info(f"search_in_source: query: {query}, total indexed: {len(ids)} total docs {len(documents)}")
      
      return documents

    def doc_from_project_file(self, file_path):
        file_path = f"{self.settings.project_path}/{file_path}"

        with open(file_path, 'r') as f:
            metadata = {
              "source": file_path
            }
            return Document(page_content=f.read(), metadata=metadata)      

    def doc_and_summary(self, doc):
      summary = self.build_doc_summary(doc)
      doc.metadata = { **doc.metadata, **summary }
      doc.page_content = f"## SUMMARY:\n{json.dumps(summary, indent=2)}\n## CONTENT:\n{doc.page_content}"
      return doc

    def build_doc_summary(self, doc):
      prompt = \
      f"""CREATE A SUMMARY LIKE THIS:

      ```json
      {{
        "keywords": "<csv_keywords>",
        "summary": "<brief summary about the document>"
      }}
      ```

      FROM THIS CONTENT:

        * FILE NAME: { doc.metadata['source'] }
        * LANGUAGE: { doc.metadata['language'] }
        * CONTENT: { doc.page_content }
      """
      messages = self.get_ai().chat("", prompt)
      response = messages[-1].content.strip()
      blocks = list(extract_blocks(response))
      summary = { 
        "source": doc.metadata['source'],
        "language": doc.metadata['language'],
        "summary": response
      }
      if blocks:
        summary = { **summary, **json.loads(blocks[0]["content"]) }
      return summary

    def extract_query_keywords(self, query):
      try:
        prompt, system = self.knowledge_prompts.extract_query_tags(query)
        messages = self.get_ai().chat(system, prompt)
        response = messages[-1].content.strip()
        keywords = [f"TAG_{k}" for k in response.split(",")]
        return keywords
      except Exception as ex:
        logger.exception(f"Error extracting document keywords {source}: {ex}")

    def index_document(self, text, metadata):
        documents = [Document(page_content=text, metadata=metadata)]
        self.delete_documents(documents)
        self.index_documents(documents)

    def get_all_sources (self):
        db = self.get_db()
        if not db:
          return []
        collection = db._collection
        collection_docs = collection.get(include=['metadatas'])
        
        metadatas = collection_docs["metadatas"]
        doc_sources = dict([(metadata["source"], metadata) for metadata in metadatas])
        return doc_sources
      
    
    @profile_function
    def status (self):
        db = self.get_db()
        ids = []
        metadatas = []
        documents = []
        if db:
            collection = db._collection
            collection_docs = collection.get(include=['metadatas', 'documents'])
            
            ids = collection_docs["ids"]
            metadatas = collection_docs["metadatas"]
            documents = collection_docs["documents"]
        
        corrupted_docs = [ix for ix, doc in enumerate(documents) if not doc]

        doc_count = len(ids)
        doc_sources = list(dict.fromkeys([metadata["source"] for metadata in metadatas]))


        folders = list(dict.fromkeys([Path(file_path).parent for file_path in doc_sources]))      
        
        file_count = len(doc_sources)

        keywords = self.knowledge_keywords.get_keywords()
        keyword_count = 0
        for key, value in keywords.items():
            keyword_count += len(value)
        
        status_info = {
          "doc_count": doc_count,
          "file_count": file_count,
          "folders": folders,
          "empty": len(documents) - len(metadatas),
          "corrupted_docs": corrupted_docs,
          "keyword_count": keyword_count,
          "files": doc_sources
        }
        return status_info
    
    @classmethod
    def get_documents_from_sources(cls, file_paths: [str]) -> [Document]:
        def create_document(file_path: str) -> Document:
            language = file_path.split(".")[-1] if "." in file_path else "txt"
            with open(file_path, 'r') as f:
                return Document(page_content=f.read(), metadata={ 
                    "language": language,
                    "source": file_path 
                })
        return [create_document(file_path) for file_path in file_paths]
