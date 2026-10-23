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
            <!-- Lazy rendering: a message mounts only while it is (or is about to
                 be) visible. Off-screen messages keep their wrapper in the DOM —
                 so the mini-map keeps a 1:1 index mapping and the scroll height —
                 but render a skeleton that reserves the height measured the last
                 time the message was mounted (see `measuredHeights`). -->
            <template v-for="(message, ix) in messages" :key="message.doc_id || message.id">
              <div
                :ref="el => setMessageRef(el, ix, message)"
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
                  v-if="shouldRenderMessage(message)"
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

                <!-- Placeholder: reserves exactly the space the message needs.
                     Static (no shimmer) — it is mostly painted while scrolling,
                     where animation would be noise and extra compositor work. -->
                <div
                  v-else
                  class="rounded-lg overflow-hidden select-none"
                  :style="{ height: placeholderHeight(message) + 'px' }"
                  aria-hidden="true"
                >
                  <div class="h-full w-full rounded-lg bg-base-200/25 border border-base-content/5 px-2 py-2 space-y-2">
                    <div class="h-2.5 w-24 rounded-full bg-base-content/10"></div>
                    <div class="h-2.5 w-11/12 rounded-full bg-base-content/10"></div>
                    <div class="h-2.5 w-3/4 rounded-full bg-base-content/10"></div>
                  </div>
                </div>
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
      // ─── Lazy message rendering ───────────────────────────────────────────
      // key (doc_id) -> true while the heavy <ChatEntry> is mounted.
      renderedKeys: {},
      // key -> Date.now() when the message left the viewport (unload countdown).
      hiddenAt: {},
      // key -> last measured height (px). Reserves the space of unmounted
      // messages so the scroll position and the mini-map stay accurate.
      measuredHeights: {},
      // Fallback reservation for a message never rendered yet.
      estimatedHeight: 96,
      // Keep off-screen messages mounted this long before unloading them, so a
      // quick scroll back and forth doesn't thrash mount/unmount.
      unloadDelay: 30000,
      unloadSweepInterval: 2000,
      // Pre-render band around the viewport (pixels) — makes scrolling seamless.
      visibilityMargin: '600px 0px',
      // Messages rendered immediately at the bottom on chat open (no skeleton
      // flash for the content the user is looking at).
      initialRenderCount: 10,
      intersectionObserver: null,
      resizeObserver: null,
      unloadTimer: null,
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
      // Lazy state is per conversation: never carry rendered/hidden keys over.
      this.resetLazyRendering()
      this.primeVisibleMessages()
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
        // A new message is exactly what the user is looking at: mount it right
        // away instead of waiting for the visibility observer.
        this.primeLastMessage()
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
    this.primeVisibleMessages()
    this.setupLazyRendering()
    // Land at the bottom on first render.
    this.scrollToBottom(false)
  },
  beforeUnmount() {
    this.teardownLazyRendering()
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
    setMessageRef(el, ix, message) {
      // Vue 3 dynamic array refs — collect DOM elements by index.
      // `messageElRefs` must stay aligned with `messages` (1:1) for the mini-map,
      // so the wrapper stays in the DOM even when its content is not mounted.
      if (el) {
        if (this.messageElRefs[ix] !== el) {
          this.messageElRefs[ix] = el
        }
        this.observeMessageElement(el, this.messageKey(message))
        return
      }
      const removed = this.messageElRefs[ix]
      if (removed) {
        this.unobserveMessageElement(removed)
        this.messageElRefs[ix] = null
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
    },

    // ─────────────────────────────────────────────────────────────
    // Lazy rendering — only visible messages are mounted
    // ─────────────────────────────────────────────────────────────

    // Stable identity of a message (the same key the v-for uses).
    messageKey(message) {
      const key = message?.doc_id || message?.id
      return key ? String(key) : ''
    },
    // Messages whose child keeps live UI state and must never be unmounted:
    // still streaming, currently being edited, inline tools open, or the target
    // of the processing-details drawer.
    isPinnedMessage(message) {
      const key = this.messageKey(message)
      if (!message?.done) return true
      if (this.editMessage && this.messageKey(this.editMessage) === key) return true
      if (this.eventsOpenKey === key) return true
      if (this.showEventsPanel && this.activeEventsMessageKey === key) return true
      return false
    },
    shouldRenderMessage(message) {
      if (this.renderedKeys[this.messageKey(message)]) return true
      return this.isPinnedMessage(message)
    },
    // Reserved space for an unmounted message: its last real height, or the
    // estimate when it was never mounted.
    placeholderHeight(message) {
      const height = this.measuredHeights[this.messageKey(message)] || this.estimatedHeight
      return Math.max(Math.round(height), 56)
    },
    elementFor(key) {
      return (this.messageElRefs || []).find(el => el && el.dataset.lazyKey === key) || null
    },
    setupLazyRendering() {
      if (typeof IntersectionObserver === 'undefined') return
      this.intersectionObserver = new IntersectionObserver(this.handleIntersections, {
        root: this.scrollContainerEl,
        rootMargin: this.visibilityMargin,
        threshold: 0
      })
      this.resizeObserver = new ResizeObserver(this.handleMessageResize)
      // Elements rendered before the observers existed (first mount) register here.
      ;(this.messageElRefs || []).forEach((el, ix) => {
        if (el) this.observeMessageElement(el, this.messageKey(this.messages[ix]))
      })
    },
    teardownLazyRendering() {
      this.stopUnloadTimer()
      if (this.intersectionObserver) {
        this.intersectionObserver.disconnect()
        this.intersectionObserver = null
      }
      if (this.resizeObserver) {
        this.resizeObserver.disconnect()
        this.resizeObserver = null
      }
    },
    observeMessageElement(el, key) {
      if (!key) return
      if (el.dataset.lazyKey !== key) el.dataset.lazyKey = key
      // Idempotent: the ref callback runs on every patch.
      if (!this.intersectionObserver || el.dataset.lazyObserved === '1') return
      el.dataset.lazyObserved = '1'
      this.intersectionObserver.observe(el)
      this.resizeObserver?.observe(el)
    },
    unobserveMessageElement(el) {
      this.intersectionObserver?.unobserve(el)
      this.resizeObserver?.unobserve(el)
      delete el.dataset.lazyObserved
    },
    handleIntersections(entries) {
      entries.forEach(entry => {
        const key = entry.target.dataset.lazyKey
        if (!key) return
        if (entry.isIntersecting) {
          this.markMessageVisible(key)
        } else {
          this.markMessageHidden(key)
        }
      })
    },
    markMessageVisible(key) {
      delete this.hiddenAt[key]
      if (this.renderedKeys[key]) return
      this.renderedKeys[key] = true
      this.$nextTick(() => this.onMessageRendered(key))
    },
    markMessageHidden(key) {
      // Nothing mounted -> nothing to unload.
      if (!this.renderedKeys[key]) return
      if (this.hiddenAt[key]) return
      this.hiddenAt[key] = Date.now()
      this.startUnloadTimer()
    },
    // A message just got its real DOM: cache its height and keep the view steady.
    onMessageRendered(key) {
      const el = this.elementFor(key)
      if (!el) return
      const height = Math.round(el.getBoundingClientRect().height)
      if (!height) return
      const previous = this.measuredHeights[key]
      if (previous !== height) this.measuredHeights[key] = height
      // First measurement replaces the estimate -> the layout above may shift.
      if (!previous) this.keepViewportStable(el, height - this.estimatedHeight)
    },
    keepViewportStable(el, delta) {
      if (!delta) return
      if (this.autoScroll) {
        // Pinned to the bottom: just stay there.
        this.scrollToBottom(false)
        return
      }
      const container = this.scrollContainerEl
      if (!container) return
      const containerTop = container.getBoundingClientRect().top
      const rect = el.getBoundingClientRect()
      // Only content ABOVE the viewport can shift what the user is looking at.
      if (rect.bottom <= containerTop + 1) {
        container.scrollTop += delta
      }
    },
    handleMessageResize(entries) {
      entries.forEach(entry => {
        const key = entry.target.dataset.lazyKey
        if (!key) return
        const box = entry.borderBoxSize?.[0]
        const height = Math.round(box ? box.blockSize : entry.contentRect.height)
        if (!height) return
        if (this.measuredHeights[key] === height) return
        this.measuredHeights[key] = height
      })
    },
    // Store the current height BEFORE the child is removed, so the placeholder
    // reserves exactly the same space and the scroll position doesn't jump.
    cacheMessageHeight(key) {
      const el = this.elementFor(key)
      if (!el) return
      const height = Math.round(el.getBoundingClientRect().height)
      if (height > 0 && this.measuredHeights[key] !== height) {
        this.measuredHeights[key] = height
      }
    },
    startUnloadTimer() {
      if (this.unloadTimer) return
      this.unloadTimer = setInterval(() => this.sweepHiddenMessages(), this.unloadSweepInterval)
    },
    stopUnloadTimer() {
      if (this.unloadTimer) {
        clearInterval(this.unloadTimer)
        this.unloadTimer = null
      }
    },
    // Unmount messages that have been off-screen longer than `unloadDelay`.
    sweepHiddenMessages() {
      const now = Date.now()
      const keys = Object.keys(this.hiddenAt)
      if (!keys.length) {
        this.stopUnloadTimer()
        return
      }
      keys.forEach(key => {
        if (now - this.hiddenAt[key] < this.unloadDelay) return
        if (!this.renderedKeys[key]) {
          delete this.hiddenAt[key]
          return
        }
        const message = (this.messages || []).find(m => this.messageKey(m) === key)
        // Dropped from the list (filter/delete) — just forget it.
        if (!message) {
          delete this.renderedKeys[key]
          delete this.hiddenAt[key]
          return
        }
        // Live UI state (streaming, editing, events open) — pin it, retry later.
        if (this.isPinnedMessage(message)) {
          delete this.hiddenAt[key]
          return
        }
        this.cacheMessageHeight(key)
        delete this.renderedKeys[key]
        delete this.hiddenAt[key]
      })
      if (!Object.keys(this.hiddenAt).length) this.stopUnloadTimer()
    },
    resetLazyRendering() {
      this.renderedKeys = {}
      this.hiddenAt = {}
      this.stopUnloadTimer()
    },
    // Mount the last messages right away (they are what the user opens a chat
    // for) plus every message still generating.
    primeVisibleMessages() {
      const list = this.messages || []
      const from = Math.max(0, list.length - this.initialRenderCount)
      for (let ix = from; ix < list.length; ix++) {
        const key = this.messageKey(list[ix])
        if (key) this.renderedKeys[key] = true
      }
      list.filter(m => !m.done).forEach(m => {
        const key = this.messageKey(m)
        if (key) this.renderedKeys[key] = true
      })
    },
    primeLastMessage() {
      const list = this.messages || []
      const key = this.messageKey(list[list.length - 1])
      if (key) this.renderedKeys[key] = true
    }
  }
}
</script>