"""
Document and content converter tools.

This module converts project documents and inline content between formats,
reusing the engines already used elsewhere in the project:

    - pypandoc (pandoc binary), as used by ``codx.junior.chat.chat_export``
    - BeautifulSoup + html2text, as used by ``fetch_webpage``
    - the Playwright manager (``codx.junior.browser.browser``) for html -> pdf

Supported conversions:
    - markdown -> pdf      (pandoc + a PDF engine)
    - markdown -> docx     (pandoc)
    - html     -> markdown (BeautifulSoup + html2text, no external binary)
    - html     -> pdf      (headless Chromium, or pandoc + a PDF engine)

Rendering engines for ``html -> pdf``:
    - ``browser``: headless Chromium prints the page exactly as a browser
      renders it (JavaScript, flexbox/grid, custom fonts, background colors and
      images). Required for visually rich slide decks (Reveal.js, Marp, custom
      CSS) and for ``url`` sources.
    - ``pandoc``: static HTML conversion, no JavaScript, no modern CSS.
    - ``auto``: browser first, pandoc fallback when Chromium cannot be used.

Missing Playwright components (the ``playwright`` package and the Chromium
build) are installed on first use by the browser module; set
``CODX_BROWSER_AUTO_INSTALL=0`` to disable it.

All Playwright handling lives in ``codx.junior.browser.browser``; this module
only decides what to render and where to save it.

Sources and outputs:
    - The source is either inline ``content``, a project file ``source_path``
      or a ``url`` (browser rendering only). The source format is inferred from
      the file extension.
    - The result is always written inside the project (``output_path``).
      PDF and DOCX are binary, so they are only referenced by path, while the
      converted markdown is also returned inline in the tool response.

Chart:
    flowchart LR
        A[content / source_path / url] --> B{source_format}
        B -->|markdown| C[pandoc]
        B -->|html| D[html2text]
        B -->|html| E{render_engine}
        E -->|browser| F[codx.junior.browser]
        E -->|pandoc| C
        C --> G[pdf / docx]
        D --> H[markdown]
        F --> G

Made with ❤️ by codx-junior
"""

import os
import logging
import tempfile
from typing import List, Optional

import html2text
import pypandoc
from bs4 import BeautifulSoup

from codx.junior.browser.browser import (
    BROWSER_MEDIA_TYPES,
    BrowserUnavailableError,
    ensure_playwright_ready,
    parse_margin,
    parse_page_size,
    print_pdf,
)
from codx.junior.settings import CODXJuniorSettings
from .model import ToolResponse
from .project_tools import path_to_absolute_project_path

# Configure logging
logger = logging.getLogger(__name__)

# Formats supported as source and as target
SOURCE_FORMATS = ("markdown", "html")
TARGET_FORMATS = ("pdf", "docx", "markdown")

# Supported source -> target pairs. Any other combination is rejected.
SUPPORTED_CONVERSIONS = (
    ("markdown", "pdf"),
    ("markdown", "docx"),
    ("html", "markdown"),
    ("html", "pdf"),
)

# Extension used when the caller does not provide an output path
OUTPUT_EXTENSIONS = {
    "pdf": ".pdf",
    "docx": ".docx",
    "markdown": ".md",
}

# Extensions used to infer the source format from a project file
SOURCE_FORMAT_EXTENSIONS = {
    "markdown": (".md", ".markdown", ".mdx"),
    "html": (".html", ".htm", ".xhtml"),
}

# Pandoc readers per source format: gfm keeps tables, task lists and
# strikethrough of GitHub flavored markdown.
PANDOC_READERS = {
    "markdown": "gfm",
    "html": "html",
}

# PDF engines available to pandoc, in fallback preference order
PDF_ENGINES = ("xelatex", "lualatex", "pdflatex", "weasyprint", "wkhtmltopdf", "typst")
# xelatex handles Unicode/emoji content, as done by the chat export
DEFAULT_PDF_ENGINE = "xelatex"
# A missing engine aborts fast, but a rendering error does not: limit retries
MAX_PDF_ENGINE_ATTEMPTS = 3

# Rendering engines used for html -> pdf
RENDER_ENGINES = ("auto", "browser", "pandoc")
DEFAULT_RENDER_ENGINE = "auto"

# Maximum characters of converted markdown returned inline in the response
MAX_INLINE_MARKDOWN_CHARS = 20000

# Default output name when neither 'source_path' nor 'output_path' is given
DEFAULT_OUTPUT_NAME = "document"


