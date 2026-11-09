# LLM web search & scraping — alternatives to Obscura

> Scope: **LLM web research** (search → fetch → clean text for the model), *not* the
> co-browsing container. Companion to `docs/obscura-evaluation.md`.
> Retrieval basis: project sources + upstream READMEs/PyPI/API fetched during the
> session (see [Sources](#sources)).

---

## 1. Where we are today

| Piece | File | Implementation | Weak point |
|---|---|---|---|
| `web_search` | `codx/junior/tools/duckduckgo_search.py` | `ddgs` (HTML scraping of DuckDuckGo) | breaks silently — the query `obscura headless browser rust review …` returned **0 results**; snippets truncated to 150 chars; no content, only links |
| `fetch_webpage` | `codx/junior/tools/fetch_webpage.py` | `requests` + BeautifulSoup + **html2text** on the *whole* `<body>` | no JS execution, **no main-content extraction** (nav/footer/cookie banners/related-links dominate the tokens), no size cap, no SSRF guard, no deadline, 10s hard timeout |
| Render path | `codx/junior/browser/browser.py` (+ `docker_browser_manager.py`) | Playwright → Chromium container over CDP | heavy (200+ MB, ~2 s startup) but **already paid for** by co-browsing |
| Doc/PDF path | `doc_converter` tool | headless Chromium / pandoc | not wired into `fetch_webpage` |

Conclusion: the gap is **not a missing browser**, it is (a) content extraction quality,
(b) a real search backend, (c) hardening of the fetch step. Obscura/Lightpanda only
address "make the render step cheaper".

---

## 2. Layers — pick one option per layer

```
search  →  fetch/render  →  extract (main content)  →  truncate/chunk  →  model
  ①          ②                 ③
```

### ① Search backend
| Option | Notes | Fit |
|---|---|---|
| **SearXNG** (self-host, Docker) | meta-search over ~70 engines, `?format=json`, no key, no quota; needs one container + a UA/rate policy | ★★★ best self-hosted, replaces `ddgs` |
| **Brave Search API / Serper / Bing** | paid, stable, snippets + optional `extra_snippets` | ★★ if a paid key is acceptable |
| **Tavily** | search *and* returns cleaned page content in one call (1 credit) | ★★ least integration work, vendor lock |
| **Exa** | neural search + `/contents` | ★★ research-grade, paid |
| `ddgs` (current) | free, breaks (observed) | ★ keep as last-resort fallback only |

### ② Fetch / render
| Option | Runtime | JS | License | Notes |
|---|---|---|---|---|
| **`requests` + trafilatura** (no browser) | ~50 ms | ✗ | Apache-2.0 | covers the large majority of docs/news/blog pages |
| **Existing Chromium container** (Playwright, already in repo) | ~2 s, 200 MB+ | ✓ | BSD (Playwright) | zero new dependency; use only when the no-JS pass returns ~empty |
| **Crawl4AI** (lib / Docker) | Playwright Chromium bundled | ✓ | Apache-2.0 (repo), cloud is commercial | `AsyncWebCrawler().arun()`, markdown + `fit_markdown` pruning, caching, `/scrape` HTTP server, MCP, cloud API (`api.crawl4ai.com`) |
| **Firecrawl** (self-host or cloud) | own workers + proxies | ✓ | AGPL-3.0 core | `/scrape` markdown/JSON, `/search`, `/interact`; P95 ≈ 3.4 s claimed, "96 % of the web"; heavy self-host (needs Redis/queue) |
| **Jina Reader** (`r.jina.ai/<url>`, `s.jina.ai/<query>`) | hosted | ✓ (picks chromium vs curl-impersonate) | Apache-2.0 OSS branch / free SaaS tier | **zero install**, URL→markdown + search→markdown, PDFs/Office, rate-limited, third-party egress |
| **Lightpanda** (Zig) | ~123 MB / 100 pages, 5 s | partial | AGPL-3.0 | direct obscura competitor: `lightpanda fetch --dump markdown|html|pdf|png|structured_data`, `--obey-robots`, CDP on `:9222`, MCP, Docker `lightpanda/browser`, org-backed |
| **Obscura** (Rust) | ~30 MB / session | partial | see eval doc | faster/smaller, single-maintainer, MCP first |
| **Hosted browser infra**: Browserbase, Hyperbrowser, Steel.dev, Browserless | remote CDP | ✓ | commercial | per-session pricing, no infra to run, good for bot-protected sites |

### ③ Extraction (main content → markdown)
| Option | Notes |
|---|---|
| **trafilatura 2.3.x** | purpose-built reader-mode: text + metadata (title/date/author/site), outputs MD/JSON/XML, benchmark-leading precision/recall; `bare_extraction()` for programmatic use |
| readability-lxml / `justext` | older reader-mode, weaker metadata |
| markdownify | better link/table fidelity than html2text; often paired *after* trafilatura's HTML subset |
| `resiliparse`, `boilerpy3` | alternatives when trafilatura mis-detects |
| MarkItDown (Microsoft) | doc-centric (PDF/DOCX/HTML→MD); weak at boilerplate removal, overlaps `doc_converter` |
| Docling | PDF/scan layout extraction, heavy |

---

## 3. Recommendation for this repo

**Phase 1 — no new services (highest value/effort ratio)**
1. `fetch_webpage`: `requests` → **trafilatura `bare_extraction()`** for main content +
   metadata, fall back to BeautifulSoup/markdownify when extraction returns `< N` chars.
2. Add the missing guards: allow-listed schemes (http/https), **private-IP/loopback block**
   (resolve then check, also block redirects to private), `max_bytes` cap (~5 MB), total
   deadline, `Accept: text/html,*/*` and a real UA. (Obscura's SSRF default is the bar to match.)
3. If the extracted text is empty/skeleton → second pass through the **existing Chromium
   container** (`Browser`) and re-extract. No new binary.

**Phase 2 — fix the search layer**
4. Replace/augment `ddgs` with **SearXNG** (self-hosted container, JSON API) or a
   Brave/Tavily key stored in **global settings → `integrations[]`** (project convention:
   secrets never in `.codx` project JSON).

**Phase 3 — only if concurrency/cost demands it**
5. One adapter for a **lite engine** behind `codx/junior/browser/` (never call it from tools
   directly): **Lightpanda first** (same class as obscura, org-backed, `--obey-robots`,
   `--dump markdown`), obscura as the alternative if its perf holds on our fixtures.
6. Optional "premium fetch" toggle using **Jina Reader** or **Firecrawl Cloud** for
   bot-protected/JS-heavy pages, key in `integrations[]`, off by default (third-party egress
   = data-leak decision, same class as `--stealth`).

**Rejected as primary path:** full managed-browser infra (Browserbase/Steel) — we already
run Chromium; and Crawl4AI-as-a-service as the default — its README is now a cloud funnel,
self-host cost ≈ Firecrawl.

---

## 4. Acceptance criteria (any candidate)

- `fetch_webpage` on 20 fixtures (docs, blog, news, GitHub, SPA, PDF, paywall, cookie wall):
  ≥ 80 % of pages return boilerplate-free text; token count ≤ 40 % of today's output.
- No private-IP egress; response bounded by bytes *and* time.
- JS fallback only when needed (measure: % of fetches that escalate).
- p95 latency budget: no-JS ≤ 1.5 s, escalated ≤ 6 s.
- Every third-party engine is behind a settings flag and degrades to local on failure.

---

## Sources

- `codx/junior/tools/fetch_webpage.py`, `codx/junior/tools/duckduckgo_search.py`,
  `codx/junior/browser/browser.py` (this repo).
- Crawl4AI README + releases (v0.9.5, 14 Oct 2026) — Apache-2.0 repo, cloud `api.crawl4ai.com`.
- Firecrawl README (`/search`, `/scrape`, `/interact`, AGPL-3.0 core).
- Jina Reader README (`r.jina.ai`, `s.jina.ai`, OSS branch = stateless, PDF/Office ingest, 2026-04 resync).
- Trafilatura on PyPI (v2.3.1).
- Lightpanda browser README (benchmarks 123 MB / 5 s vs 2 GB / 46 s per 100 pages; binaries need glibc 2.35+/2.38+; `--dump markdown`, CDP, MCP, Docker image).
- Obscura: see `docs/obscura-evaluation.md`.
