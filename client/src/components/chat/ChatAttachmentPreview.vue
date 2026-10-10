<script setup>
import ChatAttachment from '@/api/model/ChatAttachment.js'
</script>

<template>
  <div class="flex flex-col gap-2 bg-base-200/50 rounded-lg p-3 border border-base-100">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <i class="fa-solid fa-paperclip text-primary text-sm"></i>
        <span class="font-medium text-xs">Attachments</span>
        <span class="badge badge-xs badge-ghost">{{ fileObjects.length }}</span>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="fileObjects.length === 0" class="text-xs text-base-content/50 text-center py-3">
      No attachments
    </div>

    <!-- Thumbnail Grid -->
    <div v-else class="flex gap-2 overflow-x-auto pb-1">
      <div
        v-for="(attachment, idx) in fileObjects"
        :key="idx"
        class="relative group flex-shrink-0 cursor-pointer"
        @click="openPreview(idx)"
        @mouseenter="onThumbHover(attachment, $event)"
        @mouseleave="onThumbLeave"
      >
        <!-- Thumbnail Container -->
        <div class="w-12 h-12 rounded-lg overflow-hidden border border-base-100 bg-base-100 flex items-center justify-center hover:border-primary transition-colors">
          <!-- Image Thumbnail -->
          <img
            v-if="attachment.isImage()"
            :src="`data:${attachment.file_type};base64,${attachment.base64_data}`"
            :alt="attachment.file_name"
            class="w-full h-full object-cover"
          />

          <!-- File Icon Thumbnail -->
          <div v-else class="w-full h-full bg-gradient-to-br from-base-200 to-base-300 flex flex-col items-center justify-center gap-1">
            <i :class="getFileIcon(attachment)" class="text-3xl opacity-60"></i>
            <span class="text-xs font-medium text-base-content/60">{{ attachment.getExtension().toUpperCase() }}</span>
          </div>
        </div>

        <!-- Filename tooltip — images use the floating 3x preview instead -->
        <div
          v-if="!attachment.isImage()"
          class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-base-900 text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10"
        >
          {{ attachment.file_name }}
        </div>
      </div>
    </div>

    <!-- Summary -->
    <div v-if="fileObjects.length > 0" class="text-xs text-base-content/60 border-t border-base-100/50 pt-2 mt-1">
      Total: <span class="font-semibold text-base-content">{{ getTotalSize() }}</span>
    </div>
  </div>

  <!-- Floating 3x image preview — follows the hovered thumbnail.
       Teleported to <body> so the grid's `overflow-x-auto` never clips it. -->
  <teleport to="body">
    <div
      v-if="hoverPreview"
      class="fixed z-50 w-36 pointer-events-none"
      :style="{ left: hoverPreview.left + 'px', top: hoverPreview.top + 'px' }"
    >
      <div class="relative w-36 h-36 rounded-lg border border-primary/40 bg-base-100 shadow-2xl overflow-hidden">
        <img
          :src="`data:${hoverPreview.attachment.file_type};base64,${hoverPreview.attachment.base64_data}`"
          :alt="hoverPreview.attachment.file_name"
          class="w-full h-full object-contain"
        />
        <div class="absolute inset-x-0 bottom-0 px-1.5 py-1 bg-base-300/80 text-[10px] text-base-content/80 truncate">
          {{ hoverPreview.attachment.file_name }}
        </div>
      </div>
    </div>
  </teleport>

  <!-- Preview Modal -->
  <modal
    v-if="selectedIndex !== null && showModal"
    :close="true"
    @close="closePreview"
    class="w-full max-w-2xl"
  >
    <template #title>
      <div class="flex items-center gap-2">
        <i :class="getFileIcon(currentAttachment)" class="text-lg"></i>
        <span>{{ currentAttachment.file_name }}</span>
      </div>
    </template>

    <!-- Preview Content -->
    <div class="flex flex-col gap-4">
      <template v-if="currentAttachment.isImage()">
        <!-- Image header: zoom (view tool) + edit toggle live here -->
        <div class="flex items-center justify-between gap-2">
          <span class="text-xs font-semibold uppercase tracking-wide text-base-content/50">Image Preview</span>
          <div class="flex items-center gap-2">
            <!-- Zoom -->
            <div class="join">
              <button class="btn btn-xs btn-outline join-item" @click="zoomImageEditor(-0.1)" title="Zoom out">
                <i class="fa-solid fa-magnifying-glass-minus"></i>
              </button>
              <span class="btn btn-xs btn-outline join-item pointer-events-none">{{ Math.round(editZoom * 100) }}%</span>
              <button class="btn btn-xs btn-outline join-item" @click="zoomImageEditor(0.1)" title="Zoom in">
                <i class="fa-solid fa-magnifying-glass-plus"></i>
              </button>
            </div>

            <button
              v-if="!editControlsVisible"
              class="btn btn-xs btn-outline"
              @click="showEditControls"
            >
              <i class="fa-solid fa-pen"></i> Edit
            </button>
            <button
              v-else
              class="btn btn-xs btn-ghost"
              @click="hideEditControls"
            >
              <i class="fa-solid fa-xmark"></i> Done
            </button>
          </div>
        </div>

        <!-- Editable image canvas: fixed viewport, centered, scrollable on overflow -->
        <div class="bg-base-200/60 rounded-lg overflow-auto h-96 w-full flex">
          <div class="relative m-auto shrink-0">
            <canvas
              ref="imageEditCanvas"
              class="max-w-none select-none"
              :class="cropEnabled ? 'cursor-crosshair' : ''"
              @mousedown.prevent="startCrop"
            ></canvas>
            <div
              v-if="cropEnabled"
              class="absolute border-2 border-primary bg-primary/20 pointer-events-none"
              :style="cropOverlayStyle"
            ></div>
          </div>
        </div>

        <p v-if="cropEnabled" class="text-xs text-base-content/50 text-center">
          Drag on the image to select the crop area
        </p>

        <!-- Image tools: all editing controls live here -->
        <div v-if="editControlsVisible" class="p-3 bg-base-200/50 rounded-lg flex flex-col gap-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold uppercase tracking-wide">Image Tools</span>
            <button class="btn btn-xs btn-ghost" @click="resetImageEditor">
              <i class="fa-solid fa-rotate"></i> Reset
            </button>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <button class="btn btn-xs btn-outline" @click="rotateImageEditor(-90)" title="Rotate left">
              <i class="fa-solid fa-rotate-left"></i> Rotate Left
            </button>
            <button class="btn btn-xs btn-outline" @click="rotateImageEditor(90)" title="Rotate right">
              <i class="fa-solid fa-rotate-right"></i> Rotate Right
            </button>
            <button
              class="btn btn-xs"
              :class="cropEnabled ? 'btn-primary' : 'btn-outline'"
              @click="toggleCrop"
              title="Crop"
            >
              <i class="fa-solid fa-crop"></i> Crop
            </button>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <label class="form-control">
              <span class="label-text text-xs mb-1">Width (px)</span>
              <input
                v-model.number="editResizeWidth"
                type="number"
                min="1"
                class="input input-xs input-bordered"
                @change="onResizeDimensionChanged('width')"
              />
            </label>
            <label class="form-control">
              <span class="label-text text-xs mb-1">Height (px)</span>
              <input
                v-model.number="editResizeHeight"
                type="number"
                min="1"
                class="input input-xs input-bordered"
                @change="onResizeDimensionChanged('height')"
              />
            </label>
          </div>

          <label class="flex items-center gap-2 text-xs cursor-pointer">
            <input v-model="editKeepAspect" type="checkbox" class="checkbox checkbox-xs" />
            Keep aspect ratio
          </label>

          <!-- File name -->
          <label class="form-control">
            <span class="label-text text-xs mb-1">File Name</span>
            <input
              v-model="editFileName"
              type="text"
              class="input input-xs input-bordered w-full"
              @change="renameAttachment"
              @keyup.enter="renameAttachment"
            />
          </label>

          <!-- Output + apply -->
          <div class="flex items-center justify-between gap-3">
            <span class="text-xs text-base-content/60">
              Output: <span v-if="estimatedFileSizeKB > 0" class="font-semibold text-primary">≈ {{ estimatedFileSizeKB }} KB</span>
            </span>
            <button class="btn btn-xs btn-primary" :disabled="imageSaving" @click="applyImageEdits">
              <span v-if="imageSaving" class="loading loading-xs"></span>
              Apply Changes
            </button>
          </div>
        </div>
      </template>

      <!-- File Icon Preview -->
      <template v-else>
        <div class="w-full h-64 bg-gradient-to-br from-base-200 to-base-300 rounded-lg flex flex-col items-center justify-center gap-3">
          <i :class="getFileIcon(currentAttachment)" class="text-6xl opacity-40"></i>
          <span class="text-sm font-medium text-base-content/60">{{ currentAttachment.getExtension().toUpperCase() }}</span>
        </div>
      </template>

      <!-- File Info -->
      <div class="grid grid-cols-2 gap-4 p-3 bg-base-200/50 rounded-lg">
        <div v-if="!currentAttachment.isImage()">
          <div class="text-xs font-medium text-base-content/60">File Name</div>
          <input
            v-model="editFileName"
            type="text"
            class="input input-xs input-bordered w-full mt-1"
            @change="renameAttachment"
            @keyup.enter="renameAttachment"
          />
        </div>
        <div>
          <div class="text-xs font-medium text-base-content/60">File Size</div>
          <div class="text-sm font-semibold text-base-content">{{ currentAttachment.getFormattedSize() }}</div>
        </div>
        <div v-if="currentAttachment.isImage() && editSourceImage">
          <div class="text-xs font-medium text-base-content/60">Original Size</div>
          <div class="text-sm font-semibold text-base-content">
            {{ editSourceImage.naturalWidth }} × {{ editSourceImage.naturalHeight }}
          </div>
        </div>
      </div>
    </div>

    <!-- Footer Actions -->
    <template #footer>
      <button
        class="btn btn-sm btn-primary"
        @click="downloadAttachment(currentAttachment)"
      >
        <i class="fa-solid fa-download"></i>
        Download
      </button>
      <button
        class="btn btn-sm btn-error"
        @click="removeAndClose"
      >
        <i class="fa-solid fa-trash"></i>
        Remove
      </button>
    </template>
  </modal>
