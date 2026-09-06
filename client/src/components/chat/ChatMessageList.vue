<script setup>
import ChatEntry from '@/components/ChatEntry.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col overflow-hidden">
    
    <!-- Scrollable Messages Container -->
    <div class="flex-1 overflow-y-auto min-h-0">
      <div class="max-w-[860px] mx-auto flex flex-col px-4 py-6">

        <!-- ── Message Blocks ── -->
        <template v-for="(message, ix) in messages" :key="message.doc_id || message.id">
          <div
            :class="[
              'group/block relative',
              isNewSpeaker(message, ix) ? 'mt-6' : 'mt-0.5',
            ]"
          >
            <ChatEntry
              :chat="chat"
              :message="message"
              :mentionList="mentionList"
              :menu-less="readOnly"
              :usersList="usersList"
              :isNewSpeaker="isNewSpeaker(message, ix)"
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
        </template>

        <!-- Scroll anchor -->
        <div class="h-4" ref="anchor"></div>
      </div>
    </div>

    <!-- Fixed Footer: Composer Section -->
    <div v-if="!readOnly" class="shrink-0">
      <div class="max-w-[860px] mx-auto px-4 py-4 flex flex-col gap-1.5">

        <!-- IntelliSense dropdown — appears above composer -->
        <div class="relative z-50">
          <slot name="intellisense" />
        </div>

        <!-- The input box itself -->
        <slot name="input" />

        <!-- Attached files row — below composer -->
        <slot name="files" />

      </div>
    </div>
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
    'search-files',
    'preview-file',
  ],
  computed: {
    isVibe() {
      return this.chat.mode === 'vibe'
    }
  },
  methods: {
    scrollToBottom() {
      setTimeout(() => this.$refs.anchor?.scrollIntoView({ behavior: 'smooth' }), 200)
    },
    isNewSpeaker(message, ix) {
      if (ix === 0) return true
      const prev = this.messages[ix - 1]
      return prev.role !== message.role || prev.user !== message.user
    }
  }
}
</script>