DOC_CONVERTER_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "doc_converter",
        "description": (
            "Convert document content between formats and save the result inside the project. "
            "Supported conversions: markdown -> pdf, markdown -> docx, html -> markdown, "
            "html -> pdf. "
            "HTML to PDF is printed by a headless Chromium ('render_engine', default 'auto'), "
            "so JavaScript, modern CSS, custom fonts and background images are kept; pandoc is "
            "used as fallback and always for markdown. "
            "Chromium is installed automatically (once) when it is missing. "
            "For visually rich slide decks (Reveal.js, Marp, custom CSS) pass 'slides' = true and "
            "optionally 'page_break_selector' to get one PDF page per slide. "
            "The source is inline 'content', a project file 'source_path' or a 'url' (browser "
            "rendering only); the source format is inferred from the file extension and can be "
            "forced with 'source_format'. "
            "The output is always written to 'output_path' (default: the source name with the "
            "target extension). PDF and DOCX files are binary: they are referenced by path and "
            "must be read from the file system, while converted markdown is also returned inline."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target_format": {
                    "type": "string",
                    "enum": list(TARGET_FORMATS),
                    "description": (
                        "Format to produce: 'pdf' (from markdown or html), 'docx' (from markdown) "
                        "or 'markdown' (from html)."
                    )
                },
                "content": {
                    "type": "string",
                    "description": (
                        "Inline source content to convert. Do not use together with "
                        "'source_path' or 'url'."
                    )
                },
                "source_path": {
                    "type": "string",
                    "description": (
                        "Relative or absolute path of a project file used as the conversion source. "
                        "Its extension determines 'source_format'. Do not use together with "
                        "'content' or 'url'."
                    )
                },
                "source_format": {
                    "type": "string",
                    "enum": list(SOURCE_FORMATS),
                    "description": (
                        "Format of the source: 'markdown' or 'html'. Inferred from 'source_path' "
                        "when omitted, and required when only 'content' is provided."
                    )
                },
                "output_path": {
                    "type": "string",
                    "description": (
                        "Relative or absolute project path for the converted file. Defaults to the "
                        "source file name (or 'document') with the target extension."
                    )
                },
                "title": {
                    "type": "string",
                    "description": (
                        "Optional document title metadata written into the pdf or docx output."
                    )
                },
                "pdf_engine": {
                    "type": "string",
                    "enum": list(PDF_ENGINES),
                    "default": DEFAULT_PDF_ENGINE,
                    "description": (
                        "PDF engine used by pandoc (default: xelatex). Fallback engines are tried "
                        "when the selected one is unavailable or fails. Ignored by the browser "
                        "renderer."
                    )
                },
                "render_engine": {
                    "type": "string",
                    "enum": list(RENDER_ENGINES),
                    "default": DEFAULT_RENDER_ENGINE,
                    "description": (
                        "Renderer for html -> pdf: 'auto' (default) prints with a headless "
                        "Chromium (installed automatically when missing) and falls back to pandoc "
                        "when it cannot be used, 'browser' forces the browser renderer (needed for "
                        "rich html slides and 'url' sources) and 'pandoc' always uses pandoc."
                    )
                },
                "url": {
                    "type": "string",
                    "description": (
                        "Page URL (http(s):// or file://) to render with the browser engine "
                        "instead of project content. Only valid for html -> pdf."
                    )
                },
                "slides": {
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "Slide deck preset for html -> pdf: 1920x1080 landscape pages, screen "
                        "media, background graphics and zero margins. Use it for Reveal.js, Marp "
                        "or custom CSS decks; 'page_size', 'landscape', 'media', "
                        "'print_background' and 'margin' override the preset."
                    )
                },
                "page_size": {
                    "type": "string",
                    "description": (
                        "PDF page size: a paper format ('A4', 'Letter', 'Legal', ...) or explicit "
                        "dimensions such as '1920x1080' (CSS pixels) or '13.33in x 7.5in'. "
                        "Defaults to 1920x1080 with 'slides', otherwise the browser default."
                    )
                },
                "landscape": {
                    "type": "boolean",
                    "description": "Print landscape. Defaults to true with 'slides'."
                },
                "media": {
                    "type": "string",
                    "enum": list(BROWSER_MEDIA_TYPES),
                    "description": (
                        "CSS media emulated before printing: 'screen' keeps the deck styles, "
                        "'print' applies the framework print rules. Defaults to 'screen' with "
                        "'slides', otherwise the browser default."
                    )
                },
                "print_background": {
                    "type": "boolean",
                    "description": (
                        "Print CSS background colors and images (default: true). Essential for "
                        "rich slides."
                    )
                },
                "margin": {
                    "type": "string",
                    "description": (
                        "Page margin: a single CSS length ('0', '1cm') or four comma separated "
                        "values (top,right,bottom,left). Defaults to 0 with 'slides'."
                    )
                },
                "page_break_selector": {
                    "type": "string",
                    "description": (
                        "CSS selector whose matched elements each start a new PDF page (e.g. "
                        "'section', '.slide', '.reveal .slides > section'). Keeps text and links "
                        "as vectors instead of screenshots. Browser engine only."
                    )
                },
                "wait_for_selector": {
                    "type": "string",
                    "description": (
                        "CSS selector to wait for before printing (e.g. a rendered slide or a "
                        "chart). Browser engine only."
                    )
                },
                "wait_timeout_ms": {
                    "type": "integer",
                    "default": 0,
                    "description": (
                        "Extra delay in milliseconds after the page is ready, so animations and "
                        "async rendering settle before printing. Browser engine only."
                    )
                },
                "script": {
                    "type": "string",
                    "description": (
                        "JavaScript executed in the page right before printing, used to prepare "
                        "animated decks (e.g. \"() => Reveal.slide(0)\" or \"return "
                        "document.querySelectorAll('section').length\"). Browser engine only."
                    )
                }
            },
            "required": ["target_format"]
        }
    }
}


