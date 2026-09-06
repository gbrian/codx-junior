<script setup>
</script>

<template>
  <div class="space-y-4">
    <!-- Loading state -->
    <div v-if="loading" class="flex items-center justify-center py-8">
      <span class="loading loading-spinner loading-md text-primary"></span>
      <span class="ml-3 text-sm text-base-content/60">Loading conversation...</span>
    </div>

    <!-- Empty state -->
    <div v-if="loaded && !loading && !conversationFlow.length" class="text-center py-8 text-base-content/50">
      <i class="fa-solid fa-comments-slash text-3xl mb-3 block opacity-30"></i>
      <div class="text-sm">No conversation data available</div>
    </div>

    <!-- Conversation Flow Timeline -->
    <div v-if="loaded && conversationFlow.length" class="space-y-0">
      <!-- Summary bar -->
      <div class="flex items-center gap-3 px-3 py-2 bg-base-200 rounded-xl mb-4 text-xs text-base-content/60">
        <i class="fa-solid fa-timeline text-primary"></i>
        <span class="font-semibold text-base-content">Conversation Flow</span>
        <span class="badge badge-primary badge-xs">{{ llmRounds }} LLM rounds</span>
        <span class="badge badge-accent badge-xs">{{ totalToolCalls }} tool calls</span>
        <span class="badge badge-ghost badge-xs">{{ conversationFlow.length }} events</span>
      </div>

      <!-- Timeline items -->
      <!-- CHANGED: removed vertical line and dot elements -->
      <div class="space-y-2">
        <div v-for="(item, idx) in conversationFlow" :key="idx">

          <!-- LLM Round card -->
          <div v-if="item.type === 'llm'" class="rounded-xl border border-secondary/30 overflow-hidden">
            <!-- Round header -->
            <button
              class="w-full flex items-center gap-3 px-4 py-2.5 bg-secondary/10 hover:bg-secondary/15 transition-colors text-left"
              @click="toggleSection(`flow-${idx}`)"
            >
              <i :class="expandedSections[`flow-${idx}`] ? 'fa-solid fa-chevron-down' : 'fa-solid fa-chevron-right'" class="text-secondary text-xs shrink-0"></i>
              <i class="fa-solid fa-robot text-secondary text-xs shrink-0"></i>
              <span class="text-sm font-semibold text-secondary">LLM Round {{ item.roundNumber }}</span>
              <span class="badge badge-xs badge-ghost font-mono">{{ item.data.model }}</span>
              <span v-if="item.data.input_tokens" class="badge badge-xs badge-success">in: {{ item.data.input_tokens }}</span>
              <span v-if="item.data.output_tokens" class="badge badge-xs badge-warning">out: {{ item.data.output_tokens }}</span>
              <span v-if="item.hasToolCalls" class="badge badge-xs badge-accent gap-1">
                <i class="fa-solid fa-wrench text-xs"></i>{{ item.toolCallCount }} tools
              </span>
              <span v-else class="badge badge-xs badge-success gap-1">
                <i class="fa-solid fa-flag-checkered text-xs"></i>final
              </span>
              <div class="ml-auto flex items-center gap-2 shrink-0">
                <span class="text-xs text-base-content/40">{{ formatDuration(item.data.duration_seconds) }}</span>
                <span class="text-xs text-base-content/30 font-mono">{{ formatTime(item.data.timestamp) }}</span>
              </div>
            </button>

            <!-- Round body (expanded) -->
            <div v-if="expandedSections[`flow-${idx}`]" class="border-t border-secondary/20">
              <!-- Context messages sent to LLM -->
              <div v-if="item.data.request_messages && item.data.request_messages.length" class="border-b border-secondary/10">
                <button
                  class="w-full flex items-center gap-2 px-4 py-2 bg-base-200/60 hover:bg-base-200 transition-colors text-left"
                  @click="toggleSection(`flow-${idx}-ctx`)"
                >
                  <i :class="expandedSections[`flow-${idx}-ctx`] ? 'fa-solid fa-chevron-down' : 'fa-solid fa-chevron-right'" class="text-xs text-base-content/30 shrink-0"></i>
                  <i class="fa-solid fa-list text-xs text-base-content/40"></i>
                  <span class="text-xs text-base-content/60 font-semibold">Context sent to LLM ({{ item.data.request_messages.length }} messages)</span>
                </button>
                <div v-if="expandedSections[`flow-${idx}-ctx`]" class="px-3 py-2 space-y-1 max-h-64 overflow-y-auto bg-base-200/20">
                  <div
                    v-for="(msg, mIdx) in item.data.request_messages"
                    :key="mIdx"
                    class="rounded px-2 py-1.5 text-xs"
                    :class="{
                      'bg-base-300/60 border border-base-content/10': msg.role === 'system',
                      'bg-info/5 border border-info/20': msg.role === 'user',
                      'bg-secondary/5 border border-secondary/20': msg.role === 'assistant',
                      'bg-accent/5 border border-accent/20': msg.role === 'tool',
                    }"
                  >
                    <div class="font-semibold mb-0.5 capitalize text-xs flex items-center gap-1.5"
                      :class="{
                        'text-base-content/40': msg.role === 'system',
                        'text-info': msg.role === 'user',
                        'text-secondary': msg.role === 'assistant',
                        'text-accent': msg.role === 'tool',
                      }">
                      {{ msg.role }}
                      <span v-if="msg.tool_call_id" class="font-mono opacity-60 text-xs">({{ msg.tool_call_id?.slice(0, 8) }}…)</span>
                    </div>
                    <div class="font-mono text-base-content/70 whitespace-pre-wrap break-words max-h-32 overflow-y-auto">{{ truncateContent(msg.content) }}</div>
                  </div>
                </div>
              </div>

              <!-- LLM Response -->
              <div class="px-4 py-3">
                <div class="text-xs font-semibold text-secondary mb-1.5 flex items-center gap-1.5">
                  <i class="fa-solid fa-reply"></i>
                  Response
                  <span v-if="item.hasToolCalls" class="badge badge-xs badge-accent">triggered {{ item.toolCallCount }} tool calls</span>
                  <span v-else class="badge badge-xs badge-success">final answer</span>
                </div>
                <div v-if="item.data.response_content" class="font-mono text-xs text-base-content/80 whitespace-pre-wrap break-words max-h-48 overflow-y-auto bg-base-100 border border-secondary/20 rounded p-2">
                  {{ truncateContent(item.data.response_content) }}
                </div>
                <div v-else class="text-xs text-base-content/30 italic">No text content (tool calls only)</div>
              </div>

              <!-- Error -->
              <div v-if="item.data.error" class="px-4 pb-3">
                <div class="p-2 rounded bg-error/10 border border-error/30 text-xs text-error">
                  <span class="font-semibold">Error: </span>{{ item.data.error }}
                </div>
              </div>

              <!-- Request meta -->
              <div class="px-4 pb-2 flex flex-wrap gap-1.5 border-t border-secondary/10 pt-2 bg-base-200/20">
                <span class="font-mono text-xs text-base-content/30" title="Request ID">req: {{ item.data.request_id?.slice(0, 16) }}…</span>
                <span class="text-base-content/20">·</span>
                <span class="badge badge-xs badge-ghost">{{ item.data.provider }}</span>
                <span v-if="item.data.input_k_tokens_cxjcoins" class="text-xs text-base-content/30">{{ item.data.input_k_tokens_cxjcoins }}/{{ item.data.output_k_tokens_cxjcoins }} CXJ/1k</span>
              </div>
            </div>
          </div>

          <!-- Tool call card -->
          <!-- CHANGED: added ml-6 indent to visually nest tools under LLM rounds -->
          <div v-if="item.type === 'tool'" class="ml-6 rounded-xl border overflow-hidden"
            :class="item.data.success ? 'border-accent/30' : 'border-error/40'"
          >
            <button
              class="w-full flex items-center gap-3 px-4 py-2.5 transition-colors text-left"
              :class="item.data.success ? 'bg-accent/8 hover:bg-accent/12' : 'bg-error/8 hover:bg-error/12'"
              @click="toggleSection(`flow-${idx}`)"
            >
              <i :class="expandedSections[`flow-${idx}`] ? 'fa-solid fa-chevron-down' : 'fa-solid fa-chevron-right'" class="text-xs text-base-content/40 shrink-0"></i>
              <i class="fa-solid fa-wrench text-xs shrink-0" :class="item.data.success ? 'text-accent' : 'text-error'"></i>
              <span class="text-sm font-semibold font-mono" :class="item.data.success ? 'text-accent' : 'text-error'">{{ item.data.tool_name }}</span>
              <span v-if="item.data.success" class="badge badge-xs badge-success">ok</span>
              <span v-else class="badge badge-xs badge-error">failed</span>
              <span v-if="item.data.cached" class="badge badge-xs badge-ghost">cached</span>
              <div class="ml-auto flex items-center gap-2 shrink-0">
                <span class="text-xs text-base-content/40">{{ formatDuration(item.data.duration_seconds) }}</span>
                <span class="text-xs text-base-content/30 font-mono">{{ formatTime(item.data.timestamp) }}</span>
              </div>
            </button>

            <!-- Tool body (expanded) -->
            <div v-if="expandedSections[`flow-${idx}`]" class="border-t space-y-3 p-3"
              :class="item.data.success ? 'border-accent/20' : 'border-error/20'"
            >
              <!-- Args -->
              <div v-if="item.data.request_args && Object.keys(item.data.request_args).length" class="space-y-1">
                <div class="text-xs font-semibold text-base-content/50 flex items-center gap-1">
                  <i class="fa-solid fa-arrow-right-to-bracket text-xs"></i> Arguments
                </div>
                <div class="bg-base-100 rounded p-2 font-mono text-xs text-base-content/70 overflow-x-auto max-h-40 overflow-y-auto border border-base-300 whitespace-pre-wrap">{{ formatJson(item.data.request_args) }}</div>
              </div>

              <!-- Result -->
              <div class="space-y-1">
                <div class="text-xs font-semibold text-base-content/50 flex items-center gap-1">
                  <i class="fa-solid fa-arrow-right-from-bracket text-xs"></i> Result
                </div>
                <div class="bg-base-100 rounded p-2 font-mono text-xs text-base-content/70 overflow-x-auto max-h-40 overflow-y-auto border border-base-300 whitespace-pre-wrap">{{ truncateContent(typeof item.data.result === 'string' ? item.data.result : formatJson(item.data.result)) }}</div>
              </div>

              <!-- Error -->
              <div v-if="item.data.error_message" class="p-2 rounded bg-error/10 border border-error/30 text-xs text-error">
                <span class="font-semibold">Error: </span>{{ item.data.error_message }}
              </div>

              <!-- Meta -->
              <div class="flex flex-wrap gap-1.5 pt-1 border-t border-base-300 text-xs text-base-content/30 font-mono">
                <span title="Tool call ID">call: {{ item.data.tool_call_id?.slice(0, 16) }}…</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LlmRequestsViewer',
  props: {
    chatSession: { type: Object, default: null },
    isAdmin: { type: Boolean, default: false }
  },
  data() {
    return {
      loading: false,
      loaded: false,
      allMessages: null,
      expandedSections: {}
    }
  },
  computed: {
    chatInfo() {
      return this.chatSession?.chat_session
    },
    llmRequests() {
      return this.chatSession?.llm_requests || []
    },
    // Map request_id -> archived llm message (full context + response)
    llmMessagesByRequestId() {
      const map = {}
      if (this.allMessages?.llm_messages) {
        for (const msg of this.allMessages.llm_messages) {
          if (msg.request_id) {
            map[msg.request_id] = msg
          }
        }
      }
      return map
    },
    sortedToolMessages() {
      if (!this.allMessages?.tool_messages) return []
      return [...this.allMessages.tool_messages].sort((a, b) => a.timestamp - b.timestamp)
    },
    // Build ordered conversation flow: LLM round → tool calls triggered → LLM round → ...
    conversationFlow() {
      if (!this.loaded) return []

      const items = []

      // Sort llm_requests by timestamp (token_event wraps the data in enriched form)
      const sortedLlmRequests = [...this.llmRequests].sort((a, b) => {
        const tsA = a.token_event?.timestamp ?? a.timestamp ?? 0
        const tsB = b.token_event?.timestamp ?? b.timestamp ?? 0
        return tsA - tsB
      })

      let roundNumber = 0
      for (let i = 0; i < sortedLlmRequests.length; i++) {
        const req = sortedLlmRequests[i]
        // Support both enriched (token_event wrapper) and flat structures
        const tokenData = req.token_event ?? req
        const requestId = tokenData.request_id
        const reqTs = tokenData.timestamp ?? 0
        const nextReqTs = i + 1 < sortedLlmRequests.length
          ? (sortedLlmRequests[i + 1].token_event?.timestamp ?? sortedLlmRequests[i + 1].timestamp ?? Infinity)
          : Infinity

        // Tool messages that occurred between this LLM call and the next
        const toolsInRound = this.sortedToolMessages.filter(t => {
          return t.timestamp >= reqTs && t.timestamp < nextReqTs
        })

        roundNumber++
        const archivedMsg = this.llmMessagesByRequestId[requestId]
        const hasToolCalls = toolsInRound.length > 0

        items.push({
          type: 'llm',
          roundNumber,
          hasToolCalls,
          toolCallCount: toolsInRound.length,
          data: {
            request_id: requestId,
            model: tokenData.model ?? '',
            provider: tokenData.provider ?? '',
            input_tokens: tokenData.input_tokens ?? 0,
            output_tokens: tokenData.output_tokens ?? 0,
            duration_seconds: tokenData.duration_seconds ?? 0,
            timestamp: reqTs,
            input_k_tokens_cxjcoins: tokenData.input_k_tokens_cxjcoins,
            output_k_tokens_cxjcoins: tokenData.output_k_tokens_cxjcoins,
            // From archived message (full conversation context)
            request_messages: archivedMsg?.request_messages ?? [],
            response_content: archivedMsg?.response_content ?? '',
            error: archivedMsg?.error ?? null
          }
        })

        // Add tool call items for this round in timestamp order
        for (const tool of toolsInRound) {
          items.push({
            type: 'tool',
            data: tool
          })
        }
      }

      return items
    },
    llmRounds() {
      return this.conversationFlow.filter(i => i.type === 'llm').length
    },
    totalToolCalls() {
      return this.conversationFlow.filter(i => i.type === 'tool').length
    }
  },
  watch: {
    chatSession() {
      // CHANGED: reset and reload when chatSession changes
      this.loaded = false
      this.allMessages = null
      this.expandedSections = {}
      this.loadConversation()
    }
  },
  mounted() {
    // CHANGED: auto-load on mount instead of requiring button click
    this.loadConversation()
  },
  methods: {
    async loadConversation() {
      if (!this.chatInfo?.chat_id) return
      this.loading = true
      try {
        const chatId = this.chatInfo.chat_id
        const result = await this.$project.$api.analytics.admin.chatSessionMessages(chatId, {})
        this.allMessages = result
        this.loaded = true
      } catch (err) {
        console.error('Failed to load conversation messages:', err)
        this.allMessages = { llm_messages: [], tool_messages: [] }
        this.loaded = true
      } finally {
        this.loading = false
      }
    },
    toggleSection(key) {
      this.expandedSections[key] = !this.expandedSections[key]
    },
    formatJson(obj) {
      try {
        return JSON.stringify(obj, null, 2)
      } catch {
        return String(obj)
      }
    },
    formatDuration(seconds) {
      return seconds ? `${Number(seconds).toFixed(2)}s` : '—'
    },
    formatTime(timestamp) {
      if (!timestamp) return '—'
      const d = typeof timestamp === 'number' ? new Date(timestamp * 1000) : new Date(timestamp)
      return d.toLocaleTimeString()
    },
    truncateContent(content) {
      if (!content) return '—'
      if (typeof content !== 'string') return this.formatJson(content)
      const limit = 2000
      return content.length > limit ? content.slice(0, limit) + '\n… (truncated)' : content
    }
  }
}
</script>