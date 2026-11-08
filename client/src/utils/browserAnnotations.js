/**
 * Browser annotation model + renderer.
 *
 * An annotation is stored in **normalized coordinates** (0..1) relative to the
 * live browser view.  That is what lets the same drawing be rendered over the
 * live VNC iframe at any size and later composited on top of a full-resolution
 * page screenshot before it is sent to the AI.
 *
 * The module is intentionally framework-free: the board component owns the
 * pointer/undo state, while every path, arrow, note and image is drawn by the
 * functions below.  The board and the exporter therefore share one renderer.
 */

/** Vertical reference used to scale stroke widths / font sizes. */
export const ANNOTATION_BASE_HEIGHT = 720

/** Drawing tools exposed by the board toolbar. */
export const ANNOTATION_TOOLS = [
  { id: 'select', icon: 'fa-arrow-pointer', label: 'Select and move' },
  { id: 'pen', icon: 'fa-pen', label: 'Pen' },
  { id: 'marker', icon: 'fa-highlighter', label: 'Highlighter' },
  { id: 'arrow', icon: 'fa-arrow-right', label: 'Arrow' },
  { id: 'rect', icon: 'fa-square', label: 'Rectangle' },
  { id: 'ellipse', icon: 'fa-circle', label: 'Ellipse' },
  { id: 'note', icon: 'fa-note-sticky', label: 'Sticky note' },
  { id: 'text', icon: 'fa-font', label: 'Text' },
  { id: 'image', icon: 'fa-image', label: 'Insert image' },
  { id: 'eraser', icon: 'fa-eraser', label: 'Eraser' }
]

/** Colors that stay legible on both light and dark pages/screenshots. */
export const ANNOTATION_COLORS = [
  { value: '#ef4444', label: 'Red' },
  { value: '#f59e0b', label: 'Amber' },
  { value: '#22c55e', label: 'Green' },
  { value: '#3b82f6', label: 'Blue' },
  { value: '#a855f7', label: 'Purple' },
  { value: '#ffffff', label: 'White' },
  { value: '#111827', label: 'Black' }
]

const COLOR_NAMES = ANNOTATION_COLORS.reduce((names, color) => {
  names[color.value] = color.label.toLowerCase()
  return names
}, {})

/** Font stack used for notes and text annotations. */
const TEXT_FONT = 'Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'

let annotationCounter = 0

/**
 * Build a collision-resistant id. `crypto.randomUUID` is available in secure
 * contexts (the app is normally served over HTTPS or localhost); the fallback
 * keeps the board working on plain-http LAN connections.
 */
export function createAnnotationId() {
  try {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return `ann_${crypto.randomUUID()}`
    }
  } catch (e) {
    // fall through to the counter-based id
  }
  annotationCounter += 1
  return `ann_${Date.now().toString(36)}_${annotationCounter}`
}

/** Clamp a number to the normalized 0..1 range. */
export function clamp01(value) {
  return Math.min(1, Math.max(0, Number(value) || 0))
}

/** Convert client coordinates to normalized board coordinates. */
export function pointFromEvent(event, rect) {
  const width = rect?.width || 1
  const height = rect?.height || 1
  return {
    x: clamp01((event.clientX - rect.left) / width),
    y: clamp01((event.clientY - rect.top) / height)
  }
}

function ensurePoint(point) {
  return {
    x: clamp01(point?.x),
    y: clamp01(point?.y)
  }
}

/**
 * Create a new annotation object.
 *
 * @param {Object} options
 * @param {string} options.tool - One of ANNOTATION_TOOLS ids (except eraser).
 * @param {Object} [options.point] - Initial normalized point.
 * @param {string} [options.color] - Stroke color.
 * @param {number} [options.width] - Stroke width at ANNOTATION_BASE_HEIGHT.
 * @returns {Object} Annotation.
 */
