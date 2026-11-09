<script setup>
import { ref } from 'vue'
import BlockEditor from '../BlockEditor.vue'

const props = defineProps({
  content: { type: String, default: '' },
  blockIndex: { type: Number, default: 0 },
  editable: { type: Boolean, default: false },
  label: { type: String, default: 'Editing markdown block' }
})

const emit = defineEmits(['save'])
const blockEditor = ref(null)
const editing = ref(false)

function startEdit() {
  if (!props.editable) return
  blockEditor.value?.startEdit()
}

function onSave({ originalContent, newContent }) {
  editing.value = false
  emit('save', {
    originalContent,
    newContent,
    blockIndex: props.blockIndex
  })
}
</script>

<template>
  <div class="group/editable-block relative">
    <!-- Block-level edit affordance. Kept visible on touch layouts (there is no
         hover) and revealed on hover/focus for pointer layouts. -->
    <div
      v-if="editable && !editing"
      class="absolute -top-2 right-0 z-20 flex items-center gap-1 rounded-lg border border-base-content/10 bg-base-100/90 px-1 py-0.5 shadow-sm opacity-0 transition-opacity group-hover/editable-block:opacity-100 focus-within:opacity-100 max-md:opacity-100"
    >
      <button
        class="btn btn-xs btn-ghost gap-1 tooltip tooltip-left"
        data-tip="Edit this block"
        aria-label="Edit this block"
        @click.stop.prevent="startEdit"
      >
        <i class="fa-solid fa-pen-to-square"></i>
        <span class="text-[11px]">Edit</span>
      </button>
    </div>

    <BlockEditor
      ref="blockEditor"
      :original-content="content"
      :is-code-block="false"
      :label="label"
      @edit-start="editing = true"
      @edit-cancel="editing = false"
      @edit-save="onSave"
    >
      <slot></slot>
    </BlockEditor>
  </div>
</template>
