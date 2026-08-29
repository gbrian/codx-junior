<script setup>
import ChatEntry from '@/components/ChatEntry.vue'
</script>

<template>
  <div class="overflow-y-auto w-full h-full">
    <!-- Use doc_id as stable key to prevent remounts on content changes -->
    <div v-for="(message, ix) in messages"
      :key="message.doc_id || message.id"
      :class="[
          'max-w-full my-2 rounded-md hover:bg-base-200 border border-slate-600/0 hover:border-slate-600/70 rounded-lg',
        ]"
    >
      <ChatEntry
        :chat="chat"
        :message="message"
        :mentionList="mentionList"
        :menu-less="readOnly"
        :usersList="usersList"
        @edited="$emit('edited', $event)"
        @enhance="$emit('enhance', message)"
        @remove="$emit('remove', message)"
        @remove-file="$emit('remove-file', { message, file: $event })"
        @hide="$emit('hide', message)"
        @answer="$emit('answer', message)"
        @run-edit="$emit('run-edit', $event)"
        @copy="$emit('copy', message)"
        @add-file-to-chat="$emit('add-file-to-chat', $event)"
        @image="$emit('image', { ...$event, readonly: true })"
        @generate-code="$emit('generate-code', $event)"
        @reload-file="$emit('reload-file', $event)"
        @open-file="$emit('open-file', $event)"
        @save-file="$emit('save-file', $event)"
        @add-file="$emit('add-file', $event)"
        @edit-message="$emit('edit-message', $event)"
        @code-file-shown.stop="$emit('code-file-shown', $event)"
        @thread="$emit('thread', $event)"
        @sub-task="$emit('sub-task', $event)"
        @message-changed="$emit('message-changed', $event)"
        @run-agents="$emit('run-agents', $event)"
        @preview-file="$emit('preview-file', $event)"
        @search-files="$emit('search-files', $event)"
      />
    </div>
    <!-- Scroll anchor -->
    <div class="anchor" ref="anchor"></div>

  </div>
</template>

<script>
export default {
  props: [
    'chat',
    'messages',
    'editMessage',
    'mentionList',
    'readOnly',
    'usersList',
    'childrenChats',
  ],
  emits: [
    'edited',
    'enhance',
    'remove',
    'remove-file',
    'hide',
    'answer',
    'run-edit',
    'copy',
    'add-file-to-chat',
    'image',
    'generate-code',
    'reload-file',
    'open-file',
    'save-file',
    'add-file',
    'edit-message',
    'code-file-shown',
    'thread',
    'sub-task',
    'set-active-chat',
    'message-changed',
    'run-agents',
    'search-files'
  ],
  computed: {
    isVibe() {
      return this.chat.mode === 'vibe'
    }
  },
  methods: {
    scrollToBottom() {
      setTimeout(() => this.$refs.anchor?.scrollIntoView(), 200)
    }
  }
}
</script>