<script setup>
import ProfileAvatar from '../profile/ProfileAvatar.vue'
import ChatFileList from '../chat/ChatFileList.vue'
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

          <!-- LLM REQUESTS TAB -->
          <div v-if="activeTab === 'requests'" class="space-y-4">
            <div v-if="!llmRequests.length" class="text-center py-8 text-base-content/50">
              <i class="fa-solid fa-inbox text-2xl mb-2 block opacity-30"></i>
              No LLM requests found
            </div>

            <div v-for="(req, idx) in llmRequests" :key="idx" class="rounded-xl border border-base-300 overflow-hidden">
              <button
                @click="toggleRequestExpansion(idx)"
                class="w-full flex items-center justify-between px-4 py-3 bg-base-200 border-b border-base-300 hover:bg-base-300 transition-colors"
              >
                <div class="flex items-center gap-3 min-w-0 flex-1">
                  <i :class="expandedSections[`req-${idx}`] ? 'fa-solid fa-chevron-down' : 'fa-solid fa-chevron-right'" class="text-primary shrink-0"></i>
                  <div class="flex items-center gap-2 min-w-0">
                    <span class="text-sm font-semibold">Request #{{ idx + 1 }}</span>
                    <span class="badge badge-primary badge-sm">{{ req.model }}</span>
                    <span class="badge badge-info badge-sm">{{ req.total_tokens }} tokens</span>
                  </div>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                  <span class="text-xs text-base-content/50">{{ formatDuration(req.duration_seconds) }}</span>
                  <span class="text-xs font-mono text-base-content/30">{{ formatDate(req.timestamp) }}</span>
                </div>
              </button>

              <!-- CHANGED: Condensed request detail — single compact info strip instead of three grids -->
              <div v-if="expandedSections[`req-${idx}`]" class="bg-base-50 border-t border-base-300">

                <!-- Compact info strip -->
                <div class="flex flex-wrap items-center gap-1.5 px-3 py-2 border-b border-base-300 bg-base-200/40 text-xs">
                  <!-- Tokens -->
                  <span class="badge badge-success badge-sm gap-1" title="Input tokens">
                    <i class="fa-solid fa-arrow-right-to-bracket text-xs"></i>{{ req.input_tokens || 0 }}
                  </span>
                  <span class="badge badge-warning badge-sm gap-1" title="Output tokens">
                    <i class="fa-solid fa-arrow-right-from-bracket text-xs"></i>{{ req.output_tokens || 0 }}
                  </span>
                  <span class="text-base-content/30">·</span>
                  <!-- Duration & cost -->
                  <span class="badge badge-ghost badge-sm gap-1" title="Duration">
                    <i class="fa-regular fa-clock text-xs"></i>{{ formatDuration(req.duration_seconds) }}
                  </span>
                  <span class="badge badge-primary badge-sm gap-1" title="Cost">
                    <i class="fa-solid fa-coins text-xs"></i>{{ formatCost(req.total_cxjcoins) }}
                  </span>
                  <span class="text-base-content/30">·</span>
                  <!-- Model & provider -->
                  <span class="font-mono text-base-content/60">{{ req.model }}</span>
                  <span class="badge badge-ghost badge-sm">{{ req.provider }}</span>
                  <span class="text-base-content/30">·</span>
                  <!-- Pricing -->
                  <span class="text-base-content/50" title="Input price / Output price (CXJ per 1k tokens)">
                    {{ req.input_k_tokens_cxjcoins }}/{{ req.output_k_tokens_cxjcoins }} CXJ/1k
                  </span>
                  <span class="text-base-content/30">·</span>
                  <!-- Token source -->
                  <span v-if="req.tokens_from_provider" class="badge badge-success badge-xs" title="Tokens from provider">provider</span>
                  <span v-else class="badge badge-ghost badge-xs" title="Tokens calculated">calculated</span>
                  <!-- Request ID -->
                  <span v-if="req.request_id" class="font-mono text-base-content/30" title="Request ID">{{ req.request_id.slice(0, 8) }}…</span>
                  <!-- Session ID -->
                  <span v-if="req.session_id" class="font-mono text-base-content/30" title="Session ID">s:{{ req.session_id.slice(0, 6) }}</span>
                  <!-- Tags -->
                  <template v-if="req.tags">
                    <span class="text-base-content/30">·</span>
                    <span v-for="tag in req.tags.split(',')" :key="tag" class="badge badge-ghost badge-xs">{{ tag.trim() }}</span>
                  </template>
                </div>

                <!-- Messages section -->
                <div class="p-3 space-y-3">
                  <!-- Messages Loading or Empty State -->
                  <div v-if="messagesLoading[idx]" class="flex items-center gap-2">
                    <span class="loading loading-spinner loading-sm text-primary"></span>
                    <span class="text-xs text-base-content/60">Loading messages...</span>
                  </div>

                  <div v-else-if="requestMessages[idx]">
                    <!-- Warning if no messages found -->
                    <div v-if="!requestMessages[idx].llm.length && !requestMessages[idx].tool.length" class="alert alert-warning p-3">
                      <i class="fa-solid fa-triangle-exclamation text-sm"></i>
                      <span class="text-sm">No messages found for this request</span>
                      <button class="btn btn-sm btn-ghost" @click="loadMessagesForRequest(idx)">
                        <i class="fa-solid fa-redo text-xs"></i> Retry
                      </button>
                    </div>

                    <!-- Messages for this request -->
                    <div v-else class="space-y-3">
                      <div class="text-sm font-semibold text-base-content/70">Associated Messages</div>

                      <!-- LLM Archived Messages -->
                      <div v-if="requestMessages[idx].llm.length" class="space-y-3">
                        <div class="text-xs font-semibold text-secondary/80 flex items-center gap-1">
                          <i class="fa-solid fa-comments text-xs"></i>
                          LLM Archived Messages ({{ requestMessages[idx].llm.length }})
                        </div>

                        <div v-for="(msg, mIdx) in requestMessages[idx].llm" :key="`llm-${idx}-${mIdx}`" class="rounded-lg border border-secondary/20 overflow-hidden">
                          <!-- Archived message header -->
                          <div class="flex items-center gap-2 px-3 py-2 bg-secondary/10 border-b border-secondary/20">
                            <i class="fa-solid fa-robot text-xs text-secondary"></i>
                            <span class="text-xs font-semibold text-secondary">{{ msg.model }}</span>
                            <span class="badge badge-xs badge-ghost">{{ msg.provider }}</span>
                            <div class="ml-auto flex items-center gap-2">
                              <span class="badge badge-xs badge-success">in: {{ msg.input_tokens }}</span>
                              <span class="badge badge-xs badge-warning">out: {{ msg.output_tokens }}</span>
                              <span class="text-xs text-base-content/40 font-mono">{{ formatDate(msg.timestamp) }}</span>
                            </div>
                          </div>

                          <!-- Request context messages (collapsible) -->
                          <div v-if="msg.request_messages && msg.request_messages.length" class="border-b border-secondary/10">
                            <button
                              @click="toggleSection(`llm-req-${idx}-${mIdx}`)"
                              class="w-full flex items-center gap-2 px-3 py-2 bg-base-200/50 hover:bg-base-200 transition-colors text-left"
                            >
                              <i :class="expandedSections[`llm-req-${idx}-${mIdx}`] ? 'fa-solid fa-chevron-down' : 'fa-solid fa-chevron-right'" class="text-xs text-base-content/40 shrink-0"></i>
                              <span class="text-xs text-base-content/60 font-semibold">Context Messages ({{ msg.request_messages.length }})</span>
                            </button>
                            <div v-if="expandedSections[`llm-req-${idx}-${mIdx}`]" class="space-y-1 p-2 max-h-80 overflow-y-auto">
                              <div
                                v-for="(ctxMsg, cIdx) in msg.request_messages"
                                :key="cIdx"
                                class="rounded p-2 text-xs"
                                :class="{
                                  'bg-base-300/50 border border-base-content/10': ctxMsg.role === 'system',
                                  'bg-info/5 border border-info/20': ctxMsg.role === 'user',
                                  'bg-secondary/5 border border-secondary/20': ctxMsg.role === 'assistant',
                                  'bg-accent/5 border border-accent/20': ctxMsg.role === 'tool',
                                }"
                              >
                                <div class="font-semibold mb-1 capitalize" :class="{
                                  'text-base-content/50': ctxMsg.role === 'system',
                                  'text-info': ctxMsg.role === 'user',
                                  'text-secondary': ctxMsg.role === 'assistant',
                                  'text-accent': ctxMsg.role === 'tool',
                                }">{{ ctxMsg.role }}</div>
                                <div class="font-mono text-base-content/70 whitespace-pre-wrap break-words max-h-40 overflow-y-auto">{{ truncateContent(ctxMsg.content) }}</div>
                              </div>
                            </div>
                          </div>

                          <!-- Response content -->
                          <div class="p-3 space-y-1">
                            <div class="text-xs font-semibold text-secondary flex items-center gap-1">
                              <i class="fa-solid fa-reply text-xs"></i> Response
                            </div>
                            <div class="font-mono text-xs text-base-content/80 whitespace-pre-wrap break-words max-h-60 overflow-y-auto bg-base-100 border border-secondary/20 rounded p-2">{{ msg.response_content || '—' }}</div>
                          </div>

                          <!-- Error if any -->
                          <div v-if="msg.error" class="px-3 pb-3">
                            <div class="p-2 rounded bg-error/10 border border-error/30">
                              <div class="text-xs text-error font-semibold mb-1">Error</div>
                              <div class="text-xs text-error/80">{{ msg.error }}</div>
                            </div>
                          </div>
                        </div>
                      </div>

                      <!-- Tool Messages -->
                      <div v-if="requestMessages[idx].tool.length" class="space-y-2">
                        <div class="text-xs font-semibold text-accent/80 flex items-center gap-1">
                          <i class="fa-solid fa-wrench text-xs"></i>
                          Tool Calls ({{ requestMessages[idx].tool.length }})
                        </div>
                        <div v-for="(msg, mIdx) in requestMessages[idx].tool" :key="`tool-${idx}-${mIdx}`" class="rounded-lg bg-accent/10 border border-accent/20 p-3 space-y-3">
                          <div class="flex items-center gap-2">
                            <span class="text-xs font-semibold text-accent">{{ msg.tool_name }}</span>
                            <span class="badge badge-accent badge-xs">{{ msg.tool_call_id?.slice(0, 8) }}</span>
                          </div>
                          <div v-if="msg.request_args && Object.keys(msg.request_args).length" class="space-y-1">
                            <div class="text-xs text-base-content/60 font-semibold">Arguments:</div>
                            <div class="bg-base-100 rounded p-2 font-mono text-xs text-base-content/70 overflow-x-auto max-h-32 overflow-y-auto border border-base-300">
                              {{ formatJson(msg.request_args) }}
                            </div>
                          </div>
                          <div v-if="msg.result" class="space-y-1">
                            <div class="text-xs text-base-content/60 font-semibold">Result:</div>
                            <div class="bg-base-100 rounded p-2 font-mono text-xs text-base-content/70 overflow-x-auto max-h-32 overflow-y-auto border border-base-300">
                              {{ typeof msg.result === 'string' ? msg.result : formatJson(msg.result) }}
                            </div>
                          </div>
                          <div v-if="msg.error_message" class="p-2 rounded-lg bg-error/10 border border-error/30">
                            <div class="text-xs text-error font-semibold mb-1">Error</div>
                            <div class="text-xs text-error/80">{{ msg.error_message }}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- TOOL CALLS TAB -->
          <div v-if="activeTab === 'tools'" class="space-y-4">
            <div v-if="!toolCalls.length" class="text-center py-8 text-base-content/50">
              <i class="fa-solid fa-inbox text-2xl mb-2 block opacity-30"></i>
              No tool calls found
            </div>

            <div v-for="(tool, idx) in toolCalls" :key="idx" class="rounded-xl border border-base-300 overflow-hidden">
              <button
                @click="toggleSection(`tool-${idx}`)"
                class="w-full flex items-center justify-between px-4 py-3 bg-base-200 border-b border-base-300 hover:bg-base-300 transition-colors"
              >
                <div class="flex items-center gap-3 min-w-0 flex-1">
                  <i :class="expandedSections[`tool-${idx}`] ? 'fa-solid fa-chevron-down' : 'fa-solid fa-chevron-right'" class="text-primary shrink-0"></i>
                  <div class="flex items-center gap-2 min-w-0">
                    <span class="text-sm font-semibold">{{ tool.name }}</span>
                    <span v-if="tool.success" class="badge badge-success badge-sm">Success</span>
                    <span v-else class="badge badge-error badge-sm">Failed</span>
                  </div>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                  <span class="text-xs text-base-content/50">{{ formatDuration(tool.time_taken) }}</span>
                  <span class="text-xs font-mono text-base-content/30">{{ formatDate(tool.timestamp) }}</span>
                </div>
              </button>

              <div v-if="expandedSections[`tool-${idx}`]" class="p-4 space-y-3 bg-base-50 border-t border-base-300">
                <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
                  <div class="space-y-1">
                    <div class="text-xs text-base-content/50 uppercase">Tool Name</div>
                    <div class="text-sm font-semibold">{{ tool.name }}</div>
                  </div>
                  <div class="space-y-1">
                    <div class="text-xs text-base-content/50 uppercase">Duration</div>
                    <div class="text-sm font-bold">{{ formatDuration(tool.time_taken) }}</div>
                  </div>
                  <div class="space-y-1">
                    <div class="text-xs text-base-content/50 uppercase">Status</div>
                    <div :class="tool.success ? 'text-success' : 'text-error'" class="text-sm font-bold">
                      {{ tool.success ? 'Success' : 'Failed' }}
                    </div>
                  </div>
                </div>

                <!-- Error Message -->
                <div v-if="tool.error_message" class="p-3 rounded-lg bg-error/10 border border-error/30">
                  <div class="text-xs text-error font-semibold mb-1">Error</div>
                  <div class="text-sm text-error/80">{{ tool.error_message }}</div>
                </div>

                <!-- Tool Event Details -->
                <div class="text-xs space-y-2 pt-2 border-t border-base-300">
                  <div class="flex items-center gap-2">
                    <span class="text-base-content/50 font-semibold uppercase w-24">Request ID:</span>
                    <span class="font-mono text-base-content/70 break-all flex-1">{{ tool.request_id || '—' }}</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <span class="text-base-content/50 font-semibold uppercase w-24">Chat ID:</span>
                    <span class="font-mono text-base-content/70 break-all flex-1">{{ tool.chat_id || '—' }}</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <span class="text-base-content/50 font-semibold uppercase w-24">Project:</span>
                    <span class="text-base-content/70 flex-1">{{ tool.project_name || '—' }}</span>
                  </div>
                </div>
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
      requestMessages: {},
      messagesLoading: {},
      tabs: [
        { id: 'overview', label: 'Overview', icon: 'fa-chart-pie' },
        { id: 'metrics', label: 'Metrics', icon: 'fa-gauge' },
        { id: 'requests', label: 'LLM Requests', icon: 'fa-message' },
        { id: 'tools', label: 'Tool Calls', icon: 'fa-wrench' }
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
    llmRequests() {
      return this.chatSession?.llm_requests || []
    },
    toolCalls() {
      return this.chatSession?.tool_calls || []
    },
    toolMetrics() {
      return this.chatSession?.tool_metrics
    },
    chatProject() {
      const { project_id } = this.chatInfo
      return this.$projects.allProjectsById[project_id] || this.$project
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

    async toggleRequestExpansion(idx) {
      const key = `req-${idx}`
      this.expandedSections[key] = !this.expandedSections[key]

      if (this.expandedSections[key] && !this.requestMessages[idx]) {
        await this.loadMessagesForRequest(idx)
      }
    },

    async loadMessagesForRequest(idx) {
      if (!this.chatSession?.chat_session?.chat_id) return

      const req = this.llmRequests[idx]
      // request_id is on token_event
      const requestId = req?.token_event?.request_id

      if (!requestId) {
        this.requestMessages[idx] = { llm: [], tool: [] }
        return
      }

      this.messagesLoading[idx] = true

      try {
        const chatId = this.chatSession.chat_session.chat_id

        const result = await this.$project.$api.analytics.admin.chatSessionMessages(chatId, { requestId })

        const llm = (result.llm_messages || [])

        const tool = (result.tool_messages || [])

        this.requestMessages[idx] = { llm, tool }
      } catch (err) {
        console.error('Failed to load request messages:', err)
        this.requestMessages[idx] = { llm: [], tool: [] }
      } finally {
        this.messagesLoading[idx] = false
      }
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

    formatJson(obj) {
      try {
        return JSON.stringify(obj, null, 2)
      } catch {
        return String(obj)
      }
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