</template>

<script>
import ChatAttachment from '@/api/model/ChatAttachment.js'

export default {
  name: 'ChatAttachmentPreview',
  props: {
    attachments: {
      type: Array,
      default: () => [],
      validator(value) {
        return Array.isArray(value)
      }
    },
    showSelector: {
      type: Boolean,
      default: false
    }
  },
  emits: ['remove-attachment', 'update-attachment'],
  data() {
    return {
      fileObjects: [],
      showModal: false,
      selectedIndex: null,
      hoverPreview: null,
      editSourceImage: null,
      editRotation: 0,
      editZoom: 1,
      editResizeWidth: 0,
      editResizeHeight: 0,
      editKeepAspect: true,
      editFileName: '',
      cropEnabled: false,
      cropRect: { x: 0, y: 0, width: 1, height: 1 },
      cropDragActive: false,
      cropDragStart: { x: 0, y: 0 },
      cropDragCurrent: { x: 0, y: 0 },
      imageSaving: false,
      editControlsVisible: false
    }
  },
  computed: {
    currentAttachment() {
      return this.selectedIndex !== null ? this.fileObjects[this.selectedIndex] : null
    },
    cropOverlayStyle() {
      return {
        left: `${this.cropRect.x * 100}%`,
        top: `${this.cropRect.y * 100}%`,
        width: `${this.cropRect.width * 100}%`,
        height: `${this.cropRect.height * 100}%`
      }
    },
    // Live preview of the output size once edits are applied.
    // Mirrors the exact calculation in applyImageEdits() so the value shown
    // is always the value that will be saved.
    finalImageSize() {
      if (!this.editSourceImage) return null
      const { width: fullW, height: fullH } = this.getRotatedSourceDimensions()
      const cropW = Math.max(1, Math.round(this.cropRect.width * fullW))
      const cropH = Math.max(1, Math.round(this.cropRect.height * fullH))
      const targetW = Math.max(1, Math.round(this.editResizeWidth || cropW))
      const targetH = Math.max(1, Math.round(this.editResizeHeight || cropH))
      return { width: targetW, height: targetH }
    },
    // Estimated final weight in KB.
    // Based on the original byte size scaled by the pixel-area ratio, with a
    // correction for the format conversion performed by applyImageEdits().
    estimatedFileSizeKB() {
      if (!this.editSourceImage || !this.currentAttachment || !this.finalImageSize) return 0
      const originalW = this.editSourceImage.naturalWidth
      const originalH = this.editSourceImage.naturalHeight
      const originalArea = originalW * originalH
      const finalArea = this.finalImageSize.width * this.finalImageSize.height
      if (!originalArea) return 0

      const originalBytes = this.currentAttachment.file_size || 0
      let estimatedBytes = originalBytes * (finalArea / originalArea)

      // applyImageEdits() outputs PNG only for PNG sources, JPEG otherwise.
      const outputMime = this.currentAttachment.file_type === 'image/png' ? 'image/png' : 'image/jpeg'
      if (outputMime === 'image/jpeg' && this.currentAttachment.file_type === 'image/png') {
        estimatedBytes *= 0.4  // PNG -> JPEG typically compresses significantly
      } else if (outputMime === 'image/png' && this.currentAttachment.file_type !== 'image/png') {
        estimatedBytes *= 2    // JPEG -> PNG can grow
      }

      return Math.max(1, Math.round(estimatedBytes / 1024))
    }
  },
  watch: {
    attachments: {
      immediate: true,
      handler(newVal) {
        this.fileObjects = newVal.map(attachment => {
          if (attachment instanceof ChatAttachment) {
            return attachment
          }
          return ChatAttachment.fromJSON(attachment)
        })
      }
    }
  },
  beforeUnmount() {
    this.endCrop()
  },
  methods: {
    openPreview(idx) {
      this.onThumbLeave()
      this.selectedIndex = idx
      this.showModal = true
      this.editControlsVisible = false
      this.editFileName = this.fileObjects[idx]?.file_name || ''
      this.$nextTick(() => this.initImageEditor())
    },
    closePreview() {
      this.endCrop()
      this.showModal = false
      this.selectedIndex = null
      this.editSourceImage = null
      this.cropEnabled = false
      this.editControlsVisible = false
      this.editFileName = ''
    },
    removeAndClose() {
      this.removeAttachmentItem(this.selectedIndex)
      this.closePreview()
    },
    removeAttachmentItem(idx) {
      this.$emit('remove-attachment', idx)
    },
    // Shows a 3x floating preview of the hovered thumbnail (images only).
    // Position is computed in viewport space; the preview is teleported to
    // <body> so the grid's horizontal scroll can never clip it.
    onThumbHover(attachment, event) {
      if (!attachment?.isImage?.()) {
        this.hoverPreview = null
        return
      }
      const rect = event.currentTarget.getBoundingClientRect()
      const size = 144 // 3x the 48px thumbnail (w-12 / h-12)
      const gap = 8
      // Center horizontally over the thumb, clamped to the viewport
      const left = Math.min(
        Math.max(rect.left + rect.width / 2 - size / 2, gap),
        window.innerWidth - size - gap
      )
      // Prefer above the thumb; flip below when there is not enough room
      const top = rect.top - size - gap >= gap
        ? rect.top - size - gap
        : rect.bottom + gap
      this.hoverPreview = { attachment, left, top }
    },
    onThumbLeave() {
      this.hoverPreview = null
    },
    getFileIcon(attachment) {
      const ext = attachment.getExtension()
      const iconMap = {
        'pdf': 'fa-solid fa-file-pdf text-red-500',
        'doc': 'fa-solid fa-file-word text-blue-500',
        'docx': 'fa-solid fa-file-word text-blue-500',
        'xls': 'fa-solid fa-file-excel text-green-500',
        'xlsx': 'fa-solid fa-file-excel text-green-500',
        'ppt': 'fa-solid fa-file-powerpoint text-orange-500',
        'pptx': 'fa-solid fa-file-powerpoint text-orange-500',
        'txt': 'fa-solid fa-file-lines text-gray-500',
        'zip': 'fa-solid fa-file-zipper text-yellow-600',
        'json': 'fa-solid fa-file-code text-purple-500',
        'xml': 'fa-solid fa-file-code text-purple-500',
        'png': 'fa-solid fa-image text-cyan-500',
        'jpg': 'fa-solid fa-image text-cyan-500',
        'jpeg': 'fa-solid fa-image text-cyan-500',
        'gif': 'fa-solid fa-image text-cyan-500',
        'svg': 'fa-solid fa-image text-cyan-500'
      }
      return iconMap[ext] || 'fa-solid fa-file text-base-content/40'
    },
    downloadAttachment(attachment) {
      const link = document.createElement('a')
      const dataUrl = `data:${attachment.file_type};base64,${attachment.base64_data}`
      link.href = dataUrl
      link.download = attachment.file_name
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    },
    renameAttachment() {
      const attachment = this.currentAttachment
      if (!attachment) return
      const newName = this.editFileName?.trim()
      if (!newName || newName === attachment.file_name) {
        this.editFileName = attachment.file_name
        return
      }
      attachment.file_name = newName
      this.$emit('update-attachment', { index: this.selectedIndex, attachment })
    },
    getTotalSize() {
      const total = this.fileObjects.reduce((sum, att) => sum + att.file_size, 0)
      return ChatAttachment.formatSize(total)
    },
    // ── Image editor ──────────────────────────────────────────────
    initImageEditor() {
      const attachment = this.currentAttachment
      if (!attachment?.isImage?.()) {
        this.editSourceImage = null
        return
      }
      const img = new Image()
      img.onload = () => {
        this.editSourceImage = img
        this.editRotation = 0
        this.editZoom = 1
        this.editKeepAspect = true
        this.cropEnabled = false
        this.cropRect = { x: 0, y: 0, width: 1, height: 1 }
        this.syncResizeDimensions()
        this.$nextTick(() => this.drawPreview())
      }
      img.src = `data:${attachment.file_type};base64,${attachment.base64_data}`
    },
    getRotatedSourceDimensions() {
      if (!this.editSourceImage) return { width: 0, height: 0 }
      const srcW = this.editSourceImage.naturalWidth
      const srcH = this.editSourceImage.naturalHeight
      const rotated = Math.abs(this.editRotation) % 180 !== 0
      return { width: rotated ? srcH : srcW, height: rotated ? srcW : srcH }
    },
    syncResizeDimensions() {
      const { width, height } = this.getRotatedSourceDimensions()
      this.editResizeWidth = width
      this.editResizeHeight = height
    },
    // Renders the image on the canvas. While cropping is active the full
    // rotated source is shown (so the crop box maps 1:1 to the image);
    // otherwise the final result (rotation + crop + resize) is rendered.
    drawPreview() {
      const canvas = this.$refs.imageEditCanvas
      if (!canvas || !this.editSourceImage) return

      const srcW = this.editSourceImage.naturalWidth
      const srcH = this.editSourceImage.naturalHeight
      const { width: fullW, height: fullH } = this.getRotatedSourceDimensions()

      const cropX = Math.round(this.cropRect.x * fullW)
      const cropY = Math.round(this.cropRect.y * fullH)
      const cropW = Math.max(1, Math.round(this.cropRect.width * fullW))
      const cropH = Math.max(1, Math.round(this.cropRect.height * fullH))

      const targetW = Math.max(1, Math.round(this.editResizeWidth || cropW))
      const targetH = Math.max(1, Math.round(this.editResizeHeight || cropH))

      const renderW = this.cropEnabled ? fullW : targetW
      const renderH = this.cropEnabled ? fullH : targetH

      const maxDimension = 1600
      const maxZoom = maxDimension / Math.max(renderW, renderH, 1)
      const zoom = Math.max(0.05, Math.min(this.editZoom, maxZoom))

      canvas.width = Math.max(1, Math.round(renderW * zoom))
      canvas.height = Math.max(1, Math.round(renderH * zoom))

      const ctx = canvas.getContext('2d')
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.imageSmoothingEnabled = true
      ctx.imageSmoothingQuality = 'high'

      if (this.cropEnabled) {
        // Full rotated source while the user selects the crop region
        ctx.translate(canvas.width / 2, canvas.height / 2)
        ctx.rotate(this.editRotation * Math.PI / 180)
        ctx.scale(zoom, zoom)
        ctx.drawImage(this.editSourceImage, -srcW / 2, -srcH / 2, srcW, srcH)
        return
      }

      // Final result: apply crop + resize on top of the rotation
      ctx.scale(zoom, zoom)
      ctx.scale(targetW / cropW, targetH / cropH)
      ctx.translate(-cropX, -cropY)
      ctx.translate(fullW / 2, fullH / 2)
      ctx.rotate(this.editRotation * Math.PI / 180)
      ctx.drawImage(this.editSourceImage, -srcW / 2, -srcH / 2, srcW, srcH)
    },
    zoomImageEditor(delta) {
      this.editZoom = Math.max(0.1, Math.min(4, this.editZoom + delta))
      this.drawPreview()
    },
    rotateImageEditor(degrees) {
      this.editRotation = (this.editRotation + degrees + 360) % 360
      this.cropEnabled = false
      this.cropRect = { x: 0, y: 0, width: 1, height: 1 }
      this.syncResizeDimensions()
      this.$nextTick(() => this.drawPreview())
    },
    resetImageEditor() {
      this.editRotation = 0
      this.editZoom = 1
      this.cropEnabled = false
      this.cropRect = { x: 0, y: 0, width: 1, height: 1 }
      this.syncResizeDimensions()
      this.$nextTick(() => this.drawPreview())
    },
    onResizeDimensionChanged(changed) {
      if (this.editKeepAspect) {
        const { width, height } = this.getRotatedSourceDimensions()
        if (width && height) {
          if (changed === 'width') {
            this.editResizeHeight = Math.max(1, Math.round((this.editResizeWidth || 1) * height / width))
          } else {
            this.editResizeWidth = Math.max(1, Math.round((this.editResizeHeight || 1) * width / height))
          }
        }
      }
      this.drawPreview()
    },
    toggleCrop() {
      if (this.cropEnabled) {
        // Turning crop off keeps the current selection and shows the result
        this.cropEnabled = false
        this.endCrop()
      } else {
        // Turning crop on starts from the full image
        this.cropEnabled = true
        this.cropRect = { x: 0, y: 0, width: 1, height: 1 }
      }
      this.drawPreview()
    },
    showEditControls() {
      this.editControlsVisible = true
    },
    hideEditControls() {
      this.editControlsVisible = false
      if (this.cropEnabled) this.toggleCrop()
    },
    getCanvasCoords(event) {
      const canvas = this.$refs.imageEditCanvas
      if (!canvas) return { x: 0, y: 0 }
      const rect = canvas.getBoundingClientRect()
      const x = (event.clientX - rect.left) * (canvas.width / rect.width)
      const y = (event.clientY - rect.top) * (canvas.height / rect.height)
      return {
        x: Math.max(0, Math.min(canvas.width, x)),
        y: Math.max(0, Math.min(canvas.height, y))
      }
    },
    startCrop(event) {
      if (!this.cropEnabled || !this.editSourceImage) return
      const canvas = this.$refs.imageEditCanvas
      if (!canvas) return
      const pos = this.getCanvasCoords(event)
      this.cropDragActive = true
      this.cropDragStart = { x: pos.x / canvas.width, y: pos.y / canvas.height }
      this.cropDragCurrent = { ...this.cropDragStart }
      this.updateCropRect()
      window.addEventListener('mousemove', this.handleCropMove)
      window.addEventListener('mouseup', this.endCrop)
    },
    handleCropMove(event) {
      if (!this.cropDragActive) return
      const canvas = this.$refs.imageEditCanvas
      if (!canvas) return
      const pos = this.getCanvasCoords(event)
      this.cropDragCurrent = { x: pos.x / canvas.width, y: pos.y / canvas.height }
      this.updateCropRect()
    },
    endCrop() {
      if (!this.cropDragActive) return
      this.cropDragActive = false
      window.removeEventListener('mousemove', this.handleCropMove)
      window.removeEventListener('mouseup', this.endCrop)
    },
    updateCropRect() {
      const clamp = v => Math.max(0, Math.min(1, v))
      const x1 = clamp(Math.min(this.cropDragStart.x, this.cropDragCurrent.x))
      const y1 = clamp(Math.min(this.cropDragStart.y, this.cropDragCurrent.y))
      const x2 = clamp(Math.max(this.cropDragStart.x, this.cropDragCurrent.x))
      const y2 = clamp(Math.max(this.cropDragStart.y, this.cropDragCurrent.y))
      this.cropRect = { x: x1, y: y1, width: x2 - x1, height: y2 - y1 }
    },
    async applyImageEdits() {
      if (!this.editSourceImage || this.imageSaving) return
      this.imageSaving = true
      try {
        const srcW = this.editSourceImage.naturalWidth
        const srcH = this.editSourceImage.naturalHeight
        const { width: fullW, height: fullH } = this.getRotatedSourceDimensions()

        const fullCanvas = document.createElement('canvas')
        fullCanvas.width = fullW
        fullCanvas.height = fullH
        const fullCtx = fullCanvas.getContext('2d')
        fullCtx.translate(fullW / 2, fullH / 2)
        fullCtx.rotate(this.editRotation * Math.PI / 180)
        fullCtx.drawImage(this.editSourceImage, -srcW / 2, -srcH / 2, srcW, srcH)

        const cropX = Math.round(this.cropRect.x * fullW)
        const cropY = Math.round(this.cropRect.y * fullH)
        const cropW = Math.max(1, Math.round(this.cropRect.width * fullW))
        const cropH = Math.max(1, Math.round(this.cropRect.height * fullH))

        const targetW = Math.max(1, Math.round(this.editResizeWidth || cropW))
        const targetH = Math.max(1, Math.round(this.editResizeHeight || cropH))

        const finalCanvas = document.createElement('canvas')
        finalCanvas.width = targetW
        finalCanvas.height = targetH
        const finalCtx = finalCanvas.getContext('2d')
        finalCtx.imageSmoothingEnabled = true
        finalCtx.imageSmoothingQuality = 'high'
        finalCtx.drawImage(fullCanvas, cropX, cropY, cropW, cropH, 0, 0, targetW, targetH)

        const originalAttachment = this.currentAttachment
        const mime = originalAttachment.file_type === 'image/png' ? 'image/png' : 'image/jpeg'
        const blob = await new Promise(resolve => finalCanvas.toBlob(resolve, mime, 0.9))
        if (!blob) throw new Error('Image processing failed')

        const ext = mime === 'image/png' ? 'png' : 'jpg'
        const baseName = (originalAttachment.file_name || 'image').replace(/\.[^.]+$/, '')
        const file = new File([blob], `${baseName}.${ext}`, { type: mime, lastModified: Date.now() })
        const attachment = await ChatAttachment.fromFile(file)

        this.fileObjects.splice(this.selectedIndex, 1, attachment)
        this.$emit('update-attachment', { index: this.selectedIndex, attachment })
        this.closePreview()
      } catch (error) {
        console.error('[AttachmentPreview] Failed to apply image edits', error)
        this.$ui?.addNotification?.({ text: 'Failed to process image', type: 'error' })
      } finally {
        this.imageSaving = false
      }
    }
  }
}
</script>