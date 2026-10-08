<script setup>
import '@woven-canvas/vue/style.css'
import { WovenCanvas } from '@woven-canvas/vue'
import {
  Block,
  Shape,
  Color,
  Text,
  Synced,
  UploadState,
  addComponent,
  getBlockDef,
  hasComponent,
  removeEntity,
  defineQuery,
  createEntity,
  RankBounds
} from '@woven-canvas/core'
</script>

<template>
  <div class="woven-canvas-scope w-full h-full relative overflow-hidden bg-base-300">
    <WovenCanvas
      class="w-full h-full"
      style="width: 100%; height: 100%"
      :background="canvasBackground"
      :asset-provider="assetProvider"
      @ready="onReady"
    />
    <div
      class="absolute inset-0 flex items-center justify-center opacity-60 text-sm pointer-events-none"
      v-if="!ready"
    >
      <span class="loading loading-spinner loading-md mr-2"></span>
      Initializing canvas…
    </div>
  </div>
</template>

<script>
export default {
  name: 'CanvaEditor',
  props: {
    modelValue: {
      type: Array,
      default: () => DEFAULT_BREAD_RECIPE_NODES
    }
  },
  emits: ['update:modelValue'],
  data() {
    return {
      editor: null,
      store: null,
      ready: false,
      isUpdatingFromProp: false,
      unsubscribeChange: null,
      blockQuery: null,
      assetProvider: createCanvaAssetProvider(),
      lastEmittedJson: null,
      canvasBackground: {
        kind: 'dots',
        color: '#ffffff',
        strokeColor: '#e2e8f0',
        subdivisionStep: 20,
        dotSize: 2
      }
    }
  },
  watch: {
    modelValue: {
      deep: true,
      handler(nodes) {
        if (!this.ready || this.isUpdatingFromProp) return
        this.loadJsonToCanvas(nodes)
      }
    }
  },
  beforeUnmount() {
    if (this.unsubscribeChange) {
      this.unsubscribeChange()
      this.unsubscribeChange = null
    }
  },
  methods: {
    onReady(editor, store) {
      this.editor = editor
      this.store = store
      this.blockQuery = defineQuery((q) => q.with(Block))
      this.unsubscribeChange = editor.subscribe(this.blockQuery, () => {
        if (this.isUpdatingFromProp) return
        this.publishCanvas()
      })
      this.ready = true
      this.loadJsonToCanvas(this.modelValue)
    },
    async publishCanvas() {
      if (this.assetProvider) {
        await this.assetProvider.settled()
      }
      if (this.isUpdatingFromProp) return
      const nodes = await this.exportCanvasToJson()
      const json = stableStringify(nodes)
      if (json === this.lastEmittedJson) return
      this.lastEmittedJson = json
      this.$emit('update:modelValue', nodes)
    },
    loadJsonToCanvas(nodes) {
      if (!this.editor || !this.blockQuery) return
      const list = Array.isArray(nodes) ? nodes : []
      this.isUpdatingFromProp = true
      this.editor.nextTick((ctx) => {
        const existing = Array.from(this.blockQuery.current(ctx))
        existing.forEach((entityId) => {
          removeEntity(ctx, entityId)
        })
        list.forEach((node) => this.createNodeBlock(ctx, node))
        this.editor.nextTick((nextCtx) => {
          this.exportCanvasToJson(nextCtx).then((exportedNodes) => {
            this.lastEmittedJson = stableStringify(exportedNodes)
            this.isUpdatingFromProp = false
          })
        })
      })
    },
    createNodeBlock(ctx, node) {
      const tag = node.tag || 'shape'
      const [x, y] = Array.isArray(node.position) ? node.position : [0, 0]
      const [width, height] = Array.isArray(node.size) ? node.size : [160, 120]
      const rotateZ = Number(node.rotateZ) || 0

      const entityId = createEntity(ctx)
      addComponent(ctx, entityId, Block, {
        tag,
        position: [x, y],
        size: [width, height],
        rotateZ,
        rank: RankBounds.genNext(ctx)
      })

      if (node.id) {
        addComponent(ctx, entityId, Synced, { id: String(node.id) })
      }

      if (tag === 'shape') {
        this.createShapeComponents(ctx, entityId, node)
      } else if (tag === 'text') {
        this.createTextComponents(ctx, entityId, node)
      } else if (tag === 'sticky-note') {
        this.createStickyNoteComponents(ctx, entityId, node)
      } else if (MEDIA_TAGS.includes(tag)) {
        this.createMediaComponents(ctx, entityId, tag, node)
      }

      if (node.text && tag !== 'text' && tag !== 'sticky-note') {
        this.createTextComponents(ctx, entityId, node)
      }
    },
    createShapeComponents(ctx, entityId, node) {
      const shapeKind = node.shape?.kind || 'rectangle'
      const radius = node.shape?.radius || 0
      const fillHex = node.color?.fill || '#ffffff'
      const strokeHex = node.stroke?.color || '#e2e8f0'
      const strokeWidth = Number(node.stroke?.width) || 1

      const fill = hexToRgba(fillHex, [255, 255, 255, 255])
      const stroke = hexToRgba(strokeHex, [203, 213, 225, 255])

      addComponent(ctx, entityId, Shape, {
        kind: shapeKind,
        radius,
        strokeKind: 'solid',
        strokeWidth,
        strokeRed: stroke[0],
        strokeGreen: stroke[1],
        strokeBlue: stroke[2],
        strokeAlpha: stroke[3],
        fillRed: fill[0],
        fillGreen: fill[1],
        fillBlue: fill[2],
        fillAlpha: fill[3]
      })
    },
    createTextComponents(ctx, entityId, node) {
      const textData = node.text || {}
      const content = String(textData.content || '')
      const textComponent = {
        content,
        fontSize: Number(textData.fontSize) || 16,
        fontFamily: String(textData.fontFamily || 'Inter, system-ui, sans-serif'),
        fontWeight: String(textData.fontWeight || '400'),
        align: String(textData.align || 'left'),
        verticalAlign: String(node.verticalAlign || 'top')
      }
      if (textData.color) {
        const rgba = hexToRgba(textData.color, [255, 255, 255, 255])
        textComponent.colorRed = rgba[0]
        textComponent.colorGreen = rgba[1]
        textComponent.colorBlue = rgba[2]
        textComponent.colorAlpha = rgba[3]
      }
      addComponent(ctx, entityId, Text, textComponent)
    },
    createStickyNoteComponents(ctx, entityId, node) {
      const fillHex = node.color?.fill || '#fef08a'
      const fill = hexToRgba(fillHex, [255, 242, 117, 255])
      addComponent(ctx, entityId, Color, {
        red: fill[0],
        green: fill[1],
        blue: fill[2],
        alpha: fill[3]
      })
      if (node.text) {
        this.createTextComponents(ctx, entityId, node)
      }
    },
    createMediaComponents(ctx, entityId, tag, node) {
      const blockDef = getBlockDef(ctx, tag)
      if (!blockDef || !blockDef.components) {
        console.warn(`Missing block definition for "${tag}"`)
        return
      }
      blockDef.components.forEach((componentDef) => {
        const data = node[componentDef.name]
        if (data) {
          addComponent(ctx, entityId, componentDef, normalizeMediaData(componentDef.name, data))
        } else {
          addComponent(ctx, entityId, componentDef)
        }
      })
    },
    async exportCanvasToJson(ctx) {
      const activeContext = ctx || (await new Promise((resolve) => {
        this.editor.nextTick(resolve)
      }))
      if (!activeContext || !this.blockQuery) return []
      return Array.from(this.blockQuery.current(activeContext))
        .map((entityId) => this.blockToNode(activeContext, entityId))
    },
    blockToNode(ctx, entityId) {
      const block = Block.read(ctx, entityId)
      const node = {
        id: this.readSyncedId(ctx, entityId),
        tag: block.tag,
        position: [block.position[0], block.position[1]],
        size: [block.size[0], block.size[1]]
      }
      if (block.rotateZ) {
        node.rotateZ = block.rotateZ
      }
      if (hasComponent(ctx, entityId, Shape)) {
        const shape = Shape.read(ctx, entityId)
        node.shape = {
          kind: shape.kind
        }
        if (shape.radius) node.shape.radius = shape.radius
        node.color = {
          fill: rgbaToHex(shape.fillRed, shape.fillGreen, shape.fillBlue)
        }
        node.stroke = {
          color: rgbaToHex(shape.strokeRed, shape.strokeGreen, shape.strokeBlue),
          width: shape.strokeWidth || 1
        }
      }
      if (hasComponent(ctx, entityId, Color)) {
        const color = Color.read(ctx, entityId)
        node.color = {
          fill: rgbaToHex(color.red, color.green, color.blue)
        }
      }
      if (hasComponent(ctx, entityId, Text)) {
        const text = Text.read(ctx, entityId)
        node.text = {
          content: text.content,
          fontSize: text.fontSize,
          fontFamily: text.fontFamily,
          fontWeight: text.fontWeight,
          align: text.align,
          color: rgbaToHex(
            text.colorRed ?? 255,
            text.colorGreen ?? 255,
            text.colorBlue ?? 255
          )
        }
        if (text.verticalAlign) {
          node.verticalAlign = text.verticalAlign
        }
      }
      if (MEDIA_TAGS.includes(block.tag)) {
        this.readMediaComponents(ctx, entityId, block.tag, node)
      }
      return node
    },
    readMediaComponents(ctx, entityId, tag, node) {
      const blockDef = getBlockDef(ctx, tag)
      if (!blockDef || !blockDef.components) return
      blockDef.components.forEach((componentDef) => {
        if (!hasComponent(ctx, entityId, componentDef)) return
        const data = componentDef.read(ctx, entityId)
        if (componentDef.name === 'asset') {
          const dataUrl = this.getAssetDataUrl(data.identifier)
          node.asset = {
            identifier: dataUrl || data.identifier,
            uploadState: dataUrl ? UploadState.Complete : data.uploadState
          }
        } else {
          node[componentDef.name] = { ...data }
        }
      })
    },
    getAssetDataUrl(identifier) {
      if (!identifier || !this.assetProvider) return null
      return this.assetProvider.getDataUrl(identifier)
    },
    readSyncedId(ctx, entityId) {
      try {
        if (hasComponent(ctx, entityId, Synced)) {
          return Synced.read(ctx, entityId).id
        }
      } catch (ex) {
        console.warn('Could not read synced id', ex)
      }
      return null
    }
  }
}

