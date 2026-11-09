<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import mermaid from 'mermaid'
import MermaidCanvas from './mermaid/MermaidCanvas.vue'
import MermaidToolbar from './mermaid/MermaidToolbar.vue'

const props = defineProps({
  diagram: { type: String, default: '' },
  theme: { type: String, default: 'dark' },
  editable: { type: Boolean, default: true },
  title: { type: String, default: 'Mermaid diagram' },
  // Optional explicit height for the inline viewer (any CSS length).
  height: { type: String, default: '' }
})

const emit = defineEmits(['change', 'update:diagram'])

const expanded = ref(false)
const editing = ref(false)
const draft = ref('')
const editError = ref('')
const copied = ref(false)
const inlineCanvas = ref(null)
const modalCanvas = ref(null)
const editorEl = ref(null)
const inlineScale = ref(1)
const modalScale = ref(1)

let copyTimer = null
let validationTimer = null
let validationToken = 0
let previousBodyOverflow = null

const draftChanged = computed(() => draft.value !== props.diagram)
const inlineHeightStyle = computed(() => props.height ? { height: props.height } : null)

function formatMermaidError(error) {
  const raw = error?.message || error?.str || String(error || '')
  return raw.replace(/^Error:\s*/i, '').trim() || 'The diagram source is not valid Mermaid.'
}

function activeCanvas() {
  return expanded.value ? modalCanvas.value : inlineCanvas.value
}

async function openExpanded() {
  expanded.value = true
  await nextTick()
  modalCanvas.value?.fit()
  if (editing.value) focusEditor()
}

async function closeExpanded() {
  expanded.value = false
  await nextTick()
  inlineCanvas.value?.fit()
  if (editing.value) focusEditor()
}

function focusEditor() {
  nextTick(() => {
    const element = editorEl.value
    if (!element) return
    element.focus()
    element.setSelectionRange(element.value.length, element.value.length)
  })
}

function startEdit() {
  if (!props.editable) return
  clearTimeout(validationTimer)
  validationToken++
  draft.value = props.diagram || ''
  editError.value = ''
  editing.value = true
  focusEditor()
}

function cancelEdit() {
  clearTimeout(validationTimer)
  validationToken++
  editing.value = false
  draft.value = ''
  editError.value = ''
  nextTick(() => activeCanvas()?.fit())
}

async function saveEdit() {
  if (!props.editable) return
  clearTimeout(validationTimer)
  validationToken++
  const source = draft.value
  if (source === props.diagram) {
    cancelEdit()
    return
  }
  if (!source.trim()) {
    editError.value = 'The diagram source is empty. Add a Mermaid diagram before saving.'
    return
  }
  try {
    await mermaid.parse(source)
  } catch (error) {
    editError.value = formatMermaidError(error)
    return
  }

  editError.value = ''
  editing.value = false
  emit('update:diagram', source)
  emit('change', source)
  await nextTick()
  activeCanvas()?.fit()
}

async function validateDraft() {
  if (!editing.value) return
  const source = draft.value
  const token = ++validationToken
  if (!source.trim()) {
    editError.value = 'The diagram source is empty.'
    return
  }
  try {
    await mermaid.parse(source)
    if (token === validationToken) editError.value = ''
  } catch (error) {
    if (token === validationToken) editError.value = formatMermaidError(error)
  }
}

function onEditorKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    event.stopPropagation()
    cancelEdit()
    return
  }
  if ((event.ctrlKey || event.metaKey) && (event.key === 's' || event.key === 'Enter')) {
    event.preventDefault()
    event.stopPropagation()
    saveEdit()
    return
  }
  if (event.key === 'Tab') {
    event.preventDefault()
    const element = event.target
    const start = element.selectionStart
    const end = element.selectionEnd
    draft.value = `${draft.value.slice(0, start)}  ${draft.value.slice(end)}`
    nextTick(() => element.setSelectionRange(start + 2, start + 2))
  }
}

async function copySource() {
  try {
    await navigator.clipboard.writeText(editing.value ? draft.value : (props.diagram || ''))
    copied.value = true
    clearTimeout(copyTimer)
    copyTimer = setTimeout(() => { copied.value = false }, 1600)
  } catch (error) {
    console.error('Failed to copy Mermaid source', error)
  }
}

