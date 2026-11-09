"""Web research stack used by the model facing tools.

The module is split by responsibility so each piece can be tested and replaced
on its own:

    settings         resolution of ``integrations[]`` + environment config
    guard            SSRF / size / deadline guards for outbound HTTP
    extract          reader-mode HTML -> markdown (trafilatura first)
    browser_fetch    Chromium escalation for JavaScript rendered pages
    premium          optional Jina Reader / Firecrawl clients (off by default)
    search_backends  SearXNG / Brave / Tavily / DuckDuckGo search providers

Consumers are ``codx.junior.tools.fetch_webpage`` and
``codx.junior.tools.duckduckgo_search`` (the ``fetch_webpage`` and
``web_search`` tools).

Made with ❤️ by codx-junior
"""
