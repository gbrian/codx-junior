<script setup>
import ProfileAvatar from '../profile/ProfileAvatar.vue'
import ChatFileList from '../chat/ChatFileList.vue'
import LlmRequestsViewer from './LlmRequestsViewer.vue'
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4" @click.self="$emit('close')">
    <div class="bg-base-100 rounded-2xl shadow-2xl w-full max-w-6xl max-h-[92vh] flex flex-col border border-base-300 overflow-hidden">

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

        <!-- Title & Meta -->
        <div class="flex flex-col gap-1 flex-1 min-w-0">
          <div class="text-sm font-bold text-base-content truncate">{{ chatInfo?.chat_name }}</div>
          <div class="flex items-center gap-2 text-xs text-base-content/60">
            <span class="font-mono">{{ chatInfo?.chat_id?.slice(0, 12) }}…</span>
            <span v-if="chatInfo?.mode" class="badge badge-sm badge-ghost">{{ chatInfo.mode }}</span>
            <span v-if="hasError" class="badge badge-error badge-sm gap-1">
              <i class="fa-solid fa-circle-exclamation text-xs"></i> error
            </span>
          </div>
        </div>

        <!-- Quick meta chips -->
        <div class="flex items-center gap-1.5 flex-wrap">
          <div v-if="chatInfo?.username" class="badge badge-primary badge-sm gap-1">
            <i class="fa-regular fa-user text-xs"></i>{{ chatInfo.username }}
          </div>
          <div v-if="chatInfo?.project_name" class="badge badge-secondary badge-sm gap-1">
            <i class="fa-solid fa-folder text-xs"></i>{{ chatInfo.project_name }}
          </div>
          <div v-if="metricsInfo?.total_tokens" class="badge badge-info badge-sm gap-1">
            <i class="fa-solid fa-coins text-xs"></i>{{ metricsInfo.total_tokens }} tokens
          </div>
        </div>

        <button class="btn btn-xs btn-circle btn-ghost shrink-0" @click="$emit('close')">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <!-- Tab Navigation -->
      <div class="flex gap-0 border-b border-base-300 px-4 shrink-0 bg-base-200/50 overflow-x-auto">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="[
            'flex items-center gap-2 px-4 py-2.5 border-b-2 text-sm font-semibold transition-colors whitespace-nowrap',
            activeTab === tab.id
              ? 'border-primary text-primary'
              : 'border-transparent text-base-content/60 hover:text-base-content'
          ]"
        >
          <i :class="`fa-solid ${tab.icon}`"></i>
          {{ tab.label }}
        </button>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center p-16 flex-1">
        <span class="loading loading-spinner loading-lg text-primary"></span>
      </div>

      <!-- Content Container - Fixed Height with Internal Scroll -->
      <div class="overflow-y-auto flex-1 min-h-0">
        <div class="p-4 space-y-4">

          <!-- OVERVIEW TAB -->
          <div v-if="activeTab === 'overview'" class="space-y-4">
            
            <!-- Chat Session Info -->
            <div class="rounded-xl border border-base-300 overflow-hidden">
              <div class="flex items-center gap-2 px-4 py-2.5 bg-base-200 border-b border-base-300 shrink-0">
                <i class="fa-solid fa-info-circle text-primary"></i>
                <span class="text-sm font-semibold">Chat Session</span>
              </div>
              <div class="grid grid-cols-2 md:grid-cols-3 gap-4 p-4">
                <div class="space-y-1">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Chat ID</div>
                  <div class="text-sm font-mono text-base-content/70 break-all">{{ chatInfo?.chat_id }}</div>
                </div>
                <div class="space-y-1">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Mode</div>
                  <div class="badge badge-outline">{{ chatInfo?.mode || '—' }}</div>
                </div>
                <div class="space-y-1">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Status</div>
                  <div class="flex items-center gap-2">
                    <span v-if="chatInfo?.cancelled" class="badge badge-warning">Cancelled</span>
                    <span v-else-if="chatInfo?.error" class="badge badge-error">Error</span>
                    <span v-else class="badge badge-success">Completed</span>
                  </div>
                </div>
                <div class="space-y-1">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Username</div>
                  <div class="text-sm">{{ chatInfo?.username || '—' }}</div>
                </div>
                <div class="space-y-1">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Project</div>
                  <div class="text-sm">{{ chatInfo?.project_name || '—' }}</div>
                </div>
                <div class="space-y-1">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Started</div>
                  <div class="text-sm font-mono text-xs">{{ formatDate(chatInfo?.timestamp) }}</div>
                </div>
                <div class="space-y-1">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Duration</div>
                  <div class="text-sm font-semibold">{{ formatDuration(chatInfo?.duration_seconds) }}</div>
                </div>
                <div class="space-y-1">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Input Messages</div>
                  <div class="text-sm font-semibold">{{ chatInfo?.input_message_count || 0 }}</div>
                </div>
                <div class="space-y-1">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Output Messages</div>
                  <div class="text-sm font-semibold">{{ chatInfo?.output_message_count || 0 }}</div>
                </div>
              </div>
            </div>

            <!-- Error Info -->
            <div v-if="hasError" class="rounded-xl border border-error/50 bg-error/5 overflow-hidden">
              <div class="flex items-center gap-2 px-4 py-2.5 bg-error/10 border-b border-error/30 shrink-0">
                <i class="fa-solid fa-triangle-exclamation text-error"></i>
                <span class="text-sm font-semibold text-error">Error Details</span>
              </div>
              <div class="p-4 space-y-2">
                <div class="text-sm text-base-content/80">{{ chatInfo?.error }}</div>
              </div>
            </div>

            <div class="flex gap-2 justify-between text-xs">
              <!-- Profiles -->
              <div v-if="profiles.length" class="rounded-xl border border-base-300 overflow-hidden flex">
                <div class="flex items-center gap-2 px-4 py-2.5 bg-base-200 border-b border-base-300 shrink-0">
                  <i class="fa-solid fa-user-group text-secondary"></i>
                  <span class="text-sm font-semibold">Profiles</span>
                </div>
                <div class="p-4 flex gap-2">
                  <ProfileAvatar
                    v-for="profile in profiles"
                    :key="profile.name"
                    :profile="profile"
                    width="10"
                  />
                </div>
              </div>

              <!-- Files -->
              <div v-if="chatInfo?.files?.length" class="rounded-xl border border-base-300 overflow-hidden flex">
                <div class="p-4">
                  <ChatFileList
                    :files="chatInfo.files"
                    :message-files="[]"
                    :chat-project="getChatProject()"
                  />
                </div>
              </div>
            </div>

            <!-- ADDED: Chat History Summary -->
            <div v-if="chatHistorySummary.length" class="rounded-xl border border-base-300 overflow-hidden">
              <div class="flex items-center gap-2 px-4 py-2.5 bg-base-200 border-b border-base-300 shrink-0">
                <i class="fa-solid fa-comments text-primary"></i>
                <span class="text-sm font-semibold">Chat History Summary</span>
                <span class="badge badge-ghost badge-xs ml-auto">{{ chatHistorySummary.length }} LLM rounds</span>
              </div>
              <div class="p-3 space-y-2 max-h-96 overflow-y-auto">
                <div
                  v-for="(round, idx) in chatHistorySummary"
                  :key="idx"
                  class="rounded-lg border border-base-300 overflow-hidden"
                >
                  <!-- Round header -->
                  <div class="flex items-center gap-2 px-3 py-1.5 bg-secondary/8 text-xs text-secondary/80">
                    <i class="fa-solid fa-robot text-xs"></i>
                    <span class="font-semibold">Round {{ idx + 1 }}</span>
                    <span class="badge badge-xs badge-ghost font-mono">{{ round.model }}</span>
                    <span v-if="round.toolCallCount" class="badge badge-xs badge-accent">{{ round.toolCallCount }} tools</span>
                    <span v-else class="badge badge-xs badge-success">final</span>
                    <span class="ml-auto font-mono text-base-content/30">{{ formatDuration(round.duration_seconds) }}</span>
                  </div>
                  <!-- Response preview -->
                  <div v-if="round.response_preview" class="px-3 py-2 text-xs text-base-content/70 font-mono whitespace-pre-wrap break-words max-h-24 overflow-y-auto bg-base-100/50">
                    {{ round.response_preview }}
                  </div>
                  <div v-else class="px-3 py-2 text-xs text-base-content/30 italic">No text response (tool calls only)</div>
                </div>
              </div>
            </div>
            <!-- No history available yet hint -->
            <div v-else-if="!chatHistorySummary.length && llmRequestsForOverview.length === 0" class="text-center text-xs text-base-content/40 py-2">
              No LLM history available for this session.
            </div>

          </div>

          <!-- METRICS TAB -->
          <div v-if="activeTab === 'metrics'" class="space-y-4">
            
            <!-- Overall Metrics -->
            <div class="rounded-xl border border-info/40 bg-info/5 overflow-hidden">
              <div class="flex items-center gap-2 px-4 py-2.5 bg-info/10 border-b border-info/30 shrink-0">
                <i class="fa-solid fa-gauge text-info"></i>
                <span class="text-sm font-semibold">Overall Metrics</span>
              </div>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4 p-4">
                <div class="space-y-1 p-3 rounded-lg bg-base-100 border border-info/20">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Total Tokens</div>
                  <div class="text-2xl font-bold text-info">{{ metricsInfo?.total_tokens || 0 }}</div>
                </div>
                <div class="space-y-1 p-3 rounded-lg bg-base-100 border border-info/20">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Input Tokens</div>
                  <div class="text-2xl font-bold text-success">{{ metricsInfo?.total_input_tokens || 0 }}</div>
                </div>
                <div class="space-y-1 p-3 rounded-lg bg-base-100 border border-info/20">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Output Tokens</div>
                  <div class="text-2xl font-bold text-warning">{{ metricsInfo?.total_output_tokens || 0 }}</div>
                </div>
                <div class="space-y-1 p-3 rounded-lg bg-base-100 border border-info/20">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Cost</div>
                  <div class="text-2xl font-bold text-primary">{{ formatCost(metricsInfo?.total_cxjcoins) }}</div>
                </div>
              </div>
            </div>

            <!-- LLM Calls Metrics -->
            <div v-if="metricsInfo" class="rounded-xl border border-base-300 overflow-hidden">
              <div class="flex items-center gap-2 px-4 py-2.5 bg-base-200 border-b border-base-300 shrink-0">
                <i class="fa-solid fa-message text-secondary"></i>
                <span class="text-sm font-semibold">LLM Requests</span>
              </div>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-3 p-4">
                <div class="space-y-1">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Total Calls</div>
                  <div class="text-xl font-bold">{{ metricsInfo.llm_calls || 0 }}</div>
                </div>
                <div class="space-y-1">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Duration</div>
                  <div class="text-xl font-bold">{{ formatDuration(metricsInfo.total_llm_duration_seconds) }}</div>
                </div>
                <div class="space-y-1">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Avg Duration</div>
                  <div class="text-xl font-bold">{{ formatDuration(metricsInfo.total_llm_duration_seconds / (metricsInfo.llm_calls || 1)) }}</div>
                </div>
                <div class="space-y-1">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Cost</div>
                  <div class="text-xl font-bold text-primary">{{ formatCost(metricsInfo.total_cxjcoins) }}</div>
                </div>
              </div>
            </div>

            <!-- Tool Calls Metrics -->
            <div v-if="metricsInfo" class="rounded-xl border border-base-300 overflow-hidden">
              <div class="flex items-center gap-2 px-4 py-2.5 bg-base-200 border-b border-base-300 shrink-0">
                <i class="fa-solid fa-wrench text-accent"></i>
                <span class="text-sm font-semibold">Tool Calls</span>
              </div>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-3 p-4">
                <div class="space-y-1">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Total Calls</div>
                  <div class="text-xl font-bold">{{ metricsInfo.tool_calls || 0 }}</div>
                </div>
                <div class="space-y-1">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Successful</div>
                  <div class="text-xl font-bold text-success">{{ metricsInfo.successful_tool_calls || 0 }}</div>
                </div>
                <div class="space-y-1">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Failed</div>
                  <div class="text-xl font-bold" :class="metricsInfo.failed_tool_calls ? 'text-error' : ''">
                    {{ metricsInfo.failed_tool_calls || 0 }}
                  </div>
                </div>
                <div class="space-y-1">
                  <div class="text-xs text-base-content/50 font-semibold uppercase">Avg Duration</div>
                  <div class="text-xl font-bold">{{ formatDuration(metricsInfo.avg_tool_duration_seconds) }}</div>
                </div>
              </div>
            </div>

            <!-- Tool Breakdown -->
            <div v-if="toolMetrics && Object.keys(toolMetrics).length" class="space-y-3">
              <div v-for="(metrics, toolName) in toolMetrics" :key="toolName" class="rounded-xl border border-base-300 overflow-hidden">
                <div class="flex items-center gap-2 px-4 py-2.5 bg-base-200 border-b border-base-300 shrink-0">
                  <i class="fa-solid fa-cube text-warning"></i>
                  <span class="text-sm font-semibold">{{ toolName }}</span>
                  <span class="ml-auto badge badge-sm" :class="metrics.success_rate === 100 ? 'badge-success' : 'badge-warning'">
                    {{ metrics.success_rate.toFixed(0) }}%
                  </span>
                </div>
                <div class="grid grid-cols-2 md:grid-cols-5 gap-3 p-4">
                  <div><div class="text-xs text-base-content/50">Calls</div><div class="font-bold">{{ metrics.total_calls }}</div></div>
                  <div><div class="text-xs text-base-content/50">Success</div><div class="font-bold text-success">{{ metrics.successful }}</div></div>
                  <div><div class="text-xs text-base-content/50">Failed</div><div class="font-bold" :class="metrics.failed ? 'text-error' : ''">{{ metrics.failed }}</div></div>
                  <div><div class="text-xs text-base-content/50">Total Time</div><div class="font-bold">{{ formatDuration(metrics.total_duration) }}</div></div>
                  <div><div class="text-xs text-base-content/50">Avg Time</div><div class="font-bold">{{ formatDuration(metrics.avg_duration) }}</div></div>
                </div>
              </div>
            </div>
          </div>

          <!-- CONVERSATION TAB — replaces old "LLM Requests" + "Tool Calls" tabs -->
          <div v-if="activeTab === 'conversation'">
            <LlmRequestsViewer
              :chat-session="chatSession"
              :is-admin="isAdmin"
            />
          </div>

        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LogEntryDetail',
  props: {
    chatSession: { type: Object, default: null },
    loading: { type: Boolean, default: false },
    isAdmin: { type: Boolean, default: false }
  },
  emits: ['close'],
  data() {
    return {
      activeTab: 'overview',
      expandedSections: {},
      tabs: [
        { id: 'overview', label: 'Overview', icon: 'fa-chart-pie' },
        { id: 'metrics', label: 'Metrics', icon: 'fa-gauge' },
        { id: 'conversation', label: 'Conversation', icon: 'fa-timeline' }
      ],
      profiles: []
    }
  },

  created() {
    this.loadProfiles()
  },

  computed: {
    hasError() {
      return !!this.chatSession?.chat_session?.error
    },
    chatInfo() {
      return this.chatSession?.chat_session
    },
    metricsInfo() {
      return this.chatSession?.metrics
    },
    toolMetrics() {
      return this.chatSession?.tool_metrics
    },
    chatProject() {
      const { project_id } = this.chatInfo
      return this.$projects.allProjectsById[project_id] || this.$project
    },
    // ADDED: raw llm_requests list for overview use
    llmRequestsForOverview() {
      return this.chatSession?.llm_requests || []
    },
    // ADDED: build a concise summary of each LLM round for the overview tab
    chatHistorySummary() {
      const requests = this.llmRequestsForOverview
      if (!requests.length) return []

      const toolCalls = this.chatSession?.tool_calls || []

      return requests
        .map(req => {
          const tokenData = req.token_event ?? req
          const reqTs = tokenData.timestamp ?? 0

          // Count tool calls that occurred after this request timestamp
          const nextReq = requests[requests.indexOf(req) + 1]
          const nextTs = nextReq
            ? ((nextReq.token_event ?? nextReq).timestamp ?? Infinity)
            : Infinity

          const toolsInRound = toolCalls.filter(t => {
            const toolEvent = t.tool_event ?? t
            return toolEvent.timestamp >= reqTs && toolEvent.timestamp < nextTs
          })

          // Get response preview: trim and limit to 300 chars
          const responseText = tokenData.response_content || ''
          const preview = responseText.trim().slice(0, 300) + (responseText.length > 300 ? '…' : '')

          return {
            model: tokenData.model || '',
            duration_seconds: tokenData.duration_seconds || 0,
            input_tokens: tokenData.input_tokens || 0,
            output_tokens: tokenData.output_tokens || 0,
            toolCallCount: toolsInRound.length,
            response_preview: preview || null
          }
        })
        .sort((a, b) => {
          // Already in original order from llm_requests
          return 0
        })
    }
  },

  watch: {
    chatSession() {
      this.loadProfiles()
    }
  },

  methods: {
    toggleSection(key) {
      this.expandedSections[key] = !this.expandedSections[key]
    },

    async loadProfiles() {
      if (!this.chatSession) {
        return
      }
      this.profiles = (await this.$storex.profiles.loadProjectProfiles(this.chatProject))
            .filter(p => this.chatInfo?.profiles?.includes(p.name))
    },

    getChatProject() {
      return this.$projects?.allProjects?.find(p => p.project_id === this.chatInfo?.project_id)
    },

    formatDuration(seconds) {
      return seconds ? `${seconds.toFixed(2)}s` : '—'
    },

    formatCost(coins) {
      return coins ? `${coins.toFixed(5)} CXJ` : '—'
    },

    formatDate(timestamp) {
      if (typeof timestamp === 'number') {
        return new Date(timestamp * 1000).toLocaleString()
      }
      return new Date(timestamp).toLocaleString()
    }
  }
}
</script>