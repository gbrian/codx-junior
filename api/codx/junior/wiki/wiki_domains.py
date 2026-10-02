import os
import json
import logging
from typing import Dict, List, Optional

from slugify import slugify
from langchain_core.documents import Document

from codx.junior.settings import CODXJuniorSettings
from codx.junior.knowledge.knowledge_db import KnowledgeDB
from codx.junior.knowledge.knowledge_graph import DependencyGraph

logger = logging.getLogger(__name__)


class WikiDomains:
    def __init__(self, settings: CODXJuniorSettings, db: KnowledgeDB, ai):
        self.settings = settings
        self.db = db
        self.ai = ai
        self.domain_map_file = os.path.join(settings.codx_path, "domain_map.json")

    def detect_domains(self, graph: DependencyGraph, source_map: Dict) -> List[Dict]:
        # Group files by existing category from source_map
        category_groups: Dict[str, List[str]] = {}
        for source, doc in source_map.items():
            cat = doc.metadata.get("category", "") or "uncategorized"
            category_groups.setdefault(cat, []).append(source)

        # Strengthen groupings using graph connectivity
        files_data = graph._graph.get("files", {})
        merged = self._merge_connected_categories(category_groups, files_data)

        # Use AI to name and describe each domain cluster
        domains = []
        for cat_name, files in merged.items():
            entry_points = self._find_entry_points(files, files_data)
            keywords = self._collect_keywords(files, source_map)
            dep_domains = self._find_dependency_domains(files, files_data, merged)

            prompt = f"""
<category_name>{cat_name}</category_name>
<files>
{chr(10).join(files)}
</files>
<entry_points>
{chr(10).join(entry_points)}
</entry_points>

Generate a JSON object describing this software domain/module cluster with these fields:
- "name": A clear, concise domain name (2-4 words)
- "description": A 2-3 sentence description of what this domain does

Return only the JSON object, no extra text.
"""
            try:
                messages = self._ai_chat(prompt)
                content = messages[-1].content.strip()
                if content.startswith("```"):
                    content = "\n".join(content.split("\n")[1:-1])
                import json as _json
                ai_data = _json.loads(content)
                name = ai_data.get("name", cat_name)
                description = ai_data.get("description", "")
            except Exception as ex:
                logger.warning("AI domain naming failed for %s: %s", cat_name, ex)
                name = cat_name
                description = ""

            domains.append({
                "name": name,
                "slug": slugify(name),
                "description": description,
                "files": files,
                "depends_on_domains": dep_domains,
                "entry_points": entry_points,
                "keywords": keywords,
            })

        return domains

    def build_domain_page(self, domain: Dict, graph: DependencyGraph) -> str:
        files_data = graph._graph.get("files", {})
        all_imports = set()
        all_imported_by = set()
        for f in domain.get("files", []):
            entry = files_data.get(f, {})
            all_imports.update(entry.get("imports", []))
            all_imported_by.update(entry.get("imported_by", []))

        # Filter to cross-domain dependencies only
        domain_files_set = set(domain.get("files", []))
        cross_imports = [f for f in all_imports if f not in domain_files_set]
        cross_imported_by = [f for f in all_imported_by if f not in domain_files_set]

        prompt = f"""
<domain_name>{domain['name']}</domain_name>
<description>{domain.get('description', '')}</description>
<files>
{chr(10).join(domain.get('files', []))}
</files>
<entry_points>
{chr(10).join(domain.get('entry_points', []))}
</entry_points>
<depends_on_files>
{chr(10).join(cross_imports)}
</depends_on_files>
<used_by_files>
{chr(10).join(cross_imported_by)}
</used_by_files>
<keywords>
{', '.join(domain.get('keywords', []))}
</keywords>

Generate a comprehensive markdown wiki page for this software domain.
Include these sections:
# {domain['name']}
## Overview
## Files in Domain
## Dependencies
## Used By
## Entry Points

Use markdown formatting. Do not add code fences around the entire document.
"""
        try:
            messages = self._ai_chat(prompt)
            return messages[-1].content.strip()
        except Exception as ex:
            logger.error("Error building domain page for %s: %s", domain['name'], ex)
            return f"# {domain['name']}\n\n{domain.get('description', '')}\n"

    def save_domain_map(self, domains: List[Dict]) -> None:
        try:
            tmp = self.domain_map_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(domains, fh, indent=2)
            os.replace(tmp, self.domain_map_file)
            logger.info("Domain map saved to %s", self.domain_map_file)
        except Exception as ex:
            logger.error("Error saving domain map: %s", ex)

    def load_domain_map(self) -> List[Dict]:
        if not os.path.isfile(self.domain_map_file):
            return []
        try:
            with open(self.domain_map_file, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception as ex:
            logger.error("Error loading domain map: %s", ex)
            return []

    # ── helpers ───────────────────────────────────────────────────────────────

    def _ai_chat(self, prompt: str):
        from codx.junior.model.model import CodxUser
        from codx.junior.ai import AI
        ai = AI(settings=self.settings, llm_model=self.settings.get_wiki_model(), user=CodxUser(username=__name__))
        return ai.chat(prompt=prompt, headers={"tags": "wiki,domains"})

    def _merge_connected_categories(
        self,
        category_groups: Dict[str, List[str]],
        files_data: Dict
    ) -> Dict[str, List[str]]:
        # Simple heuristic: keep categories as-is but consolidate tiny ones
        result = {}
        overflow = []
        for cat, files in category_groups.items():
            if len(files) >= 2:
                result[cat] = list(files)
            else:
                overflow.extend(files)
        if overflow:
            result.setdefault("general", []).extend(overflow)
        return result

    def _find_entry_points(self, files: List[str], files_data: Dict) -> List[str]:
        # Entry points: files with no internal importers within the domain set
        domain_set = set(files)
        entries = []
        for f in files:
            imported_by = files_data.get(f, {}).get("imported_by", [])
            internal_importers = [i for i in imported_by if i in domain_set]
            if not internal_importers:
                entries.append(f)
        return entries[:5]

    def _collect_keywords(self, files: List[str], source_map: Dict) -> List[str]:
        kws = set()
        for f in files:
            doc = source_map.get(f)
            if doc:
                for kw in doc.metadata.get("keywords", []):
                    kws.add(kw)
        return sorted(kws)[:20]

    def _find_dependency_domains(
        self,
        files: List[str],
        files_data: Dict,
        all_domains: Dict[str, List[str]]
    ) -> List[str]:
        domain_set = set(files)
        external_imports = set()
        for f in files:
            for imp in files_data.get(f, {}).get("imports", []):
                if imp not in domain_set:
                    external_imports.add(imp)

        dep_domains = set()
        for ext_f in external_imports:
            for cat, cat_files in all_domains.items():
                if ext_f in cat_files:
                    dep_domains.add(slugify(cat))
        return list(dep_domains)
