<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import mermaid from 'mermaid'

const props = defineProps({
  diagram: { type: String, default: '' },
  theme: { type: String, default: 'dark' },
  minScale: { type: Number, default: 0.1 },
  maxScale: { type: Number, default: 5 }
})

const emit = defineEmits(['rendered', 'error', 'update:scale', 'update:natural-size'])

const viewport = ref(null)
const stage = ref(null)
const loading = ref(false)
const renderError = ref('')
const scale = ref(1)
const translateX = ref(0)
const translateY = ref(0)
const dragging = ref(false)

// Natural SVG size (before any zoom) and the current view transform.
let natural = { width: 0, height: 0 }
let renderCounter = 0
let renderToken = 0
let renderTimer = null
let resizeObserver = null
let hasUserAdjustedView = false

// Pointer bookkeeping: one pointer pans, two pointers pinch-zoom.
const pointers = new Map()
let dragState = null
let pinchState = null

function configureMermaid() {
  mermaid.initialize({
    startOnLoad: false,
    // Strict keeps generated markup sanitized: diagram sources come from chat
    // messages and models, never from trusted code.
    securityLevel: 'strict',
    theme: props.theme === 'light' ? 'default' : 'dark',
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif',
    flowchart: { useMaxWidth: false, htmlLabels: true },
    sequence: { useMaxWidth: false },
    gantt: { useMaxWidth: false },
    class: { useMaxWidth: false },
    state: { useMaxWidth: false },
    er: { useMaxWidth: false },
    journey: { useMaxWidth: false },
    pie: { useMaxWidth: false },
    quadrantChart: { useMaxWidth: false },
    requirement: { useMaxWidth: false },
    mindmap: { useMaxWidth: false },
    timeline: { useMaxWidth: false },
    gitGraph: { useMaxWidth: false },
    sankey: { useMaxWidth: false }
  })
}

function scheduleRender(delay = 140) {
  clearTimeout(renderTimer)
  renderTimer = setTimeout(renderDiagram, delay)
}

function readNaturalSize(svg) {
  const box = svg.viewBox?.baseVal
  if (box && box.width > 0 && box.height > 0) {
    return { width: box.width, height: box.height }
  }
  const rect = svg.getBoundingClientRect()
  if (rect.width > 0 && rect.height > 0) {
    return { width: rect.width, height: rect.height }
  }
  return {
    width: parseFloat(svg.getAttribute('width')) || 800,
    height: parseFloat(svg.getAttribute('height')) || 600
  }
}

function sizeSvg(svg, width, height) {
  // Mermaid emits `max-width` + `width:100%`; that fights a manual zoom. Pin
  // the SVG to its natural size and let the stage transform do the scaling.
  svg.setAttribute('width', width)
  svg.setAttribute('height', height)
  svg.style.maxWidth = 'none'
  svg.style.width = `${width}px`
  svg.style.height = `${height}px`
  svg.style.display = 'block'
}

function errorMessage(error) {
  const raw = error?.message || error?.str || String(error || '')
  return raw.replace(/^Error:\s*/i, '').trim() || 'The diagram could not be rendered.'
}

function removeMermaidArtifacts(id) {
  for (const element of [document.getElementById(id), document.getElementById(`d${id}`)]) {
    if (element && !stage.value?.contains(element)) element.remove()
  }
}

async function renderDiagram() {
  clearTimeout(renderTimer)
  const source = String(props.diagram ?? '')
  const token = ++renderToken
  const id = `mermaid-viewer-svg-${++renderCounter}`
  renderError.value = ''
  loading.value = true

  if (!source.trim()) {
    stage.value && (stage.value.innerHTML = '')
    loading.value = false
    renderError.value = 'The diagram source is empty.'
    emit('error', renderError.value)
    return
  }

  try {
    await nextTick()
    if (token !== renderToken || !stage.value) return
    const result = await mermaid.render(id, source)
    if (token !== renderToken || !stage.value) return

    const svgMarkup = typeof result === 'string' ? result : result?.svg
    if (!svgMarkup) throw new Error('Mermaid did not return an SVG.')

    stage.value.innerHTML = svgMarkup
    if (typeof result?.bindFunctions === 'function') result.bindFunctions(stage.value)

    const svg = stage.value.querySelector('svg')
    if (!svg) throw new Error('Mermaid did not return an SVG.')

    natural = readNaturalSize(svg)
    sizeSvg(svg, natural.width, natural.height)
    emit('update:natural-size', { ...natural })

    await nextTick()
    if (token !== renderToken) return
    // First render / explicit "fit" state starts fitted; a user's manual zoom
    // is preserved across live source updates (the fullscreen editor preview).
    if (hasUserAdjustedView) applyTransform()
    else fit()
    emit('rendered', { ...natural })
  } catch (error) {
    if (token !== renderToken || !stage.value) return
    stage.value.innerHTML = ''
    renderError.value = errorMessage(error)
    emit('error', error)
  } finally {
    if (token === renderToken) loading.value = false
    removeMermaidArtifacts(id)
  }
}

