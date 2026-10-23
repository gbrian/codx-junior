<script setup>
import ChatEntry from '@/components/ChatEntry.vue'
import ChatEntryEventCard from '@/components/ChatEntryEventCard.vue'
import ChatEntryToolCard from '@/components/ChatEntryToolCard.vue'
import ChatEntryMetadata from '@/components/ChatEntryMetadata.vue'
import ChatAttachmentCard from '@/components/ChatAttachmentCard.vue'
import ChatMiniMap from '@/components/chat/ChatMiniMap.vue'
</script>

<template>
  <div class="w-full h-full flex gap-0 overflow-hidden @container/chat">

    <!-- Left Column: Events Panel (when open) -->
    <div
      v-if="showEventsPanel && activeMessageData"
      class="w-64 @3xl/chat:w-96 h-full border-r border-base-100 bg-base-200/50 flex flex-col flex-shrink-0 transition-all duration-300"
    >
      <!-- Header -->
      <div class="flex items-center justify-between px-4 py-3 border-b border-base-100 flex-shrink-0 bg-base-100">
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
        <!-- Attachments section -->
        <div v-if="activeMessageData.attachments && activeMessageData.attachments.length > 0" class="px-4 py-3 border-b border-base-100">
          <ChatAttachmentCard
            :attachments="activeMessageData.attachments"
            :isExpanded="true"
            @toggle="toggleExpanded('attachments')"
            @remove-attachment="removeAttachment"
          />
        </div>

        <!-- Summary section -->
        <div class="px-4 py-3 border-b border-base-100 flex-shrink-0">
          <h4 class="text-xs font-semibold text-base-content/70 mb-3 flex items-center gap-2">
            <i class="fa-solid fa-chart-line"></i> Summary
          </h4>
          <ChatEntryMetadata
            :metadata="activeMessageData.metadata"
            :toolCount="activeMessageData.toolCount"
            :lifecycleCount="activeMessageData.lifecycleCount"
            :attachmentCount="activeMessageData.attachmentCount"
          />
        </div>

        <!-- Tools section -->
        <div v-if="activeMessageData.toolEvents.length > 0" class="px-4 py-3 border-b border-base-100">
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
          <p>No events, tools, or attachments</p>
        </div>
      </div>

      <!-- Footer stats -->
      <div class="border-t border-base-100 px-4 py-2 text-xs text-base-content/60 flex-shrink-0 bg-base-100">
        <div class="flex justify-between items-center">
          <span>{{ activeMessageData.totalEvents }} item{{ activeMessageData.totalEvents !== 1 ? 's' : '' }}</span>
          <span v-if="activeMessageData.metadata?.time_taken" class="text-success">
            <i class="fa-solid fa-hourglass-end"></i> {{ formatDuration(activeMessageData.metadata.time_taken) }}
          </span>
        </div>
      </div>
    </div>

    <!-- Main Chat Column (right side or full width) -->
    <!-- Named container: chat panels can be any width (mobile, split view, dockview),
         so layout reacts to the panel width instead of the viewport. -->
    <div class="flex-1 h-full flex flex-col overflow-hidden @container/panel">

      <!-- Scrollable Messages Container + MiniMap side by side -->
      <div class="flex-1 flex overflow-hidden min-h-0">

        <!-- Scrollable Messages Container -->
        <div class="flex-1 overflow-y-auto overflow-x-hidden min-h-0" ref="scrollContainer" @scroll="onScroll">
          <div class="max-w-[860px] mx-auto flex flex-col px-3 py-3 @lg/panel:px-4 @lg/panel:py-6">

            <!-- ── Message Blocks ── -->
            <template v-for="(message, ix) in messages" :key="message.doc_id || message.id">
              <div
                :ref="el => setMessageRef(el, ix)"
                :class="[
                  'group/block relative rounded-lg transition-all duration-150',
                  isNewSpeaker(message, ix) ? 'mt-4 @lg/panel:mt-6' : 'mt-0.5',
                  editMessage
                    ? editMessage.doc_id === message.doc_id
                      ? 'ring-2 ring-warning bg-warning/5'
                      : 'opacity-40'
                    : '',
                ]"
              >
                <ChatEntry
                  :chat="chat"
                  :message="message"
                  :mentionList="mentionList"
                  :menu-less="readOnly"
                  :usersList="usersList"
                  :isNewSpeaker="isNewSpeaker(message, ix)"
                  :events-open="eventsOpenKey === (message.doc_id || message.id)"
                  :events-drawer-open="showEventsPanel && activeEventsMessageKey === (message.doc_id || message.id)"
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
                  @edit-message="$emit('edit-message', message)"
                  @code-file-shown.stop="$emit('code-file-shown', $event)"
                  @thread="$emit('thread', $event)"
                  @sub-task="$emit('sub-task', $event)"
                  @message-changed="$emit('message-changed', $event)"
                  @run-agents="$emit('run-agents', $event)"
                  @preview-file="$emit('preview-file', $event)"
                  @search-files="$emit('search-files', $event)"
                  @show-events="onShowEvents"
                  @show-events-drawer="onShowEventsDrawer"
                  @update-attachment="$emit('update-attachment', $event)"
                />
              </div>
            </template>

            <!-- ── Processing placeholder ── -->
            <!-- Immediate feedback that the server is working on the request.
                 Shown right after sending, until the first streamed chunk
                 arrives (then the real assistant bubble takes over). -->
            <div
              v-if="showProcessingPlaceholder"
              role="status"
              aria-live="polite"
              class="group/block relative rounded-lg mt-4 @lg/panel:mt-6"
            >
              <div class="flex gap-2 items-start w-full @lg/panel:gap-3">
                <div class="w-6 shrink-0 flex flex-col items-center pt-0.5 @lg/panel:w-7">
                  <img class="w-6" src="/only_icon.png" alt="Assistant" />
                </div>
                <div class="flex-1 min-w-0 pb-0.5">
                  <div class="flex items-center gap-2 mb-1 leading-none">
                    <span class="font-semibold text-sm text-base-content/80">Assistant</span>
                    <span class="text-[11px] text-base-content/40">Working…</span>
                  </div>
                  <div class="inline-flex items-center gap-2 rounded-lg px-4 py-3 bg-base-200/70 border border-base-100 text-base-content/60">
                    <span class="loading loading-dots loading-sm text-primary"></span>
                    <span class="text-xs">Waiting for the server to respond…</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Scroll anchor -->
            <div class="h-4" ref="anchor"></div>
          </div>
        </div>

        <!-- Right Mini-Map — pinned to the right of the messages column (desktop only) -->
        <div v-if="messages.length" class="shrink-0 h-full">
          <ChatMiniMap
            :messages="messages"
            :messageRefs="messageElRefs"
            :scrollContainer="scrollContainerEl"
          />
        </div>

      </div>

      <!-- Fixed Footer: Composer Section -->
      <!-- data-chat-composer marks the whole composer area, taps inside it keep the composer open on mobile -->
      <div v-if="!readOnly" class="shrink-0" data-chat-composer>
        <div class="max-w-[860px] mx-auto px-2 py-3 @lg/panel:px-4 @lg/panel:py-4 flex flex-col gap-1.5">

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
    'processing',
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
    'update-attachment',
  ],
  data() {
    return {
      // Full "Processing Details" drawer (one message at a time).
      showEventsPanel: false,
      activeEventsMessageKey: null,
      // Inline tools list, toggled from each message header.
      eventsOpenKey: null,
      expandedId: null,
      messageElRefs: [],
      scrollContainerEl: null,
      // ─── Auto-scroll state ────────────────────────────────────────────────
      // True while the view should keep following new/streamed messages. Set to
      // false the moment the user scrolls away from the bottom, and back to true
      // when they scroll back down (or send a new message).
      autoScroll: true,
      lastMessageCount: 0,
      // Distance (px) from the bottom still considered "at the bottom". Handles
      // fractional scroll positions and short-content rounding.
      bottomThreshold: 80,
    }
  },
  computed: {
    isVibe() {
      return this.chat.mode === 'vibe'
    },
    isMobile() {
      return this.$ui?.isMobile
    },
    // True while an assistant message is still streaming — in that case the
    // assistant's own bubble already shows the loading state, so the
    // processing placeholder must stay hidden.
    hasStreamingAssistantMessage() {
      return (this.messages || []).some(m => m.role === 'assistant' && !m.done)
    },
    // Show the placeholder only while the chat is processing and the assistant
    // has not started streaming yet.
    showProcessingPlaceholder() {
      return !!this.processing && !this.hasStreamingAssistantMessage
    },
    // Lightweight fingerprint of the conversation used to trigger auto-scroll.
    // Changes when a message is added, when the last message's content grows
    // (streaming) or when its `done`/`think` state flips.
    messagesSignal() {
      const list = this.messages || []
      const last = list[list.length - 1]
      return [
        list.length,
        last?.doc_id || last?.id || '',
        (last?.content || '').length,
        (last?.think || '').length,
        last?.done ? 1 : 0,
      ].join(':')
    },
    // Live data for the events drawer. It is derived from the reactive `messages`
    // prop (looked up by the active drawer message key), so newly streamed
    // tools/events appear immediately without having to close and reopen it.
    activeMessageData() {
      const key = this.activeEventsMessageKey
      if (!key) return null
      const message = this.messages?.find(m => (m.doc_id || m.id) === key)
      if (!message) return null

      const toolEvents = message.tool_events || []
      const lifecycleEvents = message.lifecycle_events || []
      const attachments = message.attachments || []

      return {
        toolEvents,
        lifecycleEvents,
        attachments,
        metadata: message.meta_data,
        toolCount: toolEvents.length,
        lifecycleCount: lifecycleEvents.length,
        attachmentCount: attachments.length,
        totalEvents: toolEvents.length + lifecycleEvents.length + attachments.length,
      }
    }
  },
  watch: {
    'chat.id': function() {
      this.closeEventsPanel()
      this.eventsOpenKey = null
      // Opening a different chat: start pinned to the bottom so the latest
      // messages are visible.
      this.autoScroll = true
      this.lastMessageCount = (this.messages || []).length
      this.scrollToBottom(false)
    },
    // React to any change in the conversation (new message or streaming update).
    messagesSignal() {
      const count = (this.messages || []).length
      const grew = count !== this.lastMessageCount
      this.lastMessageCount = count

      if (grew) {
        // A brand new message (user send or assistant start) always pulls the
        // view back to the bottom, even if the user had scrolled up.
        this.autoScroll = true
        this.scrollToBottom(false)
        return
      }

      // Content is updating in place (streaming) — keep following only while
      // the user is still pinned to the bottom.
      if (this.autoScroll) {
        this.scrollToBottom(false)
      }
    },
    // Keep the placeholder visible right after sending.
    showProcessingPlaceholder(val) {
      if (val && this.autoScroll) {
        this.scrollToBottom(false)
      }
    }
  },
  mounted() {
    this.scrollContainerEl = this.$refs.scrollContainer
    this.lastMessageCount = (this.messages || []).length
    // Land at the bottom on first render.
    this.scrollToBottom(false)
  },
  methods: {
    // Whether the scroll container is currently at (or very near) the bottom.
    isAtBottom() {
      const el = this.scrollContainerEl
      if (!el) return true
      const distance = el.scrollHeight - el.scrollTop - el.clientHeight
      return distance <= this.bottomThreshold
    },
    // User scrolled: refresh the pinned state. Scrolling to the bottom re-pins
    // (so new data keeps coming into view); scrolling up un-pins.
    onScroll() {
      this.autoScroll = this.isAtBottom()
    },
    // Scroll to the bottom of the conversation. Automatic follow uses instant
    // scrolling so intermediate scroll events can't accidentally un-pin the view.
    scrollToBottom(smooth = false) {
      this.$nextTick(() => {
        const el = this.scrollContainerEl
        if (!el) return
        if (smooth) {
          el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
        } else {
          el.scrollTop = el.scrollHeight
        }
      })
    },
    scrollToTop() {
      if (this.scrollContainerEl) {
        this.scrollContainerEl.scrollTop = 0
      }
    },
    isNewSpeaker(message, ix) {
      if (ix === 0) return true
      const prev = this.messages[ix - 1]
      return prev.role !== message.role || prev.user !== message.user
    },
    setMessageRef(el, ix) {
      // Vue 3 dynamic array refs — collect DOM elements by index
      if (el) {
        this.messageElRefs[ix] = el
      }
    },
    // Inline tools list (rendered inside the message bubble). The parent only
    // tracks which message's inline panel is expanded; clicking the same message
    // again collapses it. The drawer is handled separately (see onShowEventsDrawer).
    onShowEvents(message) {
      const key = message?.doc_id || message?.id
      if (!key) return
      this.eventsOpenKey = this.eventsOpenKey === key ? null : key
    },
    // Dedicated side drawer with the full processing details. Toggles closed
    // when the same message is requested again.
    onShowEventsDrawer(message) {
      const key = message?.doc_id || message?.id
      if (!key) return
      if (this.showEventsPanel && this.activeEventsMessageKey === key) {
        this.closeEventsPanel()
        return
      }
      this.activeEventsMessageKey = key
      this.showEventsPanel = true
      this.expandedId = null
    },
    closeEventsPanel() {
      this.showEventsPanel = false
      this.activeEventsMessageKey = null
    },
    toggleExpanded(eventId) {
      this.expandedId = this.expandedId === eventId ? null : eventId
    },
    removeAttachment(idx) {
      if (this.activeMessageData && this.activeMessageData.attachments) {
        this.activeMessageData.attachments.splice(idx, 1)
      }
    },
    formatDuration(seconds) {
      if (!seconds) return '0s'
      const baseMoment = moment({ h: 0, m: 0, s: 0, ms: 0 })
      return baseMoment.add(Math.floor(seconds), 'seconds').format('mm:ss')
    }
  }
}
</script>