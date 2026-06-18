<script setup>
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4" @click.self="$emit('close')">
    <div class="bg-base-100 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[92vh] flex flex-col border border-base-300">

      <!-- Header -->
      <div
        class="flex items-center gap-3 px-4 py-3 rounded-t-2xl border-b shrink-0"
        :class="hasError ? 'bg-error/20 border-error/30' : 'bg-base-300 border-base-content/10'"
      >
        <div class="flex items-center gap-1.5 shrink-0">
          <div class="w-3 h-3 rounded-full bg-error/70 cursor-pointer" @click="$emit('close')"></div>
          <div class="w-3 h-3 rounded-full bg-warning/70"></div>
          <div class="w-3 h-3 rounded-full bg-success/70"></div>
        </div>

        <div class="w-px h-5 bg-base-content/20"></div>

        <!-- Direction indicator -->
        <div class="flex items-center gap-2 shrink-0">
          <div class="relative flex items-center justify-center w-8 h-8 rounded-lg" :class="directionColor.bg">
            <span v-if="isFull" class="flex flex-col items-center leading-[0] gap-[2px]">
              <i class="fa-solid fa-arrow-up text-[10px]" :class="directionColor.text"></i>
              <i class="fa-solid fa-arrow-down text-[10px]" :class="directionColor.text"></i>
            </span>
            <i v-else-if="displayEntry?.direction === 'request'" class="fa-solid fa-arrow-up text-base text-success"></i>
            <i v-else class="fa-solid fa-arrow-down text-base text-warning"></i>
          </div>
          <div>
            <div class="text-xs font-bold uppercase tracking-widest leading-none" :class="directionColor.text">
              {{ isFull ? 'full' : (displayEntry?.direction || '—') }}
            </div>
            <div class="text-xs text-base-content/30 font-mono leading-none mt-0.5">{{ displayEntry?.timestamp }}</div>
          </div>
        </div>

        <div class="w-px h-5 bg-base-content/20"></div>

        <!-- Meta chips -->
        <div class="flex items-center gap-1.5 flex-wrap flex-1 min-w-0 overflow-hidden">
          <div class="badge badge-primary badge-sm gap-1 shrink-0">
            <i class="fa-solid fa-robot text-xs"></i>{{ displayEntry?.model || 'unknown' }}
          </div>
          <div class="badge badge-secondary badge-sm gap-1 shrink-0">
            <i class="fa-solid fa-plug text-xs"></i>{{ displayEntry?.provider || 'unknown' }}
          </div>
          <div class="badge badge-ghost badge-sm gap-1 shrink-0">
            <i class="fa-regular fa-user text-xs"></i>{{ displayEntry?.username }}
          </div>
          <div v-if="displayEntry?.project" class="badge badge-accent badge-sm gap-1 shrink-0">
            <i class="fa-solid fa-folder text-xs"></i>{{ displayEntry?.project }}
          </div>
          <div v-if="responseEntry?.duration_seconds != null" class="badge badge-info badge-sm gap-1 shrink-0">
            <i class="fa-solid fa-stopwatch text-xs"></i>{{ responseEntry.duration_seconds.toFixed(2) }}s
          </div>
          <div v-if="displayEntry?.session_id" class="badge badge-ghost badge-sm font-mono gap-1 shrink-0">
            <i class="fa-solid fa-comments text-xs"></i>{{ displayEntry?.session_id.slice(0, 8) }}…
          </div>
          <div v-if="isFull" class="badge badge-info badge-sm gap-1 shrink-0">
            <i class="fa-solid fa-arrows-up-down text-xs"></i> full
          </div>
          <!-- Error badge in header — shown prominently when errors exist -->
          <div v-if="hasError" class="badge badge-error badge-sm gap-1 shrink-0 animate-pulse">
            <i class="fa-solid fa-circle-exclamation text-xs"></i> error
          </div>
        </div>

        <button class="btn btn-xs btn-circle btn-ghost shrink-0" @click="$emit('close')">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center p-16">
        <span class="loading loading-spinner loading-lg text-primary"></span>
      </div>

      <!-- Main content -->
      <div v-else-if="displayEntry" class="overflow-y-auto flex-1 min-h-0 flex flex-col">

        <!-- Base URL banner -->
        <div v-if="displayEntry.base_url" class="flex items-center gap-2 px-4 py-2 bg-base-200/50 border-b border-base-300 text-xs font-mono text-base-content/40 shrink-0">
          <i class="fa-solid fa-globe shrink-0"></i>
          <span class="truncate">{{ displayEntry.base_url }}</span>
        </div>

        <!-- Error banner — shown when any entry has error info -->
        <div v-if="hasError" class="flex flex-col gap-2 px-4 py-3 bg-error/10 border-b border-error/30 shrink-0">
          <div class="flex items-center gap-2 text-error text-sm font-bold">
            <i class="fa-solid fa-triangle-exclamation"></i>
            <span>ERROR DETECTED</span>
          </div>
          <!-- Request error block -->
          <div v-if="requestError" class="flex items-start gap-3 rounded-lg bg-base-100 border border-error/40 px-3 py-2.5">
            <div class="flex items-center gap-1.5 shrink-0 mt-0.5">
              <i class="fa-solid fa-arrow-up text-success text-xs"></i>
              <span class="text-xs font-semibold text-base-content/50 uppercase tracking-wider">Request</span>
            </div>
            <div class="w-px self-stretch bg-error/20 mx-1"></div>
            <div class="flex flex-col gap-0.5 min-w-0">
              <span class="text-xs font-bold text-error font-mono">{{ requestError.error_type }}</span>
              <span class="text-sm text-base-content/80 break-words">{{ requestError.error_message }}</span>
            </div>
          </div>
          <!-- Response error block -->
          <div v-if="responseError" class="flex items-start gap-3 rounded-lg bg-base-100 border border-error/40 px-3 py-2.5">
            <div class="flex items-center gap-1.5 shrink-0 mt-0.5">
              <i class="fa-solid fa-arrow-down text-warning text-xs"></i>
              <span class="text-xs font-semibold text-base-content/50 uppercase tracking-wider">Response</span>
            </div>
            <div class="w-px self-stretch bg-error/20 mx-1"></div>
            <div class="flex flex-col gap-0.5 min-w-0">
              <span class="text-xs font-bold text-error font-mono">{{ responseError.error_type }}</span>
              <span class="text-sm text-base-content/80 break-words">{{ responseError.error_message }}</span>
            </div>
          </div>
        </div>

        <div class="p-4 space-y-4 flex-1">

          <!-- REQUEST messages -->
          <div
            class="rounded-xl overflow-hidden border flex flex-col"
            :class="requestError ? 'border-error/50' : requestEntry ? 'border-success/40' : 'border-base-300'"
          >
            <div
              class="flex items-center gap-2 px-4 py-2 border-b text-xs font-semibold shrink-0"
              :class="requestError
                ? 'bg-error/10 border-error/20 text-error'
                : requestEntry
                  ? 'bg-success/10 border-success/20 text-success'
                  : 'bg-base-200 border-base-300 text-base-content/40'"
            >
              <i class="fa-solid fa-arrow-up-from-bracket"></i>
              <span>REQUEST MESSAGES</span>
              <span class="font-mono font-normal opacity-60 ml-1">
                {{ requestMessages.length }} msg{{ requestMessages.length !== 1 ? 's' : '' }}
              </span>
              <span v-if="!requestEntry" class="ml-2 opacity-40 italic font-normal">(not available)</span>
              <!-- Request error inline badge with tooltip -->
              <div v-if="requestError" class="tooltip" :data-tip="requestError.error_message">
                <div class="badge badge-error badge-xs gap-1 ml-1 cursor-help">
                  <i class="fa-solid fa-circle-exclamation text-xs"></i>{{ requestError.error_type }}
                </div>
              </div>
              <button class="btn btn-xs btn-ghost ml-auto opacity-50" @click="messagesExpanded = !messagesExpanded">
                <i :class="messagesExpanded ? 'fa-solid fa-compress' : 'fa-solid fa-expand'" class="text-xs"></i>
              </button>
            </div>

            <!-- Request error inline detail -->
            <div v-if="requestError" class="flex items-start gap-2 px-4 py-3 bg-error/5 border-b border-error/20">
              <i class="fa-solid fa-triangle-exclamation text-error text-sm mt-0.5 shrink-0"></i>
              <div class="flex flex-col gap-1">
                <span class="text-xs font-bold text-error font-mono">{{ requestError.error_type }}</span>
                <span class="text-sm text-base-content/80">{{ requestError.error_message }}</span>
              </div>
            </div>

            <div
              class="divide-y divide-base-300 overflow-y-auto transition-all duration-200"
              :class="messagesExpanded ? 'max-h-[60vh]' : 'max-h-64'"
            >
              <div
                v-for="(msg, i) in requestMessages"
                :key="i"
                class="px-4 py-3"
                :class="{
                  'bg-primary/5': msg.role === 'user',
                  'bg-secondary/5': msg.role === 'assistant',
                  'bg-warning/5': msg.role === 'system',
                  'bg-info/5': msg.role === 'tool'
                }"
              >
                <div class="flex items-center gap-2 mb-2">
                  <div
                    class="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold"
                    :class="{
                      'bg-primary/15 text-primary': msg.role === 'user',
                      'bg-secondary/15 text-secondary': msg.role === 'assistant',
                      'bg-warning/15 text-warning': msg.role === 'system',
                      'bg-info/15 text-info': msg.role === 'tool'
                    }"
                  >
                    <i :class="{
                      'fa-regular fa-user': msg.role === 'user',
                      'fa-solid fa-robot': msg.role === 'assistant',
                      'fa-solid fa-gear': msg.role === 'system',
                      'fa-solid fa-wrench': msg.role === 'tool'
                    }" class="text-xs"></i>
                    <span class="ml-1 uppercase tracking-wider text-xs">{{ msg.role }}</span>
                  </div>
                  <span v-if="msg.name" class="text-xs text-base-content/30 font-mono">{{ msg.name }}</span>
                  <span class="ml-auto text-xs text-base-content/20 font-mono">{{ i + 1 }}/{{ requestMessages.length }}</span>
                </div>
                <pre class="whitespace-pre-wrap font-sans text-sm text-base-content leading-relaxed">{{ msgContent(msg) }}</pre>
              </div>

              <div v-if="!requestMessages.length && !requestError" class="px-4 py-8 text-center text-xs text-base-content/25 italic">
                — No messages in request payload —
              </div>
            </div>
          </div>

          <!-- RESPONSE content -->
          <div
            class="rounded-xl overflow-hidden border flex flex-col"
            :class="responseError ? 'border-error/50' : responseEntry ? 'border-warning/40' : 'border-base-300'"
          >
            <div
              class="flex items-center gap-2 px-4 py-2 border-b text-xs font-semibold shrink-0"
              :class="responseError
                ? 'bg-error/10 border-error/20 text-error'
                : responseEntry
                  ? 'bg-warning/10 border-warning/20 text-warning'
                  : 'bg-base-200 border-base-300 text-base-content/40'"
            >
              <i class="fa-solid fa-arrow-down-to-bracket"></i>
              <span>RESPONSE CONTENT</span>
              <span v-if="responseEntry?.duration_seconds != null" class="font-mono font-normal opacity-70 ml-1">
                {{ responseEntry.duration_seconds.toFixed(2) }}s
              </span>
              <span v-if="!responseEntry" class="ml-2 opacity-40 italic font-normal">(not available)</span>
              <!-- Response error inline badge with tooltip -->
              <div v-if="responseError" class="tooltip" :data-tip="responseError.error_message">
                <div class="badge badge-error badge-xs gap-1 ml-1 cursor-help">
                  <i class="fa-solid fa-circle-exclamation text-xs"></i>{{ responseError.error_type }}
                </div>
              </div>
              <button v-if="responseEntry" class="btn btn-xs btn-ghost ml-auto opacity-50" @click="responseExpanded = !responseExpanded">
                <i :class="responseExpanded ? 'fa-solid fa-compress' : 'fa-solid fa-expand'" class="text-xs"></i>
              </button>
            </div>

            <!-- Response error detail block -->
            <div v-if="responseError" class="flex items-start gap-2 px-4 py-3 bg-error/5 border-b border-error/20">
              <i class="fa-solid fa-triangle-exclamation text-error text-sm mt-0.5 shrink-0"></i>
              <div class="flex flex-col gap-1">
                <span class="text-xs font-bold text-error font-mono">{{ responseError.error_type }}</span>
                <span class="text-sm text-base-content/80">{{ responseError.error_message }}</span>
              </div>
            </div>

            <div
              v-if="responseEntry && responseContent"
              class="px-4 py-3 overflow-y-auto transition-all duration-200"
              :class="responseExpanded ? 'max-h-[60vh]' : 'max-h-48'"
            >
              <pre class="whitespace-pre-wrap font-sans text-sm text-base-content leading-relaxed">{{ responseContent }}</pre>
            </div>

            <div v-if="responseEntry && !responseContent && !responseError" class="px-4 py-8 text-center text-xs text-base-content/25 italic">
              — No content —
            </div>

            <div v-if="!responseEntry" class="px-4 py-8 text-center text-xs text-base-content/25 italic">
              — No response entry found —
            </div>

            <!-- Tool calls -->
            <div v-if="responseToolCalls" class="border-t border-warning/20">
              <div class="flex items-center gap-1.5 px-4 py-2 bg-base-200 text-xs font-semibold text-base-content/50 shrink-0">
                <i class="fa-solid fa-wrench text-xs"></i> TOOL CALLS
              </div>
              <div class="px-4 py-3 overflow-y-auto max-h-48">
                <pre class="text-xs text-base-content/70 bg-base-200 rounded-lg p-3 whitespace-pre-wrap">{{ formatJson(responseToolCalls) }}</pre>
              </div>
            </div>
          </div>

          <!-- Raw payloads collapsible -->
          <div class="collapse collapse-arrow rounded-xl border border-base-300 bg-base-200">
            <input type="checkbox" />
            <div class="collapse-title text-xs font-mono font-semibold text-base-content/40 py-2.5 min-h-0 flex items-center gap-2">
              <i class="fa-solid fa-code"></i> raw payloads
            </div>
            <div class="collapse-content bg-base-300/30 space-y-3">
              <div v-if="requestEntry">
                <div class="text-xs text-success font-semibold mb-1 mt-2">↑ request</div>
                <pre class="text-xs font-mono text-base-content/60 whitespace-pre-wrap overflow-auto max-h-48">{{ formatJson(requestEntry.payload) }}</pre>
              </div>
              <div v-if="responseEntry">
                <div class="text-xs text-warning font-semibold mb-1">↓ response</div>
                <pre class="text-xs font-mono text-base-content/60 whitespace-pre-wrap overflow-auto max-h-48">{{ formatJson(responseEntry.payload) }}</pre>
              </div>
            </div>
          </div>

          <!-- Footer: request IDs + tags -->
          <div class="flex flex-wrap items-center gap-2 pt-2 border-t border-base-300">
            <div v-if="displayEntry.request_id" class="flex items-center gap-1.5 text-xs font-mono bg-base-200 border border-base-300 rounded-lg px-2 py-1">
              <i class="fa-solid fa-fingerprint text-primary text-xs"></i>
              <span class="text-base-content/50">{{ displayEntry.request_id.slice(0, 20) }}…</span>
              <button class="btn btn-xs btn-ghost btn-circle" title="Find paired entry" @click="$emit('find-pair', displayEntry.request_id)">
                <i class="fa-solid fa-link text-info text-xs"></i>
              </button>
            </div>
            <div v-if="displayEntry.parent_request_id" class="flex items-center gap-1.5 text-xs font-mono bg-warning/10 border border-warning/30 rounded-lg px-2 py-1">
              <i class="fa-solid fa-turn-up text-warning text-xs"></i>
              <span class="text-base-content/50">{{ displayEntry.parent_request_id.slice(0, 16) }}…</span>
              <button class="btn btn-xs btn-warning btn-outline ml-1" @click="$emit('navigate-parent', displayEntry.parent_request_id)">
                ↑ Parent
              </button>
            </div>
            <div v-if="displayEntry.tags" class="flex items-center gap-1 text-xs bg-base-200 border border-base-300 rounded-lg px-2 py-1">
              <i class="fa-solid fa-tag text-base-content/30 text-xs"></i>
              <span class="text-base-content/50">{{ displayEntry.tags }}</span>
            </div>
            <span class="ml-auto text-xs text-base-content/20 font-mono">{{ displayEntry.log_id }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LogEntryDetail',
  emits: ['close', 'navigate-parent', 'find-pair', 'open-entry'],
  props: {
    requestEntry: { type: Object, default: null },
    responseEntry: { type: Object, default: null },
    loading: { type: Boolean, default: false },
  },
  data() {
    return {
      messagesExpanded: false,
      responseExpanded: false
    }
  },
  computed: {
    isFull() {
      return !!(this.requestEntry && this.responseEntry)
    },
    displayEntry() {
      return this.requestEntry || this.responseEntry
    },
    directionColor() {
      if (this.hasError) return { bg: 'bg-error/20', text: 'text-error' }
      if (this.isFull) return { bg: 'bg-info/20', text: 'text-info' }
      if (this.requestEntry) return { bg: 'bg-success/20', text: 'text-success' }
      return { bg: 'bg-warning/20', text: 'text-warning' }
    },
    // Extract error fields from request entry
    requestError() {
      if (!this.requestEntry?.error_type) return null
      return {
        error_type: this.requestEntry.error_type,
        error_message: this.requestEntry.error_message
      }
    },
    // Extract error fields from response entry
    responseError() {
      if (!this.responseEntry?.error_type) return null
      return {
        error_type: this.responseEntry.error_type,
        error_message: this.responseEntry.error_message
      }
    },
    hasError() {
      return !!(this.requestError || this.responseError)
    },
    requestMessages() {
      return this.requestEntry?.payload?.messages || []
    },
    responseContent() {
      return this.responseEntry?.payload?.content || null
    },
    responseToolCalls() {
      const tc = this.responseEntry?.payload?.tool_calls
      return tc && tc.length ? tc : null
    }
  },
  methods: {
    msgContent(msg) {
      if (typeof msg.content === 'string') return msg.content
      if (Array.isArray(msg.content)) return msg.content.map(c => c.text || JSON.stringify(c)).join('\n')
      return JSON.stringify(msg.content, null, 2)
    },
    formatJson(obj) {
      try { return JSON.stringify(obj, null, 2) } catch { return String(obj) }
    }
  }
}
</script>