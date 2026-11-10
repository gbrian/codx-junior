<script setup>
</script>

<template>
  <modal :close="true" class="w-full max-w-3xl" @close="$emit('close')">
    <template #header>
      <div class="flex min-w-0 items-center gap-2">
        <i class="fa-solid fa-image text-primary"></i>
        <span class="min-w-0 truncate text-sm font-semibold">{{ title }}</span>
        <span v-if="outputSize" class="shrink-0 text-[11px] tabular-nums text-base-content/50">
          {{ outputSize.width }} × {{ outputSize.height }}
        </span>
      </div>
    </template>

    <div class="flex flex-col gap-3">
      <!-- Toolbar: zoom + rotation + crop + reset -->
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="join">
          <button class="btn btn-xs btn-outline join-item" title="Zoom out" @click="zoomBy(-0.1)">
            <i class="fa-solid fa-magnifying-glass-minus"></i>
          </button>
          <span class="btn btn-xs btn-outline join-item pointer-events-none tabular-nums">
            {{ Math.round(zoom * 100) }}%
          </span>
          <button class="btn btn-xs btn-outline join-item" title="Zoom in" @click="zoomBy(0.1)">
            <i class="fa-solid fa-magnifying-glass-plus"></i>
          </button>
        </div>

        <div class="flex items-center gap-1">
          <button class="btn btn-xs btn-outline" title="Rotate left" @click="rotateBy(-90)">
            <i class="fa-solid fa-rotate-left"></i>
          </button>
          <button class="btn btn-xs btn-outline" title="Rotate right" @click="rotateBy(90)">
            <i class="fa-solid fa-rotate-right"></i>
          </button>
          <button
            class="btn btn-xs"
            :class="cropEnabled ? 'btn-primary' : 'btn-outline'"
            title="Crop"
            @click="toggleCrop"
          >
            <i class="fa-solid fa-crop"></i> Crop
          </button>
          <button class="btn btn-xs btn-ghost" title="Reset" @click="reset">
            <i class="fa-solid fa-rotate"></i> Reset
          </button>
        </div>
      </div>

      <!-- Editable canvas: fixed viewport, centered, scrollable on overflow -->
      <div class="flex h-[58vh] w-full overflow-auto rounded-lg bg-base-200/60">
        <div class="relative m-auto shrink-0">
          <canvas
            ref="editCanvas"
            class="max-w-none select-none"
            :class="cropEnabled ? 'cursor-crosshair' : ''"
            @mousedown.prevent="startCrop"
          ></canvas>
          <div
            v-if="cropEnabled"
            class="pointer-events-none absolute border-2 border-primary bg-primary/20"
            :style="cropStyle"
          ></div>
        </div>
      </div>
      <p v-if="cropEnabled" class="text-center text-xs text-base-content/50">
        Drag on the image to select the crop area
      </p>

      <!-- Output size -->
      <div class="grid grid-cols-2 gap-3">
        <label class="form-control">
          <span class="label-text mb-1 text-xs">Width (px)</span>
          <input
            v-model.number="resizeWidth"
            type="number"
            min="1"
            class="input input-xs input-bordered"
            @change="onDimensionChanged('width')"
          />
        </label>
        <label class="form-control">
          <span class="label-text mb-1 text-xs">Height (px)</span>
          <input
            v-model.number="resizeHeight"
            type="number"
            min="1"
            class="input input-xs input-bordered"
            @change="onDimensionChanged('height')"
          />
        </label>
      </div>

      <label class="flex cursor-pointer items-center gap-2 text-xs">
        <input v-model="keepAspect" type="checkbox" class="checkbox checkbox-xs" />
        Keep aspect ratio
      </label>

      <!-- Alt text (also used as the image label in the message) -->
      <label class="form-control">
        <span class="label-text mb-1 text-xs">Alt text</span>
        <input
          v-model="alt"
          type="text"
          class="input input-xs input-bordered w-full"
          placeholder="Describe the image"
        />
      </label>

      <p v-if="error" class="text-xs text-error">{{ error }}</p>
    </div>

    <template #footer>
      <button class="btn btn-sm btn-ghost" @click="download">
        <i class="fa-solid fa-download"></i> Download
      </button>
      <button class="btn btn-sm" @click="$emit('close')">Cancel</button>
      <button class="btn btn-sm btn-primary" :disabled="!source || saving" @click="apply">
        <span v-if="saving" class="loading loading-xs"></span>
        Apply changes
      </button>
    </template>
  </modal>