export function createAnnotation({ tool = 'pen', point = { x: 0, y: 0 }, color = '#ef4444', width = 4, ...rest } = {}) {
  const start = ensurePoint(point)
  const annotation = {
    id: createAnnotationId(),
    tool,
    color,
    width: Math.max(1, Number(width) || 4),
    author: rest.author || null,
    createdAt: Date.now(),
    ...rest
  }

  if (tool === 'pen' || tool === 'marker' || tool === 'arrow') {
    annotation.points = [start, { ...start }]
  } else {
    annotation.x = start.x
    annotation.y = start.y
  }

  if (tool === 'rect' || tool === 'ellipse' || tool === 'image') {
    annotation.w = rest.w || 0
    annotation.h = rest.h || 0
  }

  if (tool === 'text' || tool === 'note') {
    annotation.text = rest.text || ''
    annotation.fontSize = rest.fontSize || (tool === 'note' ? 16 : 18)
    if (tool === 'note') annotation.w = rest.w || 0.24
  }

  return annotation
}

/** Human readable name of a color, used in the AI instructions. */
export function annotationColorName(color) {
  return COLOR_NAMES[String(color || '').toLowerCase()] || String(color || 'colored')
}

/**
 * Bounding box of an annotation in normalized coordinates.
 * Returns `{ x, y, w, h }` with positive width/height.
 */
export function annotationBounds(annotation) {
  if (!annotation) return { x: 0, y: 0, w: 0, h: 0 }
  if (annotation.tool === 'pen' || annotation.tool === 'marker' || annotation.tool === 'arrow') {
    const points = annotation.points || []
    if (!points.length) return { x: 0, y: 0, w: 0, h: 0 }
    const xs = points.map(p => p.x)
    const ys = points.map(p => p.y)
    const x = Math.min(...xs)
    const y = Math.min(...ys)
    return { x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y }
  }
  if (annotation.tool === 'text') {
    // The exact text box depends on the renderer; this approximation is only
    // used for selection / hit testing and is deliberately generous.
    const width = Math.max(0.04, Math.min(0.9, (annotation.text || '').length * 0.009))
    return { x: annotation.x, y: annotation.y, w: width, h: 0.045 }
  }
  if (annotation.tool === 'note') {
    const width = annotation.w || 0.24
    return { x: annotation.x, y: annotation.y, w: width, h: annotation.h || 0.14 }
  }
  const x = annotation.x || 0
  const y = annotation.y || 0
  const w = annotation.w || 0
  const h = annotation.h || 0
  return {
    x: Math.min(x, x + w),
    y: Math.min(y, y + h),
    w: Math.abs(w),
    h: Math.abs(h)
  }
}

/** True when a normalized point is inside the annotation bounds. */
export function annotationContains(annotation, point, tolerance = 0.012) {
  if (!annotation || !point) return false
  if (annotation.tool === 'pen' || annotation.tool === 'marker') {
    const points = annotation.points || []
    return points.some(item => Math.abs(item.x - point.x) <= tolerance && Math.abs(item.y - point.y) <= tolerance)
  }
  if (annotation.tool === 'arrow') {
    const [start, end] = annotation.points || []
    if (!start || !end) return false
    return distanceToSegment(point, start, end) <= tolerance * 1.5
  }
  const bounds = annotationBounds(annotation)
  return point.x >= bounds.x - tolerance &&
    point.x <= bounds.x + bounds.w + tolerance &&
    point.y >= bounds.y - tolerance &&
    point.y <= bounds.y + bounds.h + tolerance
}

function distanceToSegment(point, start, end) {
  const dx = end.x - start.x
  const dy = end.y - start.y
  if (dx === 0 && dy === 0) return Math.hypot(point.x - start.x, point.y - start.y)
  const t = Math.max(0, Math.min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / (dx * dx + dy * dy)))
  return Math.hypot(point.x - (start.x + t * dx), point.y - (start.y + t * dy))
}

/**
 * Return a translated copy of an annotation (used by the select tool).
 * Freehand points, arrows and shapes move as a whole.
 */
export function translateAnnotation(annotation, dx, dy) {
  const next = { ...annotation }
  if (annotation.points) {
    next.points = annotation.points.map(point => ({
      x: clamp01(point.x + dx),
      y: clamp01(point.y + dy)
    }))
  }
  if (annotation.tool !== 'pen' && annotation.tool !== 'marker' && annotation.tool !== 'arrow') {
    next.x = clamp01((annotation.x || 0) + dx)
    next.y = clamp01((annotation.y || 0) + dy)
  }
  return next
}

