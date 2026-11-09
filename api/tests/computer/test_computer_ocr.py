"""OCR + text matching tests (skipped when tesseract is unavailable)."""

import io
import shutil

import pytest

from codx.junior.computer import ocr


pytestmark = pytest.mark.skipif(not shutil.which("tesseract"), reason="tesseract not installed")


def _image(text):
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (900, 220), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 48)
    except Exception:
        font = ImageFont.load_default(size=48)
    draw.text((30, 60), text, fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_extract_text_and_find_text():
    result = ocr.extract_text(_image("Hello Computer World"))
    assert result["available"] is True
    assert "Hello" in result["text"]
    assert result["words"]

    match = ocr.find_text(result["words"], "Computer")
    assert match is not None
    assert match["cx"] > 0 and match["cy"] > 0

    # Multi-word query uses the union of the words on one line.
    phrase = ocr.find_text(result["words"], "Hello Computer")
    assert phrase is not None
    assert phrase["width"] > match["width"]


def test_find_text_is_case_insensitive_and_returns_none_for_missing():
    result = ocr.extract_text(_image("Save Changes"))
    assert ocr.find_text(result["words"], "save") is not None
    assert ocr.find_text(result["words"], "delete everything") is None


def test_extract_text_handles_invalid_image_without_raising():
    result = ocr.extract_text(b"not an image")
    assert result["available"] is True
    # Either an empty result or an error field: OCR must never break a screenshot.
    assert result.get("text", "") == "" or result.get("error")
