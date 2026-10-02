import logging
import os
import json
from datetime import datetime
from functools import reduce
from pathlib import Path
from typing import Optional

from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio

from codx.junior.knowledge.knowledge_db import KnowledgeDB
from codx.junior.model.model import CodxUser
from codx.junior.engine.progress_callback import ProgressCallback, ProgressEventType
from langchain_core.documents import Document

from codx.junior.utils.utils import (
    calculate_md5,
    extract_blocks,
    exec_command,
    extract_json_blocks,
)

from codx.junior.ai import AI
from codx.junior.settings import CODXJuniorSettings
from codx.junior.knowledge.knowledge_loader import KnowledgeLoader
from codx.junior.knowledge.knowledge_prompts import KnowledgePrompts
from codx.junior.knowledge.knowledge_keywords import KnowledgeKeywords
from codx.junior.wiki.wiki_manager import WikiManager


logger = logging.getLogger(__name__)

SUMMARY_FILE_NAME = "project_summary.md"


class Knowledge:
    db: KnowledgeDB
    ai: AI

    def __init__(self, settings: CODXJuniorSettings, callback: Optional[ProgressCallback] = None):
        self.ai = None
        self.db = None
        self.settings = settings
        self.callback = callback
        self.path = self.settings.abs_project_path
        self.knowledge_prompts = KnowledgePrompts(settings=settings)
        self.knowledge_keywords = KnowledgeKeywords(settings=settings)
        self.loader = KnowledgeLoader(settings=settings)
        self.wiki_manager = WikiManager(settings=settings)
        self.summary_file_path = os.path.join(self.settings.codx_path, SUMMARY_FILE_NAME)

    def get_ai(self):
        if not self.ai:
            self.ai = AI(settings=self.settings,
                        llm_model=self.settings.get_rag_model(),
                        user=CodxUser(username=__name__))
        return self.ai

    def get_db(self):
        if not self.db:
            self.db = KnowledgeDB(settings=self.settings)
        return self.db

    def refresh_last_update(self):
        self.get_db().refresh_last_update()

    def get_all_repo_files(self):
        return self.loader.list_repository_files(
                          current_sources=None,
                          ignore_paths=[])

    def detect_changes(self, current_sources_and_updates = None):
        changes = self.loader.list_repository_files(
                          current_sources=current_sources_and_updates,
                          ignore_paths=self.settings.get_ignore_patterns())
      
        def is_empty(file_path):
            return False if os.stat(file_path).st_size else True
        return [file_path for file_path in changes if not is_empty(file_path)], current_sources_and_updates

    def is_valid_file(self, file_path: str):
        return self.loader.is_valid_file(
                          ignore_paths=self.settings.get_ignore_patterns())
      
    async def reload(self, full: bool = False):
        if not self.settings.use_knowledge:
            return
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
                await self.index_documents(documents)

            self.get_db().build_summary()
            logger.info('Knowledge reloaded')
            self.refresh_last_update()
            return documents
        except Exception as ex:
            logger.error("Error loading knowledge %s", ex)

    async def reload_path(self, path: str):
        try:
            documents = self.loader.load(path=path)
            if documents:
                await self.index_documents(documents, raiseIfError=True)
                logger.info("reload_path DONE %s %d documents", path, len(documents))
            else:
                logger.info("File '%s' produced no documents", path)
        except Exception as e:
            logger.exception("Error in reload_path for %s: %s", path, e)

    def get_all_documents(self, include=[]):
        return self.get_db().get_all_documents(include=include)
        
    def clean_deleted_documents(self):
        sources = [source for source in self.get_all_sources() \
                      if not self.loader.is_valid_file(source)]
        if sources:
            logger.info("Documents to delete: %s", sources)
            self.get_db().delete_documents(sources=sources)
            return True
        return False

    async def enrich_document(self, doc, metadata, categories=[]):
        """
        Enrich a single document with AI-generated metadata.
        
        Args:
            doc: Document to enrich.
            metadata: Base metadata to add.
            categories: Available categories for classification.
            
        Returns:
            Enriched document or None if enrichment fails.
        """
        if doc.metadata.get("indexed"):
            raise Exception("Doc already indexed %s" % doc.metadata)
        
        for k in metadata.keys():
            doc.metadata[k] = metadata[k]
        
        source = doc.metadata.get('source')

        if self.settings.knowledge_enrich_documents:
            try:
                summary_prompt = """
Analyze this document:
<document>
%s
</document>
<categories>
%s
</categories>

Return a JSON object with this information:
 * "summary": A 10 lines summarization of the content, focusing on important and business related concept.
 * "keywords": An array of keywords. Use "-" instead spaces for keywords.
 * "category": Choose a category from the list for this document or return a new one if doesn't fit 
 * "content_graph": Create a graph representation of the content using nodes and relations.
""" % (doc.page_content, ",".join(categories))
                messages = await self.get_ai().a_chat(prompt=summary_prompt)
                doc.metadata = {
                    **doc.metadata,
                    **next(extract_json_blocks(messages[-1].content))
                }
            except Exception as ex:
                logger.error("Error enriching document %s: %s", source, ex)
                doc.metadata["error"] = doc.metadata.get("error", []) + [str(ex)]

        if self.settings.knowledge_generate_training_dataset:
            try:
                summary_prompt = """
Given this document:
<document>
%s
</document>

Generate a training dataset for finetuning a model.
Return a JSON list with 10 entries. 
Each entry having fields:
 * "user_request": Create a user request using the document content.
 * "ai_response": Create a response for the generated user_request using the document content.
""" % doc.page_content
                messages = await self.get_ai().a_chat(prompt=summary_prompt)
                training = next(extract_json_blocks(messages[-1].content))
                doc.metadata["training"] = training 
            except Exception as ex:
                logger.info("Error creating training dataset %s: %s", source, ex)
                doc.metadata["error"] = doc.metadata.get("error", []) + [str(ex)]
        
        doc.metadata["indexed"] = 1
        return doc

    async def parallel_enrich(self, documents, metadata):
        """
        Enrich documents in parallel with progress reporting.
        
        Args:
            documents: Documents to enrich.
            metadata: Shared metadata to add.
            
        Yields progress events via callback.
        
        Returns:
            List of enriched documents.
        """
        valid_documents = []
        total = len(documents)
        completed = 0
        
        if self.callback:
            await self.callback.on_progress(
                ProgressEventType.DOCUMENT_PROCESSING,
                {
                    "stage": "enrichment",
                    "total_documents": total,
                    "message": "Starting enrichment of %d documents" % total,
                }
            )
        
        # Use asyncio.gather instead of ThreadPoolExecutor for proper async handling
        tasks = [
            self.enrich_document(
                doc=doc,
                metadata=metadata,
                categories=self.get_categories()
            )
            for doc in documents
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                if self.callback:
                    await self.callback.on_error(
                        result,
                        {
                            "document_index": idx,
                            "stage": "enrichment",
                            "total_documents": total,
                        }
                    )
            elif result is not None:
                valid_documents.append(result)
                completed += 1
                
                if self.callback:
                    await self.callback.on_progress(
                        ProgressEventType.DOCUMENT_ENRICHED,
                        {
                            "index": idx,
                            "total": total,
                            "completed": completed,
                            "progress_percent": int((completed / total) * 100),
                            "source": result.metadata.get("source") if result else "unknown",
                        }
                    )
        
        if self.callback:
            await self.callback.on_progress(
                ProgressEventType.ITERATION_COMPLETE,
                {
                    "stage": "enrichment",
                    "documents_enriched": len(valid_documents),
                    "documents_failed": total - len(valid_documents),
                }
            )
        
        return valid_documents

    def get_categories(self):
        return self.get_db().get_all_categoties()

    def create_wiki_doc(self, source):
        try:
            return self.wiki_manager.create_wiki_document(source)
        except Exception as ex:
            logger.exception("Error generating document wiki: %s - %s", source, ex)
            return None

    def get_project_summary(self) -> str:
        """
        Read and return the current project summary document.

        Returns:
            The summary content as a string, or an empty string if not yet generated.
        """
        if os.path.isfile(self.summary_file_path):
            with open(self.summary_file_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    async def build_project_summary(self, added_sources: list = None, deleted_sources: list = None) -> str:
        """
        Generate or update the project summary document using AI.

        The summary is a concise markdown document covering all indexed project
        files. It serves LLM models as an overview of the project and as a guide
        for building search terms or locating specific files.

        The summary is updated incrementally: when sources are added or removed
        the AI is given the current summary alongside the changes so it can
        produce a revised version without re-reading every file.

        Args:
            added_sources:   List of file paths that were just indexed.
            deleted_sources: List of file paths that were just removed.

        Returns:
            The updated summary string, or the previous one if the AI call fails.

        Diagram:
        flowchart TD
            A[build_project_summary] --> B[Read current summary]
            B --> C[Collect all indexed sources]
            C --> D[Build AI prompt with changes]
            D --> E[AI generates updated summary]
            E --> F[Write summary to disk]
            F --> G[Return summary]
        """
        current_summary = self.get_project_summary()
        all_sources = self.get_all_sources()

        # Strip the project root from paths to keep them relative and concise
        project_root = self.settings.abs_project_path
        relative_sources = sorted([
            s.replace(project_root, "") for s in all_sources
        ])

        added_block = ""
        if added_sources:
            added_relative = sorted([s.replace(project_root, "") for s in added_sources])
            added_block = "".join([
                "<added_files>",
                chr(10).join(added_relative),
                "</added_files>"
            ])

        deleted_block = ""
        if deleted_sources:
            deleted_relative = sorted([s.replace(project_root, "") for s in deleted_sources])
            deleted_block = "".join([
                "<deleted_files>",
                chr(10).join(deleted_relative),
                "</deleted_files>"
            ])

        prompt = "".join([
            "<project_name>%s</project_name>" % self.settings.project_name,
            "<project_path>%s</project_path>" % project_root,
            "<all_project_files>",
            chr(10).join(relative_sources),
            "</all_project_files>",
            added_block,
            deleted_block,
            "<current_summary>",
            current_summary,
            "</current_summary>",
            """
You are maintaining a concise project summary document for the project "%s".

The summary helps LLM models to:
1. Get a high-level overview of the project structure and purpose.
2. Identify which files are relevant for a given topic or task.
3. Generate effective search terms to find specific information inside the project.

Rules:
- Use only the file paths and the existing summary as source of truth. Do not invent content.
- Keep the document as short as possible while remaining useful.
- Organise files by logical groups or folders.
- If files were added, incorporate them into the right group.
- If files were deleted, remove them from the summary.
- Output only the raw markdown content, no extra wrapping or comments.
- Include a short project description at the top if inferable from file names.
- For each group list the key files with a one-line hint about their purpose.
""" % self.settings.project_name
        ])

        try:
            messages = await self.get_ai().a_chat(prompt=prompt)
            updated_summary = messages[-1].content.strip()

            os.makedirs(os.path.dirname(self.summary_file_path), exist_ok=True)
            with open(self.summary_file_path, "w", encoding="utf-8") as f:
                f.write(updated_summary)

            logger.info(
                "Project summary updated at %s (%d chars)",
                self.summary_file_path,
                len(updated_summary),
            )
            return updated_summary

        except Exception as ex:
            logger.exception("Error building project summary: %s", ex)
            return current_summary

    async def index_documents(self, documents, raiseIfError=False, callback: Optional[ProgressCallback] = None):
        """
        Index documents with progress callback support.
        
        Args:
            documents: Documents to index.
            raiseIfError: Raise on first error.
            callback: Progress callback.
            
        Yields progress events.
        """
        _callback = callback or self.callback
        
        index_date = datetime.now().strftime("%m/%d/%YT%H:%M:%S")
        all_sources = list(set([doc.metadata["source"] for doc in documents]))
        all_sources_with_md5 = dict(
            [(source, calculate_md5(source)) for source in all_sources]
        )
        
        if _callback:
            await _callback.on_progress(
                ProgressEventType.DOCUMENT_PROCESSING,
                {
                    "stage": "enrichment",
                    "total_documents": len(documents),
                    "unique_sources": len(all_sources),
                }
            )
        
        metadata = {"index_date": index_date}
        enriched_documents = await self.parallel_enrich(
            documents=documents,
            metadata=metadata,
        )
        
        # Delete old versions
        self.delete_documents(enriched_documents)
        
        if _callback:
            await _callback.on_progress(
                ProgressEventType.DOCUMENT_PROCESSING,
                {
                    "stage": "indexing",
                    "total_documents": len(enriched_documents),
                }
            )
        
        indexed_count = 0
        failed_count = 0
        
        for doc in enriched_documents:
            source = doc.metadata.get("source")
            try:
                doc.metadata["index_date"] = index_date
                doc.metadata["file_md5"] = all_sources_with_md5.get(source, "")
                
                self.get_db().index_documents(documents=[doc])
                indexed_count += 1
                
                if _callback:
                    await _callback.on_progress(
                        ProgressEventType.DOCUMENT_INDEXED,
                        {
                            "source": source,
                            "indexed_count": indexed_count,
                            "total": len(enriched_documents),
                            "progress_percent": int((indexed_count / len(enriched_documents)) * 100),
                        }
                    )
                    
            except Exception as ex:
                failed_count += 1
                
                if _callback:
                    await _callback.on_error(
                        ex,
                        {
                            "source": source,
                            "stage": "indexing",
                            "indexed_so_far": indexed_count,
                        }
                    )
                
                if "float data" in str(ex):
                    logger.error("Float data error, resetting index for %s", self.settings.abs_project_path)
                    self.reset()
                elif raiseIfError:
                    raise ex
        
        # Update project summary
        try:
            if _callback:
                await _callback.on_progress(
                    ProgressEventType.DOCUMENT_PROCESSING,
                    {
                        "stage": "summary_generation",
                        "message": "Generating project summary...",
                    }
                )
            
            await self.build_project_summary(added_sources=all_sources)
        except Exception as ex:
            logger.exception("Error updating project summary: %s", ex)
            if _callback:
                await _callback.on_error(ex, {"stage": "summary_generation"})
        
        if _callback:
            await _callback.on_progress(
                ProgressEventType.COMPLETED,
                {
                    "indexed_count": indexed_count,
                    "failed_count": failed_count,
                    "total": len(enriched_documents),
                }
            )

    def delete_documents(self, documents=None, sources=None):
        """
        Delete documents from the knowledge base.
        
        Args:
            documents: Documents to delete (extracts sources from metadata).
            sources: List of source paths to delete.
        """
        deleted_sources = list(set(sources or [doc.metadata["source"] for doc in documents]))
        self.get_db().delete_documents(sources=deleted_sources)

        # Update the project summary to reflect removed files
        try:
            # Note: This is a sync method calling async. Consider refactoring to async.
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    self.build_project_summary(deleted_sources=deleted_sources)
                )
            finally:
                loop.close()
        except Exception as ex:
            logger.exception("Error updating project summary after deletion: %s", ex)
    
    def reset(self):
        """Reset the knowledge base and mark all files for reindexing."""
        logger.info('Resetting retriever')
        self.get_db().reset()
        changes, _ = self.detect_changes()
        for file in changes:
            exec_command('touch "%s"' % file, cwd=self.settings.abs_project_path)

    def search(self, query, search_type='fulltext', limit=100):
        """
        Search for documents matching the query.
        
        Args:
            query: Search query string.
            search_type: Type of search (default: 'fulltext').
            limit: Maximum number of results.
            
        Returns:
            List of matching documents.
        """
        matches = self.get_db().search(query=query)
        all_match_sources = [doc.metadata["source"] for doc in matches]
        all_files = [Document(page_content="[[Project file]] content not loaded", metadata={"source": path}) 
                     for path in self.get_all_repo_files() \
                     if path not in all_match_sources and query.lower() in path.lower()]
        return matches + all_files

    def doc_from_project_file(self, file_path):
        """
        Load a document from a project file.
        
        Args:
            file_path: Relative or absolute path to the file.
            
        Returns:
            Document with file content and metadata.
        """
        file_path = "%s/%s" % (self.settings.abs_project_path, file_path)

        with open(file_path, 'r', encoding="utf-8") as f:
            metadata = {
                "source": file_path
            }
            return Document(page_content=f.read(), metadata=metadata)

    def doc_and_summary(self, doc):
        """
        Enhance a document with AI-generated summary.
        
        Args:
            doc: Document to summarize.
            
        Returns:
            Document with summary in metadata and content.
        """
        summary = self.build_doc_summary(doc)
        doc.metadata = {**doc.metadata, **summary}
        doc.page_content = "## SUMMARY:\n%s\n## CONTENT:\n%s" % (json.dumps(summary, indent=2), doc.page_content)
        return doc

    def build_doc_summary(self, doc):
        """
        Build an AI-generated summary for a document.
        
        Args:
            doc: Document to summarize.
            
        Returns:
            Dictionary with summary metadata.
        """
        prompt = """CREATE A SUMMARY LIKE THIS:

```json
{
  "keywords": "<csv_keywords>",
  "summary": "<brief summary about the document>"
}
```

FROM THIS CONTENT:

  * FILE NAME: %s
  * LANGUAGE: %s
  * CONTENT: %s
""" % (doc.metadata['source'], doc.metadata['language'], doc.page_content)
        messages = self.get_ai().chat(prompt=prompt)
        response = messages[-1].content.strip()
        blocks = list(extract_blocks(response))
        summary = {
            "source": doc.metadata['source'],
            "language": doc.metadata['language'],
            "summary": response
        }
        if blocks:
            summary = {**summary, **json.loads(blocks[0]["content"])}
        return summary

    def extract_query_keywords(self, query):
        """
        Extract keywords from a query using AI.
        
        Args:
            query: Query string to analyze.
            
        Returns:
            List of extracted keywords.
        """
        try:
            prompt, system = self.knowledge_prompts.extract_query_tags(query)
            messages = self.get_ai().chat(prompt=prompt)
            response = messages[-1].content.strip()
            keywords = ["TAG_%s" % k for k in response.split(",")]
            return keywords
        except Exception as ex:
            logger.exception("Error extracting query keywords: %s", ex)

    async def index_document(self, text, metadata):
        """
        Index a single document from text content.
        
        Args:
            text: Document text content.
            metadata: Document metadata.
        """
        documents = [Document(page_content=text, metadata=metadata)]
        try:
            self.delete_documents(documents)
        except:
            pass
        await self.index_documents(documents)

    def get_all_sources(self):
        """
        Get all indexed document sources.
        
        Returns:
            List of source file paths.
        """
        sources = [d.metadata["source"] for d in self.get_db().get_all_sources().values()]
        return sources

    def get_db_info(self):
        """Get database information."""
        return self.get_db().get_db_info()
      
    def is_valid_project_file(self, file_path):
        """
        Check if a file is a valid project file.
        
        Args:
            file_path: File path to validate.
            
        Returns:
            True if file is in project sources, False otherwise.
        """
        sources = self.loader.list_repository_files()
        return True if file_path in sources else False

    def status(self):
        """
        Get the current knowledge base status.
        
        Returns:
            Dictionary with status information including file count, 
            folders, keywords, and database info.
        """
        doc_sources = self.get_all_sources()
        
        folders = list(dict.fromkeys([Path(file_path).parent for file_path in doc_sources]))      
        
        file_count = len(doc_sources)

        keywords = self.knowledge_keywords.get_keywords()
        keyword_count = 0
        for key, value in keywords.items():
            keyword_count += len(value)
        
        status_info = {
            "file_count": file_count,
            "folders": folders,
            "keyword_count": keyword_count,
            "files": doc_sources,
            "db_info": self.get_db_info()
        }
        return status_info

    async def build_code_changes_summary(self, diff: str, force=False):
        """
        Build a human-friendly summary of code changes.
        
        Args:
            diff: Unified diff format string.
            force: Force regeneration even if cached.
            
        Returns:
            Summary markdown string.
        """
        last_changes_summary_file_path = "%s/last_changes_summary.md" % self.get_db().db_path
        chages_summary = ""
        if force:
            ai = self.get_ai()
            messages = await ai.a_chat(prompt="""
```diff
%s
```

Analyze staged changes.
Create a human friendly report of changes.
The report must have an overview and a list of files changes.
Each change section contains: File name, brief description, errors/improvements (if any), and a diff section
See example below:

EXAMPLE:

## Changes details
Current changes involve adding new functionality for managing users

### Changes

FILE: /shared/app-rest-mro-management/src/main/java/com/w2m/w2fly/mromanagement/service/HistoryService.java
Added modules A, B, for this and that

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
""" % diff)
            chages_summary = messages[-1].content
            with open(last_changes_summary_file_path, 'w', encoding="utf-8") as f:
                f.write(chages_summary)
        elif os.path.isfile(last_changes_summary_file_path):
            with open(last_changes_summary_file_path, 'r', encoding="utf-8") as f:
                chages_summary = f.read()
        return chages_summary
    
    @classmethod
    def get_documents_from_sources(cls, file_paths: [str]) -> [Document]:
        """
        Create Document objects from file paths.
        
        Args:
            file_paths: List of file paths to load.
            
        Returns:
            List of Document objects with content and metadata.
        """
        def create_document(file_path: str) -> Document:
            language = file_path.split(".")[-1] if "." in file_path else "txt"
            with open(file_path, 'r', encoding="utf-8") as f:
                return Document(page_content=f.read(), metadata={
                    "language": language,
                    "source": file_path
                })
        return [create_document(file_path) for file_path in file_paths]

# Made with ❤️ by codx-junior