/** Find the topmost annotation under a normalized point. */
export function findAnnotationAt(annotations, point, tolerance = 0.012) {
  for (let index = (annotations || []).length - 1; index >= 0; index -= 1) {
    const annotation = annotations[index]
    if (annotationContains(annotation, point, tolerance)) return annotation
  }
  return null
}

function scaledWidth(annotation, height) {
  const factor = Math.max(0.4, height / ANNOTATION_BASE_HEIGHT)
  const multiplier = annotation.tool === 'marker' ? 4 : 1
  return Math.max(1.5, (annotation.width || 4) * factor * multiplier)
}

function scaledFontSize(annotation, height, baseSize) {
  const factor = Math.max(0.55, height / ANNOTATION_BASE_HEIGHT)
  return Math.max(11, (annotation.fontSize || baseSize || 16) * factor)
}

function roundedRect(ctx, x, y, width, height, radius) {
  const r = Math.max(0, Math.min(radius, width / 2, height / 2))
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + width, y, x + width, y + height, r)
  ctx.arcTo(x + width, y + height, x, y + height, r)
  ctx.arcTo(x, y + height, x, y, r)
  ctx.arcTo(x, y, x + width, y, r)
  ctx.closePath()
}

/** Wrap text to a pixel width, preserving explicit newlines. */
export function wrapText(ctx, text, maxWidth) {
  const source = String(text || '')
  const lines = []
  source.split(/\r?\n/).forEach((paragraph) => {
    const words = paragraph.split(/\s+/).filter(Boolean)
    if (!words.length) {
      lines.push('')
      return
    }
    let line = ''
    words.forEach((word) => {
      const candidate = line ? `${line} ${word}` : word
      if (line && ctx.measureText(candidate).width > maxWidth) {
        lines.push(line)
        line = word
      } else {
        line = candidate
      }
    })
    if (line) lines.push(line)
  })
  return lines.length ? lines : ['']
}

/**
 * Measure a sticky note: the note grows downwards with the text.
 * @returns {{ width: number, height: number, lines: string[], fontSize: number, padding: number, lineHeight: number }}
 */
export function measureNote(ctx, annotation, width, height) {
  const fontSize = scaledFontSize(annotation, height, 16)
  const padding = Math.max(10, fontSize * 0.75)
  const noteWidth = Math.max(130, (annotation.w || 0.24) * width)
  const maxTextWidth = Math.max(40, noteWidth - padding * 2)
  ctx.save()
  ctx.font = `500 ${fontSize}px ${TEXT_FONT}`
  const lines = wrapText(ctx, annotation.text || '', maxTextWidth)
  ctx.restore()
  const lineHeight = fontSize * 1.35
  const noteHeight = Math.max(56, lines.length * lineHeight + padding * 2)
  return { width: noteWidth, height: noteHeight, lines, fontSize, padding, lineHeight }
}

/**
 * Draw one annotation.
 *
 * @param {CanvasRenderingContext2D} ctx
 * @param {Object} annotation
 * @param {number} width - Canvas width in CSS pixels.
 * @param {number} height - Canvas height in CSS pixels.
 * @param {Map<string, HTMLImageElement>} [images] - Loaded image cache.
 */