const MEDIA_TAGS = ['image', 'tape']
const DEFAULT_TAPE_THICKNESS = 30
const INLINE_ASSET_PATTERN = /^(data:|blob:|https?:|\/)/i

const DEFAULT_BREAD_RECIPE_NODES = [
  {
    id: 'bread-step-1',
    tag: 'sticky-note',
    position: [100, 100],
    size: [220, 120],
    color: { fill: '#fef08a' },
    text: {
      content: 'Mix flour, water, yeast, and salt',
      fontSize: 16,
      align: 'center'
    },
    verticalAlign: 'middle'
  },
  {
    id: 'bread-step-2',
    tag: 'sticky-note',
    position: [100, 240],
    size: [220, 120],
    color: { fill: '#fef08a' },
    text: {
      content: 'Knead dough for 10 minutes',
      fontSize: 16,
      align: 'center'
    },
    verticalAlign: 'middle'
  },
  {
    id: 'bread-step-3',
    tag: 'sticky-note',
    position: [100, 380],
    size: [220, 120],
    color: { fill: '#fef08a' },
    text: {
      content: 'First rise: 1 hour',
      fontSize: 16,
      align: 'center'
    },
    verticalAlign: 'middle'
  },
  {
    id: 'bread-step-4',
    tag: 'sticky-note',
    position: [100, 520],
    size: [220, 120],
    color: { fill: '#fef08a' },
    text: {
      content: 'Shape the loaf',
      fontSize: 16,
      align: 'center'
    },
    verticalAlign: 'middle'
  },
  {
    id: 'bread-step-5',
    tag: 'sticky-note',
    position: [100, 660],
    size: [220, 120],
    color: { fill: '#fef08a' },
    text: {
      content: 'Second rise: 30 minutes',
      fontSize: 16,
      align: 'center'
    },
    verticalAlign: 'middle'
  },
  {
    id: 'bread-step-6',
    tag: 'sticky-note',
    position: [100, 800],
    size: [220, 120],
    color: { fill: '#fef08a' },
    text: {
      content: 'Bake at 220°C for 30 minutes',
      fontSize: 16,
      align: 'center'
    },
    verticalAlign: 'middle'
  }
]

