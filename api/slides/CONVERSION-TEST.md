# Slides → PDF conversion test

**Date:** 2025 conversion test run
**Source:** [`slides/test-slide.html`](./test-slide.html) — single rich slide, 1920×1080, dark theme, inline SVG chart, KPI cards, CSS gradients.
**Target:** `slides/test-slide.pdf` (1920×1080 landscape, one page per `section.slide`).

## Result: ❌ blocked by missing render engines

`doc_converter(target_format="pdf", source_path="slides/test-slide.html", slides=True, render_engine="browser", page_break_selector="section.slide")`

| Attempt | Configuration | Outcome |
|---|---|---|
| 1 | `render_engine=browser` + `source_path` | Falls through to pandoc; all engines missing |
| 2 | inline HTML probe, `render_engine=browser` | Same — pandoc fallback only |
| 3 | `render_engine=browser` + `url=file:///…/slides/test-slide.html` | **`the browser renderer is not available (the playwright package is not installed …)`** |
| 4 | `render_engine=pandoc`, `pdf_engine=weasyprint` | `weasyprint not found` |
| 5 | `render_engine=pandoc`, `pdf_engine=typst` | `pdf-engine must be one of pagedjs-cli, wkhtmltopdf, weasyprint, prince, pdflatex, lualatex, xelatex, latexmk, tectonic, pdfroff, context` |

### Root cause

Neither of the two HTML→PDF paths is usable on this host:

1. **Browser renderer (preferred, keeps CSS/SVG/fonts):** requires the `playwright` Python package plus the Chromium binary. Not installed.
2. **Pandoc path (fallback):** requires one of `xelatex`, `lualatex`, `pdflatex`, `weasyprint`, `wkhtmltopdf`, `typst`. None installed. (Pandoc additionally reports `rsvg-convert` missing, needed to rasterize SVG diagrams.)

Consequence: `doc_converter` cannot produce **any** PDF on this host, from HTML *or* markdown, because markdown→PDF uses the same pandoc/LaTeX chain. DOCX output is unaffected (pandoc needs no external engine).

## Fix

Install the browser renderer (recommended — only this path preserves the slide design):

```bash
pip install playwright
playwright install chromium        # add --with-deps on bare Linux hosts
```

Alternative, lower fidelity — a pandoc HTML engine:

```bash
apt-get install -y weasyprint      # or wkhtmltopdf
```

After that, re-run:

```text
doc_converter(
  target_format = "pdf",
  source_path   = "slides/test-slide.html",
  output_path   = "slides/test-slide.pdf",
  render_engine = "browser",
  slides        = True,
  page_size     = "1920x1080",
  page_break_selector = "section.slide",
)
```

## Workaround until then

Open `slides/test-slide.html` in Chrome/Chromium → **Print** → Destination *Save as PDF* →
Layout *Landscape* → Paper *1920×1080 px* (or A4/Letter landscape, scaled to fit) →
**Background graphics: ON** → *Margins: None*. The slide carries no external assets, so
the result is self-contained.