export function drawAnnotation(ctx, annotation, width, height, images) {
  if (!ctx || !annotation || !width || !height) return
  ctx.save()
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.strokeStyle = annotation.color || '#ef4444'
  ctx.fillStyle = annotation.color || '#ef4444'
  ctx.lineWidth = scaledWidth(annotation, height)
  ctx.globalAlpha = annotation.tool === 'marker' ? 0.32 : 1

  const points = (annotation.points || []).map(point => ({
    x: point.x * width,
    y: point.y * height
  }))

  if (annotation.tool === 'pen' || annotation.tool === 'marker') {
    if (points.length === 1) {
      ctx.beginPath()
      ctx.arc(points[0].x, points[0].y, ctx.lineWidth / 2, 0, Math.PI * 2)
      ctx.fill()
    } else {
      ctx.beginPath()
      ctx.moveTo(points[0].x, points[0].y)
      for (let index = 1; index < points.length; index += 1) {
        const previous = points[index - 1]
        const current = points[index]
        const middleX = (previous.x + current.x) / 2
        const middleY = (previous.y + current.y) / 2
        ctx.quadraticCurveTo(previous.x, previous.y, middleX, middleY)
      }
      const last = points[points.length - 1]
      ctx.lineTo(last.x, last.y)
      ctx.stroke()
    }
    ctx.restore()
    return
  }

  if (annotation.tool === 'arrow') {
    const [start, end] = points
    if (!start || !end) {
      ctx.restore()
      return
    }
    const angle = Math.atan2(end.y - start.y, end.x - start.x)
    const headLength = Math.max(12, ctx.lineWidth * 4.2)
    const spread = Math.PI / 7
    ctx.beginPath()
    ctx.moveTo(start.x, start.y)
    ctx.lineTo(end.x, end.y)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(end.x, end.y)
    ctx.lineTo(
      end.x - headLength * Math.cos(angle - spread),
      end.y - headLength * Math.sin(angle - spread)
    )
    ctx.lineTo(
      end.x - headLength * Math.cos(angle + spread),
      end.y - headLength * Math.sin(angle + spread)
    )
    ctx.closePath()
    ctx.fill()
    ctx.restore()
    return
  }

  if (annotation.tool === 'rect' || annotation.tool === 'ellipse') {
    const x = annotation.x * width
    const y = annotation.y * height
    const w = annotation.w * width
    const h = annotation.h * height
    ctx.globalAlpha = 0.1
    ctx.fillStyle = annotation.color || '#ef4444'
    ctx.beginPath()
    if (annotation.tool === 'rect') {
      ctx.rect(x, y, w, h)
    } else {
      ctx.ellipse(x + w / 2, y + h / 2, Math.abs(w / 2), Math.abs(h / 2), 0, 0, Math.PI * 2)
    }
    ctx.fill()
    ctx.globalAlpha = 1
    ctx.strokeStyle = annotation.color || '#ef4444'
    ctx.stroke()
    ctx.restore()
    return
  }

  if (annotation.tool === 'text') {
    const fontSize = scaledFontSize(annotation, height, 18)
    ctx.font = `600 ${fontSize}px ${TEXT_FONT}`
    ctx.textBaseline = 'top'
    const x = annotation.x * width
    const y = annotation.y * height
    const lines = String(annotation.text || '').split(/\r?\n/)
    // A subtle dark halo keeps light text readable on white pages and dark
    // text readable on dark pages, without painting a full background.
    ctx.lineWidth = Math.max(2, fontSize * 0.16)
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.35)'
    lines.forEach((line, index) => {
      const lineY = y + index * fontSize * 1.3
      ctx.strokeText(line, x, lineY)
      ctx.fillStyle = annotation.color || '#ef4444'
      ctx.fillText(line, x, lineY)
    })
    ctx.restore()
    return
  }

  if (annotation.tool === 'note') {
    const metrics = measureNote(ctx, annotation, width, height)
    const x = annotation.x * width
    const y = annotation.y * height
    const noteWidth = Math.min(metrics.width, width - x - 8)
    const noteHeight = metrics.height

    ctx.save()
    ctx.shadowColor = 'rgba(0, 0, 0, 0.35)'
    ctx.shadowBlur = Math.max(6, height * 0.012)
    ctx.shadowOffsetY = Math.max(3, height * 0.006)
    ctx.fillStyle = '#fef3c7'
    roundedRect(ctx, x, y, noteWidth, noteHeight, 8)
    ctx.fill()
    ctx.restore()

    ctx.strokeStyle = annotation.color || '#f59e0b'
    ctx.lineWidth = Math.max(1.5, ctx.lineWidth * 0.6)
    roundedRect(ctx, x, y, noteWidth, noteHeight, 8)
    ctx.stroke()

    ctx.fillStyle = '#1f2937'
    ctx.font = `500 ${metrics.fontSize}px ${TEXT_FONT}`
    ctx.textBaseline = 'top'
    metrics.lines.forEach((line, index) => {
      ctx.fillText(line, x + metrics.padding, y + metrics.padding + index * metrics.lineHeight)
    })
    ctx.restore()
    return
  }

  if (annotation.tool === 'image') {
    const x = annotation.x * width
    const y = annotation.y * height
    const w = annotation.w * width
    const h = annotation.h * height
    const image = images?.get?.(annotation.id)
    if (image && image.complete !== false) {
      ctx.drawImage(image, x, y, w, h)
    } else {
      ctx.globalAlpha = 0.85
      ctx.fillStyle = 'rgba(15, 23, 42, 0.55)'
      roundedRect(ctx, x, y, w, h, 6)
      ctx.fill()
      ctx.strokeStyle = annotation.color || '#ef4444'
      ctx.setLineDash([6, 4])
      ctx.stroke()
      ctx.setLineDash([])
      ctx.fillStyle = '#ffffff'
      ctx.font = `500 ${Math.max(11, Math.min(18, h * 0.12))}px ${TEXT_FONT}`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(annotation.name || 'Image', x + w / 2, y + h / 2)
    }
    ctx.restore()
    return
  }

  ctx.restore()
}

