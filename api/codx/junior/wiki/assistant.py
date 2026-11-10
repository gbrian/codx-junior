"""
Per-project documentation assistant.

The assistant answers questions about a project using its generated wiki as the
primary source of truth, with optional knowledge-base snippets as a fallback.
It is intentionally independent from the chat engine: the docs UI can call it
without creating a persisted chat, and every answer carries the pages it used
so the UI can offer citations.

Retrieval is local and deterministic (title/description/tag scoring over the
docs-site manifest plus full-text page reads). The knowledge base is queried as
an optional enrichment; if Milvus is unavailable the assistant still works.

Mermaid diagram of the flow:

```mermaid
flowchart TD
    Q[User question] --> S[Score wiki pages]
    S --> P[Read top pages]
    P --> K[Optional knowledge search]
    K --> C[Build context]
    C --> A[AI answer with citations]
    A --> R[Return answer + citations + follow-ups]
```
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from codx.junior.wiki.site import WikiSiteBuilder, strip_frontmatter

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 12000
MAX_PAGES = 5
MAX_HISTORY_MESSAGES = 8

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does",
    "for", "from", "how", "i", "in", "is", "it", "me", "my", "of", "on",
    "or", "our", "please", "show", "tell", "that", "the", "their", "this",
    "to", "was", "we", "what", "when", "where", "which", "who", "why",
    "will", "with", "would", "you", "your",
}

_SYSTEM_PROMPT = """You are the documentation assistant for a software project.
You answer questions using ONLY the documentation and code context provided.

