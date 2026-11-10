"""
Standalone wiki site server.

Serves a generated VitePress build and exposes a small documentation assistant
backed by a **local OpenAI-compatible endpoint** (Ollama, vLLM, LM Studio…).

This file has no codx-junior runtime dependency: the exported wiki can be
deployed on its own host with only the files in this folder.

Environment:
    WIKI_ROOT               Wiki folder (default: directory of this file)
    WIKI_DIST               VitePress build output (default: .vitepress/dist)
    WIKI_HOST / WIKI_PORT   Bind address (default: 0.0.0.0:8080)
    WIKI_AI_BASE_URL        Local OpenAI-compatible base URL
    WIKI_AI_API_KEY         API key (use "ollama" for Ollama if required)
    WIKI_AI_MODEL           Model name
    WIKI_AI_TIMEOUT         Request timeout in seconds
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

logger = logging.getLogger("wiki-site")
logging.basicConfig(level=logging.INFO)

WIKI_ROOT = Path(os.environ.get("WIKI_ROOT", Path(__file__).resolve().parent))
WIKI_DIST = Path(os.environ.get("WIKI_DIST", WIKI_ROOT / ".vitepress" / "dist"))
MANIFEST = WIKI_ROOT / "docs.json"
AI_BASE_URL = os.environ.get("WIKI_AI_BASE_URL", "http://127.0.0.1:11434/v1")
AI_API_KEY = os.environ.get("WIKI_AI_API_KEY", "ollama")
AI_MODEL = os.environ.get("WIKI_AI_MODEL", "qwen2.5:7b")
AI_TIMEOUT = float(os.environ.get("WIKI_AI_TIMEOUT", "120"))

app = FastAPI(title="codx-junior wiki", version="1.0")

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does",
    "for", "from", "how", "i", "in", "is", "it", "me", "my", "of", "on",
    "or", "our", "please", "show", "tell", "that", "the", "their", "this",
    "to", "was", "we", "what", "when", "where", "which", "who", "why",
    "will", "with", "would", "you", "your",
}


def _tokens(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z0-9_./-]+", (text or "").lower())
    return [word.strip("./-") for word in words if word.strip("./-") not in _STOPWORDS]


def _read_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def _manifest() -> Dict[str, Any]:
    return _read_json(MANIFEST, {})


def _site() -> Dict[str, Any]:
    data = _manifest()
    data.pop("pages", None)
    return data


def _page_path(page: str) -> Optional[Path]:
    relative = str(page or "").replace("\\", "/").lstrip("/")
    if not relative:
        return None
    if not relative.endswith(".md"):
        relative += ".md"
    target = (WIKI_ROOT / relative).resolve()
    root = WIKI_ROOT.resolve()
    if not str(target).startswith(str(root) + os.sep) or not target.is_file():
        return None
    return target


def _page(page: str) -> Optional[Dict[str, Any]]:
    path = _page_path(page)
    if not path:
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    frontmatter: Dict[str, Any] = {}
    body = text
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if match:
        try:
            import yaml
            loaded = yaml.safe_load(match.group(1))
            if isinstance(loaded, dict):
                frontmatter = loaded
        except Exception:
            frontmatter = {}
        body = text[match.end():]
    return {
        "path": str(path.relative_to(WIKI_ROOT)).replace(os.sep, "/")[:-3],
        "title": frontmatter.get("title") or next(
            (line.lstrip("# ").strip() for line in body.splitlines() if line.startswith("# ")),
            path.stem.replace("-", " ").title(),
        ),
        "description": frontmatter.get("description") or "",
        "content": body,
    }


def _select_pages(question: str, page_path: Optional[str]) -> List[Dict[str, Any]]:
    manifest = _manifest()
    pages = list((manifest.get("pages") or {}).values())
    if not pages:
        return []
    tokens = _tokens(question)
    ranked = []
    for page in pages:
        title = str(page.get("title", "")).lower()
        description = str(page.get("description", "")).lower()
        tags = " ".join(page.get("tags", []) or []).lower()
        path = str(page.get("path", "")).lower()
        score = 0
        for token in tokens:
            if token in title:
                score += 8
            if token in description:
                score += 4
            if token in tags:
                score += 3
            if token in path:
                score += 2
        if page_path and page.get("path") == page_path.lstrip("/"):
            score += 5
        ranked.append((score, page))
    ranked.sort(key=lambda item: (item[0], item[1].get("updated_at", 0)), reverse=True)
    selected = [page for score, page in ranked if score > 0][:5]
    if not selected:
        selected = [page for _score, page in ranked[:4]]
    loaded = []
    for page in selected:
        content = _page(page["path"])
        if content:
            loaded.append(content)
    return loaded


def _prompt(question: str, pages: List[Dict[str, Any]], history: List[Dict[str, str]]) -> str:
    manifest = _manifest()
    project = manifest.get("project", {})
    docs = "\n\n".join(
        f"<doc path=\"{page['path']}\" title=\"{page['title']}\">\n{page['content'][:9000]}\n</doc>"
        for page in pages
    )
    conversation = "\n".join(
        f"{message.get('role', 'user')}: {message.get('content', '')}"
        for message in (history or [])[-8:]
    )
    return f"""