/**
 * Draw all annotations plus an optional selection outline.
 *
 * @param {CanvasRenderingContext2D} ctx
 * @param {Object[]} annotations
 * @param {number} width
 * @param {number} height
 * @param {Map<string, HTMLImageElement>} [images]
 * @param {string|null} [selectedId]
 */
export function drawAnnotations(ctx, annotations, width, height, images, selectedId = null) {
  ;(annotations || []).forEach(annotation => drawAnnotation(ctx, annotation, width, height, images))
  if (!selectedId) return
  const selected = (annotations || []).find(annotation => annotation.id === selectedId)
  if (!selected) return
  const bounds = annotationBounds(selected)
  const pad = 6
  ctx.save()
  ctx.strokeStyle = '#38bdf8'
  ctx.lineWidth = 1.5
  ctx.setLineDash([6, 4])
  ctx.strokeRect(
    bounds.x * width - pad,
    bounds.y * height - pad,
    bounds.w * width + pad * 2,
    bounds.h * height + pad * 2
  )
  ctx.setLineDash([])
  ctx.fillStyle = '#38bdf8'
  ;[
    [bounds.x * width - pad, bounds.y * height - pad],
    [bounds.x * width + bounds.w * width + pad, bounds.y * height - pad],
    [bounds.x * width - pad, bounds.y * height + bounds.h * height + pad],
    [bounds.x * width + bounds.w * width + pad, bounds.y * height + bounds.h * height + pad]
  ].forEach(([x, y]) => ctx.fillRect(x - 2, y - 2, 4, 4))
  ctx.restore()
}

/** Load an image data URL for an image annotation. */
export function loadAnnotationImage(annotation) {
  return new Promise((resolve, reject) => {
    if (!annotation?.src) {
      reject(new Error('Annotation has no image data'))
      return
    }
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('Could not load annotation image'))
    image.src = annotation.src
  })
}

/**
 * Resize an uploaded image so it can travel through the annotation canvas and
 * the collaborative data channel without exploding the message size.
 *
 * @param {File} file
 * @param {number} [maxDimension=1600]
 * @returns {Promise<{ src: string, width: number, height: number, name: string }>}
 */
export function prepareAnnotationImage(file, maxDimension = 1600) {
  return new Promise((resolve, reject) => {
    if (!file) {
      reject(new Error('No image selected'))
      return
    }
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('Could not read the image'))
    reader.onload = () => {
      const image = new Image()
      image.onerror = () => reject(new Error('Could not decode the image'))
      image.onload = () => {
        const scale = Math.min(1, maxDimension / Math.max(image.width, image.height))
        const width = Math.max(1, Math.round(image.width * scale))
        const height = Math.max(1, Math.round(image.height * scale))
        if (scale === 1 && file.size < 450 * 1024) {
          resolve({ src: String(reader.result), width, height, name: file.name || 'image' })
          return
        }
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        const context = canvas.getContext('2d')
        context.drawImage(image, 0, 0, width, height)
        const type = file.type === 'image/png' ? 'image/png' : 'image/jpeg'
        resolve({
          src: canvas.toDataURL(type, type === 'image/jpeg' ? 0.9 : undefined),
          width,
          height,
          name: file.name || 'image'
        })
      }
      image.src = String(reader.result)
    }
    reader.readAsDataURL(file)
  })
}

