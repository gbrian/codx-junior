<script setup>
// imports only
</script>

<template>
  <div
    class="relative w-5 h-full flex-shrink-0 flex flex-col bg-base-200/30 border-l border-base-300/50 cursor-pointer select-none overflow-hidden"
    ref="trackEl"
    @click="onTrackClick"
    title="Mini-map — click to navigate"
  >
    <!-- Viewport indicator -->
    <div
      v-if="viewportIndicator.height > 0"
      class="absolute left-0 right-0 bg-base-content/10 border border-base-content/20 rounded-sm pointer-events-none transition-all duration-100"
      :style="{
        top: viewportIndicator.top + 'px',
        height: viewportIndicator.height + 'px',
      }"
    ></div>

    <!-- Message marks -->
    <div
      v-for="(mark, ix) in marks"
      :key="mark.id"
      class="absolute left-0.5 right-0.5 rounded-sm mb-0.5 opacity-30 hover:opacity-60 transition-all duration-150 flex items-center justify-center"
      :class="markClass(mark)"
      :style="{
        top: mark.top + 'px',
        height: Math.max(mark.height, 3) + 'px',
      }"
      :title="markTitle(mark, ix)"
      @click.stop="scrollToMark(mark)"
    >
    </div>
  </div>
</template>

<script>
export default {
  props: {
    messages: {
      type: Array,
      default: () => []
    },
    messageRefs: {
      type: Array,
      default: () => []
    },
    scrollContainer: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      marks: [],
      viewportIndicator: { top: 0, height: 0 },
      rafId: null,
      resizeObserver: null,
    }
  },
  mounted() {
    this.$nextTick(() => this.attachScrollListener())
  },
  beforeUnmount() {
    this.detachScrollListener()
  },
  watch: {
    messages() {
      this.$nextTick(() => this.recalculate())
    },
    messageRefs() {
      this.$nextTick(() => this.recalculate())
    },
    scrollContainer(newVal) {
      this.detachScrollListener()
      if (newVal) this.attachScrollListener()
    }
  },
  methods: {
    attachScrollListener() {
      const el = this.scrollContainer
      if (!el) return
      el.addEventListener('scroll', this.onScroll, { passive: true })
      // Also watch resize
      this.resizeObserver = new ResizeObserver(() => this.recalculate())
      this.resizeObserver.observe(el)
      this.recalculate()
    },
    detachScrollListener() {
      const el = this.scrollContainer
      if (el) el.removeEventListener('scroll', this.onScroll)
      if (this.resizeObserver) {
        this.resizeObserver.disconnect()
        this.resizeObserver = null
      }
    },
    onScroll() {
      if (this.rafId) cancelAnimationFrame(this.rafId)
      this.rafId = requestAnimationFrame(() => this.recalculate())
    },
    recalculate() {
      const container = this.scrollContainer
      const track = this.$refs.trackEl
      if (!container || !track || !this.messageRefs.length) {
        this.marks = []
        this.viewportIndicator = { top: 0, height: 0 }
        return
      }

      const containerRect = container.getBoundingClientRect()
      const totalScrollHeight = container.scrollHeight
      const trackHeight = track.clientHeight

      // Scale factor: map scrollHeight → trackHeight
      const scale = trackHeight / Math.max(totalScrollHeight, 1)

      // Build marks
      const newMarks = []
      const currentUsername = this.$user?.username
      
      for (let i = 0; i < this.messageRefs.length; i++) {
        const el = this.messageRefs[i]
        const msg = this.messages[i]
        if (!el || !msg) continue

        const elRect = el.getBoundingClientRect()
        // Position relative to scroll content (not viewport)
        const topInScroll = elRect.top - containerRect.top + container.scrollTop
        const markTop = topInScroll * scale
        const markHeight = Math.max(elRect.height * scale, 3)

        // Check if current user has read this message
        const hasSeen = msg.read_by && msg.read_by.includes(currentUsername)

        newMarks.push({
          id: msg.doc_id || msg.id || i,
          top: markTop,
          height: markHeight,
          role: msg.role,
          isAnswer: msg.is_answer,
          isHidden: msg.hide,
          hasDone: msg.done,
          hasTools: (msg.tool_events?.length || 0) > 0,
          hasSeen: hasSeen,
          user: msg.user,
          scrollTop: topInScroll,
        })
      }
      this.marks = newMarks

      // Viewport indicator
      const viewportTopPx = container.scrollTop * scale
      const viewportHeightPx = container.clientHeight * scale
      this.viewportIndicator = {
        top: viewportTopPx,
        height: viewportHeightPx,
      }
    },
    markClass(mark) {
      function baseClass() {
        if (mark.isHidden) return 'bg-warning'
        if (mark.isAnswer) return 'bg-success'
        if (mark.role === 'assistant') {
          return mark.hasTools ? 'bg-warning' : 'bg-info'
        }
        // user message
        return 'bg-primary'
      }
      return [
        baseClass(),
        'border-l-6',
        mark.hasSeen ? 'border-success' : 'border-error'
      ].join(" ")
    },
    markTitle(mark, ix) {
      const role = mark.role === 'assistant' ? '🤖 Assistant' : `👤 ${mark.user || 'User'}`
      const status = mark.isHidden ? ' [archived]' : ''
      const tools = mark.hasTools ? ' [has tools]' : ''
      const readStatus = mark.role === 'assistant' ? (mark.hasSeen ? ' [seen]' : ' [unseen]') : ''
      return `#${ix + 1} ${role}${tools}${status}${readStatus}`
    },
    scrollToMark(mark) {
      const container = this.scrollContainer
      if (!container) return
      container.scrollTo({ top: mark.scrollTop - 16, behavior: 'smooth' })
    },
    onTrackClick(e) {
      const track = this.$refs.trackEl
      const container = this.scrollContainer
      if (!track || !container) return
      const rect = track.getBoundingClientRect()
      const clickRatio = (e.clientY - rect.top) / track.clientHeight
      const targetScrollTop = clickRatio * container.scrollHeight
      container.scrollTo({ top: targetScrollTop - container.clientHeight / 2, behavior: 'smooth' })
    }
  }
}
</script>