<project>
  <name>{project.get('title') or project.get('name')}</name>
  <description>{project.get('description', '')}</description>
</project>

<documentation>
{docs or '(no documentation pages found)'}
</documentation>

<conversation>
{conversation or '(new conversation)'}
</conversation>

<question>
{question}
</question>

Answer using only the documentation above. Be concise and concrete. If the
docs do not contain the answer, say so and point to the closest pages. Use
markdown and cite pages as [Page title](page/path). End with a Sources list.
""".strip()


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "wiki": str(WIKI_ROOT),
        "dist": WIKI_DIST.is_dir(),
        "model": AI_MODEL,
    }


@app.get("/api/site")
def site() -> Dict[str, Any]:
    return _site()


@app.get("/api/page")
def page(path: str = ""):
    found = _page(path)
    if not found:
        raise HTTPException(status_code=404, detail="Page not found")
    return found


@app.post("/api/assistant")
async def assistant(request: Request):
    payload = await request.json()
    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=422, detail="A question is required")
    pages = _select_pages(question, payload.get("page"))
    prompt = _prompt(question, pages, payload.get("history") or [])
    try:
        body = json.dumps({
            "model": AI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a documentation assistant. Answer only from the provided wiki pages.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }).encode("utf-8")
        request_ai = urllib.request.Request(
            f"{AI_BASE_URL.rstrip('/')}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AI_API_KEY}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request_ai, timeout=AI_TIMEOUT) as response:
            completion = json.loads(response.read().decode("utf-8"))
        answer = (
            completion.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            or ""
        ).strip()
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as ex:
        logger.exception("Local AI request failed: %s", ex)
        answer = "The local AI is unavailable.\n\nClosest pages:\n" + "\n".join(
            f"- {page['title']} (`{page['path']}`)" for page in pages
        )
    citations = [
        {
            "title": page["title"],
            "path": page["path"],
            "description": page.get("description", ""),
        }
        for page in pages
    ]
    return {
        "answer": answer,
        "citations": citations,
        "pages_used": [page["path"] for page in pages],
        "model": AI_MODEL,
    }


@app.get("/{full_path:path}")
async def static_site(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    candidates = []
    base = (WIKI_DIST / full_path).resolve()
    dist = WIKI_DIST.resolve()
    if str(base).startswith(str(dist)):
        if base.is_dir():
            candidates.append(base / "index.html")
        candidates.extend([base, base.with_suffix(".html")])
    candidates.append(WIKI_DIST / "index.html")
    for candidate in candidates:
        if candidate.is_file():
            return FileResponse(candidate)
    raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host=os.environ.get("WIKI_HOST", "0.0.0.0"),
        port=int(os.environ.get("WIKI_PORT", "8080")),
        reload=False,
    )