</template>

<script>
// Output mime of the edited picture: data URLs declare it, plain links fall back
// to the file extension and then to PNG (lossless, keeps screenshots crisp).
function mimeFromSrc(src = '') {
  const dataMatch = /^data:(image\/[a-z0-9.+-]+)/i.exec(src)
  if (dataMatch) return dataMatch[1].toLowerCase()
  const extension = (src.split('?')[0].split('.').pop() || '').toLowerCase()
  const byExtension = {
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    webp: 'image/webp'
  }
  return byExtension[extension] || 'image/png'
}

export default {
  name: 'ChatImageEditorModal',
  props: {
    // { src, alt } — the same shape message images are stored with.
    image: { type: Object, default: null }
  },
  emits: ['close', 'save'],
  data() {
    return {
      source: null,
      mimeType: 'image/png',
      alt: '',
      rotation: 0,
      zoom: 1,
      resizeWidth: 0,
      resizeHeight: 0,
      keepAspect: true,
      cropEnabled: false,
      cropRect: { x: 0, y: 0, width: 1, height: 1 },
      cropDragActive: false,
      cropDragStart: { x: 0, y: 0 },
      cropDragCurrent: { x: 0, y: 0 },
      saving: false,
      error: null
    }
  },
  computed: {
    title() {
      return this.image?.alt || 'Image'
    },
    cropStyle() {
      return {
        left: `${this.cropRect.x * 100}%`,
        top: `${this.cropRect.y * 100}%`,
        width: `${this.cropRect.width * 100}%`,
        height: `${this.cropRect.height * 100}%`
      }
    },
    // Source dimensions once the rotation is applied (crop is relative to them)
    rotatedDimensions() {
      if (!this.source) return { width: 0, height: 0 }
      const sourceWidth = this.source.naturalWidth
      const sourceHeight = this.source.naturalHeight
      const rotated = Math.abs(this.rotation) % 180 !== 0
      return {
        width: rotated ? sourceHeight : sourceWidth,
        height: rotated ? sourceWidth : sourceHeight
      }
    },
    // Final output size: the crop region plus the requested resize
    outputSize() {
      if (!this.source) return null
      const { width: fullWidth, height: fullHeight } = this.rotatedDimensions
      const cropWidth = Math.max(1, Math.round(this.cropRect.width * fullWidth))
      const cropHeight = Math.max(1, Math.round(this.cropRect.height * fullHeight))
      return {
        width: Math.max(1, Math.round(this.resizeWidth || cropWidth)),
        height: Math.max(1, Math.round(this.resizeHeight || cropHeight))
      }
    }
  },
  watch: {
    image() {
      this.loadImage()
    }
  },
  mounted() {
    this.loadImage()
  },
  beforeUnmount() {
    this.endCrop()
  },
  methods: {
    // ── Loading ───────────────────────────────────────────────────
    loadImage() {
      this.error = null
      this.source = null
      const src = this.image?.src
      if (!src) return
      this.mimeType = mimeFromSrc(src)
      this.alt = this.image?.alt || ''
      const img = new Image()
      img.onload = () => {
        this.source = img
        this.rotation = 0
        this.zoom = 1
        this.keepAspect = true
        this.cropEnabled = false
        this.cropRect = { x: 0, y: 0, width: 1, height: 1 }
        this.syncDimensions()
        this.$nextTick(() => this.draw())
      }
      img.onerror = () => {
        this.error = 'The image could not be loaded'
      }
      img.src = src
    },
    syncDimensions() {
      const { width, height } = this.rotatedDimensions
      this.resizeWidth = width
      this.resizeHeight = height
    },
    // ── Rendering ─────────────────────────────────────────────────
    // While cropping is active the full rotated source is shown so the crop box
    // maps 1:1 to the image; otherwise the final result is rendered.
    draw() {
      const canvas = this.$refs.editCanvas
      if (!canvas || !this.source) return

      const sourceWidth = this.source.naturalWidth
      const sourceHeight = this.source.naturalHeight
      const { width: fullWidth, height: fullHeight } = this.rotatedDimensions

      const cropX = Math.round(this.cropRect.x * fullWidth)
      const cropY = Math.round(this.cropRect.y * fullHeight)
      const cropWidth = Math.max(1, Math.round(this.cropRect.width * fullWidth))
      const cropHeight = Math.max(1, Math.round(this.cropRect.height * fullHeight))

      const output = this.outputSize
      const renderWidth = this.cropEnabled ? fullWidth : output.width
      const renderHeight = this.cropEnabled ? fullHeight : output.height

      const maxDimension = 1600
      const maxZoom = maxDimension / Math.max(renderWidth, renderHeight, 1)
      const zoom = Math.max(0.05, Math.min(this.zoom, maxZoom))

      canvas.width = Math.max(1, Math.round(renderWidth * zoom))
      canvas.height = Math.max(1, Math.round(renderHeight * zoom))

      const ctx = canvas.getContext('2d')
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.imageSmoothingEnabled = true
      ctx.imageSmoothingQuality = 'high'

      if (this.cropEnabled) {
        ctx.translate(canvas.width / 2, canvas.height / 2)
        ctx.rotate(this.rotation * Math.PI / 180)
        ctx.scale(zoom, zoom)
        ctx.drawImage(this.source, -sourceWidth / 2, -sourceHeight / 2, sourceWidth, sourceHeight)
        return
      }

      ctx.scale(zoom, zoom)
      ctx.scale(output.width / cropWidth, output.height / cropHeight)
      ctx.translate(-cropX, -cropY)
      ctx.translate(fullWidth / 2, fullHeight / 2)
      ctx.rotate(this.rotation * Math.PI / 180)
      ctx.drawImage(this.source, -sourceWidth / 2, -sourceHeight / 2, sourceWidth, sourceHeight)
    },
    // ── Tools ─────────────────────────────────────────────────────
    zoomBy(delta) {
      this.zoom = Math.max(0.1, Math.min(4, this.zoom + delta))
      this.draw()
    },
    rotateBy(degrees) {
      this.rotation = (this.rotation + degrees + 360) % 360
      this.cropEnabled = false
      this.cropRect = { x: 0, y: 0, width: 1, height: 1 }
      this.syncDimensions()
      this.$nextTick(() => this.draw())
    },
    reset() {
      this.rotation = 0
      this.zoom = 1
      this.cropEnabled = false
      this.cropRect = { x: 0, y: 0, width: 1, height: 1 }
      this.syncDimensions()
      this.$nextTick(() => this.draw())
    },
    onDimensionChanged(changed) {
      if (this.keepAspect) {
        const { width, height } = this.rotatedDimensions
        if (width && height) {
          if (changed === 'width') {
            this.resizeHeight = Math.max(1, Math.round((this.resizeWidth || 1) * height / width))
          } else {
            this.resizeWidth = Math.max(1, Math.round((this.resizeHeight || 1) * width / height))
          }
        }
      }
      this.draw()
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
      this.draw()
    },
    getCanvasCoords(event) {
      const canvas = this.$refs.editCanvas
      if (!canvas) return { x: 0, y: 0 }
      const rect = canvas.getBoundingClientRect()
      return {
        x: Math.max(0, Math.min(canvas.width, (event.clientX - rect.left) * (canvas.width / rect.width))),
        y: Math.max(0, Math.min(canvas.height, (event.clientY - rect.top) * (canvas.height / rect.height)))
      }
    },
    startCrop(event) {
      if (!this.cropEnabled || !this.source) return
      const canvas = this.$refs.editCanvas
      if (!canvas) return
      const position = this.getCanvasCoords(event)
      this.cropDragActive = true
      this.cropDragStart = { x: position.x / canvas.width, y: position.y / canvas.height }
      this.cropDragCurrent = { ...this.cropDragStart }
      this.updateCropRect()
      window.addEventListener('mousemove', this.handleCropMove)
      window.addEventListener('mouseup', this.endCrop)
    },
    handleCropMove(event) {
      if (!this.cropDragActive) return
      const canvas = this.$refs.editCanvas
      if (!canvas) return
      const position = this.getCanvasCoords(event)
      this.cropDragCurrent = { x: position.x / canvas.width, y: position.y / canvas.height }
      this.updateCropRect()
    },
    endCrop() {
      if (!this.cropDragActive) return
      this.cropDragActive = false
      window.removeEventListener('mousemove', this.handleCropMove)
      window.removeEventListener('mouseup', this.endCrop)
    },
    updateCropRect() {
      const clamp = value => Math.max(0, Math.min(1, value))
      const x1 = clamp(Math.min(this.cropDragStart.x, this.cropDragCurrent.x))
      const y1 = clamp(Math.min(this.cropDragStart.y, this.cropDragCurrent.y))
      const x2 = clamp(Math.max(this.cropDragStart.x, this.cropDragCurrent.x))
      const y2 = clamp(Math.max(this.cropDragStart.y, this.cropDragCurrent.y))
      this.cropRect = { x: x1, y: y1, width: x2 - x1, height: y2 - y1 }
    },
    // ── Apply / download ──────────────────────────────────────────
    apply() {
      if (!this.source || this.saving) return
      this.saving = true
      this.error = null
      try {
        const sourceWidth = this.source.naturalWidth
        const sourceHeight = this.source.naturalHeight
        const { width: fullWidth, height: fullHeight } = this.rotatedDimensions

        const rotatedCanvas = document.createElement('canvas')
        rotatedCanvas.width = fullWidth
        rotatedCanvas.height = fullHeight
        const rotatedCtx = rotatedCanvas.getContext('2d')
        rotatedCtx.translate(fullWidth / 2, fullHeight / 2)
        rotatedCtx.rotate(this.rotation * Math.PI / 180)
        rotatedCtx.drawImage(this.source, -sourceWidth / 2, -sourceHeight / 2, sourceWidth, sourceHeight)

        const cropX = Math.round(this.cropRect.x * fullWidth)
        const cropY = Math.round(this.cropRect.y * fullHeight)
        const cropWidth = Math.max(1, Math.round(this.cropRect.width * fullWidth))
        const cropHeight = Math.max(1, Math.round(this.cropRect.height * fullHeight))

        const output = this.outputSize
        const finalCanvas = document.createElement('canvas')
        finalCanvas.width = output.width
        finalCanvas.height = output.height
        const finalCtx = finalCanvas.getContext('2d')
        finalCtx.imageSmoothingEnabled = true
        finalCtx.imageSmoothingQuality = 'high'
        finalCtx.drawImage(
          rotatedCanvas,
          cropX, cropY, cropWidth, cropHeight,
          0, 0, output.width, output.height
        )

        const mime = ['image/png', 'image/jpeg', 'image/webp'].includes(this.mimeType)
          ? this.mimeType
          : 'image/png'

        this.$emit('save', { src: finalCanvas.toDataURL(mime, 0.92), alt: this.alt })
      } catch (ex) {
        console.error('[ChatImageEditorModal] Failed to apply image edits', ex)
        this.error = 'Failed to process the image'
      } finally {
        this.saving = false
      }
    },
    download() {
      const src = this.image?.src
      if (!src) return
      const name = (this.alt || 'image').replace(/[^\w.-]+/g, '_')
      const link = document.createElement('a')
      link.href = src
      link.download = /\.[a-z0-9]+$/i.test(name) ? name : `${name}.png`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    }
  }
}
</script>