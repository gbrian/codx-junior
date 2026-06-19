import os
import json
import logging
import time
from typing import Dict, List, Optional

from langchain_core.documents import Document

from codx.junior.settings import CODXJuniorSettings
from codx.junior.knowledge.knowledge_db import KnowledgeDB
from codx.junior.knowledge.knowledge_graph import DependencyGraph

logger = logging.getLogger(__name__)


class WikiIndex:
    def __init__(self, settings: CODXJuniorSettings, db: KnowledgeDB):
        self.settings = settings
        self.db = db
        self.wiki_path = settings.get_project_wiki_path()

    def build(self, wiki_settings: Dict, domain_map: List[Dict], graph: DependencyGraph) -> Dict:
        index: Dict = {
            "version": 1,
            "updated_at": int(time.time()),
            "files": {},
            "domains": {},
        }

        files_data = graph._graph.get("files", {})

        # Index domains
        for domain in domain_map:
            slug = domain.get("slug", "")
            index["domains"][slug] = {
                "name": domain.get("name", ""),
                "slug": slug,
                "description": domain.get("description", ""),
                "files": domain.get("files", []),
                "entry_points": domain.get("entry_points", []),
                "keywords": domain.get("keywords", []),
                "depends_on_domains": domain.get("depends_on_domains", []),
                "wiki_path": f"domains/{slug}.md",
            }

        # Index files from wiki categories
        categories = wiki_settings.get("categories", [])
        for category in self._flatten_categories(categories):
            for file_entry in category.get("files", []):
                fp = file_entry.get("path", "")
                if not fp:
                    continue
                slug = file_entry.get("slug", "")
                wiki_file = file_entry.get("wiki_file", "")
                graph_entry = files_data.get(fp.lstrip("/"), {})
                index["files"][fp] = {
                    "path": fp,
                    "slug": slug,
                    "category": category.get("title", ""),
                    "wiki_file": wiki_file,
                    "imports": graph_entry.get("imports", []),
                    "imported_by": graph_entry.get("imported_by", []),
                    "external_deps": graph_entry.get("external_deps", []),
                }

        return index

    def get_file_entry(self, file_path: str) -> Optional[Dict]:
        index = self._load_index()
        return index.get("files", {}).get(file_path)

    def get_domain_entry(self, domain_slug: str) -> Optional[Dict]:
        index = self._load_index()
        return index.get("domains", {}).get(domain_slug)

    def save(self, index: Dict) -> None:
        index_path = os.path.join(self.wiki_path, "wiki_index.json")
        os.makedirs(self.wiki_path, exist_ok=True)
        try:
            tmp = index_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(index, fh, indent=2)
            os.replace(tmp, index_path)
            logger.info("Wiki index saved to %s", index_path)
        except Exception as ex:
            logger.error("Error saving wiki index: %s", ex)

    def index_to_milvus(self, index: Dict) -> None:
        documents = []

        for slug, domain in index.get("domains", {}).items():
            wiki_file = os.path.join(self.wiki_path, domain.get("wiki_path", ""))
            page_content = domain.get("description", "")
            if os.path.isfile(wiki_file):
                try:
                    with open(wiki_file, "r", encoding="utf-8") as fh:
                        page_content = fh.read()
                except Exception:
                    pass

            documents.append(Document(
                page_content=page_content,
                metadata={
                    "source": domain.get("wiki_path", f"domains/{slug}.md"),
                    "category": "wiki",
                    "keywords": domain.get("keywords", []),
                    "summary": domain.get("description", ""),
                },
            ))

        for fp, entry in index.get("files", {}).items():
            wiki_file_path = entry.get("wiki_file", "")
            if not wiki_file_path or not os.path.isfile(wiki_file_path):
                continue
            try:
                with open(wiki_file_path, "r", encoding="utf-8") as fh:
                    page_content = fh.read()
            except Exception:
                continue

            documents.append(Document(
                page_content=page_content,
                metadata={
                    "source": wiki_file_path,
                    "category": "wiki",
                    "keywords": [],
                    "summary": "",
                },
            ))

        if documents:
            try:
                self.db.index_documents(documents)
                logger.info("Indexed %d wiki documents to Milvus", len(documents))
            except Exception as ex:
                logger.error("Error indexing wiki to Milvus: %s", ex)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _load_index(self) -> Dict:
        index_path = os.path.join(self.wiki_path, "wiki_index.json")
        if not os.path.isfile(index_path):
            return {}
        try:
            with open(index_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception as ex:
            logger.error("Error loading wiki index: %s", ex)
            return {}

    def _flatten_categories(self, categories: List[Dict]) -> List[Dict]:
        result = []
        for cat in categories:
            result.append(cat)
            children = cat.get("children", [])
            if children:
                result.extend(self._flatten_categories(children))
        return result