class _BrowserRendererUnavailable(RuntimeError):
    """Raised when the browser renderer used to print PDFs cannot be used."""


def _resolve_project_path(
    settings: CODXJuniorSettings, file_path: str
) -> Optional[str]:
    """
    Resolve a relative or absolute path and ensure it stays inside the project.

    Args:
        settings: The project settings.
        file_path: Relative or absolute path to resolve.

    Returns:
        Optional[str]: Normalized absolute path, or None when it escapes the
        project root.

    Example:
        >>> _resolve_project_path(settings, "docs/guide.md")
        '/project/docs/guide.md'
    """
    if not file_path:
        return None

    abs_path = path_to_absolute_project_path(settings=settings, file_path=file_path)
    if not abs_path:
        return None

    abs_path = os.path.normpath(abs_path)
    project_root = os.path.normpath(settings.abs_project_path)
    if abs_path != project_root and not abs_path.startswith(project_root + os.sep):
        logger.warning("Path outside project root: %s", file_path)
        return None
    return abs_path


def _to_relative_path(settings: CODXJuniorSettings, abs_path: str) -> str:
    """
    Convert an absolute path into a project-relative path when possible.

    Args:
        settings: The project settings.
        abs_path: Absolute path to convert.

    Returns:
        str: Project-relative path (or the original path when outside).
    """
    if abs_path.startswith(settings.abs_project_path):
        return os.path.relpath(abs_path, settings.abs_project_path)
    return abs_path


def _detect_source_format(source_path: Optional[str]) -> Optional[str]:
    """
    Infer the source format from a file extension.

    Args:
        source_path: Project file path used as conversion source.

    Returns:
        Optional[str]: 'markdown', 'html', or None when it cannot be inferred.

    Example:
        >>> _detect_source_format("docs/guide.md")
        'markdown'
    """
    if not source_path:
        return None

    extension = os.path.splitext(source_path)[1].lower()
    for source_format, extensions in SOURCE_FORMAT_EXTENSIONS.items():
        if extension in extensions:
            return source_format
    return None


def _resolve_source_format(
    source_format: Optional[str], source_path: Optional[str]
) -> str:
    """
    Determine the source format from the argument or the file extension.

    Args:
        source_format: Explicit source format provided by the caller.
        source_path: Project file path used as conversion source.

    Returns:
        str: Resolved source format ('markdown' or 'html').

    Raises:
        ValueError: If the format is invalid or cannot be inferred.
    """
    if source_format:
        resolved = source_format.strip().lower()
        if resolved not in SOURCE_FORMATS:
            raise ValueError(
                f"source_format '{source_format}' is not supported. "
                f"Use one of: {', '.join(SOURCE_FORMATS)}"
            )
        return resolved

    detected = _detect_source_format(source_path=source_path)
    if detected:
        return detected

    raise ValueError(
        "source_format ('markdown' or 'html') is required when the source is inline "
        "'content' or when the file extension is not recognized"
    )


def _build_output_path(
    source_path: Optional[str], output_path: Optional[str], target_format: str
) -> str:
    """
    Build the project-relative output path for the converted document.

    Args:
        source_path: Source file path, used to derive the default name.
        output_path: Explicit output path provided by the caller.
        target_format: Conversion target format.

    Returns:
        str: Project-relative output path.

    Example:
        >>> _build_output_path("docs/guide.md", None, "pdf")
        'docs/guide.pdf'
        >>> _build_output_path(None, "exports/manual", "docx")
        'exports/manual.docx'
    """
    extension = OUTPUT_EXTENSIONS[target_format]

    if output_path:
        # Keep the caller path but ensure it carries the target extension
        if not os.path.splitext(output_path)[1]:
            return f"{output_path}{extension}"
        return output_path

    stem = DEFAULT_OUTPUT_NAME
    folder = ""
    if source_path:
        stem = os.path.splitext(os.path.basename(source_path))[0] or DEFAULT_OUTPUT_NAME
        folder = os.path.dirname(source_path)

    file_name = f"{stem}{extension}"
    return os.path.join(folder, file_name) if folder else file_name


def _resource_path(settings: CODXJuniorSettings, source_abs_path: Optional[str]) -> str:
    """
    Build the pandoc ``--resource-path`` value to resolve relative resources.

    Relative images and links are looked up first next to the source file and
    then at the project root.

    Args:
        settings: The project settings.
        source_abs_path: Absolute path of the source file, if any.

    Returns:
        str: Colon separated list of resource folders.

    Example:
        >>> _resource_path(settings, "/project/docs/guide.md")
        '/project/docs:/project'
    """
    folders = [os.path.normpath(settings.abs_project_path)]
    if source_abs_path:
        folders.insert(0, os.path.dirname(source_abs_path))
    # Remove duplicates while keeping order
    return os.pathsep.join(dict.fromkeys(folders))