Rules:
- Be concise, concrete and friendly. Prefer short sections, steps and examples.
- When the docs contain code, include a runnable example and explain the hint.
- Use fenced ```mermaid blocks when a diagram makes the answer clearer.
- Cite the wiki pages you used inline as [Page title](wiki:page/path).
- If the context does not contain the answer, say so explicitly and suggest the
  closest pages or the next question to ask. Never invent APIs or behaviour.
- Finish with a short "Sources" list of the pages you used.
"""


def _tokens(text: str) -> List[str]:
    """Tokenise a question/page into lowercase content words."""
    words = re.findall(r"[a-zA-Z0-9_./-]+", (text or "").lower())
    return [word.strip("./-") for word in words if word.strip("./-") not in _STOPWORDS]


def _score_page(question_tokens: List[str], page: Dict[str, Any], current_page: Optional[str]) -> int:
    """Deterministic relevance score for one wiki page."""
    title = str(page.get("title", "")).lower()
    description = str(page.get("description", "")).lower()
    tags = " ".join(page.get("tags", []) or []).lower()
    section = str(page.get("section", "")).lower()
    path = str(page.get("path", "")).lower()
    score = 0
    for token in question_tokens:
        if token in title:
            score += 8
        if token in description:
            score += 4
        if token in tags:
            score += 3
        if token in section:
            score += 2
        if token in path:
            score += 2
    if current_page and page.get("path") == current_page:
        score += 5
    if page.get("kind") == "overview":
        score += 2
    return score


def _trim(text: str, limit: int) -> str:
    """Trim a string to a maximum number of characters."""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n\n… (truncated)"


class WikiAssistant:
    """Answer questions about one project using its documentation."""

    def __init__(self, settings: Any) -> None:
        self.settings = settings
        self.site_builder = WikiSiteBuilder(settings=settings)
        self._ai = None

    # ── public API ──────────────────────────────────────────────────────────

    async def answer(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
        page_path: Optional[str] = None,
        use_knowledge: bool = True,
    ) -> Dict[str, Any]:
        """
        Answer a documentation question.

        Args:
            question: Natural-language question.
            history: Previous turns as ``[{"role": "user"|"assistant", "content": ...}]``.
            page_path: Wiki page currently open in the UI (used as context hint).
            use_knowledge: Enrich context with knowledge-base search results.

        Returns:
            Dictionary with ``answer``, ``citations``, ``suggestions`` and
            ``pages_used``. Never raises for AI failures: a graceful fallback
            answer is returned instead.
        """
        question = (question or "").strip()
        if not question:
            raise ValueError("A question is required")
        history = [
            {
                "role": message.get("role", "user"),
                "content": str(message.get("content", ""))[:2000],
            }
            for message in (history or [])[-MAX_HISTORY_MESSAGES:]
            if message.get("content")
        ]

        # Always work from a fresh manifest. The scheduler normally rebuilds it,
        # but this makes the assistant see pages written by another process (or
        # a restarted background worker) without waiting for the next batch.
        site = self.site_builder.build_if_stale(write=True)
        pages = list(site.get("pages", {}).values())
        selected = self._select_pages(question, pages, page_path)
        context_pages = self._load_page_context(selected) if selected else []

        knowledge = []
        if use_knowledge:
            knowledge = await asyncio.to_thread(self._search_knowledge, question)

        prompt = self._build_prompt(question, history, context_pages, knowledge, site)
        try:
            answer = await self._ask_ai(prompt)
            mode = "ai"
        except Exception as ex:
            logger.exception("Wiki assistant AI call failed: %s", ex)
            answer = self._fallback_answer(question, context_pages, knowledge)
            mode = "fallback"

        citations = self._citations(answer, context_pages, knowledge)
        return {
            "project": {
                "name": self.settings.project_name,
                "codx_path": self.settings.codx_path,
            },
            "question": question,
            "answer": answer,
            "mode": mode,
            "citations": citations,
            "suggestions": self._followups(question, selected, citations),
            "pages_used": [page["path"] for page in context_pages],
            "context": {
                "wiki_pages": len(context_pages),
                "knowledge_documents": len(knowledge),
                "codebase_search": bool(use_knowledge),
            },
            "generated_at": int(time.time()),
        }

    # ── retrieval ───────────────────────────────────────────────────────────

    def _select_pages(
        self,
        question: str,
        pages: List[Dict[str, Any]],
        current_page: Optional[str],
    ) -> List[Dict[str, Any]]:
        if not pages:
            return []
        tokens = _tokens(question)
        ranked = sorted(
            pages,
            key=lambda page: (
                _score_page(tokens, page, current_page),
                page.get("updated_at", 0),
            ),
            reverse=True,
        )
        selected = [page for page in ranked if _score_page(tokens, page, current_page) > 0]
        if not selected:
            selected = [page for page in ranked if page.get("kind") == "overview"][:2]
        if not selected:
            selected = ranked[:3]
        return selected[:MAX_PAGES]

    def _load_page_context(self, pages: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Attach the markdown body of each selected page."""
        context: List[Dict[str, Any]] = []
        budget = MAX_CONTEXT_CHARS
        for page in pages:
            loaded = self.site_builder.page(page["path"])
            if not loaded:
                continue
            body = strip_frontmatter(loaded.get("content", ""))
            allowed = max(0, min(len(body), budget))
            context.append({
                **page,
                "content": _trim(body, allowed),
                "headings": loaded.get("headings", []),
            })
            budget -= allowed
            if budget <= 0:
                break
        return context

    def _search_knowledge(self, question: str) -> List[Dict[str, Any]]:
        """Best-effort knowledge search; failures are non-fatal."""
        try:
            from codx.junior.knowledge.knowledge_db import KnowledgeDB

            documents = KnowledgeDB(settings=self.settings).search(question, _limit=8)
        except Exception as ex:
            logger.debug("Wiki assistant knowledge search unavailable: %s", ex)
            return []
        results: List[Dict[str, Any]] = []
        for document in documents or []:
            metadata = getattr(document, "metadata", {}) or {}
            content = getattr(document, "page_content", "") or ""
            if not content.strip():
                continue
            source = metadata.get("source") or metadata.get("file") or ""
            results.append({
                "source": source,
                "content": _trim(content, 1800),
                "score": metadata.get("score"),
            })
            if len(results) >= 4:
                break
        return results

    # ── prompt / AI ─────────────────────────────────────────────────────────

    def _build_prompt(
        self,
        question: str,
        history: List[Dict[str, str]],
        pages: List[Dict[str, Any]],
        knowledge: List[Dict[str, Any]],
        site: Dict[str, Any],
    ) -> str:
        project = site.get("project", {})
        page_blocks = []
        for page in pages:
            page_blocks.append(
                f"<doc path=\"{page['path']}\" title=\"{page['title']}\" "
                f"section=\"{page.get('section', '')}\">\n"
                f"{page.get('content', '')}\n</doc>"
            )
        knowledge_blocks = [
            f"<snippet source=\"{item['source']}\">\n{item['content']}\n</snippet>"
            for item in knowledge
        ]
        history_text = "\n".join(
            f"{message.get('role', 'user')}: {message.get('content', '')}"
            for message in history
            if message.get("content")
        )
        child_projects = site.get("child_projects", [])
        children_text = "\n".join(
            self._child_project_summary(child) for child in child_projects
        ) or "none"
        return f"""
<project>
  <name>{project.get('title') or project.get('name')}</name>
  <description>{project.get('description', '')}</description>
  <kind>{project.get('kind', 'generic')}</kind>
  <languages>{', '.join(project.get('languages', []))}</languages>
</project>

<child_projects>
{children_text}
</child_projects>

<documentation>
{chr(10).join(page_blocks) or '(no wiki pages available)'}
</documentation>

<code_context>
{chr(10).join(knowledge_blocks) or '(no extra code context)'}
</code_context>

<conversation>
{history_text or '(new conversation)'}
</conversation>

<question>
{question}
</question>

Answer the question for a developer reading this project's documentation.
Use the documentation as the primary source. Use code context only to add
precision. Cite pages as [Page title](wiki:path). Keep the answer under ~350
words unless a step-by-step example needs more. End with a "Sources" section.
""".strip()

    async def _ask_ai(self, prompt: str) -> str:
        from codx.junior.ai import AI
        from codx.junior.model.model import CodxUser

        model = self.settings.get_rag_model() or self.settings.get_wiki_model()
        self._ai = AI(
            settings=self.settings,
            llm_model=model,
            user=CodxUser(username="wiki-assistant"),
            system=_SYSTEM_PROMPT,
        )
        messages = await self._ai.a_chat(
            prompt=prompt,
            headers={"tags": "wiki,assistant"},
        )
        content = (messages[-1].content or "").strip()
        if content.startswith("```") and content.endswith("```"):
            content = "\n".join(content.splitlines()[1:-1])
        return content

    def _fallback_answer(
        self,
        question: str,
        pages: List[Dict[str, Any]],
        knowledge: List[Dict[str, Any]],
    ) -> str:
        """Deterministic answer used when the AI provider is not available."""
        name = self.settings.project_name or "this project"
        lines = [
            f"I could not reach the AI model to answer **{question}** completely.",
            "",
            f"Here are the most relevant places in the {name} documentation:",
            "",
        ]
        for page in pages:
            lines.append(
                f"- [{page['title']}](wiki:{page['path']}) — "
                f"{page.get('description', 'Open this page for details.')}"
            )
        if knowledge:
            lines.extend(["", "Related code context:", ""])
            for item in knowledge[:3]:
                lines.append(f"- `{item.get('source', 'source')}`")
        lines.append("")
        lines.append("Ask again in a moment, or open one of the pages above.")
        return "\n".join(lines)

    def _child_project_summary(self, child: Dict[str, Any]) -> str:
        """Describe a child project and its most important wiki pages."""
        lines = [
            f"- {child.get('title')}: {child.get('description', '')} "
            f"(wiki: {child.get('wiki_url', '')}, {child.get('page_count', 0)} pages)"
        ]
        try:
            docs_path = os.path.join(
                child.get("wiki_path") or os.path.join(child.get("codx_path") or "", "wiki"),
                "docs.json",
            )
            if os.path.isfile(docs_path):
                with open(docs_path, "r", encoding="utf-8") as handle:
                    child_site = json.load(handle)
                for page in list(child_site.get("pages", {}).values())[:8]:
                    lines.append(
                        f"    · {page.get('title')}: {page.get('description', '')}"
                    )
        except (OSError, ValueError):
            pass
        return "\n".join(lines)

    # ── citations / follow-ups ──────────────────────────────────────────────

    def _citations(
        self,
        answer: str,
        pages: List[Dict[str, Any]],
        knowledge: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        cited_paths = set(re.findall(r"wiki:([^\s)\]>]+)", answer or ""))
        citations: List[Dict[str, Any]] = []
        seen = set()
        for page in pages:
            path = page["path"]
            if path in seen:
                continue
            if cited_paths and path not in cited_paths:
                # Keep used pages as suggestions even when the model omitted a
                # link; this keeps the UI useful when citations are incomplete.
                pass
            seen.add(path)
            citations.append({
                "type": "wiki",
                "title": page["title"],
                "path": path,
                "description": page.get("description", ""),
                "icon": page.get("icon", "fa-regular fa-file-lines"),
            })
        for item in knowledge[:3]:
            source = item.get("source", "")
            if source and source not in seen:
                seen.add(source)
                citations.append({
                    "type": "source",
                    "title": source.split("/")[-1] or source,
                    "path": source,
                    "description": "Project source / knowledge snippet",
                    "icon": "fa-solid fa-code",
                })
        return citations

    def _followups(
        self,
        question: str,
        pages: List[Dict[str, Any]],
        citations: List[Dict[str, Any]],
    ) -> List[str]:
        suggestions: List[str] = []
        for page in pages[:2]:
            suggestions.append(f"Show me an example from \"{page['title']}\".")
        suggestions.extend([
            "What are the main modules and how do they connect?",
            "What should I read next?",
            "Where is the entry point of the project?",
        ])
        seen = set()
        result = []
        for suggestion in suggestions:
            if suggestion not in seen and suggestion.lower() != (question or "").lower():
                seen.add(suggestion)
                result.append(suggestion)
        return result[:4]