function createCanvaAssetProvider() {
  const dataUrls = new Map()
  const pending = new Set()

  function encode(blob, identifier) {
    return new Promise((resolve) => {
      const reader = new FileReader()
      reader.onload = () => {
        const result = typeof reader.result === 'string' ? reader.result : ''
        if (result) {
          dataUrls.set(identifier, result)
        }
        resolve(result)
      }
      reader.onerror = () => resolve('')
      reader.readAsDataURL(blob)
    })
  }

  return {
    storage: 'local',
    maxRetries: 1,
    retryDelay: 500,
    upload(blob, identifier) {
      const job = encode(blob, identifier)
      pending.add(job)
      job.then(() => pending.delete(job))
      return job.then(() => ({}))
    },
    async resolveUrl(identifier) {
      if (!identifier) return identifier
      if (INLINE_ASSET_PATTERN.test(identifier)) return identifier
      const dataUrl = dataUrls.get(identifier)
      if (dataUrl) return dataUrl
      throw new Error(`Asset not found: ${identifier}`)
    },
    async delete(identifier) {
      dataUrls.delete(identifier)
    },
    getDataUrl(identifier) {
      return dataUrls.get(identifier) || null
    },
    settled() {
      return Promise.all(Array.from(pending))
    }
  }
}

function normalizeMediaData(name, data) {
  const value = { ...data }
  if (name === 'asset') {
    value.identifier = String(value.identifier || '')
    if (INLINE_ASSET_PATTERN.test(value.identifier)) {
      value.uploadState = UploadState.Complete
    } else if (value.uploadState === UploadState.Pending || value.uploadState === UploadState.Uploading) {
      value.uploadState = UploadState.Failed
    } else {
      value.uploadState = value.uploadState || UploadState.Complete
    }
  } else if (name === 'image') {
    value.width = clampUint16(value.width)
    value.height = clampUint16(value.height)
    value.alt = String(value.alt || '')
  } else if (name === 'tape') {
    value.thickness = Number(value.thickness) || DEFAULT_TAPE_THICKNESS
  }
  return value
}

function clampUint16(value) {
  const num = Math.round(Number(value) || 0)
  if (num < 0) return 0
  return num > 65535 ? 65535 : num
}

function stableStringify(value) {
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(',')}]`
  }
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`
  }
  return JSON.stringify(value)
}

function hexToRgba(hex, fallback) {
  if (!hex || typeof hex !== 'string') return fallback
  let value = hex.replace('#', '').trim()
  if (value.length === 3) {
    value = value.split('').map((c) => c + c).join('')
  }
  if (value.length !== 6) return fallback
  const num = parseInt(value, 16)
  if (Number.isNaN(num)) return fallback
  return [(num >> 16) & 255, (num >> 8) & 255, num & 255, 255]
}

function rgbaToHex(r, g, b) {
  const channel = (v) => Math.max(0, Math.min(255, Math.round(v || 0))).toString(16).padStart(2, '0')
  return `#${channel(r)}${channel(g)}${channel(b)}`
}
</script>
