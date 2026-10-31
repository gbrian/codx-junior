---
title: "codx-junior - slides to pdf pipeline"
subtitle: "Conversion test / slide 01"
date: "render test"
---

# One file. Zero deps. Pixel-exact PDF.

Rich CSS, inline SVG charts and custom fonts are printed by a headless
Chromium: vectors stay vectors, gradients stay gradients.

```text
doc_converter(target_format="pdf", slides=True)
```

| Canvas | Engine | Assets |
|:-------|:-------|:-------|
| 1920 x 1080 | Headless Chromium | 0 external |

## Deck render time

Milliseconds per slide, by build size (`render_ms`).

| Deck size (slides) | 2   | 4   | 6   | 8   | 10  | 12  | 14  | 16  |
|:-------------------|----:|----:|----:|----:|----:|----:|----:|----:|
| render_ms          | 196 | 174 | 180 | 148 | 156 | 120 | 130 | 58  |

Lowest recorded value: **58 ms** at 16 slides.

## Key figures

| 3.4x | 0 | 1 |
|:-----|:--|:--|
| Faster than pandoc | CDN requests | HTML file |

---

Export: `Cmd/Ctrl + P` - Landscape - Background graphics ON   |   Page 01 / 01
