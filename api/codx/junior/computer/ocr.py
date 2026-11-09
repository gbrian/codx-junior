"""
OCR for desktop screenshots.

A graphical desktop has no DOM: the only structured view of the screen the
model can read is the text rendered on it.  Tesseract is already installed in
the API image (``tesseract-ocr``), so this module turns a PNG screenshot into
plain text plus word bounding boxes.  The boxes let the AI click by text
(``click_text``) without guessing pixel coordinates.

The implementation calls the ``tesseract`` binary directly instead of importing
``pytesseract``: it avoids a Python dependency at runtime and gives us the TSV
output with per-word geometry.
"""

from __future__ import annotations

import csv
import io
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MIN_CONFIDENCE = 25.0
#: Keep the amount of OCR text returned to the model bounded.
MAX_OCR_CHARS = 12000


def tesseract_available() -> bool:
    """Return True when the tesseract binary can be executed."""
    return bool(shutil.which("tesseract"))


def _parse_tsv(tsv: str) -> List[Dict[str, Any]]:
    """Parse tesseract TSV output into word entries with boxes."""
    words: List[Dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(tsv), delimiter="\t")
    for row in reader:
        if row.get("level") != "5":
            continue
        text = (row.get("text") or "").strip()
        if not text:
            continue
        try:
            confidence = float(row.get("conf") or -1)
            left = int(row.get("left") or 0)
            top = int(row.get("top") or 0)
            width = int(row.get("width") or 0)
            height = int(row.get("height") or 0)
        except ValueError:
            continue
        if confidence < 0:
            continue
        words.append({
            "text": text,
            "confidence": round(confidence, 1),
            "x": left,
            "y": top,
            "width": width,
            "height": height,
            "cx": left + width // 2,
            "cy": top + height // 2,
            "line": f"{row.get('block_num')}:{row.get('par_num')}:{row.get('line_num')}",
        })
    return words


def _group_lines(words: List[Dict[str, Any]]) -> str:
    """Rebuild readable lines from word boxes (ordered by line then x)."""
    lines: Dict[str, List[Dict[str, Any]]] = {}
    order: List[str] = []
    for word in words:
        key = word["line"]
        if key not in lines:
            lines[key] = []
            order.append(key)
        lines[key].append(word)
    output = []
    for key in order:
        line = sorted(lines[key], key=lambda item: item["x"])
        output.append(" ".join(item["text"] for item in line))
    return "\n".join(output)


def _ocr_variant(path: str, psm: int) -> str:
    """Run tesseract with one page-segmentation mode."""
    result = subprocess.run(
        ["tesseract", path, "stdout", "--psm", str(psm), "tsv"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "tesseract failed").strip()[:500])
    return result.stdout or ""


def extract_text(
    image: bytes,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    lang: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Read text from PNG/JPEG bytes.

    Args:
        image: Encoded image bytes.
        min_confidence: Drop words below this tesseract confidence (0-100).
        lang: Optional tesseract language (default: ``CODX_COMPUTER_OCR_LANG``
            or ``eng``).

    Returns:
        ``{"text": ..., "words": [...], "available": bool, "error": ...}``.
        OCR failures never raise: a screenshot without text is still useful.
    """
    if not tesseract_available():
        return {
            "text": "",
            "words": [],
            "available": False,
            "error": "tesseract is not installed in the API image",
        }
    if not image:
        return {"text": "", "words": [], "available": True}
    language = (lang or os.environ.get("CODX_COMPUTER_OCR_LANG") or "eng").strip()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
            handle.write(image)
            tmp_path = handle.name
        best_words: List[Dict[str, Any]] = []
        # PSM 6 (uniform block) works for terminals and application windows;
        # PSM 11 (sparse text) catches menus and scattered desktop labels.
        for psm in (6, 11):
            try:
                tsv = _ocr_variant(tmp_path, psm)
            except Exception as ex:
                logger.debug("tesseract psm=%s failed: %s", psm, ex)
                continue
            words = _parse_tsv(tsv)
            if len(words) > len(best_words):
                best_words = words
        words = [word for word in best_words if word["confidence"] >= float(min_confidence)]
        text = _group_lines(words)
        if len(text) > MAX_OCR_CHARS:
            text = text[:MAX_OCR_CHARS] + "\n… (OCR truncated)"
        return {"text": text, "words": words, "available": True, "lang": language}
    except Exception as ex:
        logger.warning("OCR failed: %s", ex)
        return {"text": "", "words": [], "available": True, "error": str(ex)}
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def find_text(words: List[Dict[str, Any]], text: str, index: int = 0) -> Optional[Dict[str, Any]]:
    """
    Find the *index*-th OCR word matching *text* (case-insensitive).

    A multi-word query matches the first word of a consecutive line sequence and
    returns the centre of the union box.
    """
    query = [part for part in str(text or "").strip().lower().split() if part]
    if not query:
        return None
    matches: List[Dict[str, Any]] = []
    for position, word in enumerate(words):
        if word["text"].lower() != query[0]:
            continue
        if len(query) == 1:
            matches.append(word)
            continue
        # Look ahead on the same line for the remaining words.
        line_words = [word]
        cursor = position + 1
        while cursor < len(words) and words[cursor]["line"] == word["line"] and len(line_words) < len(query):
            line_words.append(words[cursor])
            cursor += 1
        if [item["text"].lower() for item in line_words] == query:
            left = min(item["x"] for item in line_words)
            top = min(item["y"] for item in line_words)
            right = max(item["x"] + item["width"] for item in line_words)
            bottom = max(item["y"] + item["height"] for item in line_words)
            matches.append({
                "text": " ".join(item["text"] for item in line_words),
                "x": left,
                "y": top,
                "width": right - left,
                "height": bottom - top,
                "cx": (left + right) // 2,
                "cy": (top + bottom) // 2,
                "confidence": min(item["confidence"] for item in line_words),
                "line": word["line"],
            })
    index = max(0, int(index or 0))
    return matches[index] if index < len(matches) else None
