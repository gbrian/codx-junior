<script setup>
import CodeViewer from '../CodeViewer.vue'
</script>

<template>
  <div class="flex flex-col gap-4 bg-base-200 rounded-lg">
    <!-- Code blocks section — each row can be picked for a bulk save -->
    <div v-if="codeBlocks.length" class="flex flex-col gap-3">
      <div
        v-for="(block, index) in codeBlocks"
        :key="`code-${index}`"
        class="flex items-start gap-2"
      >
        <!-- Selection checkbox (only for blocks written to disk) -->
        <label
          v-if="selectionKeys[index]"
          class="shrink-0 pt-3 cursor-pointer tooltip tooltip-right"
          :data-tip="`Select ${block.filePath}`"
        >
          <input
            type="checkbox"
            class="checkbox checkbox-sm checkbox-primary"
            :checked="isSelected(index)"
            :disabled="savingSelection"
            :aria-label="`Select ${block.filePath}`"
            @change="$emit('toggle-select', selectionKeys[index])"
          />
        </label>

        <div class="min-w-0 flex-1">
          <CodeViewer
            :code="block.content"
            :language="block.language"
            :file="block.filePath"
            :finished="true"
            :chat="chat"
            :showCodeOpened="true"
            :message="message"
            :diff-option="true"
            @save-file="$emit('save-file', $event)"
            @add-file="$emit('add-file', $event)"
            @open-file="$emit('open-file', $event)"
            @sub-task="$emit('sub-task', $event)"
          />
        </div>
      </div>
    </div>

    <!-- Linked files not in code blocks -->
    <div 
      v-for="file in linkedFilesNotInBlocks" 
      :key="file"
      class="flex gap-2 items-center text-xs p-2 bg-base-100 rounded-md"
    >
      <button
        class="btn btn-xs btn-ghost gap-1 tooltip tooltip-left"
        data-tip="Add file to chat"
        @click.stop="$emit('add-file', file)"
      >
        <i class="fa-solid fa-plus"></i>
      </button>
      <i class="fa-solid fa-file text-primary"></i>
      <a 
        class="hover:underline cursor-pointer flex-1 truncate" 
        @click="$emit('open-file', file)" 
        :title="file"
      >
        {{ file.split('/').reverse()[0] }}
      </a>
      <i 
        class="fa-regular fa-circle-xmark cursor-pointer hover:text-error" 
        @click.stop="$emit('remove-file', file)"
      ></i>
    </div>

    <!-- Empty state -->
    <div v-if="!codeBlocks.length && !linkedFilesNotInBlocks.length" class="text-center text-base-300 py-4">
      <i class="fa-solid fa-inbox text-lg mb-2"></i>
      <p class="text-sm">No files to display</p>
    </div>
  </div>
</template>

<script>
export default {
  props: ['codeBlocks', 'linkedFiles', 'chat', 'message', 'selectionKeys', 'selectedKeys', 'savingSelection'],
  emits: ['save-file', 'add-file', 'open-file', 'sub-task', 'remove-file', 'toggle-select'],
  computed: {
    linkedFilesNotInBlocks() {
      return this.linkedFiles
      if (!this.linkedFiles?.length) return []
      
      const codeBlockPaths = this.codeBlocks.map(b => b.filePath).filter(Boolean)
      
      return this.linkedFiles.filter(file => !codeBlockPaths.includes(file))
    }
  },
  methods: {
    // Selection state is owned by ChatEntry; this component only renders it.
    isSelected(index) {
      const key = this.selectionKeys?.[index]
      return !!key && (this.selectedKeys || []).includes(key)
    }
  }
}
</script>