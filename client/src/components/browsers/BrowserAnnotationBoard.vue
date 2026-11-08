<template>
  <div class="absolute inset-0 z-20 select-none">
    <!-- Drawing surface -->
    <canvas
      ref="canvas"
      class="absolute inset-0 w-full h-full touch-none"
      :class="cursorClass"
      aria-label="Annotation canvas over the live browser"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
      @pointerleave="onPointerLeave"
      @dblclick="onDoubleClick"
      @contextmenu.prevent
      @dragover.prevent
      @drop.prevent="onDropImage"
    ></canvas>

    <!-- Resize handles for the selected mark. The box is DOM (not canvas) so
         the handles stay crisp and keep receiving pointer events while the
         canvas is repainted. -->
    <div v-if="selectionRect" class="pointer-events-none absolute inset-0 z-10">
      <div
        class="absolute rounded-sm border border-sky-400/90 shadow-[0_0_0_1px_rgba(56,189,248,0.25)]"
        :style="selectionBoxStyle"
        aria-hidden="true"
      ></div>
      <div
        v-for="handle in selectionHandles"
        :key="handle.id"
        class="pointer-events-auto absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-sm border border-sky-400 bg-white shadow"
        :class="handle.cursorClass"
        :style="handle.style"
        :aria-label="`Resize ${handle.id}`"
        @pointerdown.stop.prevent="startResize(handle.id, $event)"
      ></div>
    </div>

    <!-- Toolbar. It can be dragged anywhere over the page or docked as a footer
         so it never permanently shadows the content the user is marking. -->
    <div
      ref="toolbar"
      class="absolute z-30 w-auto max-w-[calc(100%-1rem)]"
      :class="toolbarDock === 'bottom' && !toolbarPosition && 'flex flex-col-reverse'"
      :style="toolbarStyle"
      role="toolbar"
      aria-label="Annotation tools"
    >
      <div class="flex flex-wrap items-center gap-1 rounded-xl border border-white/10 bg-[#111827]/95 px-2 py-1.5 text-white shadow-2xl backdrop-blur">
        <button
          class="flex h-7 w-6 touch-none cursor-grab items-center justify-center rounded-md text-white/40 hover:bg-white/10 hover:text-white active:cursor-grabbing"
          title="Drag the toolbar"
          aria-label="Drag the annotation toolbar"
          @pointerdown.prevent="startToolbarDrag"
        >
          <i class="fa-solid fa-grip-vertical text-[10px]" aria-hidden="true"></i>
        </button>

        <div class="flex items-center gap-0.5 rounded-lg bg-white/5 p-0.5">
          <button
            v-for="item in tools"
            :key="item.id"
            class="flex h-7 w-7 items-center justify-center rounded-md text-[12px] transition-colors"
            :class="tool === item.id ? 'bg-primary text-primary-content shadow' : 'text-white/70 hover:bg-white/10 hover:text-white'"
            :title="item.label"
            :aria-label="item.label"
            :aria-pressed="tool === item.id ? 'true' : 'false'"
            @click="selectTool(item.id)"
          >
            <i class="fa-solid" :class="item.icon" aria-hidden="true"></i>
          </button>
        </div>

        <span class="mx-0.5 h-5 w-px bg-white/10" aria-hidden="true"></span>

        <!-- Colors -->
        <div class="flex items-center gap-0.5" role="group" aria-label="Annotation color">
          <button
            v-for="color in palette"
            :key="color.value"
            class="h-5 w-5 rounded-full border transition-transform hover:scale-110"
            :class="strokeColor === color.value ? 'border-white ring-2 ring-primary' : 'border-white/30'"
            :style="{ backgroundColor: color.value }"
            :title="color.label"
            :aria-label="`Use ${color.label}`"
            :aria-pressed="strokeColor === color.value ? 'true' : 'false'"
            @click="chooseColor(color.value)"
          ></button>
        </div>

        <span class="mx-0.5 h-5 w-px bg-white/10" aria-hidden="true"></span>

        <!-- Width -->
        <label class="hidden items-center gap-1 text-[10px] text-white/60 sm:flex" title="Stroke width">
          <i class="fa-solid fa-up-down" aria-hidden="true"></i>
          <input
            v-model.number="strokeWidth"
            type="range"
            min="1"
            max="12"
            step="1"
            class="range range-xs w-16"
            aria-label="Stroke width"
          />
        </label>

        <span class="mx-0.5 h-5 w-px bg-white/10" aria-hidden="true"></span>

        <!-- History -->
        <div class="flex items-center gap-0.5">
          <button
            class="flex h-7 w-7 items-center justify-center rounded-md text-white/70 hover:bg-white/10 hover:text-white disabled:opacity-30"
            title="Undo (Ctrl+Z)"
            aria-label="Undo"
            :disabled="!history.length"
            @click="undo"
          >
            <i class="fa-solid fa-rotate-left" aria-hidden="true"></i>
          </button>
          <button
            class="flex h-7 w-7 items-center justify-center rounded-md text-white/70 hover:bg-white/10 hover:text-white disabled:opacity-30"
            title="Redo (Ctrl+Shift+Z)"
            aria-label="Redo"
            :disabled="!future.length"
            @click="redo"
          >
            <i class="fa-solid fa-rotate-right" aria-hidden="true"></i>
          </button>
          <button
            class="flex h-7 w-7 items-center justify-center rounded-md text-white/70 hover:bg-error/20 hover:text-error disabled:opacity-30"
            title="Clear all annotations"
            aria-label="Clear all annotations"
            :disabled="!annotations.length"
            @click="clearAll"
          >
            <i class="fa-solid fa-trash-can" aria-hidden="true"></i>
          </button>
        </div>

        <span class="flex-1"></span>

        <button
          class="btn btn-xs gap-1 border-0 bg-primary text-primary-content hover:bg-primary/80"
          :disabled="sending || !annotations.length"
          :aria-busy="sending ? 'true' : 'false'"
          title="Copy the annotated image and send it as a new message to the open chat"
          @click="sendToChat"
        >
          <span v-if="sending" class="loading loading-spinner loading-xs"></span>
          <i v-else class="fa-solid fa-paper-plane" aria-hidden="true"></i>
          <span class="hidden sm:inline">{{ sending ? 'Preparing…' : 'Send' }}</span>
        </button>
        <button
          class="flex h-7 w-7 items-center justify-center rounded-md text-white/70 hover:bg-white/10 hover:text-white"
          :title="toolbarDock === 'bottom' ? 'Dock toolbar at the top' : 'Dock toolbar as a footer'"
          :aria-label="toolbarDock === 'bottom' ? 'Dock toolbar at the top' : 'Dock toolbar as a footer'"
          @click="toggleToolbarDock"
        >
          <i
            class="fa-solid"
            :class="toolbarDock === 'bottom' ? 'fa-arrow-up-to-line' : 'fa-arrow-down-to-line'"
            aria-hidden="true"
          ></i>
        </button>
        <button
          class="flex h-7 w-7 items-center justify-center rounded-md text-white/70 hover:bg-white/10 hover:text-white"
          title="Close drawing board (Esc)"
          aria-label="Close drawing board"
          @click="$emit('close')"
        >
          <i class="fa-solid fa-xmark" aria-hidden="true"></i>
        </button>
      </div>

      <!-- Second line: mode / hint + collaboration presence -->
      <div class="mt-1 flex items-center gap-2 rounded-lg bg-black/55 px-2 py-1 text-[10px] text-white/70 backdrop-blur">
        <span class="flex items-center gap-1 font-semibold text-white/90">
          <i class="fa-solid fa-pen-ruler text-primary" aria-hidden="true"></i>
          {{ activeToolLabel }}
        </span>
        <span class="truncate">
          {{ hint }}
        </span>
        <span class="flex-1"></span>
        <span v-if="participants.length" class="flex items-center gap-1" :title="participantTitle">
          <i class="fa-solid fa-users text-white/50" aria-hidden="true"></i>
          <span
            v-for="participant in visibleParticipants"
            :key="participant.clientId"
            class="flex h-4 w-4 items-center justify-center rounded-full bg-primary/80 text-[8px] font-bold uppercase text-primary-content"
            :title="participantName(participant)"
          >
            {{ participantInitials(participant) }}
          </span>
          <span v-if="participants.length > visibleParticipants.length">+{{ participants.length - visibleParticipants.length }}</span>
        </span>
        <span class="hidden font-mono text-white/40 sm:inline">{{ annotations.length }} mark{{ annotations.length === 1 ? '' : 's' }}</span>
      </div>
    </div>

    <!-- Text / note editor -->
    <div
      v-if="textDraft"
      class="absolute z-40 w-[min(22rem,calc(100%-1rem))] rounded-xl border border-white/15 bg-[#111827]/98 p-2 text-white shadow-2xl"
      :style="textDraftStyle"
      role="dialog"
      aria-label="Annotation text"
    >
      <div class="mb-1 flex items-center justify-between gap-2 text-[10px] uppercase tracking-wide text-white/50">
        <span>{{ textDraft.tool === 'note' ? 'Sticky note' : 'Text label' }}</span>
        <span class="hidden sm:inline">Ctrl+Enter to save</span>
      </div>
      <textarea
        ref="textInput"
        v-model="textDraft.value"
        rows="3"
        class="textarea textarea-sm w-full resize-y select-text border-white/10 bg-black/30 text-sm text-white placeholder:text-white/30 focus:border-primary"
        :placeholder="textDraft.tool === 'note' ? 'Write a note for the AI…' : 'Write a label…'"
        @keydown.esc.stop.prevent="cancelTextDraft"
        @keydown.ctrl.enter.prevent="saveTextDraft"
        @keydown.meta.enter.prevent="saveTextDraft"
      ></textarea>
      <div class="mt-1 flex items-center justify-between gap-2">
        <span class="flex items-center gap-1 text-[10px] text-white/40">
          <span class="h-2.5 w-2.5 rounded-full" :style="{ backgroundColor: textDraft.color }"></span>
          {{ textDraft.tool === 'note' ? 'Placed on the page' : 'Anchored on the page' }}
        </span>
        <div class="flex gap-1">
          <button class="btn btn-xs btn-ghost text-white/70" @click="cancelTextDraft">Cancel</button>
          <button class="btn btn-xs btn-primary" :disabled="!textDraft.value.trim()" @click="saveTextDraft">
            {{ textDraft.existingId ? 'Save' : 'Place' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Pending image hint -->
    <div
      v-if="pendingImage"
      class="pointer-events-none absolute left-1/2 bottom-16 z-30 -translate-x-1/2 rounded-full bg-primary px-3 py-1 text-xs font-medium text-primary-content shadow-xl"
    >
      Click the page to place “{{ pendingImage.name }}”
    </div>

    <!-- Sending overlay -->
    <div
      v-if="sending"
      class="absolute inset-0 z-50 flex items-center justify-center bg-black/45 backdrop-blur-[1px]"
    >
      <div class="rounded-xl bg-[#111827] px-4 py-3 text-center text-white shadow-2xl">
        <span class="loading loading-spinner loading-md text-primary"></span>
        <p class="mt-2 text-xs text-white/70">Capturing the page and your marks…</p>
      </div>
    </div>

    <!-- Hidden image file input -->
    <input
      ref="imageInput"
      type="file"
      accept="image/*"
      class="hidden"
      @change="onImageFile"
    />
  </div>
</template>

<script>
import {
  ANNOTATION_COLORS,
  ANNOTATION_TOOLS,
  annotationBounds,
  clamp01,
  cloneAnnotations,
  createAnnotation,
  describeAnnotations,
  drawAnnotations,
  findAnnotationAt,
  loadAnnotationImage,
  measureNote,
  pointFromEvent,
  prepareAnnotationImage,
  translateAnnotation
} from '@/utils/browserAnnotations'
import {
  broadcastBrowserCollab,
  getCollabParticipants,
  getCollabClientId,
  onBrowserCollab
} from '@/utils/browserCollab'

const MAX_HISTORY = 40

export default {
  name: 'BrowserAnnotationBoard',
  props: {
    sessionId: { type: String, default: null },
    pageUrl: { type: String, default: '' },
    pageTitle: { type: String, default: '' },
    // Meeting id enables WebRTC data-channel collaboration between call peers.
    meetId: { type: String, default: null },
    // Returns the page background: a data URL, `{ dataUrl, kind }` or null.
    getScreenshot: { type: Function, default: null },
    currentUser: { type: Object, default: null },
    // False while the page is interactive: the board stays mounted (so the
    // drawing survives toggling annotation mode) but stops its presence timer.
    active: { type: Boolean, default: true }
  },
  emits: ['close', 'send', 'change'],
  data() {
    return {
      tools: ANNOTATION_TOOLS,
      palette: ANNOTATION_COLORS,
      tool: 'pen',
      strokeColor: '#ef4444',
      strokeWidth: 4,
      annotations: [],
      activeAnnotation: null,
      selectedId: null,
      textDraft: null,
      pendingImage: null,
      sending: false,
      history: [],
      future: [],
      canvasSize: { width: 0, height: 0 },
      participants: [],
      dragState: null,
      erasing: false,
      erasedIds: new Set(),
      imageCache: new Map(),
      resizeObserver: null,
      redrawFrame: null,
      presenceTimer: null,
      presenceAnnounced: false,
      keyboardHandler: null,
      collabUnsubscribe: null,
      // Toolbar docking / free drag state
      toolbarDock: 'top',
      toolbarPosition: null,
      toolbarDrag: null,
      // Selected-element resize gesture
      resizeState: null
    }
  },
  computed: {
    activeToolLabel() {
      if (this.tool === 'select') return 'Select & move'
      const found = this.tools.find(item => item.id === this.tool)
      return found?.label || 'Annotate'
    },
    cursorClass() {
      if (this.tool === 'select') return 'cursor-move'
      if (this.tool === 'text' || this.tool === 'note') return 'cursor-text'
      if (this.tool === 'eraser') return 'cursor-cell'
      if (this.tool === 'image') return 'cursor-copy'
      return 'cursor-crosshair'
    },
    hint() {
      if (this.pendingImage) return 'Click to place the image. Use Select to move it afterwards.'
      if (this.tool === 'select') return 'Click a mark to select it. Drag to move, Delete to remove.'
      if (this.tool === 'image') return 'Choose an image, then click the page to place it.'
      if (this.tool === 'eraser') return 'Click or drag over a mark to erase it.'
      if (this.tool === 'note' || this.tool === 'text') return 'Click the page to write; the text becomes part of the AI instructions.'
      return 'Draw over the page. The screenshot + marks are sent together to the AI.'
    },
    textDraftStyle() {
      if (!this.textDraft) return {}
      const width = this.canvasSize.width || 800
      const height = this.canvasSize.height || 600
      const left = Math.max(8, Math.min(width - 300, this.textDraft.point.x * width))
      const top = Math.max(8, Math.min(height - 160, this.textDraft.point.y * height))
      return { left: `${left}px`, top: `${top}px` }
    },
    toolbarStyle() {
      if (this.toolbarPosition) {
        return {
          left: `${this.toolbarPosition.x}px`,
          top: `${this.toolbarPosition.y}px`,
          bottom: 'auto',
          transform: 'none'
        }
      }
      if (this.toolbarDock === 'bottom') {
        return {
          left: '50%',
          bottom: '0.5rem',
          top: 'auto',
          transform: 'translateX(-50%)'
        }
      }
      return {
        left: '50%',
        top: '0.5rem',
        bottom: 'auto',
        transform: 'translateX(-50%)'
      }
    },
    selectedAnnotation() {
      if (!this.selectedId) return null
      return this.annotations.find(annotation => annotation.id === this.selectedId) || null
    },
    selectionRect() {
      const annotation = this.selectedAnnotation
      if (!annotation || !this.canvasSize.width || !this.canvasSize.height) return null
      const bounds = annotationBounds(annotation)
      return {
        // Inflate tiny boxes (a straight arrow has zero width/height) so the
        // resize handles never collapse on top of each other.
        x: bounds.x * this.canvasSize.width,
        y: bounds.y * this.canvasSize.height,
        w: Math.max(6, bounds.w * this.canvasSize.width),
        h: Math.max(6, bounds.h * this.canvasSize.height)
      }
    },
    selectionBoxStyle() {
      if (!this.selectionRect) return {}
      const rect = this.selectionRect
      return {
        left: `${rect.x}px`,
        top: `${rect.y}px`,
        width: `${rect.w}px`,
        height: `${rect.h}px`
      }
    },
    selectionHandles() {
      const rect = this.selectionRect
      if (!rect) return []
      const positions = {
        nw: [0, 0, 'cursor-nwse-resize'],
        n: [0.5, 0, 'cursor-ns-resize'],
        ne: [1, 0, 'cursor-nesw-resize'],
        e: [1, 0.5, 'cursor-ew-resize'],
        se: [1, 1, 'cursor-nwse-resize'],
        s: [0.5, 1, 'cursor-ns-resize'],
        sw: [0, 1, 'cursor-nesw-resize'],
        w: [0, 0.5, 'cursor-ew-resize']
      }
      return Object.entries(positions).map(([id, [fx, fy, cursorClass]]) => ({
        id,
        cursorClass,
        style: {
          left: `${rect.x + rect.w * fx}px`,
          top: `${rect.y + rect.h * fy}px`
        }
      }))
    },
    visibleParticipants() {
      return this.participants.slice(0, 4)
    },
    participantTitle() {
      return this.participants.map(item => this.participantName(item)).join(', ')
    }
  },
  watch: {
    annotations() {
      this.$emit('change', { count: this.annotations.length })
    },
    meetId(value, previous) {
      if (value === previous) return
      if (this.collabUnsubscribe) {
        this.collabUnsubscribe()
        this.collabUnsubscribe = null
      }
      this.bindCollaboration()
      this.startPresence()
    },
    active(value) {
      if (value) {
        this.$nextTick(() => {
          this.resizeCanvas()
          this.startPresence()
          this.broadcastCollab({ kind: 'annotation', action: 'sync-request' })
        })
      } else {
        this.stopPresence()
      }
    }
  },
  mounted() {
    this.loadToolbarDock()
    this.bindCollaboration()
    this.observeSize()
    this.startPresence()
    this.keyboardHandler = (event) => this.onKeyDown(event)
    window.addEventListener('keydown', this.keyboardHandler)
  },
  beforeUnmount() {
    if (this.resizeObserver) this.resizeObserver.disconnect()
    if (this.redrawFrame) cancelAnimationFrame(this.redrawFrame)
    this.stopPresence()
    if (this.keyboardHandler) window.removeEventListener('keydown', this.keyboardHandler)
    if (this.windowResizeHandler) window.removeEventListener('resize', this.windowResizeHandler)
    window.removeEventListener('pointermove', this.onToolbarDragMove)
    window.removeEventListener('pointerup', this.endToolbarDrag)
    window.removeEventListener('pointermove', this.onResizeMove)
    window.removeEventListener('pointerup', this.endResize)
    if (this.collabUnsubscribe) this.collabUnsubscribe()
  },
  methods: {
    // ── Collaboration ───────────────────────────────────────────────────────
    bindCollaboration() {
      this.collabUnsubscribe = onBrowserCollab((event) => this.onCollabEvent(event))
      if (!this.meetId) return
      // A local sync request is answered by every peer already drawing on this
      // session, so a participant who opens the board later catches up.
      if (this.active) {
        this.$nextTick(() => {
          this.broadcastCollab({ kind: 'annotation', action: 'sync-request' })
        })
      }
    },
    startPresence() {
      this.stopPresence()
      if (!this.active) {
        this.participants = []
        return
      }
      if (!this.meetId) {
        this.participants = []
        return
      }
      this.publishPresence()
      this.presenceTimer = setInterval(() => this.publishPresence(), 15000)
      this.refreshParticipants()
    },
    stopPresence() {
      if (this.presenceTimer) clearInterval(this.presenceTimer)
      this.presenceTimer = null
    },
    currentUserInfo() {
      const user = this.currentUser || this.$storex?.users?.user || {}
      return {
        username: user.username || 'guest',
        name: user.name || user.username || 'Guest',
        avatar: user.avatar || ''
      }
    },
    publishPresence() {
      if (!this.meetId || !this.active) return
      broadcastBrowserCollab(this.meetId, {
        kind: 'presence',
        sessionId: this.sessionId,
        user: this.currentUserInfo(),
        pageUrl: this.pageUrl,
        annotating: true
      })
      this.refreshParticipants()
    },
    refreshParticipants() {
      if (!this.meetId) return
      this.participants = getCollabParticipants(this.meetId)
        .filter(item => !item.sessionId || item.sessionId === this.sessionId)
        .filter(item => item.clientId !== getCollabClientId())
    },
    onCollabEvent(event) {
      if (!event) return
      if (event.sessionId && this.sessionId && event.sessionId !== this.sessionId) return
      if (event.kind === 'presence') {
        this.refreshParticipants()
        return
      }
      if (event.kind !== 'annotation') return
      const remoteAuthor = event.user?.name || event.user?.username || 'A participant'
      switch (event.action) {
        case 'sync-request':
          this.sendAnnotationState()
          break
        case 'state':
          this.applyRemoteState(event.ops, remoteAuthor, { replace: event.replace === true })
          break
        case 'add':
          this.applyRemoteAdd(event.op, remoteAuthor)
          break
        case 'update':
          this.applyRemoteUpdate(event.op)
          break
        case 'remove':
          this.applyRemoteRemove(event.id)
          break
        default:
          break
      }
      this.refreshParticipants()
    },
    applyRemoteAdd(annotation, author) {
      if (!annotation?.id || this.annotations.some(item => item.id === annotation.id)) return
      const op = { ...annotation, author: annotation.author || author, remote: true }
      this.annotations = [...this.annotations, op]
      this.prepareOpImages(op)
      this.redraw()
    },
    applyRemoteUpdate(annotation) {
      if (!annotation?.id) return
      this.annotations = this.annotations.map(item => (
        item.id === annotation.id ? { ...annotation, remote: true } : item
      ))
      this.prepareOpImages(annotation)
      this.redraw()
    },
    applyRemoteRemove(id) {
      if (!id) return
      this.annotations = this.annotations.filter(item => item.id !== id)
      if (this.selectedId === id) this.selectedId = null
      this.imageCache.delete(id)
      this.redraw()
    },
    applyRemoteState(ops, author, { replace = false } = {}) {
      if (!Array.isArray(ops)) return
      const byId = replace ? new Map() : new Map(this.annotations.map(item => [item.id, item]))
      ops.forEach((annotation) => {
        if (!annotation?.id) return
        byId.set(annotation.id, {
          ...annotation,
          author: annotation.author || author,
          remote: true
        })
        this.prepareOpImages(annotation)
      })
      this.annotations = Array.from(byId.values())
      if (replace) {
        this.selectedId = null
        this.imageCache.clear()
        this.prepareAllImages()
      }
      this.redraw()
    },
    broadcastCollab(payload) {
      broadcastBrowserCollab(this.meetId, {
        sessionId: this.sessionId,
        user: this.currentUserInfo(),
        ...payload
      })
    },
    sendAnnotationState({ replace = false } = {}) {
      this.broadcastCollab({
        kind: 'annotation',
        action: 'state',
        replace,
        ops: cloneAnnotations(this.annotations)
      })
    },
    broadcastAdd(annotation) {
      this.broadcastCollab({ kind: 'annotation', action: 'add', op: annotation })
    },
    broadcastRemove(annotation) {
      this.broadcastCollab({ kind: 'annotation', action: 'remove', id: annotation.id })
    },
    broadcastUpdate(annotation) {
      this.broadcastCollab({ kind: 'annotation', action: 'update', op: annotation })
    },

    // ── Canvas sizing / rendering ───────────────────────────────────────────
    observeSize() {
      const element = this.$refs.canvas?.parentElement
      if (!element) return
      const update = () => this.resizeCanvas()
      if (typeof ResizeObserver !== 'undefined') {
        this.resizeObserver = new ResizeObserver(update)
        this.resizeObserver.observe(element)
      }
      window.addEventListener('resize', update)
      this.windowResizeHandler = update
      this.$nextTick(update)
    },
    resizeCanvas() {
      const canvas = this.$refs.canvas
      const parent = canvas?.parentElement
      if (!canvas || !parent) return
      const rect = parent.getBoundingClientRect()
      // Hidden board (v-show while interacting with the page): keep the last
      // size and toolbar position instead of collapsing everything to 1×1.
      if (rect.width < 2 || rect.height < 2) return
      const width = Math.max(1, Math.round(rect.width))
      const height = Math.max(1, Math.round(rect.height))
      const dpr = Math.min(window.devicePixelRatio || 1, 2.5)
      if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
        canvas.width = Math.round(width * dpr)
        canvas.height = Math.round(height * dpr)
      }
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      if (this.canvasSize.width !== width || this.canvasSize.height !== height) {
        this.canvasSize = { width, height }
      }
      this.$nextTick(() => this.clampToolbarPosition())
      this.redraw()
    },
    redraw() {
      if (this.redrawFrame) return
      this.redrawFrame = requestAnimationFrame(() => {
        this.redrawFrame = null
        const canvas = this.$refs.canvas
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        const dpr = Math.min(window.devicePixelRatio || 1, 2.5)
        const width = canvas.width / dpr
        const height = canvas.height / dpr
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
        ctx.clearRect(0, 0, width, height)
        const all = this.activeAnnotation
          ? [...this.annotations, this.activeAnnotation]
          : this.annotations
        drawAnnotations(ctx, all, width, height, this.imageCache, null)
      })
    },
    prepareOpImages(annotation) {
      if (annotation?.tool !== 'image' || !annotation.src || this.imageCache.has(annotation.id)) return
      loadAnnotationImage(annotation)
        .then((image) => {
          this.imageCache.set(annotation.id, image)
          this.redraw()
        })
        .catch(() => { /* keep the placeholder */ })
    },

    // ── Toolbar / tools ─────────────────────────────────────────────────────
    selectTool(tool) {
      // Switching tools commits an in-progress note instead of silently
      // dropping what the user typed.
      if (this.textDraft) {
        if (this.textDraft.value?.trim()) this.saveTextDraft()
        else this.textDraft = null
      }
      if (tool === 'image') {
        this.pickImage()
        return
      }
      this.pendingImage = null
      this.tool = tool
      if (tool !== 'select') this.selectedId = null
      if (tool !== 'text' && tool !== 'note') this.textDraft = null
      this.redraw()
    },
    chooseColor(color) {
      this.strokeColor = color
      if (this.textDraft) this.textDraft.color = color
    },

    // ── Movable / dockable toolbar ─────────────────────────────────────────
    loadToolbarDock() {
      try {
        const saved = localStorage.getItem('codx-browser-annotations-toolbar-dock')
        this.toolbarDock = saved === 'bottom' ? 'bottom' : 'top'
      } catch (e) {
        this.toolbarDock = 'top'
      }
    },
    saveToolbarDock() {
      try {
        localStorage.setItem('codx-browser-annotations-toolbar-dock', this.toolbarDock)
      } catch (e) {
        // storage is optional
      }
    },
    toggleToolbarDock() {
      this.toolbarDock = this.toolbarDock === 'bottom' ? 'top' : 'bottom'
      this.toolbarPosition = null
      this.saveToolbarDock()
      this.$nextTick(() => this.redraw())
    },
    startToolbarDrag(event) {
      if (event.button !== undefined && event.button !== 0) return
      const toolbarElement = this.$refs.toolbar
      const boardElement = this.$el
      if (!toolbarElement || !boardElement) return
      const toolbar = toolbarElement.getBoundingClientRect()
      const board = boardElement.getBoundingClientRect()
      if (!toolbar.width || !toolbar.height || !board.width) return
      this.toolbarPosition = {
        x: Math.max(0, Math.min(board.width - toolbar.width, toolbar.left - board.left)),
        y: Math.max(0, Math.min(board.height - toolbar.height, toolbar.top - board.top))
      }
      this.toolbarDrag = {
        startX: event.clientX,
        startY: event.clientY,
        x: this.toolbarPosition.x,
        y: this.toolbarPosition.y,
        width: toolbar.width,
        height: toolbar.height,
        boardWidth: board.width,
        boardHeight: board.height
      }
      event.currentTarget?.setPointerCapture?.(event.pointerId)
      window.addEventListener('pointermove', this.onToolbarDragMove)
      window.addEventListener('pointerup', this.endToolbarDrag)
    },
    onToolbarDragMove(event) {
      const drag = this.toolbarDrag
      if (!drag) return
      const x = drag.x + (event.clientX - drag.startX)
      const y = drag.y + (event.clientY - drag.startY)
      this.toolbarPosition = {
        x: Math.max(0, Math.min(drag.boardWidth - drag.width, x)),
        y: Math.max(0, Math.min(drag.boardHeight - drag.height, y))
      }
    },
    endToolbarDrag() {
      this.toolbarDrag = null
      window.removeEventListener('pointermove', this.onToolbarDragMove)
      window.removeEventListener('pointerup', this.endToolbarDrag)
    },
    clampToolbarPosition() {
      if (!this.toolbarPosition) return
      const toolbar = this.$refs.toolbar?.getBoundingClientRect()
      const board = this.$el?.getBoundingClientRect()
      if (!toolbar || !board) return
      this.toolbarPosition = {
        x: Math.max(0, Math.min(board.width - toolbar.width, this.toolbarPosition.x)),
        y: Math.max(0, Math.min(board.height - toolbar.height, this.toolbarPosition.y))
      }
    },
    pickImage() {
      this.$refs.imageInput?.click()
    },
    async onImageFile(event) {
      const file = event.target?.files?.[0]
      event.target.value = ''
      if (!file) return
      try {
        this.pendingImage = await prepareAnnotationImage(file)
        this.tool = 'image'
      } catch (error) {
        this.notify('error', error.message || 'Could not read the image')
      }
    },
    async onDropImage(event) {
      const file = [...(event.dataTransfer?.files || [])].find(item => item.type.startsWith('image/'))
      if (!file) return
      try {
        this.pendingImage = await prepareAnnotationImage(file)
        this.tool = 'image'
      } catch (error) {
        this.notify('error', error.message || 'Could not read the image')
      }
    },

    // ── Pointer handling ────────────────────────────────────────────────────
    canvasPoint(event) {
      const rect = this.$refs.canvas?.getBoundingClientRect()
      return pointFromEvent(event, rect)
    },
    onPointerDown(event) {
      if (event.button !== undefined && event.button !== 0) return
      const point = this.canvasPoint(event)
      this.$refs.canvas?.setPointerCapture?.(event.pointerId)

      if (this.textDraft) {
        this.saveTextDraft()
        return
      }
      if (this.tool === 'image') {
        if (this.pendingImage) this.placeImage(point)
        else this.pickImage()
        return
      }
      if (this.tool === 'eraser') {
        this.beginErase(point)
        return
      }
      if (this.tool === 'select') {
        this.beginSelect(point)
        return
      }
      if (this.tool === 'text' || this.tool === 'note') {
        this.openTextDraft(point, this.tool)
        return
      }
      this.activeAnnotation = createAnnotation({
        tool: this.tool,
        point,
        color: this.strokeColor,
        width: this.strokeWidth,
        author: this.currentUserInfo().name
      })
      this.redraw()
    },
    onPointerMove(event) {
      if (!this.activeAnnotation && !this.dragState && !this.erasing) return
      const point = this.canvasPoint(event)
      if (this.erasing) {
        this.eraseAt(point)
        return
      }
      if (this.dragState) {
        const dx = point.x - this.dragState.start.x
        const dy = point.y - this.dragState.start.y
        if (Math.abs(dx) > 0.0005 || Math.abs(dy) > 0.0005) {
          const moved = translateAnnotation(this.dragState.original, dx, dy)
          this.annotations = this.annotations.map(item => (item.id === moved.id ? moved : item))
          this.redraw()
        }
        return
      }
      if (!this.activeAnnotation) return
      const annotation = this.activeAnnotation
      if (annotation.tool === 'pen' || annotation.tool === 'marker') {
        const points = annotation.points
        const last = points[points.length - 1]
        if (!last || Math.hypot(point.x - last.x, point.y - last.y) > 0.0015) {
          points.push(point)
        }
      } else if (annotation.tool === 'arrow') {
        annotation.points[1] = point
      } else if (annotation.tool === 'rect' || annotation.tool === 'ellipse') {
        annotation.w = point.x - annotation.x
        annotation.h = point.y - annotation.y
      }
      this.redraw()
    },
    onPointerUp(event) {
      try {
        this.$refs.canvas?.releasePointerCapture?.(event?.pointerId)
      } catch (e) {
        // The capture may already be gone after a browser gesture.
      }
      if (this.erasing) {
        this.erasing = false
        this.erasedIds.clear()
        return
      }
      if (this.dragState) {
        const selected = this.annotations.find(item => item.id === this.dragState.id)
        if (selected) this.broadcastUpdate(selected)
        this.dragState = null
        return
      }
      if (!this.activeAnnotation) return
      const annotation = this.finishAnnotation(this.activeAnnotation)
      this.activeAnnotation = null
      if (annotation) this.addAnnotation(annotation)
      this.redraw()
    },
    onPointerLeave() {
      // Pointer capture keeps delivering pointermove/up outside the canvas, so
      // leaving the element must not finish the stroke.
    },
    finishAnnotation(annotation) {
      if (annotation.tool === 'rect' || annotation.tool === 'ellipse') {
        const x = annotation.x
        const y = annotation.y
        const w = annotation.w || 0
        const h = annotation.h || 0
        if (Math.abs(w) < 0.005 || Math.abs(h) < 0.005) return null
        annotation.x = Math.min(x, x + w)
        annotation.y = Math.min(y, y + h)
        annotation.w = Math.abs(w)
        annotation.h = Math.abs(h)
        return annotation
      }
      if (annotation.tool === 'arrow') {
        const [start, end] = annotation.points || []
        if (!start || !end || Math.hypot(end.x - start.x, end.y - start.y) < 0.008) return null
        return annotation
      }
      const points = annotation.points || []
      if (points.length < 2) {
        const only = points[0]
        if (!only) return null
        annotation.points = [only, { x: only.x + 0.0001, y: only.y + 0.0001 }]
      }
      return annotation
    },
    addAnnotation(annotation) {
      this.pushHistory()
      this.annotations = [...this.annotations, annotation]
      this.prepareOpImages(annotation)
      this.broadcastAdd(annotation)
      this.redraw()
    },
    replaceAnnotation(annotation) {
      this.annotations = this.annotations.map(item => (item.id === annotation.id ? annotation : item))
    },

    // ── Select / move / erase ───────────────────────────────────────────────
    beginSelect(point) {
      const hit = findAnnotationAt(this.annotations, point)
      if (!hit) {
        this.selectedId = null
        this.redraw()
        return
      }
      this.selectedId = hit.id
      this.dragState = {
        id: hit.id,
        start: point,
        original: cloneAnnotations([hit])[0]
      }
      this.pushHistory()
      this.redraw()
    },
    beginErase(point) {
      this.pushHistory()
      this.erasing = true
      this.erasedIds = new Set()
      this.eraseAt(point)
    },
    eraseAt(point) {
      const hit = findAnnotationAt(this.annotations, point, 0.016)
      if (!hit || this.erasedIds.has(hit.id)) return
      this.erasedIds.add(hit.id)
      this.annotations = this.annotations.filter(item => item.id !== hit.id)
      this.imageCache.delete(hit.id)
      this.broadcastRemove(hit)
      this.redraw()
    },
    deleteSelected() {
      if (!this.selectedId) return
      const annotation = this.annotations.find(item => item.id === this.selectedId)
      if (!annotation) return
      this.pushHistory()
      this.annotations = this.annotations.filter(item => item.id !== this.selectedId)
      this.imageCache.delete(this.selectedId)
      this.selectedId = null
      this.broadcastRemove(annotation)
      this.redraw()
    },

    // ── Resize selected element ─────────────────────────────────────────────
    startResize(handle, event) {
      if (!this.selectedAnnotation || this.tool !== 'select') return
      this.pushHistory()
      this.resizeState = {
        handle,
        original: cloneAnnotations([this.selectedAnnotation])[0],
        box: annotationBounds(this.selectedAnnotation)
      }
      event.currentTarget?.setPointerCapture?.(event.pointerId)
      window.addEventListener('pointermove', this.onResizeMove)
      window.addEventListener('pointerup', this.endResize)
    },
    onResizeMove(event) {
      if (!this.resizeState) return
      const point = this.canvasPoint(event)
      const box = this.computeResizedBox(this.resizeState.box, this.resizeState.handle, point)
      const next = this.resizeAnnotationToBox(this.resizeState.original, this.resizeState.box, box)
      this.annotations = this.annotations.map(annotation => (
        annotation.id === next.id ? next : annotation
      ))
      this.redraw()
    },
    endResize() {
      if (this.resizeState) {
        const selected = this.annotations.find(annotation => annotation.id === this.selectedId)
        if (selected) this.broadcastUpdate(selected)
      }
      this.resizeState = null
      window.removeEventListener('pointermove', this.onResizeMove)
      window.removeEventListener('pointerup', this.endResize)
    },
    /** New normalized box for a corner/edge handle. */
    computeResizedBox(box, handle, point) {
      const minSize = 0.008
      let x = box.x
      let y = box.y
      let w = Math.max(box.w, minSize)
      let h = Math.max(box.h, minSize)
      const right = x + w
      const bottom = y + h
      if (handle.includes('w')) {
        x = Math.min(Math.max(point.x, 0), right - minSize)
        w = right - x
      } else if (handle.includes('e')) {
        const nextRight = Math.max(Math.min(point.x, 1), x + minSize)
        w = nextRight - x
      }
      if (handle.includes('n')) {
        y = Math.min(Math.max(point.y, 0), bottom - minSize)
        h = bottom - y
      } else if (handle.includes('s')) {
        const nextBottom = Math.max(Math.min(point.y, 1), y + minSize)
        h = nextBottom - y
      }
      return { x, y, w, h }
    },
    /** Apply a new box to any kind of mark (shapes, images, strokes, text). */
    resizeAnnotationToBox(original, from, to) {
      const next = { ...original }
      if (original.points) {
        const scaleX = from.w > 0 ? to.w / from.w : 1
        const scaleY = from.h > 0 ? to.h / from.h : 1
        next.points = original.points.map(point => ({
          x: clamp01(to.x + (point.x - from.x) * scaleX),
          y: clamp01(to.y + (point.y - from.y) * scaleY)
        }))
        return next
      }
      if (original.tool === 'text') {
        const scale = from.h > 0 ? to.h / from.h : (from.w > 0 ? to.w / from.w : 1)
        next.x = clamp01(to.x)
        next.y = clamp01(to.y)
        next.w = clamp01(to.w)
        next.h = clamp01(to.h)
        next.fontSize = Math.max(8, Math.min(240, (original.fontSize || 18) * scale))
        return next
      }
      next.x = clamp01(to.x)
      next.y = clamp01(to.y)
      next.w = clamp01(to.w)
      next.h = clamp01(to.h)
      return next
    },

    // ── Text / notes ────────────────────────────────────────────────────────
    openTextDraft(point, tool, existing = null) {
      this.textDraft = {
        point: { ...point },
        tool,
        color: existing?.color || this.strokeColor,
        value: existing?.text || '',
        existingId: existing?.id || null
      }
      this.$nextTick(() => this.$refs.textInput?.focus())
    },
    saveTextDraft() {
      if (!this.textDraft) return
      const value = this.textDraft.value.trim()
      if (!value) {
        this.cancelTextDraft()
        return
      }
      const draft = this.textDraft
      if (draft.existingId) {
        const existing = this.annotations.find(item => item.id === draft.existingId)
        if (existing) {
          this.pushHistory()
          const next = { ...existing, text: value, color: draft.color }
          this.replaceAnnotation(next)
          this.broadcastUpdate(next)
        }
        this.textDraft = null
        this.redraw()
        return
      }
      const annotation = createAnnotation({
        tool: draft.tool,
        point: draft.point,
        color: draft.color,
        width: this.strokeWidth,
        text: value,
        author: this.currentUserInfo().name
      })
      if (draft.tool === 'note') {
        const ctx = this.$refs.canvas?.getContext('2d')
        if (ctx && this.canvasSize.width && this.canvasSize.height) {
          const metrics = measureNote(ctx, annotation, this.canvasSize.width, this.canvasSize.height)
          annotation.w = metrics.width / this.canvasSize.width
          annotation.h = metrics.height / this.canvasSize.height
        } else {
          annotation.h = 0.16
        }
      } else {
        const lines = String(value).split(/\r?\n/)
        const lineHeight = 18 * 1.3
        annotation.h = Math.min(1, (lines.length * lineHeight) / (this.canvasSize.height || 720))
      }
      // Keep the whole note/label on screen even when it was placed near an
      // edge; the AI receives the same coordinates the user sees.
      annotation.x = Math.max(0, Math.min(annotation.x, 1 - (annotation.w || 0)))
      annotation.y = Math.max(0, Math.min(annotation.y, 1 - (annotation.h || 0)))
      this.textDraft = null
      this.addAnnotation(annotation)
    },
    cancelTextDraft() {
      this.textDraft = null
    },
    onDoubleClick(event) {
      const point = this.canvasPoint(event)
      const hit = findAnnotationAt(this.annotations, point)
      if (hit && (hit.tool === 'text' || hit.tool === 'note')) {
        this.tool = hit.tool
        this.openTextDraft({ x: hit.x, y: hit.y }, hit.tool, hit)
      }
    },

    // ── Images ──────────────────────────────────────────────────────────────
    placeImage(point) {
      const pending = this.pendingImage
      if (!pending) return
      const canvasAspect = (this.canvasSize.width || 16) / (this.canvasSize.height || 9)
      const imageAspect = pending.width / pending.height
      let w = 0.3
      let h = (w * canvasAspect) / imageAspect
      if (h > 0.55) {
        h = 0.55
        w = (h * imageAspect) / canvasAspect
      }
      const x = Math.max(0, Math.min(1 - w, point.x - w / 2))
      const y = Math.max(0, Math.min(1 - h, point.y - h / 2))
      const annotation = createAnnotation({
        tool: 'image',
        point: { x, y },
        color: this.strokeColor,
        width: this.strokeWidth,
        w,
        h,
        src: pending.src,
        name: pending.name,
        author: this.currentUserInfo().name
      })
      this.pendingImage = null
      this.tool = 'select'
      this.selectedId = annotation.id
      this.addAnnotation(annotation)
    },

    // ── History ─────────────────────────────────────────────────────────────
    pushHistory() {
      this.history = [...this.history.slice(-(MAX_HISTORY - 1)), cloneAnnotations(this.annotations)]
      this.future = []
    },
    undo() {
      if (!this.history.length) return
      const previous = this.history[this.history.length - 1]
      this.future = [...this.future, cloneAnnotations(this.annotations)]
      this.history = this.history.slice(0, -1)
      this.annotations = previous
      this.selectedId = null
      this.imageCache.clear()
      this.prepareAllImages()
      this.sendAnnotationState({ replace: true })
      this.redraw()
    },
    redo() {
      if (!this.future.length) return
      const next = this.future[this.future.length - 1]
      this.future = this.future.slice(0, -1)
      this.history = [...this.history, cloneAnnotations(this.annotations)]
      this.annotations = next
      this.selectedId = null
      this.imageCache.clear()
      this.prepareAllImages()
      this.sendAnnotationState({ replace: true })
      this.redraw()
    },
    clearAll() {
      if (!this.annotations.length) return
      this.pushHistory()
      this.annotations = []
      this.selectedId = null
      this.imageCache.clear()
      this.sendAnnotationState({ replace: true })
      this.redraw()
    },
    prepareAllImages() {
      this.annotations.forEach(annotation => this.prepareOpImages(annotation))
    },

    // ── Keyboard ────────────────────────────────────────────────────────────
    onKeyDown(event) {
      if (!this.active) return
      const tag = String(event.target?.tagName || '').toLowerCase()
      if (tag === 'input' || tag === 'textarea' || event.target?.isContentEditable) return
      if (event.key === 'Escape') {
        if (this.textDraft) {
          this.cancelTextDraft()
        } else if (this.pendingImage) {
          this.pendingImage = null
          this.tool = 'pen'
        } else {
          this.$emit('close')
        }
        return
      }
      const mod = event.ctrlKey || event.metaKey
      if (mod && event.key.toLowerCase() === 'z') {
        event.preventDefault()
        if (event.shiftKey) this.redo()
        else this.undo()
        return
      }
      if (mod && event.key.toLowerCase() === 'y') {
        event.preventDefault()
        this.redo()
        return
      }
      if (event.key === 'Delete' || event.key === 'Backspace') {
        if (this.selectedId) {
          event.preventDefault()
          this.deleteSelected()
        }
        return
      }
      if (mod || event.altKey) return
      const shortcuts = {
        v: 'select',
        p: 'pen',
        h: 'marker',
        a: 'arrow',
        r: 'rect',
        o: 'ellipse',
        n: 'note',
        t: 'text',
        x: 'eraser'
      }
      const tool = shortcuts[event.key.toLowerCase()]
      if (tool) {
        this.selectTool(tool)
      }
    },

    // ── Export / send to chat ───────────────────────────────────────────────
    /** Make sure every inserted image completed loading before an export. */
    async ensureImagesLoaded() {
      const pending = this.annotations.filter(annotation => (
        annotation.tool === 'image' && annotation.src && !this.imageCache.has(annotation.id)
      ))
      await Promise.allSettled(pending.map(annotation => (
        loadAnnotationImage(annotation)
          .then((image) => { this.imageCache.set(annotation.id, image) })
          .catch(() => { /* keep the placeholder */ })
      )))
    },
    async resolveBackground() {
      if (!this.getScreenshot) return { dataUrl: null, kind: 'none' }
      try {
        const result = await this.getScreenshot()
        if (!result) return { dataUrl: null, kind: 'none' }
        if (typeof result === 'string') return { dataUrl: result, kind: 'page' }
        return {
          dataUrl: result.dataUrl || null,
          kind: result.kind || (result.dataUrl ? 'page' : 'none')
        }
      } catch (error) {
        console.warn('[BrowserAnnotationBoard] Background capture failed', error)
        return { dataUrl: null, kind: 'error' }
      }
    },
    loadImage(dataUrl) {
      return new Promise((resolve, reject) => {
        if (!dataUrl) {
          resolve(null)
          return
        }
        const image = new Image()
        image.onload = () => resolve(image)
        image.onerror = () => reject(new Error('Could not load the page capture'))
        image.src = dataUrl
      })
    },
    async renderComposite(background) {
      let width = Math.max(640, Math.round((this.canvasSize.width || 1280) * 2))
      let height = Math.max(360, Math.round((this.canvasSize.height || 720) * 2))
      let image = null
      if (background?.dataUrl) {
        try {
          image = await this.loadImage(background.dataUrl)
          if (image?.naturalWidth) {
            width = image.naturalWidth
            height = image.naturalHeight
          }
        } catch (error) {
          image = null
        }
      }

      // A 4K live frame produces an unnecessarily large PNG. Keep the export
      // under 2048 px on the long edge; annotations are normalized, so they
      // scale with the background.
      const maxDimension = 2048
      if (width > maxDimension || height > maxDimension) {
        const scale = maxDimension / Math.max(width, height)
        width = Math.max(1, Math.round(width * scale))
        height = Math.max(1, Math.round(height * scale))
      }

      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')
      if (image) {
        ctx.drawImage(image, 0, 0, width, height)
      } else {
        // No page capture: still produce a legible background so the marks and
        // the page URL reach the model even when the browser view is protected.
        const gradient = ctx.createLinearGradient(0, 0, width, height)
        gradient.addColorStop(0, '#0f172a')
        gradient.addColorStop(1, '#1e293b')
        ctx.fillStyle = gradient
        ctx.fillRect(0, 0, width, height)
        ctx.fillStyle = 'rgba(255, 255, 255, 0.75)'
        ctx.font = `600 ${Math.max(14, Math.round(height * 0.028))}px Inter, system-ui, sans-serif`
        ctx.fillText('Annotated browser instructions', Math.round(width * 0.03), Math.round(height * 0.07))
        ctx.fillStyle = 'rgba(148, 163, 184, 0.9)'
        ctx.font = `400 ${Math.max(11, Math.round(height * 0.018))}px Inter, system-ui, sans-serif`
        const subtitle = this.pageUrl || 'Live page capture unavailable'
        ctx.fillText(subtitle.slice(0, 140), Math.round(width * 0.03), Math.round(height * 0.11))
      }

      drawAnnotations(ctx, this.annotations, width, height, this.imageCache, null)

      ctx.save()
      ctx.fillStyle = 'rgba(15, 23, 42, 0.55)'
      ctx.font = `500 ${Math.max(10, Math.round(height * 0.014))}px Inter, system-ui, sans-serif`
      ctx.textAlign = 'right'
      ctx.textBaseline = 'bottom'
      ctx.fillText('codx-junior · browser annotations', width - Math.round(width * 0.015), height - Math.round(height * 0.012))
      ctx.restore()

      return canvas.toDataURL('image/png')
    },
    async sendToChat() {
      if (this.sending) return
      // A text being typed is still a mark: commit it before capturing.
      if (this.textDraft?.value?.trim()) this.saveTextDraft()
      else if (this.textDraft) this.textDraft = null
      if (!this.annotations.length) return
      this.sending = true
      try {
        await this.ensureImagesLoaded()
        const background = await this.resolveBackground()
        const dataUrl = await this.renderComposite(background)
        const summary = describeAnnotations(this.annotations).join('\n')
        this.$emit('send', {
          dataUrl,
          summary,
          annotations: cloneAnnotations(this.annotations),
          pageUrl: this.pageUrl,
          pageTitle: this.pageTitle,
          count: this.annotations.length,
          captureKind: background?.kind || 'none',
          sessionId: this.sessionId
        })
      } catch (error) {
        console.error('[BrowserAnnotationBoard] Could not prepare annotations', error)
        this.notify('error', error.message || 'Could not prepare the annotated screenshot')
      } finally {
        this.sending = false
      }
    },
    notify(type, text) {
      this.$storex?.ui?.addNotification?.({ type, text })
    },
    participantName(participant) {
      return participant?.user?.name || participant?.user?.username || 'Participant'
    },
    participantInitials(participant) {
      const name = this.participantName(participant)
      return name.split(/\s+/).map(part => part[0]).join('').slice(0, 2)
    }
  }
}
</script>
