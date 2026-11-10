"""Tests for the model facing web stack (guard, extraction, search, fetch)."""

import pytest

from codx.junior.web import guard
from codx.junior.web.extract import (
    clean_markdown,
    extract_content,
    is_thin,
    text_from_markdown,
    truncate_markdown,
)
from codx.junior.web.settings import IntegrationConfig, WebSettings

ARTICLE = """
<html><head><title>Reader mode</title></head><body>
<nav>NAVTOKEN menu</nav>
<article><h1>Reader mode</h1>
<p>{body}</p>
</article>
<footer>FOOTERTOKEN</footer>
<script>var x = 1;</script>
</body></html>
""".format(body="Sentence with real content. " * 40)


# ---------------------------------------------------------------------------
# guard
# ---------------------------------------------------------------------------

def test_guard_rejects_private_and_local_targets():
    for url in (
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.5:2375/containers/json",
        "http://localhost/admin",
    ):
        with pytest.raises(guard.UnsafeUrlError):
            guard.validate_url(url)


def test_guard_rejects_other_schemes():
    with pytest.raises(guard.UnsafeUrlError):
        guard.validate_url("file:///etc/passwd")
    with pytest.raises(guard.UnsafeUrlError):
        guard.validate_url("gopher://example.com")


def test_guard_normalizes_public_urls(monkeypatch):
    monkeypatch.setattr(guard, "resolve_host", lambda host, port=None: ["93.184.216.34"])
    assert guard.validate_url("https://example.com/a#frag") == "https://example.com/a"


def test_guard_allows_private_targets_when_asked():
    assert guard.validate_url("http://127.0.0.1/x", allow_private=True) == "http://127.0.0.1/x"


# ---------------------------------------------------------------------------
# extraction
# ---------------------------------------------------------------------------

def test_extraction_drops_page_chrome():
    content = extract_content(ARTICLE, url="https://example.com/post")
    assert content.extractor
    assert "Sentence with real content" in content.markdown
    assert "NAVTOKEN" not in content.markdown
    assert "FOOTERTOKEN" not in content.markdown
    assert "var x" not in content.markdown


def test_extraction_of_empty_document():
    content = extract_content("", url="https://example.com")
    assert content.extractor == "empty"
    assert content.markdown == ""
    assert is_thin(content)


def test_thin_detection_uses_text_length():
    content = extract_content("<html><body><p>hi</p></body></html>")
    assert is_thin(content)
    assert not is_thin(extract_content(ARTICLE), html_len=len(ARTICLE))


def test_markdown_helpers():
    assert text_from_markdown("See [docs](https://x) ![i](a.png) **now**") == "See docs now"
    assert clean_markdown("a\n\n\n\nb") == "a\n\nb"
    assert truncate_markdown("abcdef", 3) == ("abc", True)
    assert truncate_markdown("abc", None) == ("abc", False)


def test_bot_wall_detection():
    assert guard  # keeps the import used if hints move
    from codx.junior.web.extract import bot_wall_reason

    assert bot_wall_reason("<html>Just a moment...</html>")
    assert bot_wall_reason(ARTICLE) is None


# ---------------------------------------------------------------------------
# search chain
# ---------------------------------------------------------------------------

def _web_settings(*names):
    return WebSettings(search_backends=[IntegrationConfig(name=name) for name in names])


def test_search_falls_back_and_keeps_errors(monkeypatch):
    from codx.junior.web import search_backends

    def boom(config, query, max_results, search_type):
        raise search_backends.SearchBackendError("not configured")

    def ok(config, query, max_results, search_type):
        return [search_backends.SearchHit(title="T", url="https://example.com/x", snippet="S")]

    monkeypatch.setitem(search_backends._BACKENDS, "searxng", boom)
    monkeypatch.setitem(search_backends._BACKENDS, "ddgs", ok)

    result = search_backends.search_web(
        "query",
        backends=["searxng", "ddgs"],
        settings=_web_settings("searxng", "ddgs"),
    )

    assert result.backend == "ddgs"
    assert len(result.hits) == 1
    assert any("searxng" in error for error in result.errors)


def test_search_without_results_reports_every_backend(monkeypatch):
    from codx.junior.web import search_backends

    monkeypatch.setitem(
        search_backends._BACKENDS, "ddgs", lambda *args, **kwargs: []
    )

    result = search_backends.search_web(
        "nothing",
        backends=["ddgs"],
        settings=_web_settings("ddgs"),
    )

    assert result.is_empty
    assert result.errors == ["ddgs: no results"]


def test_search_validates_input():
    from codx.junior.web import search_backends

    with pytest.raises(ValueError):
        search_backends.search_web("  ", settings=_web_settings("ddgs"))
    with pytest.raises(ValueError):
        search_backends.search_web("q", search_type="videos", settings=_web_settings("ddgs"))


# ---------------------------------------------------------------------------
# fetch pipeline
# ---------------------------------------------------------------------------

def test_fetch_page_extracts_static_html(monkeypatch):
    from codx.junior.web import fetch as web_fetch

    page = guard.FetchedPage(
        url="https://example.com/post",
        final_url="https://example.com/post",
        status=200,
        content_type="text/html; charset=utf-8",
        text=ARTICLE,
    )
    monkeypatch.setattr(web_fetch, "validate_url", lambda url, allow_private=False: url)
    monkeypatch.setattr(web_fetch, "safe_get", lambda *args, **kwargs: page)

    result = web_fetch.fetch_page(
        "https://example.com/post",
        settings=WebSettings(browser_escalation=False, max_output_chars=100_000),
    )

    assert "Sentence with real content" in result.markdown
    assert "NAVTOKEN" not in result.markdown
    assert result.rendered is False
    assert result.final_url == "https://example.com/post"


def test_fetch_page_caps_the_output(monkeypatch):
    from codx.junior.web import fetch as web_fetch

    page = guard.FetchedPage(
        url="https://example.com/post",
        final_url="https://example.com/post",
        status=200,
        content_type="text/html",
        text=ARTICLE,
    )
    monkeypatch.setattr(web_fetch, "validate_url", lambda url, allow_private=False: url)
    monkeypatch.setattr(web_fetch, "safe_get", lambda *args, **kwargs: page)

    result = web_fetch.fetch_page(
        "https://example.com/post",
        max_chars=100,
        settings=WebSettings(browser_escalation=False),
    )

    assert len(result.markdown) == 100
    assert result.truncated is True


def test_fetch_page_refuses_private_targets():
    from codx.junior.web.fetch import fetch_page

    with pytest.raises(guard.UnsafeUrlError):
        fetch_page("http://169.254.169.254/latest/meta-data")