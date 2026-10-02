<script setup>
import moment from 'moment'
import Markdown from '../Markdown.vue'
</script>

<template>
  <div class="flex flex-col h-full gap-2">
    <!-- Header -->
    <div class="flex items-center justify-between shrink-0 px-2 pt-2">
      <label class="text-sm font-semibold text-base-content/70 flex items-center gap-2">
        <i class="fa-solid fa-history"></i>
        History Wall
      </label>
      <span class="badge badge-md badge-ghost">{{ history.length }} entries</span>
    </div>

    <!-- Scrollable Wall Container -->
    <div class="flex-1 overflow-y-auto scrollbar-thin px-2 pb-2 space-y-3">
      <!-- History Entries -->
      <div
        v-for="(entry, idx) in sortedHistory"
        :key="`${entry.timestamp}-${idx}`"
        class="p-4 rounded-lg bg-base-100 border border-base-content/10 shadow-sm hover:shadow-md transition-shadow cursor-pointer group"
      >
        <!-- Entry Header -->
        <div class="flex items-start justify-between mb-3">
          <div class="flex flex-col gap-2 flex-1 min-w-0">
            <!-- Date and Time -->
            <div class="flex items-center gap-3 flex-wrap">
              <div class="flex items-center gap-1 text-xs text-base-content/60 font-mono">
                <i class="fa-solid fa-calendar"></i>
                <span>{{ formatDate(entry.timestamp) }}</span>
              </div>
              <div class="text-xs text-base-content/50">
                {{ formatRelativeTime(entry.timestamp) }}
              </div>
            </div>

            <!-- Message Count and Summary Preview -->
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-xs text-base-content/60 gap-1">
                <i class="fa-solid fa-message"></i>
                {{ entry.message_ids?.length || 0 }} messages
              </span>
              <span v-if="entry.summary" class="text-xs text-base-content/60 italic">
                "{{ truncateText(entry.summary, 80) }}"
              </span>
            </div>
          </div>

        </div>

        <!-- Entry Content (Summary) -->
        <div class="pl-2 border-l border-base-content/10">
          <markdown
            v-if="entry.summary"
            class="prose max-w-none"
            :text="entry.summary"
          />
          <div v-else class="text-xs text-base-content/40 italic">-- no summary --</div>
        </div>

      </div>

      <!-- Empty State -->
      <div v-if="!history.length && !currentDescription" class="flex flex-col items-center justify-center gap-3 py-12 text-center text-base-content/50">
        <i class="fa-solid fa-inbox text-3xl opacity-30"></i>
        <p class="text-sm">No history entries yet</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    history: {
      type: Array,
      required: true
    },
    currentDescription: {
      type: String,
      required: true
    }
  },
  data() {
    return {}
  },
  computed: {
    sortedHistory() {
      return [...this.history].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    }
  },
  methods: {
    formatDate(timestamp) {
      return moment(timestamp).format('YYYY-MM-DD HH:mm:ss')
    },
    formatFullDate(timestamp) {
      return moment(timestamp).format('dddd, MMMM D, YYYY [at] HH:mm:ss')
    },
    formatRelativeTime(timestamp) {
      const m = moment(timestamp)
      return m.isAfter(moment().subtract(7, 'days'))
        ? m.fromNow()
        : m.format('MM-DD HH:mm')
    },
    truncateText(text, length) {
      if (!text) return ''
      return text.length > length ? text.substring(0, length) + '...' : text
    }
  }
}
</script>