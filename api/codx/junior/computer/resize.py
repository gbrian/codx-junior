"""
Desktop resolution helpers for computer sessions.

The viewer knows its own size, the machine knows which framebuffer sizes it can
actually use.  These pure helpers translate one into the other so the API, the
backends and the tests share the same rules:

* sizes are clamped to what VNC/X11/Docker reliably support (640x480 ..
  7680x4320) so a wildly wrong request degrades instead of breaking the desktop;
* both dimensions are forced to even numbers (RFB framebuffers are 32-bpp and
  odd sizes are rejected by several VNC servers);
* ``mode="client"`` keeps the viewer aspect ratio, so the desktop fills the panel
  instead of being letterboxed by the live view.

Resizing is best effort by nature: a VNC server without ``ExtendedDesktopSize``
or an X server without RandR simply cannot change the framebuffer of a running
session.  In that case the callers report ``supported=False`` (and the viewer
keeps scaling the image); they never invent a size the machine is not using.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import re
from typing import Any, Optional, Tuple

#: Smallest/largest desktop accepted by the API (matches ``BrowserSession``).
MIN_WIDTH = 640
MIN_HEIGHT = 480
MAX_WIDTH = 7680
MAX_HEIGHT = 4320

#: ``1920x1080``, ``1920X1080``, ``1920:1080`` and ``1920 x 1080`` are accepted.
RESOLUTION_PATTERN = re.compile(r"^\s*(\d{3,4})\s*[xX×:]\s*(\d{3,4})\s*$")


def even(value: Any) -> int:
    """
    Round a pixel dimension down to an even number of at least 2 pixels.

    Args:
        value: Any numeric value coming from JSON or a form field.

    Returns:
        int: Even dimension (invalid input becomes 2).
    """
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return 2
    number = max(2, number)
    return number - (number % 2)


def parse_resolution(value: Any) -> Optional[Tuple[int, int]]:
    """
    Parse a ``WIDTHxHEIGHT`` string (or a 2-item sequence) into a tuple.

    Args:
        value: ``"1920x1080"``, ``" 1366 X 768 "``, ``[800, 600]``...

    Returns:
        Optional[Tuple[int, int]]: Parsed size, or None when it cannot be read.
    """
    if isinstance(value, (tuple, list)) and len(value) == 2:
        try:
            return int(value[0]), int(value[1])
        except (TypeError, ValueError):
            return None
    match = RESOLUTION_PATTERN.match(str(value or ""))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _clamp(value: int, low: int, high: int) -> int:
    """Clamp *value* into ``[low, high]``."""
    return max(low, min(high, int(value)))


def fit_resolution(
    width: Any,
    height: Any,
    max_width: int = MAX_WIDTH,
    max_height: int = MAX_HEIGHT,
    min_width: int = MIN_WIDTH,
    min_height: int = MIN_HEIGHT,
) -> Tuple[int, int]:
    """
    Clamp a requested resolution into the supported range keeping the aspect.

    The width is clamped first and the height derived from it, so a viewer with
    a very wide or very tall panel still gets a usable desktop instead of an
    error.

    Args:
        width: Requested width in pixels.
        height: Requested height in pixels.
        max_width/max_height/min_width/min_height: Accepted bounds.

    Returns:
        Tuple[int, int]: Even, in-range resolution.

    Raises:
        ValueError: When the requested size is not a positive number.
    """
    try:
        requested_width = int(round(float(width)))
        requested_height = int(round(float(height)))
    except (TypeError, ValueError) as ex:
        raise ValueError("width and height must be numbers") from ex
    if requested_width <= 0 or requested_height <= 0:
        raise ValueError("width and height must be greater than zero")

    ratio = requested_width / float(requested_height)
    target_width = _clamp(requested_width, min_width, max_width)
    target_height = int(round(target_width / ratio))
    if target_height < min_height:
        target_height = min_height
        target_width = int(round(target_height * ratio))
    if target_height > max_height:
        target_height = max_height
        target_width = int(round(target_height * ratio))
    return (
        even(_clamp(target_width, min_width, max_width)),
        even(_clamp(target_height, min_height, max_height)),
    )


def resolution_from_client(
    client_width: Any,
    client_height: Any,
    scale: float = 1.0,
    max_width: int = MAX_WIDTH,
    max_height: int = MAX_HEIGHT,
) -> Tuple[int, int]:
    """
    Return the desktop resolution that fills a viewer of the given CSS size.

    Args:
        client_width: Width of the viewer element in CSS pixels.
        client_height: Height of the viewer element in CSS pixels.
        scale: Device pixel ratio (1 = CSS pixels, 2 = retina).
        max_width/max_height: Upper bounds (the caller may lower them).

    Returns:
        Tuple[int, int]: Resolution for the machine.

    Raises:
        ValueError: When the viewer size is not positive.
    """
    try:
        factor = float(scale or 1.0)
    except (TypeError, ValueError):
        factor = 1.0
    factor = max(0.5, min(2.0, factor))
    return fit_resolution(
        float(client_width) * factor,
        float(client_height) * factor,
        max_width=max_width,
        max_height=max_height,
    )


def xrandr_resize_script(width: Any, height: Any) -> str:
    """
    Build the POSIX shell script that resizes an X11 desktop with ``xrandr``.

    The script is sent to the in-container agent as ``run_command``: it picks the
    first connected output, tries the requested mode, creates it with ``cvt`` /
    ``gtf`` when the driver does not know it, and finally falls back to resizing
    the framebuffer (``--fb``).  Only numbers are interpolated, never user text.

    Args:
        width: Target width in pixels.
        height: Target height in pixels.

    Returns:
        str: Script that prints ``applied:...`` on success and a short reason
        (``no-output``, ``no-modeline``, ``unsupported``) on failure.
    """
    target_width = even(width)
    target_height = even(height)
    mode = f"{target_width}x{target_height}"
    return f"""set -u
W={target_width}
H={target_height}
MODE={mode}
out=$(xrandr --query 2>/dev/null | awk '/ connected/ {{print $1; exit}}')
if [ -z "$out" ]; then echo "no-output"; exit 3; fi
if xrandr --output "$out" --mode "$MODE" >/dev/null 2>&1; then echo "applied:$out:$MODE"; exit 0; fi
line=""
if command -v cvt >/dev/null 2>&1; then
  line=$(cvt "$W" "$H" 60 2>/dev/null | sed -n 's/^ *Modeline "[^"]*" *//p' | head -n 1)
fi
if [ -z "$line" ] && command -v gtf >/dev/null 2>&1; then
  line=$(gtf "$W" "$H" 60 2>/dev/null | sed -n 's/^ *Modeline "[^"]*" *//p' | head -n 1)
fi
if [ -z "$line" ]; then echo "no-modeline"; exit 4; fi
name="codx_$MODE"
xrandr --newmode "$name" $line >/dev/null 2>&1 || true
xrandr --addmode "$out" "$name" >/dev/null 2>&1 || true
if xrandr --output "$out" --mode "$name" >/dev/null 2>&1; then echo "applied:$out:$name"; exit 0; fi
if xrandr --fb "$MODE" >/dev/null 2>&1; then echo "applied:fb:$MODE"; exit 0; fi
echo "unsupported"
exit 5"""