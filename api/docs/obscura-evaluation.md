# Obscura — evaluation as a tool for models

Assessment of [h4ckf0r0day/obscura](https://github.com/h4ckf0r0day/obscura)
(Apache-2.0, Rust headless browser engine) as a browser/tool backend for the
agents running inside codx-junior.

Sources: repository README, `docs/Use-the-MCP-server.md`, `skills/obscura/SKILL.md`,
GitHub API metadata. State at retrieval: HEAD `1ee3ac1` (2026-11-09), 31.3k stars,
2.4k forks, 113 open issues, 101 open PRs, 1,686 commits. Vendor benchmarks are
**not independently reproduced** (the benchmark suite is a separate repo by the
same owner).

---

## 1. What it is

A headless browser engine that does *not* wrap Chromium: V8 is embedded for
JavaScript, DOM and CSS layout/paint are implemented in Rust, and the whole thing
speaks the Chrome DevTools Protocol.

| Surface | Command | What a model gets |
|---|---|---|
| MCP server | `obscura mcp` (stdio) / `obscura mcp --http --port N` | ~30 `browser_*` tools, stateful page session |
| CDP | `obscura serve --port 9222` | Works with `puppeteer-core` / `playwright-core` `connectOverCDP` |
| CLI | `obscura fetch <url>` / `obscura scrape <url...>` | One-shot `--dump html\|text\|metadata\|links\|markdown\|assets\|original`, `--eval`, `--screenshot` |
| Docker | `h4ckf0r0day/obscura` | Distroless, non-root (uid 65532), CDP on 9222, token via `OBSCURA_CDP_TOKEN` |

Vendor-reported footprint: ~30 MB RSS per page, ~70 MiB binary, 51–85 ms page
load, instant startup; optional `render` and `stealth` build features.

---

## 2. Strengths for model consumption

- **Context economy is designed in, not bolted on.** `browser_snapshot` returns
  URL/title/actionable element *references* plus body text under a shared
  `max_chars` budget (default 4000, `0` = metadata only), and there are
  `browser_markdown`, `browser_extract`, `browser_links`,
  `browser_interactive_elements`. That is the right shape for an LLM: refs +
  bounded text instead of 200 KB of raw HTML. CDP exposes the same via
  `LP.getMarkdown`, and the CLI via `--dump markdown`.
- **Stateful session.** Navigate once, then act on the live page; URL is not
  re-sent per call, and a parked (idle) page does not block new MCP requests.
- **Cost per concurrent session.** 30 MB vs 200+ MB for headless Chrome matters
  when every chat can open a browser; today one browser per session is a
  container with a full desktop stack.
- **Latency.** Page-load and startup numbers, if roughly accurate, cut the
  timeout class of failures that currently force tool retries.
- **Zero-dependency distribution.** Static binary, no Chrome, no Node — removes
  the `playwright install chromium` bootstrap (`ensure_playwright_ready`).
- **Screenshot and PDF without Chromium** (`browser_pdf`, `page.pdf()`).
- **Security thinking that fits agent use**, unusually explicit:
  - SSRF guard: private/internal IPs blocked by default, opt-in via
    `--allow-private-network`;
  - MCP HTTP transport refuses a non-loopback bind without a `Bearer` token of
    ≥32 bytes; browser `Origin`s refused unless allow-listed; bounded bodies,
    batches, connections;
  - `--obey-robots` available on `serve`.
- **Naming familiarity.** Tool names follow the Playwright-MCP vocabulary
  (`browser_navigate`/`snapshot`/`click`/`fill`/`evaluate`/`wait_for`), so a model
  needs little prompting to use them correctly.

---

## 3. Weaknesses and risks

- **Rendering fidelity is the headline caveat.** The README states long-tail CSS,
  some Web APIs, media playback, compositor effects and platform font
  rasterization "may differ from Chromium". Consequence: fine for *reading*
  pages, **not** trustworthy for "does this UI look right", visual regression, or
  pixel-faithful PDF export of rich slide decks.
- **DOM/accessibility fidelity is explicitly partial** ("compact browsing
  context, not a claim of complete accessibility conformance"). Ref-based
  clicking on a11y-heavy SPAs can resolve to the wrong node — and the MCP docs
  warn that "a failed interaction can have partial side effects", so the model
  must re-snapshot after failures. That has to be stated in our tool descriptions.
- **CDP coverage is a subset.** Documented domains: Target, Page, Runtime, DOM,
  Network, Fetch, IO, Storage, Input, LP. Not covered/not mentioned: file upload
  (`DOM.setFileInputFiles`), `Browser.setDownloadBehavior`, touch emulation,
  `DOMSnapshot`, `Accessibility`, service workers. Our current code uses
  download behaviour and expects Playwright download events, so this is the main
  integration risk, not the marketing claims.
- **Heavy-SPA tuning is manual.** Default 30 s page-script deadline and 3 s
  per-module budget with `OBSCURA_SCRIPT_DEADLINE_MS` /
  `OBSCURA_MODULE_BUDGET_MS` workarounds — React/Vue/Angular apps on slow
  networks will need per-deployment env tuning.
- **Operational rough edges.** Distroless image: no shell, no package manager,
  mounted storage must be writable by uid 65532 (relevant to `--storage-dir`);
  a worker crash closes that worker's live sessions and the client must
  reconnect; multi-worker mode returns HTTP 503 when no worker is ready.
- **Project maturity / governance.** Single-maintainer account, 113 open issues
  and 101 open pull requests against 1.7k commits (review throughput is the
  bottleneck, not activity). Commercial hosted tier ("Obscura Cloud": managed
  infra, residential proxies) is announced; Apache-2.0 with a no-gating promise
  today, no governance guarantee. Extremely high star count for the account age
  plus proxy-affiliate codes in the README are hype signals — weigh the tech, not
  the ranking.
- **Stealth is a compliance decision, not a feature flag.** Anti-fingerprinting
  (`navigator.webdriver=false`, masked natives, randomized GPU/canvas/audio) and
  3,520 blocked tracker domains are designed to defeat bot detection. Enabling it
  by default would put us on the wrong side of site ToS and of our own scraping
  policy; it must be explicit per call, logged, and paired with `--obey-robots`
  where applicable.

---

## 4. Fit with codx-junior today

Current browser stack (`codx/junior/browser/`):

- `browser.py` — the only module allowed to import Playwright: CDP automation of
  a remote Chromium container (`Browser`) plus `PdfPrinter`/`print_pdf` on a local
  headless Chromium for `doc_converter`.
- `docker_browser_manager.py` — one LinuxServer.io Chromium container per
  `BrowserSession`, publishing a **Selkies web desktop** for the user's live view
  (`/browser/<session_id>/`) and the CDP endpoint at `127.0.0.1:9222`.
- `cdp_proxy.py` — Host-header rewrite, stable `/devtools/browser/<id>`, Chromium
  supervision (reopen tab, restart s6 service).
- `scripts.py` — per-site `steps` replayed through `browse_action`.

Ranked options:

| # | Option | Verdict |
|---|---|---|
| 1 | Extra headless engine for **text/markdown extraction** (`obscura fetch --dump markdown`) or a `web_fetch` tool | **Recommended.** Cheapest win: no Chromium, 30 MB, one call, bounded output |
| 2 | Replace `print_pdf` / `doc_converter` rendering | **Conditional.** Removes the Chromium bootstrap, but must be validated against `slides/` and Reveal.js decks; keep Chromium as fallback |
| 3 | Transport for `--stealth` on bot-protected sites | **Opt-in only**, with a policy + audit trail |
| 4 | Replace the Chromium **co-browsing container** | **Rejected.** Loses the live view (needs X/Selkies, impossible on a distroless image), and download/upload/CDP gaps break existing flows |

Integration rule if adopted: a single adapter inside `codx.junior.browser`, so no
other module learns about obscura; sessions keep going through `BrowserManager`
so the live view and the automation never diverge.

---

## 5. Recommendation

**Adopt as a supplementary headless engine, not as a Chromium replacement.**
Start with one consumer and one measurable proof.

PoC (half a day):

1. `docker run` the distroless image with `OBSCURA_CDP_TOKEN`, plus a native
   binary for the CLI path; confirm `--allow-private-network` is *not* needed
   for our normal egress and that private ranges are refused.
2. Run `obscura fetch --dump markdown` over ~20 URLs already used in tests/fixtures
   and compare text quality against the current Playwright `innerText` path.
3. Connect `playwright-core` `connectOverCDP` to `obscura serve` and replay three
   existing `scripts.py` `steps` sets; record pass/fail and, specifically, whether
   downloads and file inputs work.
4. Export two `slides/` decks to PDF with both engines; visually diff page count
   and layout.
5. Measure peak RSS and p50/p95 latency for 5 concurrent pages.

Adopt if: text extraction ≥ current quality, ≥2/3 scripted flows pass, slide PDFs
are acceptable, and no CDP method we rely on is missing. Otherwise keep it as a
`web_fetch`-only tool, which is still a net win.
