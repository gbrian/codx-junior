<script setup>
import CanvaEditor from './CanvaEditor.vue'
</script>

<template>
  <!--
    Inline preview/editor of a `canva` code block.

    The stored definition is a JSON string, but <CanvaEditor> works with a plain
    node array. This wrapper parses one into the other and keeps every visual
    change PENDING until the user decides:

    - Save:    bubbles the new definition up through `change` so the consumer
               updates the code block (and the chat message).
    - Discard: reloads the last saved definition and drops the pending edits.

    A fixed (resizable) height is required because chat blocks are inline and
    <CanvaEditor> itself expands to `h-full`.
  -->
  <div class="w-full rounded-lg border border-base-100 bg-base-300 overflow-hidden">
    <!-- Unsaved changes toolbar -->
    <div
      class="flex items-center gap-2 px-3 py-2 border-b border-base-100 bg-base-200"
      v-if="dirty"
    >
      <span class="text-xs opacity-60 mr-auto flex items-center gap-1.5">
        <span class="w-1.5 h-1.5 rounded-full bg-warning"></span>
        Unsaved changes
      </span>
      <button class="btn btn-xs btn-ghost" @click="discard">
        Discard
      </button>
      <button class="btn btn-xs btn-primary" @click="save">
        <i class="fa-solid fa-floppy-disk"></i>
        Save
      </button>
    </div>

    <div class="w-full h-96 min-h-64 max-h-[80vh] resize-y overflow-hidden">
      <CanvaEditor
        class="w-full h-full"
        :modelValue="nodes"
        @update:modelValue="onCanvasUpdate"
      />
    </div>
  </div>
</template>

<script>
export default {
  name: 'CanvaViewer',
  props: {
    // Raw canva definition stored in the code block. Accepts both a root array
    // of nodes and the { nodes: [...] } envelope used by `.canva` files.
    text: {
      type: String,
      default: ''
    }
  },
  emits: ['change'],
  data() {
    return {
      // Parsed definition handed to <CanvaEditor>. Only replaced on external
      // changes so canvas edits never wipe the workspace.
      nodes: [],
      // Canonical encoding of the definition that is currently persisted.
      savedText: null,
      // Canonical encoding of the edits made on the canvas but not saved yet.
      pendingText: null
    }
  },
  computed: {
    // There are canvas edits that were not committed yet.
    dirty() {
      return this.pendingText !== null && this.pendingText !== this.savedText
    }
  },
  created() {
    this.savedText = this.text || null
    this.nodes = this.parseDefinition(this.text)
  },
  watch: {
    text(newText) {
      // Ignore the echo of the change we just emitted after saving.
      if ((newText || null) === this.savedText) return
      this.savedText = newText || null
      this.pendingText = null
      this.nodes = this.parseDefinition(newText)
    }
  },
  methods: {
    // Accept both a root array and a { nodes: [...] } envelope
    parseDefinition(content) {
      if (!content) return []
      try {
        const parsed = JSON.parse(content)
        return Array.isArray(parsed) ? parsed : (parsed.nodes || [])
      } catch (ex) {
        console.warn('Invalid canva definition', ex)
        return []
      }
    },
    // Canvas changed: hold the new definition as pending so the user decides
    // when it is persisted through Save.
    onCanvasUpdate(nodes) {
      this.pendingText = JSON.stringify({ nodes }, null, 2)
    },
    // Commit the pending definition. The consumer is responsible for updating
    // the code block (and the chat message) with the emitted JSON.
    save() {
      if (!this.dirty) return
      this.savedText = this.pendingText
      this.pendingText = null
      this.$emit('change', this.savedText)
    },
    // Drop the pending edits and reload the last saved definition. A fresh array
    // reference forces <CanvaEditor> to rebuild its workspace.
    discard() {
      this.pendingText = null
      this.nodes = [...this.parseDefinition(this.savedText)]
    }
  }
}
</script>