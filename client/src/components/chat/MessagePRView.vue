<script setup>
import CodeViewer from '../CodeViewer.vue'
</script>

<template>
  <div class="flex flex-col gap-4 p-4 bg-base-200 rounded-lg">
    <div class="text-lg font-bold flex gap-2 items-center">
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
      <CodeViewer
        v-for="(block, index) in codeBlocks"
        :key="index"
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
</template>

<script>
export default {
  props: ['codeBlocks', 'chat', 'message', 'activeBranch'],
  emits: ['save-file', 'add-file', 'open-file', 'sub-task']
}
</script>