function clampScale(value) {
  return Math.min(props.maxScale, Math.max(props.minScale, value))
}

function applyTransform() {
  if (!stage.value) return
  stage.value.style.transform = `translate3d(${translateX.value}px, ${translateY.value}px, 0) scale(${scale.value})`
}

function emitScale() {
  emit('update:scale', scale.value)
}

function setScale(nextScale, anchor = null, fromUser = true) {
  const previous = scale.value
  const next = clampScale(nextScale)
  if (next === previous) return

  if (anchor) {
    translateX.value = anchor.x - (anchor.x - translateX.value) * (next / previous)
    translateY.value = anchor.y - (anchor.y - translateY.value) * (next / previous)
  }

  scale.value = next
  if (fromUser) hasUserAdjustedView = true
  applyTransform()
  emitScale()
}

function viewportCenter() {
  const element = viewport.value
  if (!element) return { x: 0, y: 0 }
  return { x: element.clientWidth / 2, y: element.clientHeight / 2 }
}

function fit() {
  const element = viewport.value
  if (!element || !natural.width || !natural.height) return

  // Keep the floating toolbar from covering the top-right of the diagram: the
  // fitted area starts below it.
  const padding = 24
  const topInset = 52
  const availableWidth = Math.max(element.clientWidth - padding * 2, 40)
  const availableHeight = Math.max(element.clientHeight - topInset - padding, 40)
  const target = Math.min(availableWidth / natural.width, availableHeight / natural.height)
  // Fit-to-view fills the viewport. Allow a little upscale for small diagrams
  // but never blow a tiny graph up into a wall of pixels.
  const next = clampScale(Math.min(target, 2))

  scale.value = next
  translateX.value = (element.clientWidth - natural.width * next) / 2
  translateY.value = topInset + (element.clientHeight - topInset - padding - natural.height * next) / 2
  hasUserAdjustedView = false
  applyTransform()
  emitScale()
}

function resetZoom() {
  const element = viewport.value
  if (!element) return
  scale.value = 1
  translateX.value = (element.clientWidth - natural.width) / 2
  translateY.value = (element.clientHeight - natural.height) / 2
  hasUserAdjustedView = true
  applyTransform()
  emitScale()
}

function zoomIn() {
  setScale(scale.value * 1.2, viewportCenter())
}

function zoomOut() {
  setScale(scale.value / 1.2, viewportCenter())
}

function onWheel(event) {
  // Ctrl/Cmd + wheel zooms (the same gesture browsers use for page zoom), so a
  // normal wheel still scrolls the surrounding conversation.
  if (!(event.ctrlKey || event.metaKey)) return
  event.preventDefault()
  const element = viewport.value
  if (!element) return
  const rect = element.getBoundingClientRect()
  const factor = Math.exp(-event.deltaY * 0.0015)
  setScale(scale.value * factor, {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top
  })
}

function pointerPoint(pointer) {
  return { x: pointer.x, y: pointer.y }
}

function startPinch() {
  const [first, second] = [...pointers.values()]
  if (!first || !second) return
  const rect = viewport.value?.getBoundingClientRect() || { left: 0, top: 0 }
  const mid = {
    x: (first.x + second.x) / 2,
    y: (first.y + second.y) / 2
  }
  pinchState = {
    distance: Math.max(Math.hypot(first.x - second.x, first.y - second.y), 1),
    scale: scale.value,
    translateX: translateX.value,
    translateY: translateY.value,
    // Content point under the initial pinch center, in stage coordinates.
    contentX: (mid.x - rect.left - translateX.value) / scale.value,
    contentY: (mid.y - rect.top - translateY.value) / scale.value
  }
  dragState = null
}

function onPointerDown(event) {
  if (event.pointerType === 'mouse' && event.button !== 0) return
  const element = viewport.value
  if (!element) return
  element.setPointerCapture?.(event.pointerId)
  pointers.set(event.pointerId, pointerPoint(event))

  if (pointers.size === 1) {
    dragState = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      translateX: translateX.value,
      translateY: translateY.value
    }
    dragging.value = true
  } else if (pointers.size === 2) {
    startPinch()
    dragging.value = false
  }
}