function percent(value) {
  return `${Math.round(clamp01(value) * 100)}%`
}

function colorLabel(annotation) {
  return annotationColorName(annotation.color)
}

/**
 * Build the textual instructions that accompany the annotated screenshot.
 * These lines are inserted in the chat together with the image, so the model
 * knows what each mark means even if vision is disabled.
 *
 * @param {Object[]} annotations
 * @param {{ pageUrl?: string, pageTitle?: string }} [context]
 * @returns {string[]}
 */
export function describeAnnotations(annotations, context = {}) {
  const ops = (annotations || []).filter(Boolean)
  const lines = []
  if (!ops.length) {
    lines.push('The drawing has no marks yet.')
    return lines
  }

  const counts = ops.reduce((acc, annotation) => {
    acc[annotation.tool] = (acc[annotation.tool] || 0) + 1
    return acc
  }, {})
  const labels = {
    pen: 'freehand stroke',
    marker: 'highlighter',
    arrow: 'arrow',
    rect: 'rectangle',
    ellipse: 'ellipse',
    note: 'sticky note',
    text: 'text label',
    image: 'inserted image'
  }
  const summary = Object.entries(counts)
    .map(([tool, count]) => `${count} ${labels[tool] || tool}${count > 1 ? 's' : ''}`)
    .join(', ')
  lines.push(`Marks on the page: ${summary}.`)

  ops.slice(0, 40).forEach((annotation, index) => {
    const number = index + 1
    const color = colorLabel(annotation)
    if (annotation.tool === 'arrow') {
      const [start, end] = annotation.points || []
      if (start && end) {
        lines.push(`${number}. ${color} arrow from ${percent(start.x)},${percent(start.y)} to ${percent(end.x)},${percent(end.y)}.`)
      }
      return
    }
    if (annotation.tool === 'rect' || annotation.tool === 'ellipse') {
      const bounds = annotationBounds(annotation)
      const shape = annotation.tool === 'rect' ? 'rectangle' : 'ellipse'
      lines.push(
        `${number}. ${color} ${shape} around ${percent(bounds.x)},${percent(bounds.y)} to ` +
        `${percent(bounds.x + bounds.w)},${percent(bounds.y + bounds.h)}.`
      )
      return
    }
    if (annotation.tool === 'note' || annotation.tool === 'text') {
      const text = String(annotation.text || '').trim().replace(/\s+/g, ' ').slice(0, 180)
      const bounded = text ? `: "${text}"` : ''
      lines.push(`${number}. ${color} ${annotation.tool === 'note' ? 'sticky note' : 'text'} at ${percent(annotation.x)},${percent(annotation.y)}${bounded}.`)
      return
    }
    if (annotation.tool === 'image') {
      const bounds = annotationBounds(annotation)
      lines.push(
        `${number}. Inserted image "${annotation.name || 'image'}" at ` +
        `${percent(bounds.x)},${percent(bounds.y)} (${percent(bounds.w)} x ${percent(bounds.h)}).`
      )
      return
    }
    const points = annotation.points || []
    const first = points[0]
    const last = points[points.length - 1]
    if (first && last) {
      lines.push(
        `${number}. ${color} ${labels[annotation.tool] || annotation.tool} from ` +
        `${percent(first.x)},${percent(first.y)} to ${percent(last.x)},${percent(last.y)}.`
      )
    }
  })
  if (ops.length > 40) {
    lines.push(`…and ${ops.length - 40} more marks not listed.`)
  }
  if (context.pageUrl || context.pageTitle) {
    lines.push('', `Page: ${context.pageTitle || ''}${context.pageUrl ? ` (${context.pageUrl})` : ''}`)
  }
  return lines
}

/** Deep-ish clone used by undo/redo snapshots. Points are the only nested data. */
export function cloneAnnotations(annotations) {
  return (annotations || []).map(annotation => ({
    ...annotation,
    points: annotation.points ? annotation.points.map(point => ({ ...point })) : undefined
  }))
}