def _pdf_engine_candidates(pdf_engine: Optional[str]) -> list:
    """
    Build the ordered list of PDF engines to try.

    The requested engine is tried first, then the remaining known engines up to
    ``MAX_PDF_ENGINE_ATTEMPTS``. An empty engine means "let pandoc decide".

    Args:
        pdf_engine: Engine requested by the caller.

    Returns:
        list: Engine names to attempt in order.

    Example:
        >>> _pdf_engine_candidates("weasyprint")
        ['weasyprint', 'xelatex', 'lualatex']
    """
    requested = (pdf_engine or "").strip().lower()
    candidates = [requested]
    for engine in PDF_ENGINES:
        if len(candidates) >= MAX_PDF_ENGINE_ATTEMPTS:
            break
        if engine != requested:
            candidates.append(engine)
    return candidates


def _ensure_pandoc() -> str:
    """
    Verify that the pandoc binary is available.

    Returns:
        str: Installed pandoc version.

    Raises:
        RuntimeError: When pandoc is not installed or not found in the PATH.
    """
    try:
        return pypandoc.get_pandoc_version()
    except OSError as ex:
        raise RuntimeError(
            "pandoc binary is not available. Install pandoc (e.g. 'apt-get install pandoc') "
            "and a PDF engine ('texlive-xetex' for the default xelatex engine) to enable "
            "PDF and DOCX conversions."
        ) from ex


