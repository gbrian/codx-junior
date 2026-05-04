<script setup>
import ChatEntry from '@/components/ChatEntry.vue'
import TaskCard from '../kanban/TaskCard.vue'
</script>

<template>
  <div class="overflow-y-auto w-full h-full">
    <div
      class="flex flex-col overflow-y-auto overflow-x-hidden w-full"
      v-for="(message, ix) in messages"
      :key="message.id"
    >
      <ChatEntry
        :class="[
          'max-w-full mb-4 rounded-md hover:bg-base-200 border border-slate-600/0 hover:border-slate-600/70 rounded-lg',
          isChannel ? '' : 'py-2',
          editMessage
            ? editMessage === message
              ? 'border border-warning'
              : 'opacity-40'
            : ''
        ]"
        :chat="chat"
        :message="message"
        :isTopic="isTopic && !ix"
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
        @edit-message="$emit('edit-message', { event: $event, message })"
        @code-file-shown.stop="$emit('code-file-shown', $event)"
        @thread="$emit('thread', $event)"
        @sub-task="$emit('sub-task', $event)"
      />
    </div>

    <!-- Scroll anchor -->
    <div class="anchor" ref="anchor"></div>

    <!-- Child chats grid -->
    <div class="grid grid-cols-3 gap-2 mb-2" v-if="childrenChats?.length">
      <div v-for="child in childrenChats" :key="child.id" class="relative">
        <TaskCard
          class="click p-2 bg-base-100 h-40"
          :task="child"
          @click="$emit('set-active-chat', child)"
        />
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
    'isChannel',
    'isTopic'
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
    'set-active-chat'
  ],
  methods: {
    scrollToBottom() {
      setTimeout(() => this.$refs.anchor?.scrollIntoView(), 200)
    }
  }
}
</script>