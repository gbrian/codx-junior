<script setup>
import ChatEntry from '@/components/ChatEntry.vue'
import ChatEntryEventCard from '@/components/ChatEntryEventCard.vue'
import ChatEntryToolCard from '@/components/ChatEntryToolCard.vue'
import ChatEntryMetadata from '@/components/ChatEntryMetadata.vue'
</script>

<template>
  <div class="w-full h-full flex gap-0 overflow-hidden">
    
    <!-- Left Column: Events Panel (when open) -->
    <div
      v-if="showEventsPanel && activeMessageData"
      class="w-96 h-full border-r border-base-300 bg-base-200/50 flex flex-col flex-shrink-0 transition-all duration-300"
    >
      <!-- Header -->
      <div class="flex items-center justify-between px-4 py-3 border-b border-base-300 flex-shrink-0 bg-base-100">
        <h3 class="font-semibold text-sm flex items-center gap-2">
          <i class="fa-solid fa-stream text-info"></i>
          Processing Details
        </h3>
        <button
          @click="closeEventsPanel"
          class="btn btn-xs btn-ghost"
        >
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <!-- Scrollable Content -->
      <div class="flex-1 overflow-y-auto">
        <!-- Summary section -->
        <div class="px-4 py-3 border-b border-base-300 flex-shrink-0">
          <h4 class="text-xs font-semibold text-base-content/70 mb-3 flex items-center gap-2">
            <i class="fa-solid fa-chart-line"></i> Summary
          </h4>
          <ChatEntryMetadata
            :metadata="activeMessageData.metadata"
            :toolCount="activeMessageData.toolCount"
            :lifecycleCount="activeMessageData.lifecycleCount"
          />
        </div>

        <!-- Tools section -->
        <div v-if="activeMessageData.toolEvents.length > 0" class="px-4 py-3 border-b border-base-300">
          <h4 class="text-xs font-semibold text-base-content/70 mb-2 flex items-center gap-2">
            <i class="fa-solid fa-wrench text-warning"></i> Tools ({{ activeMessageData.toolCount }})
          </h4>
          <div class="space-y-2">
            <ChatEntryToolCard
              v-for="(event, idx) in activeMessageData.toolEvents"
              :key="`tool-${idx}`"
              :event="{ data: event, type: 'tool', timestamp: event.created_at || event.timestamp }"
              :isExpanded="true"
              @toggle="toggleExpanded(`tool-${idx}`)"
            />
          </div>
        </div>

        <!-- Events section -->
        <div v-if="activeMessageData.lifecycleEvents.length > 0" class="px-4 py-3">
          <h4 class="text-xs font-semibold text-base-content/70 mb-2 flex items-center gap-2">
            <i class="fa-solid fa-list text-info"></i> Events ({{ activeMessageData.lifecycleCount }})
          </h4>
          <div class="space-y-2">
            <ChatEntryEventCard
              v-for="(event, idx) in activeMessageData.lifecycleEvents"
              :key="`lifecycle-${idx}`"
              :event="{ data: event, type: 'lifecycle', timestamp: event.created_at || event.timestamp }"
              :isExpanded="true"
              @toggle="toggleExpanded(`lifecycle-${idx}`)"
            />
          </div>
        </div>

        <!-- Empty state -->
        <div v-if="activeMessageData.totalEvents === 0" class="text-center py-12 text-base-content/50 text-sm">
          <i class="fa-solid fa-inbox text-2xl mb-2 block"></i>
          <p>No events or tools executed</p>
        </div>
      </div>

      <!-- Footer stats -->
      <div class="border-t border-base-300 px-4 py-2 text-xs text-base-content/60 flex-shrink-0 bg-base-100">
        <div class="flex justify-between items-center">
          <span>{{ activeMessageData.totalEvents }} event{{ activeMessageData.totalEvents !== 1 ? 's' : '' }}</span>
          <span v-if="activeMessageData.metadata?.time_taken" class="text-success">
            <i class="fa-solid fa-hourglass-end"></i> {{ formatDuration(activeMessageData.metadata.time_taken) }}
          </span>
        </div>
      </div>
    </div>

    <!-- Main Chat Column (right side or full width) -->
    <div class="flex-1 h-full flex flex-col overflow-hidden">
      
      <!-- Scrollable Messages Container -->
      <div class="flex-1 overflow-y-auto overflow-x-hidden min-h-0">
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
                @show-events="onShowEvents"
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
  </div>
</template>

<script>
import moment from 'moment'

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
  data() {
    return {
      showEventsPanel: false,
      activeMessageData: null,
      expandedId: null
    }
  },
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
    },
    onShowEvents(eventData) {
      this.activeMessageData = eventData
      this.showEventsPanel = true
      this.expandedId = null
    },
    closeEventsPanel() {
      this.showEventsPanel = false
      this.activeMessageData = null
    },
    toggleExpanded(eventId) {
      this.expandedId = this.expandedId === eventId ? null : eventId
    },
    formatDuration(seconds) {
      if (!seconds) return '0s'
      const baseMoment = moment({ h: 0, m: 0, s: 0, ms: 0 })
      return baseMoment.add(Math.floor(seconds), 'seconds').format('mm:ss')
    }
  }
}
</script>