function onPointerMove(event) {
  const pointer = pointers.get(event.pointerId)
  if (!pointer) return
  pointer.x = event.clientX
  pointer.y = event.clientY

  if (pointers.size >= 2 && pinchState) {
    const [first, second] = [...pointers.values()]
    const distance = Math.max(Math.hypot(first.x - second.x, first.y - second.y), 1)
    const rect = viewport.value?.getBoundingClientRect() || { left: 0, top: 0 }
    const mid = {
      x: (first.x + second.x) / 2,
      y: (first.y + second.y) / 2
    }
    const next = clampScale(pinchState.scale * (distance / pinchState.distance))
    scale.value = next
    translateX.value = (mid.x - rect.left) - pinchState.contentX * next
    translateY.value = (mid.y - rect.top) - pinchState.contentY * next
    hasUserAdjustedView = true
    applyTransform()
    emitScale()
    return
  }

  if (!dragState || dragState.pointerId !== event.pointerId) return
  translateX.value = dragState.translateX + (event.clientX - dragState.startX)
  translateY.value = dragState.translateY + (event.clientY - dragState.startY)
  hasUserAdjustedView = true
  applyTransform()
}

function onPointerUp(event) {
  pointers.delete(event.pointerId)
  if (pointers.size < 2) pinchState = null

  if (pointers.size === 1) {
    const [remainingId, remaining] = [...pointers.entries()][0]
    dragState = {
      pointerId: remainingId,
      startX: remaining.x,
      startY: remaining.y,
      translateX: translateX.value,
      translateY: translateY.value
    }
    dragging.value = true
    return
  }

  if (pointers.size === 0) {
    dragState = null
    dragging.value = false
  }
}

function onKeydown(event) {
  const key = event.key
  if (['+', '=', '-', '_', '0', '1', 'f', 'F'].includes(key)) {
    event.preventDefault()
  }
  if (key === '+' || key === '=') zoomIn()
  else if (key === '-' || key === '_') zoomOut()
  else if (key === '0' || key === 'f' || key === 'F') fit()
  else if (key === '1') resetZoom()
}

function observeResize() {
  if (!viewport.value || typeof ResizeObserver === 'undefined') return
  resizeObserver = new ResizeObserver(() => {
    if (hasUserAdjustedView) applyTransform()
    else fit()
  })
  resizeObserver.observe(viewport.value)
}

onMounted(() => {
  configureMermaid()
  renderDiagram()
  observeResize()
})

onBeforeUnmount(() => {
  renderToken++
  clearTimeout(renderTimer)
  resizeObserver?.disconnect()
  resizeObserver = null
  pointers.clear()
})

watch(() => props.diagram, () => scheduleRender())
watch(() => props.theme, () => {
  configureMermaid()
  renderDiagram()
})

defineExpose({
  zoomIn,
  zoomOut,
  fit,
  resetZoom,
  getScale: () => scale.value,
  getSvgMarkup: () => stage.value?.querySelector('svg')?.outerHTML || ''
})
</script>

<template>
  <div
    ref="viewport"
    class="relative w-full h-full overflow-hidden select-none touch-none bg-base-300/40 rounded-lg"
    :class="dragging ? 'cursor-grabbing' : 'cursor-grab'"
    role="group"
    aria-label="Mermaid diagram. Drag to pan, Ctrl or Cmd with the wheel to zoom."
    tabindex="0"
    @wheel="onWheel"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerUp"
    @keydown="onKeydown"
    @dblclick="fit"
  >
    <div
      ref="stage"
      class="absolute left-0 top-0 origin-top-left will-change-transform"
    ></div>

    <div
      v-if="loading && !renderError"
      class="absolute inset-0 flex items-center justify-center bg-base-300/60"
    >
      <span class="loading loading-spinner loading-md text-info"></span>
    </div>

    <div
      v-if="renderError"
      class="absolute inset-0 overflow-auto bg-base-300/95 p-3"
      @pointerdown.stop
    >
      <div class="alert alert-error items-start text-xs">
        <i class="fa-solid fa-triangle-exclamation mt-0.5"></i>
        <div class="min-w-0">
          <div class="font-semibold mb-1">Invalid Mermaid diagram</div>
          <pre class="whitespace-pre-wrap break-words font-mono text-[11px] leading-relaxed">{{ renderError }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>