def _html_to_markdown(html: str) -> str:
    """
    Convert HTML into markdown using BeautifulSoup and html2text.

    Scripts and styles are removed and tables, links and images are preserved,
    matching the behaviour of ``fetch_webpage``.

    Args:
        html: HTML source content.

    Returns:
        str: Markdown representation of the HTML content.

    Example:
        >>> _html_to_markdown("<h1>Title</h1><p>Text</p>")
        '# Title\\n\\nText'
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove non textual elements
    for tag in soup(["script", "style"]):
        tag.decompose()

    converter = html2text.HTML2Text()
    converter.body_width = 0  # No line wrapping
    converter.ignore_images = False
    converter.ignore_emphasis = False
    converter.ignore_links = False
    converter.ignore_tables = False

    return converter.handle(str(soup)).strip()


def _pandoc_extra_args(
    resource_path: str, title: Optional[str] = None
) -> list:
    """
    Build the common pandoc arguments for document conversions.

    Args:
        resource_path: Folders used to resolve relative resources.
        title: Optional document title metadata.

    Returns:
        list: pandoc extra arguments.
    """
    extra_args = ["--standalone"]
    if resource_path:
        extra_args += ["--resource-path", resource_path]
    if title:
        extra_args += ["--metadata", f"title={title}"]
    return extra_args


def _convert_to_docx(
    content: str,
    source_format: str,
    output_file: str,
    resource_path: str,
    title: Optional[str] = None,
) -> None:
    """
    Convert content into a DOCX file with pandoc.

    Args:
        content: Source content to convert.
        source_format: Source format ('markdown' or 'html').
        output_file: Absolute path of the DOCX file to write.
        resource_path: Folders used to resolve relative resources.
        title: Optional document title metadata.

    Raises:
        Exception: Propagated from pandoc when the conversion fails.
    """
    logger.debug("Converting %s to docx: %s", source_format, output_file)
    pypandoc.convert_text(
        content,
        to="docx",
        format=PANDOC_READERS[source_format],
        outputfile=output_file,
        extra_args=_pandoc_extra_args(resource_path=resource_path, title=title),
    )


def _convert_to_pdf(
    content: str,
    source_format: str,
    output_file: str,
    resource_path: str,
    pdf_engine: Optional[str] = DEFAULT_PDF_ENGINE,
    title: Optional[str] = None,
) -> str:
    """
    Convert content into a PDF file with pandoc, trying alternative engines.

    Args:
        content: Source content to convert.
        source_format: Source format ('markdown' or 'html').
        output_file: Absolute path of the PDF file to write.
        resource_path: Folders used to resolve relative resources.
        pdf_engine: Preferred PDF engine (empty string lets pandoc decide).
        title: Optional document title metadata.

    Returns:
        str: The engine that produced the PDF ("" for the pandoc default).

    Raises:
        RuntimeError: When every attempted engine fails.
    """
    base_args = _pandoc_extra_args(resource_path=resource_path, title=title)
    errors = []

    for engine in _pdf_engine_candidates(pdf_engine=pdf_engine):
        extra_args = list(base_args)
        if engine:
            extra_args.append(f"--pdf-engine={engine}")
        try:
            logger.debug(
                "Converting %s to pdf with engine '%s': %s",
                source_format, engine or "default", output_file
            )
            pypandoc.convert_text(
                content,
                to="pdf",
                format=PANDOC_READERS[source_format],
                outputfile=output_file,
                extra_args=extra_args,
            )
            return engine
        except Exception as ex:
            logger.warning(
                "PDF conversion failed with engine '%s': %s", engine or "default", ex
            )
            errors.append(f"{engine or 'default'}: {ex}")

    raise RuntimeError(
        "no PDF engine could render the document ("
        + "; ".join(errors)
        + "). Install one of: "
        + ", ".join(PDF_ENGINES)
    )


def _browser_renderer_available() -> bool:
    """
    Return True when the browser renderer can print PDFs.

    The browser module installs the missing Playwright components on first use
    (the ``playwright`` package and the Chromium build), so a fresh deployment
    can print rich HTML slides without manual setup. Set
    ``CODX_BROWSER_AUTO_INSTALL=0`` to disable the installation.

    Returns:
        bool: True when the browser renderer is usable.
    """
    try:
        return ensure_playwright_ready()
    except Exception as ex:  # pragma: no cover - defensive
        logger.debug("browser renderer not available: %s", ex)
        return False


def _validate_print_options(page_size: Optional[str], margin: Optional[str]) -> None:
    """
    Validate PDF layout options early so bad arguments raise ``ValueError``.

    Args:
        page_size: Page size argument to validate.
        margin: Margin argument to validate.

    Raises:
        ValueError: When a page size or margin value is invalid.
    """
    parse_page_size(page_size)
    parse_margin(margin)


def _print_pdf_with_browser(target: str, output_file: str, **options) -> str:
    """
    Print a URL or project file to PDF through the Playwright manager.

    All browser handling (installation, launch, media emulation, page breaks,
    ``page.pdf``) lives in :mod:`codx.junior.browser.browser`; this wrapper only
    normalizes the exception so callers never depend on Playwright types.

    Args:
        target: URL or absolute file path to render.
        output_file: Absolute path of the PDF to write.
        **options: Print options forwarded to ``browser.print_pdf`` (``slides``,
            ``page_size``, ``landscape``, ``print_background``, ``margin``,
            ``media``, ``wait_for_selector``, ``wait_timeout_ms``, ``script``,
            ``page_break_selector``, ``auto_install``).

    Returns:
        str: Renderer label that produced the PDF.

    Raises:
        _BrowserRendererUnavailable: When Playwright or Chromium is missing and
            cannot be installed.
    """
    try:
        return print_pdf(target=target, output_file=output_file, **options)
    except BrowserUnavailableError as ex:
        raise _BrowserRendererUnavailable(str(ex)) from ex


def _cap_markdown(markdown: str) -> str:
    """
    Trim converted markdown so the tool response stays reasonably small.

    Args:
        markdown: Converted markdown content.

    Returns:
        str: The markdown, truncated with a note when it exceeds the limit.
    """
    if len(markdown) <= MAX_INLINE_MARKDOWN_CHARS:
        return markdown
    return (
        markdown[:MAX_INLINE_MARKDOWN_CHARS]
        + "\n... (truncated, read the output file for the full content)"
    )


def doc_converter(
    target_format: str,
    content: Optional[str] = None,
    source_path: Optional[str] = None,
    output_path: Optional[str] = None,
    source_format: Optional[str] = None,
    title: Optional[str] = None,
    pdf_engine: str = DEFAULT_PDF_ENGINE,
    render_engine: str = DEFAULT_RENDER_ENGINE,
    url: Optional[str] = None,
    slides: bool = False,
    page_size: Optional[str] = None,
    landscape: Optional[bool] = None,
    media: Optional[str] = None,
    print_background: Optional[bool] = None,
    margin: Optional[str] = None,
    page_break_selector: Optional[str] = None,
    wait_for_selector: Optional[str] = None,
    wait_timeout_ms: int = 0,
    script: Optional[str] = None,
    **kwargs
) -> ToolResponse:
    """
    Convert a document or content between formats and save it in the project.

    Supported conversions:

    - markdown -> pdf: rendered with pandoc and the selected PDF engine.
    - markdown -> docx: rendered with pandoc.
    - html -> markdown: rendered with BeautifulSoup + html2text, no external binary.
    - html -> pdf: printed by a headless Chromium (default) or pandoc.

    Rich HTML slides use the browser renderer: ``slides=True`` sets a 16:9
    landscape page with screen media, background graphics and no margins, and
    ``page_break_selector`` gives each slide its own PDF page. The Chromium
    build is installed automatically the first time it is required.

    Args:
        target_format: Target format: 'pdf', 'docx' or 'markdown'.
        content: Inline source content (exclusive with ``source_path``/``url``).
        source_path: Project file used as source (exclusive with ``content``/``url``).
        output_path: Project path for the converted file. Defaults to the source
            name with the target extension.
        source_format: 'markdown' or 'html'. Inferred from ``source_path``.
        title: Optional document title metadata for pdf/docx outputs.
        pdf_engine: Preferred pandoc PDF engine, default 'xelatex'. Alternative
            engines are tried when it is unavailable or fails.
        render_engine: Renderer for html -> pdf: 'auto' (browser, pandoc
            fallback), 'browser' (force) or 'pandoc'.
        url: Page URL to render with the browser engine (html -> pdf only).
        slides: Slide deck preset (1920x1080, landscape, screen media,
            backgrounds, zero margins).
        page_size: Paper format ('A4', 'Letter') or '1920x1080' / '13.33in x 7.5in'.
        landscape: Print landscape (defaults to True with ``slides``).
        media: CSS media emulated before printing ('screen' or 'print').
        print_background: Print CSS backgrounds (default True).
        margin: Page margin, one CSS length or four comma separated values.
        page_break_selector: Selector whose matches each start a new PDF page.
        wait_for_selector: Selector to wait for before printing.
        wait_timeout_ms: Extra delay in milliseconds before printing.
        script: JavaScript executed right before printing.

    Returns:
        ToolResponse: Contains:
            - user_response: Confirmation with the output path, size and renderer.
            - llm_response: Conversion details plus the converted markdown when
              the target format is markdown.

    Raises:
        ValueError: If the arguments are invalid or the conversion pair is not
            supported.

    Example:
        >>> doc_converter(target_format="pdf", source_path="docs/guide.md")
        # ToolResponse with 'docs/guide.pdf' written in the project

        >>> doc_converter(
        ...     target_format="pdf",
        ...     source_path="slides/deck.html",
        ...     slides=True,
        ...     page_break_selector=".reveal .slides > section",
        ...     wait_for_selector=".reveal .slides section.present",
        ... )
        # Rich slide deck printed page by page with headless Chromium

        >>> doc_converter(
        ...     target_format="markdown",
        ...     content="<h1>Hello</h1>",
        ...     source_format="html",
        ...     output_path="docs/hello.md"
        ... )
        # ToolResponse with '# Hello' included inline and saved to docs/hello.md
    """
    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        raise Exception("Invalid project settings")

    normalized_target = (target_format or "").strip().lower()
    if normalized_target not in TARGET_FORMATS:
        raise ValueError(
            f"target_format '{target_format}' is not supported. "
            f"Use one of: {', '.join(TARGET_FORMATS)}"
        )

    normalized_engine = (render_engine or DEFAULT_RENDER_ENGINE).strip().lower()
    if normalized_engine not in RENDER_ENGINES:
        raise ValueError(
            f"render_engine '{render_engine}' is not supported. "
            f"Use one of: {', '.join(RENDER_ENGINES)}"
        )

    if media and media.strip().lower() not in BROWSER_MEDIA_TYPES:
        raise ValueError(
            f"media '{media}' is not supported. Use one of: {', '.join(BROWSER_MEDIA_TYPES)}"
        )

    if normalized_target == "pdf" and (page_size or margin):
        _validate_print_options(page_size=page_size, margin=margin)

    if url:
        if content or source_path:
            raise ValueError("Use 'url', 'content' or 'source_path', not more than one")
        if normalized_target != "pdf":
            raise ValueError("url sources can only be converted to pdf")
        if normalized_engine == "pandoc":
            raise ValueError(
                "url sources can only be rendered with the browser engine; "
                "use render_engine='auto' or 'browser'"
            )
        # A URL always renders as a web page
        source_format = source_format or "html"
    elif not content and not source_path:
        raise ValueError(
            "Provide 'content' (inline source), 'source_path' (project file) or 'url'"
        )
    elif content and source_path:
        raise ValueError("Use 'content' or 'source_path', not both")

    resolved_source_format = _resolve_source_format(
        source_format=source_format, source_path=source_path
    )

    if (resolved_source_format, normalized_target) not in SUPPORTED_CONVERSIONS:
        supported = ", ".join(f"{src} -> {dst}" for src, dst in SUPPORTED_CONVERSIONS)
        raise ValueError(
            f"Conversion '{resolved_source_format} -> {normalized_target}' is not supported. "
            f"Supported conversions: {supported}"
        )

    if url and resolved_source_format != "html":
        raise ValueError("url sources are html only: do not force source_format='markdown'")

    if normalized_engine == "browser" and not (
        resolved_source_format == "html" and normalized_target == "pdf"
    ):
        raise ValueError(
            "render_engine 'browser' only supports html -> pdf. "
            "Use 'auto' or 'pandoc' for the other conversions."
        )

    # Read the source content from the project file when requested
    source_abs_path = None
    if url:
        source_content = None
        source_label = f"`{url}`"
    elif source_path:
        source_abs_path = _resolve_project_path(settings=settings, file_path=source_path)
        if not source_abs_path:
            raise ValueError(
                f"source_path '{source_path}' must belong to {settings.abs_project_path}"
            )
        if not os.path.isfile(source_abs_path):
            raise ValueError(f"source file not found: {source_path}")
        with open(source_abs_path, "r", encoding="utf-8") as file:
            source_content = file.read()
        source_label = f"`{source_path}`"
    else:
        source_content = content
        source_label = "inline content"

    # Resolve the output path inside the project
    rel_output_path = _build_output_path(
        source_path=source_path,
        output_path=output_path,
        target_format=normalized_target,
    )
    abs_output_path = _resolve_project_path(settings=settings, file_path=rel_output_path)
    if not abs_output_path:
        raise ValueError(
            f"output_path '{rel_output_path}' must belong to {settings.abs_project_path}"
        )

    output_folder = os.path.dirname(abs_output_path) or settings.abs_project_path
    inline_markdown = None
    engine_used = None
    notes: List[str] = []
    temp_path = None

    try:
        os.makedirs(output_folder, exist_ok=True)

        if normalized_target == "markdown":
            inline_markdown = _html_to_markdown(html=source_content)
            with open(abs_output_path, "w", encoding="utf-8") as file:
                file.write(inline_markdown)
        else:
            # HTML to PDF is printed by the browser unless excluded or unavailable
            use_browser = (
                normalized_target == "pdf"
                and resolved_source_format == "html"
                and normalized_engine != "pandoc"
                and (bool(url) or _browser_renderer_available())
            )

            if use_browser:
                target = url
                if not target and source_abs_path:
                    target = source_abs_path
                if not target:
                    # Inline content: write it next to the output so relative
                    # assets keep resolving against the project folder
                    handle, temp_path = tempfile.mkstemp(
                        prefix=".codx-doc-", suffix=".html", dir=output_folder
                    )
                    with os.fdopen(handle, "w", encoding="utf-8") as file:
                        file.write(source_content or "")
                    target = temp_path

                try:
                    engine_used = _print_pdf_with_browser(
                        target=target,
                        output_file=abs_output_path,
                        slides=slides,
                        page_size=page_size,
                        landscape=landscape,
                        print_background=print_background,
                        margin=margin,
                        media=media,
                        wait_for_selector=wait_for_selector,
                        wait_timeout_ms=wait_timeout_ms or 0,
                        script=script,
                        page_break_selector=page_break_selector,
                    )
                except _BrowserRendererUnavailable as ex:
                    if normalized_engine == "browser":
                        raise RuntimeError(
                            "the browser renderer is not available ("
                            + str(ex)
                            + "); use render_engine='pandoc' or install playwright "
                            "('pip install playwright' and 'playwright install chromium')"
                        ) from ex
                    note = f"browser renderer unavailable ({ex}); used pandoc"
                    logger.warning("doc_converter: %s", note)
                    notes.append(note)

            if not engine_used and url:
                raise RuntimeError(
                    "url sources can only be rendered with the browser engine; "
                    "install playwright ('pip install playwright' and "
                    "'playwright install chromium')"
                )

            if not engine_used:
                pandoc_version = _ensure_pandoc()
                logger.info("Converting document with pandoc %s", pandoc_version)
                resource_path = _resource_path(
                    settings=settings, source_abs_path=source_abs_path
                )
                if normalized_target == "pdf":
                    engine_used = _convert_to_pdf(
                        content=source_content,
                        source_format=resolved_source_format,
                        output_file=abs_output_path,
                        resource_path=resource_path,
                        pdf_engine=pdf_engine,
                        title=title,
                    )
                else:
                    _convert_to_docx(
                        content=source_content,
                        source_format=resolved_source_format,
                        output_file=abs_output_path,
                        resource_path=resource_path,
                        title=title,
                    )

        if not os.path.isfile(abs_output_path):
            raise RuntimeError(f"the converter did not produce the output file: {rel_output_path}")

    except Exception as ex:
        logger.exception("doc_converter failed: %s", ex)
        message = (
            f"{resolved_source_format} -> {normalized_target} conversion of "
            f"{source_label} failed: {ex}"
        )
        return ToolResponse(
            user_response=f"Conversion failed: {message}",
            llm_response=f"doc_converter error: {message}",
        )
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                logger.debug("could not remove temporary file %s", temp_path)

    file_size = os.path.getsize(abs_output_path)
    rel_output = _to_relative_path(settings=settings, abs_path=abs_output_path)

    user_response = (
        f"✓ Converted {source_label} to {normalized_target}: `{rel_output}` ({file_size} bytes)"
        + (f" using {engine_used}" if engine_used else "")
    )
    if notes:
        user_response += "\n" + "\n".join(f"> {note}" for note in notes)

    llm_lines = [
        f"> {resolved_source_format} -> {normalized_target} conversion completed in "
        f"'{settings.project_name}'",
        f"- Output: `{rel_output}` ({file_size} bytes)",
    ]
    if engine_used:
        llm_lines.append(f"- Renderer: {engine_used}")
    if notes:
        llm_lines.append("- Notes: " + "; ".join(notes))
    if inline_markdown is not None:
        llm_lines.append(f"- Converted markdown:\n\n{_cap_markdown(inline_markdown)}")

    llm_response = "\n".join(llm_lines)
    logger.info("doc_converter done: %s -> %s (%d bytes)", source_label, rel_output, file_size)

    return ToolResponse(user_response=user_response, llm_response=llm_response)


def markdown_to_pdf(
    source_path: Optional[str] = None,
    content: Optional[str] = None,
    output_path: Optional[str] = None,
    title: Optional[str] = None,
    pdf_engine: str = DEFAULT_PDF_ENGINE,
    **kwargs
) -> ToolResponse:
    """
    Convert markdown into a PDF document.

    Args:
        source_path: Project markdown file to convert.
        content: Inline markdown content to convert.
        output_path: Project path for the PDF. Defaults to the source name.
        title: Optional document title metadata.
        pdf_engine: Preferred PDF engine, default 'xelatex'.

    Returns:
        ToolResponse: Confirmation with the generated PDF path.

    Example:
        >>> markdown_to_pdf(source_path="docs/guide.md", output_path="docs/guide.pdf")
    """
    return doc_converter(
        target_format="pdf",
        source_path=source_path,
        content=content,
        output_path=output_path,
        source_format="markdown",
        title=title,
        pdf_engine=pdf_engine,
        **kwargs
    )


def markdown_to_docx(
    source_path: Optional[str] = None,
    content: Optional[str] = None,
    output_path: Optional[str] = None,
    title: Optional[str] = None,
    **kwargs
) -> ToolResponse:
    """
    Convert markdown into a DOCX document.

    Args:
        source_path: Project markdown file to convert.
        content: Inline markdown content to convert.
        output_path: Project path for the DOCX. Defaults to the source name.
        title: Optional document title metadata.

    Returns:
        ToolResponse: Confirmation with the generated DOCX path.

    Example:
        >>> markdown_to_docx(source_path="docs/guide.md", output_path="docs/guide.docx")
    """
    return doc_converter(
        target_format="docx",
        source_path=source_path,
        content=content,
        output_path=output_path,
        source_format="markdown",
        title=title,
        **kwargs
    )


def html_to_markdown(
    source_path: Optional[str] = None,
    content: Optional[str] = None,
    output_path: Optional[str] = None,
    **kwargs
) -> ToolResponse:
    """
    Convert HTML into markdown.

    Args:
        source_path: Project HTML file to convert.
        content: Inline HTML content to convert.
        output_path: Project path for the markdown. Defaults to the source name.

    Returns:
        ToolResponse: Confirmation with the output path and the markdown inline.

    Example:
        >>> html_to_markdown(source_path="docs/page.html", output_path="docs/page.md")
    """
    return doc_converter(
        target_format="markdown",
        source_path=source_path,
        content=content,
        output_path=output_path,
        source_format="html",
        **kwargs
    )


def html_to_pdf(
    source_path: Optional[str] = None,
    content: Optional[str] = None,
    output_path: Optional[str] = None,
    title: Optional[str] = None,
    pdf_engine: str = DEFAULT_PDF_ENGINE,
    **kwargs
) -> ToolResponse:
    """
    Convert HTML into a PDF document.

    HTML is printed by a headless browser by default (``render_engine='auto'``),
    so JavaScript, modern CSS and background graphics are preserved. The
    Chromium build is installed automatically the first time it is required.
    Pass ``slides=True`` (or use :func:`html_slides_to_pdf`) for slide decks.

    Args:
        source_path: Project HTML file to convert.
        content: Inline HTML content to convert.
        output_path: Project path for the PDF. Defaults to the source name.
        title: Optional document title metadata.
        pdf_engine: Preferred pandoc PDF engine (used when pandoc renders).
        **kwargs: Browser rendering options (``render_engine``, ``url``,
            ``slides``, ``page_size``, ``landscape``, ``media``,
            ``print_background``, ``margin``, ``page_break_selector``,
            ``wait_for_selector``, ``wait_timeout_ms``, ``script``,
            ``auto_install``).

    Returns:
        ToolResponse: Confirmation with the generated PDF path.

    Example:
        >>> html_to_pdf(source_path="docs/page.html", output_path="docs/page.pdf")
        >>> html_to_pdf(source_path="docs/page.html", page_size="A4")
    """
    return doc_converter(
        target_format="pdf",
        source_path=source_path,
        content=content,
        output_path=output_path,
        source_format="html",
        title=title,
        pdf_engine=pdf_engine,
        **kwargs
    )


def html_slides_to_pdf(
    source_path: Optional[str] = None,
    content: Optional[str] = None,
    url: Optional[str] = None,
    output_path: Optional[str] = None,
    slides: bool = True,
    **kwargs
) -> ToolResponse:
    """
    Convert rich HTML slides into a PDF with the browser renderer.

    Applies the slide preset (1920x1080 landscape pages, screen media,
    background graphics, zero margins) and prints with headless Chromium so
    Reveal.js, Marp and custom CSS decks keep their layout, fonts and colors.
    Chromium is installed automatically when it is missing.

    Args:
        source_path: Project HTML deck to convert.
        content: Inline HTML deck to convert.
        url: Deck URL served locally (``http://localhost:...``) or a file URI.
        output_path: Project path for the PDF. Defaults to the source name.
        slides: Slide preset flag (True by default; override individual page
            options through ``**kwargs``).
        **kwargs: Any other :func:`doc_converter` option, e.g.
            ``page_break_selector``, ``wait_for_selector``, ``script``,
            ``media``, ``page_size``, ``landscape``, ``print_background``,
            ``margin``, ``wait_timeout_ms``, ``auto_install``.

    Returns:
        ToolResponse: Confirmation with the generated PDF path and renderer.

    Example:
        >>> html_slides_to_pdf(
        ...     source_path="slides/deck.html",
        ...     page_break_selector=".reveal .slides > section",
        ...     wait_for_selector=".reveal .slides section.present",
        ... )
    """
    return doc_converter(
        target_format="pdf",
        source_path=source_path,
        content=content,
        url=url,
        output_path=output_path,
        source_format="html",
        render_engine=kwargs.pop("render_engine", DEFAULT_RENDER_ENGINE),
        slides=slides,
        **kwargs
    )

# Made with ❤️ by codx-junior