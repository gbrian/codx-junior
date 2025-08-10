import logging
import os
import json
from datetime import datetime
from functools import reduce
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor

from codx.junior.knowledge.knowledge_db import KnowledgeDB

from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain.schema.document import Document

from codx.junior.utils.utils import (
  calculate_md5,
  extract_blocks,
  exec_command
)

from codx.junior.ai import AI
from codx.junior.settings import CODXJuniorSettings
from codx.junior.knowledge.knowledge_loader import KnowledgeLoader
from codx.junior.knowledge.knowledge_prompts import KnowledgePrompts
from codx.junior.knowledge.knowledge_keywords import KnowledgeKeywords


logger = logging.getLogger(__name__)

class Knowledge:
    db: KnowledgeDB
    ai: AI

    def __init__(self, settings: CODXJuniorSettings):
        self.ai = None
        self.db = None
        self.settings = settings
        self.path = self.settings.project_path
        self.knowledge_prompts = KnowledgePrompts(settings=settings)
        self.knowledge_keywords = KnowledgeKeywords(settings=settings)
        self.loader = KnowledgeLoader(settings=settings)
        self.last_changed_file_paths = []

    def get_ai(self):
        if not self.ai:
            self.ai = AI(settings=self.settings)
        return self.ai

    def get_db(self):
        if not self.db:
            self.db = KnowledgeDB(settings=self.settings)
        return self.db

    def refresh_last_update(self):
        self.get_db().refresh_last_update()

    def detect_changes(self, last_update = None):
      current_sources = self.get_all_sources()
      if not last_update:
          last_update = self.get_db().last_update
      changes = self.loader.list_repository_files(
                          last_update=last_update if current_sources else None,
                          current_sources=current_sources,
                          ignore_paths=self.settings.get_ignore_patterns())
      
      def is_empty(file_path):
          return False if os.stat(file_path).st_size else True
      return [file_path for file_path in changes if not is_empty(file_path)], self.get_db().last_update

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
                                last_update=self.get_db().last_update if current_sources else None,
                                current_sources=current_sources,
                                ignore_paths=self.settings.get_ignore_patterns())
            if documents:
                self.index_documents(documents)

            self.last_changed_file_paths = list(dict.fromkeys([d.metadata["source"] for d in documents]))
            self.get_db().build_summary()
            logger.info('Knowledge reloaded')
            self.refresh_last_update()
            return documents
        except Exception as ex:
            logger.error(f"Error loading knowledge {ex}")

    def reload_path(self, path: str):
        # Define the task for reloading the path
        def task(path: str):
            try:
                documents = self.loader.load(last_update=None, path=path)
                if documents:
                    self.index_documents(documents, raiseIfError=True)
                logger.info(f"reload_path DONE {path} {len(documents)} documents")
            except Exception as e:
                logger.error(f"Error in reload_path for {path}: {e}")

        # Launch the task in a separate thread to ensure fire-and-forget behavior
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(task, path)

    def get_all_documents (self, include=[]):
        return self.get_db().get_all_documents(include=include)
        
    def clean_deleted_documents(self):
        documents = self.get_all_documents()
        sources = []
        for doc in documents:
          source = doc.metadata["source"]
          if not self.loader.is_valid_file(source):
            sources.append(source)

        if sources:
          logger.info(f'Documents to delete: {sources}')
          self.get_db().delete_documents(sources=sources)
          return True
        return False

    def enrich_document (self, doc, metadata):
      if doc.metadata.get("indexed"):
          raise Exception(f"Doc already indexed {doc.metadata}")
      for k in metadata.keys():
          doc.metadata[k] = metadata[k]
      source = doc.metadata.get('source')

      if self.settings.knowledge_enrich_documents:
        try:
          summary_prompt=f"""
          Given this document:
          <document>
          { doc.page_content }
          </document>

          Return a 10 lines summary with all important concepts and keywords.
          """
          messages = self.get_ai().chat(prompt=summary_prompt)
          doc.metadata["summary"] = messages[-1].content.strip()
        except Exception as ex:
          logger.info(f"Error enriching document {source}: {ex}")
          
      # NOT WOIRKING FINE
      #if self.settings.knowledge_extract_document_tags:
      #    self.extract_doc_keywords(doc)
       
      doc.metadata["indexed"] = 1
      return doc

    def extract_doc_keywords(self, doc):
      keywords = doc.metadata.get("keywords")
      try:
        if not keywords:
            keywords_prompt = f"""
            Given this document:
            <document>
            { doc.page_content }
            </document>

            Generate only one line with keywords separated by comma.
            """
            messages = self.get_ai().chat(prompt=keywords_prompt)
            response = messages[-1].content.strip()
            
            keywords = response.split("\n")[-1]
            doc.metadata["keywords"] = keywords
        source = doc.metadata['source']
        logger.info(f"Extracted keywords from {source}: {keywords}")
        self.knowledge_keywords.add_keywords(source, keywords)
      except Exception as ex:
        logger.exception(f"Error extracting document keywords {doc.metadata}: {ex}")

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
  
    def index_documents (self, documents, raiseIfError=False):
        self.delete_documents(documents)
        # logger.info(f"Indexing documents. {documents}")
        
        index_date = datetime.now().strftime("%m/%d/%YT%H:%M:%S")
        all_sources = list(set([doc.metadata["source"] for doc in documents]))
        all_sources_with_md5 = dict([(source, calculate_md5(source)) for source in all_sources])
        
        metadata = {
          "index_date": f"{index_date}"
        }
        enriched_documents = self.parallel_enrich(documents=documents, metadata=metadata)

        
        for enriched_doc in enriched_documents:
            source = enriched_doc.metadata["source"]
            try:
                #if self.settings.knowledge_extract_document_tags:
                #    self.extract_doc_keywords(enriched_doc)
                enriched_doc.metadata["index_date"] = index_date
                enriched_doc.metadata["file_md5"] = all_sources_with_md5[source]
                # logger.info(f"Indexing document: {enriched_doc}")
                
                self.get_db().index_documents(documents=[enriched_doc])
                # logger.info(f"Indexing document DONE: {enriched_doc}")
                
            except Exception as ex:
                logger.exception(f"Error indexing document {enriched_doc.metadata['source']}: {ex} at project {self.settings.project_path}")
                if "float data" in str(ex):
                  logger.error(f"{self.settings.project_path}: float data error, trying to reset index")
                  self.reset()
                elif raiseIfError:
                    raise ex

    def get_last_changed_file_paths (self):
      return self.last_changed_file_paths

    def delete_documents (self, documents=None, sources=None):
        sources = set(sources or [doc.metadata["source"] for doc in documents])
        self.get_db().delete_documents(sources=sources)
        for source in sources:
            self.knowledge_keywords.remove_keywords(source)

    def reset(self, index: str):
        logger.info('Reseting retriever')
        self.get_db().reset(index=index)

    def search(self, query):
      return self.get_db().search(query=query)
      
    def search_in_source(self, query):
      return self.get_db().search_in_source(query=query)

    def full_text_search(self, query):
        return self.get_db().full_text_search(query=query)

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
        return self.get_db().get_all_sources()

    def get_db_info (self):
        return self.get_db().get_db_info()
      
    def is_valid_project_file(self, file_path):
        sources = self.loader.list_repository_files()
        return True if file_path in sources else False

    def status (self):
        documents = self.get_all_documents()
        doc_count = len(documents)
        doc_sources = list(dict.fromkeys([doc.metadata["source"] for doc in documents]))

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
          "keyword_count": keyword_count,
          "files": doc_sources,
          "db_info": self.get_db_info()
        }
        return status_info

    def build_code_changes_summary(self, diff: str, force = False):
        last_changes_summary_file_path = f"{self.get_db().db_path}/last_changes_summary.md"
        chages_summary = ""
        if force:
            ai = self.get_ai()
            messages = ai.chat(prompt=f"""
            ```diff
            {diff}
            ```
            
            Analyze staged changes.
            Create a human friendly report of changes.
            The report must have an overview and a list of files changes.
            Each change section contains: File name, brief description, errors/improvemnts (if any), and a diff section
            See example below:
            
            EXAMPLE:

            ## Changes details
            Current changes involve adding new functionality for managing users

            ### Changes

            FILE: /shared/app-rest-mro-management/src/main/java/com/w2m/w2fly/mromanagement/service/HistoryService.java
            Added modules A, B,  for this and that
            
            ```diff
            +++ /shared/app-rest-mro-management/src/main/java/com/w2m/w2fly/mromanagement/service/HistoryService.java
            @@ -0,0 +1,33 @@
            +package com.w2m.w2fly.mromanagement.service;
            +
            +import com.w2m.w2fly.mromanagement.data.model.History;
            +import com.w2m.w2fly.mromanagement.data.repository.HistoryRepository;
            +import org.springframework.beans.factory.annotation.Autowired;
            +import org.springframework.stereotype.Service;
            +
            +import java.time.LocalDateTime;
            +
            +@Service
            +public class HistoryService
            ```
            
            ... the methods Foo and Bar has been updated to...
            """)
            chages_summary = messages[-1].content
            with open(last_changes_summary_file_path, 'w') as f:
                f.write(chages_summary)
        elif os.path.isfile(last_changes_summary_file_path):
            with open(last_changes_summary_file_path, 'r') as f:
                chages_summary = f.read()
        return chages_summary
    
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