function downloadSvg() {
  const markup = activeCanvas()?.getSvgMarkup?.()
  if (!markup) return
  const filename = `${(props.title || 'mermaid-diagram').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'mermaid-diagram'}.svg`
  const blob = new Blob([markup], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function onDocumentKeydown(event) {
  if (event.key !== 'Escape') return
  if (editing.value) {
    event.preventDefault()
    event.stopPropagation()
    cancelEdit()
    return
  }
  if (expanded.value) {
    event.preventDefault()
    event.stopPropagation()
    closeExpanded()
  }
}

watch(draft, () => {
  if (!editing.value) return
  editError.value = ''
  clearTimeout(validationTimer)
  validationTimer = setTimeout(validateDraft, 320)
})

watch(expanded, async (isExpanded) => {
  if (isExpanded) {
    previousBodyOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    await nextTick()
    modalCanvas.value?.fit()
    return
  }
  if (previousBodyOverflow !== null) {
    document.body.style.overflow = previousBodyOverflow
    previousBodyOverflow = null
  }
  await nextTick()
  inlineCanvas.value?.fit()
})

onMounted(() => {
  document.addEventListener('keydown', onDocumentKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onDocumentKeydown)
  clearTimeout(copyTimer)
  clearTimeout(validationTimer)
  if (previousBodyOverflow !== null) document.body.style.overflow = previousBodyOverflow
})
</script>

<template>
  <div class="mermaid-viewer relative w-full rounded-lg border border-base-content/10 bg-base-300/30">
    <!-- Inline toolbar (view mode) -->
    <div v-if="!editing" class="absolute right-2 top-2 z-20 max-w-[calc(100%-1rem)]">
      <MermaidToolbar
        :scale="inlineScale"
        :editable="editable"
        :expanded="false"
        :show-labels="true"
        @zoom-in="inlineCanvas?.zoomIn()"
        @zoom-out="inlineCanvas?.zoomOut()"
        @fit="inlineCanvas?.fit()"
        @reset="inlineCanvas?.resetZoom()"
        @edit="startEdit"
        @expand="openExpanded"
      />
    </div>

    <!-- Diagram canvas -->
    <div
      v-if="!editing"
      class="w-full h-[360px] md:h-[440px]"
      :style="inlineHeightStyle"
    >
      <MermaidCanvas
        ref="inlineCanvas"
        :diagram="diagram"
        :theme="theme"
        @update:scale="inlineScale = $event"
      />
    </div>

    <!-- Inline source editor -->
    <div v-else class="p-2 md:p-3">
      <div class="mb-2 flex items-center justify-between gap-2 text-xs">
        <span class="flex items-center gap-2 font-semibold text-base-content/70">
          <i class="fa-solid fa-code text-info"></i>
          Mermaid source
        </span>
        <span class="text-[10px] text-base-content/40">
          {{ draft ? draft.split('\n').length : 0 }} lines
        </span>
      </div>

      <textarea
        ref="editorEl"
        v-model="draft"
        class="block h-[280px] w-full resize-y rounded-lg border border-base-content/10 bg-base-300 p-3 font-mono text-xs leading-relaxed text-base-content focus:outline-none focus:ring-1 focus:ring-primary/40"
        spellcheck="false"
        aria-label="Mermaid diagram source"
        @keydown="onEditorKeydown"
      ></textarea>

      <div class="mt-2 flex flex-wrap items-center justify-between gap-2">
        <div class="min-w-0 text-[11px]" :class="editError ? 'text-error' : 'text-base-content/40'">
          <span v-if="editError" class="flex items-start gap-1">
            <i class="fa-solid fa-triangle-exclamation mt-0.5 shrink-0"></i>
            <span class="break-words">{{ editError }}</span>
          </span>
          <span v-else class="flex items-center gap-1">
            <i class="fa-solid fa-circle-check text-success/70"></i>
            Valid Mermaid · Ctrl/⌘+S saves
          </span>
        </div>
        <div class="flex shrink-0 items-center gap-1">
          <button
            v-if="!expanded"
            class="btn btn-xs btn-ghost gap-1"
            title="Open a larger editor with live preview"
            @click="openExpanded"
          >
            <i class="fa-solid fa-up-right-from-square"></i>
            <span class="hidden sm:inline">Big editor</span>
          </button>
          <button class="btn btn-xs btn-ghost gap-1" @click="cancelEdit">
            <i class="fa-solid fa-ban"></i> Cancel
          </button>
          <button
            class="btn btn-xs btn-primary gap-1"
            :disabled="!draftChanged || !!editError"
            @click="saveEdit"
          >
            <i class="fa-solid fa-check"></i> Save changes
          </button>
        </div>
      </div>
    </div>

    <!-- Usage hint (view mode) -->
    <div
      v-if="!editing"
      class="pointer-events-none absolute bottom-2 left-2 hidden max-w-[70%] items-center gap-1.5 rounded-md border border-base-content/10 bg-base-200/85 px-2 py-1 text-[10px] text-base-content/50 backdrop-blur-sm md:flex"
    >
      <i class="fa-solid fa-hand"></i>
      Drag to pan · Pinch or Ctrl/⌘ + wheel to zoom
    </div>

    <!-- Fullscreen modal -->
    <Teleport to="body">
      <div
        v-if="expanded"
        class="fixed inset-0 z-[9999] flex flex-col bg-base-300"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
      >
        <header class="flex flex-shrink-0 items-center justify-between gap-2 border-b border-base-content/10 px-3 py-2 md:px-4">
          <div class="flex min-w-0 items-center gap-2">
            <i class="fa-solid fa-circle-nodes text-info"></i>
            <span class="truncate text-sm font-semibold">{{ title }}</span>
            <span class="badge badge-xs badge-ghost">Mermaid</span>
            <span v-if="copied" class="badge badge-xs badge-success gap-1">
              <i class="fa-solid fa-check"></i> Copied
            </span>
          </div>
          <div class="flex flex-shrink-0 items-center gap-1">
            <button
              v-if="editable && !editing"
              class="btn btn-xs btn-ghost gap-1"
              title="Edit diagram source"
              @click="startEdit"
            >
              <i class="fa-solid fa-pen-to-square"></i>
              <span class="hidden sm:inline">Edit source</span>
            </button>
            <button class="btn btn-xs btn-ghost gap-1" title="Copy Mermaid source" @click="copySource">
              <i class="fa-solid fa-copy"></i>
              <span class="hidden sm:inline">Copy source</span>
            </button>
            <button class="btn btn-xs btn-ghost gap-1" title="Download SVG" @click="downloadSvg">
              <i class="fa-solid fa-download"></i>
              <span class="hidden sm:inline">SVG</span>
            </button>
            <button class="btn btn-xs btn-ghost px-2" title="Close (Esc)" aria-label="Close fullscreen" @click="closeExpanded">
              <i class="fa-solid fa-xmark text-lg"></i>
            </button>
          </div>
        </header>

        <div class="relative min-h-0 flex-1">
          <!-- View mode -->
          <template v-if="!editing">
            <MermaidCanvas
              ref="modalCanvas"
              class="h-full"
              :diagram="diagram"
              :theme="theme"
              @update:scale="modalScale = $event"
            />
            <div class="absolute right-3 top-3 z-20 max-w-[calc(100%-1.5rem)]">
              <MermaidToolbar
                :scale="modalScale"
                :editable="editable"
                :expanded="true"
                :show-labels="true"
                @zoom-in="modalCanvas?.zoomIn()"
                @zoom-out="modalCanvas?.zoomOut()"
                @fit="modalCanvas?.fit()"
                @reset="modalCanvas?.resetZoom()"
                @edit="startEdit"
                @shrink="closeExpanded"
              />
            </div>
          </template>

          <!-- Edit mode: source + live preview side by side -->
          <div v-else class="grid h-full min-h-0 grid-rows-2 md:grid-cols-2 md:grid-rows-1">
            <div class="flex min-h-0 flex-col border-b border-base-content/10 md:border-b-0 md:border-r">
              <div class="flex flex-shrink-0 items-center justify-between px-3 py-2 text-xs text-base-content/60">
                <span class="flex items-center gap-2 font-semibold">
                  <i class="fa-solid fa-code text-info"></i>
                  Mermaid source
                </span>
                <span class="text-[10px]">{{ draft ? draft.split('\n').length : 0 }} lines</span>
              </div>
              <textarea
                ref="editorEl"
                v-model="draft"
                class="min-h-0 w-full flex-1 resize-none bg-base-300 p-3 font-mono text-xs leading-relaxed text-base-content focus:outline-none focus:ring-1 focus:ring-primary/40"
                spellcheck="false"
                aria-label="Mermaid diagram source"
                @keydown="onEditorKeydown"
              ></textarea>
              <div class="flex flex-shrink-0 flex-wrap items-center justify-between gap-2 border-t border-base-content/10 px-3 py-2">
                <div class="min-w-0 text-[11px]" :class="editError ? 'text-error' : 'text-base-content/40'">
                  <span v-if="editError" class="flex items-start gap-1">
                    <i class="fa-solid fa-triangle-exclamation mt-0.5 shrink-0"></i>
                    <span class="break-words">{{ editError }}</span>
                  </span>
                  <span v-else class="flex items-center gap-1">
                    <i class="fa-solid fa-circle-check text-success/70"></i>
                    Valid Mermaid · Ctrl/⌘+S saves
                  </span>
                </div>
                <div class="flex shrink-0 items-center gap-1">
                  <button class="btn btn-xs btn-ghost gap-1" @click="cancelEdit">
                    <i class="fa-solid fa-ban"></i> Cancel
                  </button>
                  <button
                    class="btn btn-xs btn-primary gap-1"
                    :disabled="!draftChanged || !!editError"
                    @click="saveEdit"
                  >
                    <i class="fa-solid fa-check"></i> Save changes
                  </button>
                </div>
              </div>
            </div>

            <div class="relative min-h-0">
              <MermaidCanvas
                ref="modalCanvas"
                :diagram="draft"
                :theme="theme"
                class="h-full"
                @update:scale="modalScale = $event"
              />
              <div class="absolute right-3 top-3 z-20 max-w-[calc(100%-1.5rem)]">
                <MermaidToolbar
                  :scale="modalScale"
                  :editable="false"
                  :editing="true"
                  :expanded="true"
                  :show-labels="true"
                  @zoom-in="modalCanvas?.zoomIn()"
                  @zoom-out="modalCanvas?.zoomOut()"
                  @fit="modalCanvas?.fit()"
                  @reset="modalCanvas?.resetZoom()"
                  @shrink="closeExpanded"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
