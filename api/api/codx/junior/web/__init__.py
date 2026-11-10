"""Web research stack used by the model facing tools.

The module is split by responsibility so each piece can be tested and replaced
on its own:

    settings         resolution of ``integrations[]`` + environment config
    guard            SSRF / size / deadline guards for outbound HTTP
    extract          reader-mode HTML -> markdown (trafilatura first)
    browser_fetch    rendering escalation (lite engine, then Chromium)
    premium          optional Jina Reader / Firecrawl clients (off by default)
    search_backends  SearXNG / Brave / Tavily / DuckDuckGo search providers
    fetch            the ``fetch_webpage`` pipeline that wires them together

Consumers are ``codx.junior.tools.fetch_webpage`` and
``codx.junior.tools.duckduckgo_search`` (the ``fetch_webpage`` and
``web_search`` tools); they only format what this package returns.

Made with ❤️ by codx-junior
"""