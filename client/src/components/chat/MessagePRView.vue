<script setup>
import CodeViewer from '../CodeViewer.vue'
</script>

<template>
  <div class="flex flex-col gap-4 p-4 bg-base-200 rounded-lg">
    <div class="text-lg font-bold flex gap-2 items-center flex-wrap">
      <i class="fa-solid fa-code-branch"></i>
      PR View - {{ codeBlocks.length }} file(s)
      <span class="badge badge-sm badge-info" v-if="activeBranch">
        Active branch: <span class="font-mono ml-1">{{ activeBranch }}</span>
      </span>
      <span class="badge badge-sm badge-ghost" v-else>
        <span class="loading loading-xs"></span>
        Loading branch...
      </span>
    </div>
    
    <div class="flex flex-col gap-3">
      <div
        v-for="(block, index) in codeBlocks"
        :key="index"
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
  </div>
</template>

<script>
export default {
  props: ['codeBlocks', 'chat', 'message', 'activeBranch', 'selectionKeys', 'selectedKeys', 'savingSelection'],
  emits: ['save-file', 'add-file', 'open-file', 'sub-task', 'toggle-select'],
  methods: {
    // Selection state is owned by ChatEntry; this component only renders it.
    isSelected(index) {
      const key = this.selectionKeys?.[index]
      return !!key && (this.selectedKeys || []).includes(key)
    }
  }
}
</script>