## Obscura (Rust headless browser) — decision

Obscura evaluation: `docs/obscura-evaluation.md`.

- Verdict: supplementary headless engine for text/markdown extraction (or `print_pdf` fallback), never a replacement for the co-browsing Chromium container (its distroless image cannot host X/Selkies live view).
- Any adoption must be a single adapter inside `codx/junior/browser/`; sessions keep going through `BrowserManager`.
- `--stealth` is opt-in per call only (bot-detection evasion + ToS/robots implications); MCP HTTP transport requires `OBSCURA_MCP_TOKEN`, private-IP egress blocked unless `--allow-private-network`.
- Known gaps to re-check before use: file upload (`DOM.setFileInputFiles`), `Browser.setDownloadBehavior`/downloads, touch emulation, rendering fidelity for PDF/screenshots.

## LLM web research stack: known weak points

- `codx/junior/tools/fetch_webpage.py` = `requests` + BeautifulSoup + **html2text over the whole body**: no JS, no reader-mode extraction, no byte cap, no private-IP/SSRF guard, fixed 10s timeout.
- `codx/junior/tools/duckduckgo_search.py` (`ddgs`) scrapes DDG HTML and can return **zero results for valid queries**; snippets are cut at 150 chars. Do not treat "no results" as "nothing exists".
- Preferred order for improvement: (1) trafilatura extraction + SSRF/size guards, (2) JS fallback through the existing Chromium container (`codx/junior/browser/browser.py`), (3) real search backend (SearXNG or Brave/Tavily key in global settings `integrations[]`), (4) lite engine (Lightpanda before Obscura) as one adapter.
- Options matrix: `docs/llm-web-scraping-alternatives.md`; browser-engine verdict: `docs/obscura-evaluation.md`.

## LLM web layer: modules and config

Web research stack lives in `codx/junior/web/` (`settings.py` integrations+env, `guard.py` SSRF/size/deadline, `extract.py` trafilatura→readability→soup, `browser_fetch.py` lite engine then Chromium, `premium.py` Jina/Firecrawl, `search_backends.py` searxng|brave|tavily|ddgs, `fetch.py` orchestrator). Lite engines: `codx/junior/browser/lite_engine.py` (Lightpanda first, Obscura second, CLI-only, data-driven argv).

Tools stay thin: `tools/fetch_webpage.py` and `tools/duckduckgo_search.py` (alias `web_search`) only format results; never add HTTP logic there.

Config: global settings `integrations[]` `{name, enabled, url, api_key, options}` overridden by env (`CODX_SEARXNG_URL`, `BRAVE_API_KEY`/`CODX_BRAVE_API_KEY`, `TAVILY_API_KEY`, `CODX_JINA_READER_URL`, `FIRECRAWL_API_KEY`, `CODX_LIGHTPANDA_BIN`, `CODX_OBSCURA_BIN`, `CODX_WEB_LITE_ENGINE`, `CODX_WEB_PREMIUM_PROVIDER`, `CODX_WEB_FETCH_ALLOW_PRIVATE_HOSTS`). Defaults must never require config: static fetch + extraction + ddgs fallback.

Never enable `--stealth`/premium fetch by default; premium only when the tool asks or `CODX_WEB_PREMIUM_PROVIDER` is set.
