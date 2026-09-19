<template>
  <div class="h-full flex flex-col gap-4 overflow-auto bg-base-100 p-4">
    <!-- Header -->
    <div class="flex items-center justify-between shrink-0">
      <h2 class="text-lg font-bold flex items-center gap-2">
        <i class="fa-solid fa-file-lines text-primary"></i>
        AI Logs
      </h2>
      <button 
        class="btn btn-sm btn-ghost"
        @click="refreshLogs"
        :class="isLoading ? 'loading' : ''"
        title="Refresh logs"
      >
        <i class="fa-solid fa-rotate-right"></i>
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="flex items-center justify-center py-8">
      <div class="loading loading-spinner loading-lg"></div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="alert alert-error gap-3">
      <i class="fa-solid fa-triangle-exclamation"></i>
      <div>
        <h3 class="font-bold">Failed to load logs</h3>
        <div class="text-sm">{{ error }}</div>
      </div>
      <button class="btn btn-sm" @click="refreshLogs">Retry</button>
    </div>

    <!-- Empty State -->
    <div v-else-if="!logs || !logs.total_log_records" class="flex flex-col items-center justify-center py-12 text-center">
      <i class="fa-solid fa-inbox text-4xl text-base-content/20 mb-3"></i>
      <p class="text-base-content/60">No AI logs found for this chat</p>
      <div v-if="logs?.fallback_used" class="text-xs text-base-content/40 mt-2">
        <i class="fa-solid fa-circle-info mr-1"></i>
        {{ logs.fallback_reason }}
      </div>
    </div>

    <!-- Logs Loaded -->
    <div v-else class="flex-1 overflow-y-auto space-y-4 min-h-0">
      <!-- Tab Navigation -->
      <div class="tabs tabs-bordered gap-0">
        <a 
          :class="['tab', activeTab === 'summary' ? 'tab-active' : '']"
          @click.prevent="activeTab = 'summary'"
        >
          <i class="fa-solid fa-chart-pie mr-2"></i>Summary
        </a>
        <a 
          :class="['tab', activeTab === 'records' ? 'tab-active' : '']"
          @click.prevent="activeTab = 'records'"
        >
          <i class="fa-solid fa-list mr-2"></i>Records
          <span class="badge badge-sm badge-primary">{{ logs.total_log_records }}</span>
        </a>
        <a 
          :class="['tab', activeTab === 'forensic' ? 'tab-active' : '']"
          @click.prevent="activeTab = 'forensic'"
        >
          <i class="fa-solid fa-magnifying-glass mr-2"></i>Forensic
        </a>
      </div>

      <!-- SUMMARY TAB -->
      <div v-show="activeTab === 'summary'" class="space-y-4">
        <!-- Summary Stats Cards -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <!-- Total Records -->
          <div class="stats bg-base-200 shadow-sm">
            <div class="stat">
              <div class="stat-title text-xs">Total Records</div>
              <div class="stat-value text-2xl">{{ logs.total_log_records }}</div>
              <div class="stat-desc text-xs">
                <span class="badge badge-xs badge-info">{{ logs.total_requests }} req</span>
                <span class="badge badge-xs badge-success">{{ logs.total_responses }} res</span>
              </div>
            </div>
          </div>

          <!-- Duration -->
          <div class="stats bg-base-200 shadow-sm">
            <div class="stat">
              <div class="stat-title text-xs">Total Duration</div>
              <div class="stat-value text-2xl">{{ formatDuration(logs.total_duration_seconds) }}</div>
              <div v-if="logs.average_request_duration_seconds" class="stat-desc text-xs">
                Avg: {{ formatDuration(logs.average_request_duration_seconds) }}/req
              </div>
            </div>
          </div>

          <!-- Token Stats -->
          <div class="stats bg-base-200 shadow-sm">
            <div class="stat">
              <div class="stat-title text-xs">Est. Tokens</div>
              <div class="stat-value text-2xl">{{ formatNumber(logs.token_stats.total_estimated_tokens) }}</div>
              <div class="stat-desc text-xs">
                <span class="text-info">↓{{ formatNumber(logs.token_stats.total_estimated_input_tokens) }}</span>
                <span class="text-success">↑{{ formatNumber(logs.token_stats.total_estimated_output_tokens) }}</span>
              </div>
            </div>
          </div>

          <!-- Status -->
          <div class="stats bg-base-200 shadow-sm" :class="logs.has_errors ? 'bg-error/10' : ''">
            <div class="stat">
              <div class="stat-title text-xs">Status</div>
              <div class="stat-value text-2xl">
                <span v-if="!logs.has_errors" class="text-success">✓</span>
                <span v-else class="text-error">⚠</span>
              </div>
              <div class="stat-desc text-xs">
                <span class="badge badge-xs" 
                  :class="logs.status_distribution.success > 0 ? 'badge-success' : 'badge-ghost'"
                >{{ logs.status_distribution.success }} ok</span>
                <span v-if="logs.status_distribution.error > 0" class="badge badge-xs badge-error">
                  {{ logs.status_distribution.error }} err
                </span>
                <span v-if="logs.status_distribution.cancelled > 0" class="badge badge-xs badge-warning">
                  {{ logs.status_distribution.cancelled }} cancel
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Status Distribution Chart -->
        <div class="card bg-base-200 shadow-sm">
          <div class="card-body gap-3">
            <h3 class="card-title text-sm">Status Distribution</h3>
            <div class="flex items-end justify-around gap-2 h-24">
              <div class="flex flex-col items-center gap-2 flex-1">
                <div class="h-full bg-success rounded-t-md transition-all" 
                  :style="{ height: getStatusBarHeight('success') }"
                  :title="`Success: ${logs.status_distribution.success}`"
                ></div>
                <div class="text-xs font-semibold">✓ Success</div>
                <div class="text-xs text-base-content/60">{{ logs.status_distribution.success }}</div>
              </div>
              <div class="flex flex-col items-center gap-2 flex-1">
                <div class="h-full bg-error rounded-t-md transition-all" 
                  :style="{ height: getStatusBarHeight('error') }"
                  :title="`Error: ${logs.status_distribution.error}`"
                ></div>
                <div class="text-xs font-semibold">✕ Error</div>
                <div class="text-xs text-base-content/60">{{ logs.status_distribution.error }}</div>
              </div>
              <div class="flex flex-col items-center gap-2 flex-1">
                <div class="h-full bg-warning rounded-t-md transition-all" 
                  :style="{ height: getStatusBarHeight('cancelled') }"
                  :title="`Cancelled: ${logs.status_distribution.cancelled}`"
                ></div>
                <div class="text-xs font-semibold">⊗ Cancelled</div>
                <div class="text-xs text-base-content/60">{{ logs.status_distribution.cancelled }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Model Usage -->
        <div class="card bg-base-200 shadow-sm">
          <div class="card-body gap-3">
            <h3 class="card-title text-sm flex items-center gap-2">
              <i class="fa-solid fa-microchip text-sm"></i>
              Model Usage
            </h3>
            <div class="space-y-2">
              <div v-for="model in logs.model_usage" :key="`${model.model}-${model.provider}`"
                class="flex items-center justify-between gap-2 p-2 bg-base-100 rounded-lg hover:bg-base-300 transition-colors"
              >
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-semibold truncate" :title="model.model">{{ model.model }}</div>
                  <div class="text-xs text-base-content/60 truncate" :title="model.provider">
                    <i class="fa-solid fa-cube text-xs mr-1"></i>{{ model.provider }}
                  </div>
                </div>
                <div class="text-right shrink-0">
                  <div class="text-sm font-bold badge badge-sm badge-outline">{{ model.request_count }}</div>
                  <div class="text-xs text-base-content/60">{{ formatDuration(model.total_duration_seconds) }}</div>
                </div>
              </div>
              <div v-if="!logs.model_usage || logs.model_usage.length === 0" class="text-xs text-base-content/40 text-center py-3">
                No model usage data
              </div>
            </div>
          </div>
        </div>

        <!-- Token Breakdown -->
        <div class="card bg-base-200 shadow-sm">
          <div class="card-body gap-3">
            <h3 class="card-title text-sm flex items-center gap-2">
              <i class="fa-solid fa-coins text-sm"></i>
              Token Breakdown
            </h3>
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="text-xs badge badge-info">Input</span>
                  <span class="text-sm">Estimated input tokens</span>
                </div>
                <span class="font-bold text-info">{{ formatNumber(logs.token_stats.total_estimated_input_tokens) }}</span>
              </div>
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="text-xs badge badge-success">Output</span>
                  <span class="text-sm">Estimated output tokens</span>
                </div>
                <span class="font-bold text-success">{{ formatNumber(logs.token_stats.total_estimated_output_tokens) }}</span>
              </div>
              <div class="divider my-1"></div>
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="text-xs badge badge-primary">Total</span>
                  <span class="text-sm font-semibold">Total estimated tokens</span>
                </div>
                <span class="font-bold text-lg text-primary">{{ formatNumber(logs.token_stats.total_estimated_tokens) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Timeline & Metadata -->
        <div class="card bg-base-200 shadow-sm">
          <div class="card-body gap-3">
            <h3 class="card-title text-sm flex items-center gap-2">
              <i class="fa-solid fa-clock text-sm"></i>
              Timeline & Metadata
            </h3>
            <div class="space-y-3 text-sm">
              <div v-if="logs.first_timestamp" class="flex items-center justify-between p-2 bg-base-100 rounded">
                <span class="text-base-content/60">First log:</span>
                <span class="font-mono text-xs">{{ formatTimestamp(logs.first_timestamp) }}</span>
              </div>
              <div v-if="logs.last_timestamp" class="flex items-center justify-between p-2 bg-base-100 rounded">
                <span class="text-base-content/60">Last log:</span>
                <span class="font-mono text-xs">{{ formatTimestamp(logs.last_timestamp) }}</span>
              </div>
              <div v-if="logs.session_id" class="flex items-start justify-between gap-2 p-2 bg-base-100 rounded">
                <span class="text-base-content/60 shrink-0">Session ID:</span>
                <code class="font-mono text-xs truncate break-all text-right flex-1">{{ logs.session_id }}</code>
              </div>
              <div v-if="logs.chat_id" class="flex items-start justify-between gap-2 p-2 bg-base-100 rounded">
                <span class="text-base-content/60 shrink-0">Chat ID:</span>
                <code class="font-mono text-xs truncate break-all text-right flex-1">{{ logs.chat_id }}</code>
              </div>
            </div>
          </div>
        </div>

        <!-- Error Details -->
        <div v-if="logs.has_errors && logs.error_details.length > 0" class="card bg-error/10 border border-error shadow-sm">
          <div class="card-body gap-3">
            <h3 class="card-title text-sm text-error flex items-center gap-2">
              <i class="fa-solid fa-triangle-exclamation"></i>
              Error Details
            </h3>
            <div class="space-y-2">
              <div v-for="(error, idx) in logs.error_details" :key="idx"
                class="text-xs bg-base-100 p-2 rounded border-l-2 border-error text-base-content/80"
              >
                {{ error }}
              </div>
            </div>
          </div>
        </div>

        <!-- Fallback Indicator -->
        <div v-if="logs.fallback_used" class="alert alert-warning gap-3">
          <i class="fa-solid fa-circle-info text-lg"></i>
          <div>
            <h3 class="font-bold">Fallback lookup used</h3>
            <div class="text-sm">{{ logs.fallback_reason }}</div>
          </div>
        </div>
      </div>

      <!-- RECORDS TAB -->
      <div v-show="activeTab === 'records'" class="space-y-3">
        <!-- Record Filters -->
        <div class="flex gap-2 flex-wrap">
          <button 
            v-for="type in ['all', 'message', 'tool']"
            :key="type"
            :class="['btn btn-sm', recordTypeFilter === type ? 'btn-primary' : 'btn-ghost']"
            @click="recordTypeFilter = type"
          >
            {{ type === 'all' ? 'All Records' : type === 'message' ? 'LLM Messages' : 'Tool Calls' }}
            <span class="badge badge-xs" :class="recordTypeFilter === type ? 'badge-primary' : 'badge-ghost'">
              {{ getFilteredRecordsCount(type) }}
            </span>
          </button>
        </div>

        <!-- Records List -->
        <div class="space-y-3">
          <div v-if="filteredRecords.length === 0" class="text-center text-base-content/40 py-6">
            <i class="fa-solid fa-inbox text-2xl mb-2"></i>
            <p>No {{ recordTypeFilter === 'all' ? '' : recordTypeFilter }} records</p>
          </div>

          <div v-for="(record, idx) in paginatedRecords" :key="idx"
            class="card bg-base-200 shadow-sm cursor-pointer hover:shadow-md transition-shadow"
            @click="expandedRecord = expandedRecord === idx ? null : idx"
          >
            <div class="card-body gap-2 p-3">
              <!-- Record Header -->
              <div class="flex items-start justify-between gap-2">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <i v-if="isArchivedMessage(record)" class="fa-solid fa-message text-primary text-sm"></i>
                    <i v-else class="fa-solid fa-wrench text-warning text-sm"></i>
                    <span class="font-bold text-sm" v-if="isArchivedMessage(record)">
                      LLM Request #{{ record.message_id?.slice(0, 8) }}
                    </span>
                    <span class="font-bold text-sm" v-else>
                      Tool: {{ record.tool_name }} [{{ record.tool_call_id?.slice(0, 8) }}]
                    </span>
                  </div>
                  <div class="text-xs text-base-content/60 mt-1">
                    {{ formatTimestamp(record.timestamp) }}
                  </div>
                </div>
                <div class="flex items-center gap-1 shrink-0">
                  <span v-if="isArchivedMessage(record)" class="badge badge-xs" :class="record.error ? 'badge-error' : record.cancelled ? 'badge-warning' : 'badge-success'">
                    {{ record.error ? 'error' : record.cancelled ? 'cancelled' : 'ok' }}
                  </span>
                  <span v-else class="badge badge-xs" :class="record.success ? 'badge-success' : 'badge-error'">
                    {{ record.success ? 'ok' : 'error' }}
                  </span>
                  <i class="fa-solid fa-chevron-down text-xs transition-transform" :class="expandedRecord === idx ? 'rotate-180' : ''"></i>
                </div>
              </div>

              <!-- Quick Info -->
              <div class="text-xs text-base-content/60 space-y-1">
                <div v-if="isArchivedMessage(record)" class="flex gap-4 flex-wrap">
                  <span><strong>Model:</strong> {{ record.model }}</span>
                  <span><strong>Duration:</strong> {{ formatDuration(record.duration_seconds) }}</span>
                  <span v-if="record.input_tokens"><strong>Tokens:</strong> {{ record.input_tokens }}↓ / {{ record.output_tokens }}↑</span>
                </div>
                <div v-else class="flex gap-4 flex-wrap">
                  <span><strong>Tool:</strong> {{ record.tool_name }}</span>
                  <span><strong>Duration:</strong> {{ formatDuration(record.duration_seconds) }}</span>
                  <span v-if="record.cached" class="badge badge-xs badge-info">cached</span>
                </div>
              </div>

              <!-- Expanded Details -->
              <div v-if="expandedRecord === idx" class="mt-3 space-y-3 border-t border-base-300 pt-3">
                <!-- Archived Message Details -->
                <template v-if="isArchivedMessage(record)">
                  <!-- Response Preview -->
                  <div class="space-y-1">
                    <label class="text-xs font-bold text-base-content/70">Response:</label>
                    <div class="bg-base-100 p-2 rounded text-xs max-h-40 overflow-y-auto whitespace-pre-wrap break-words font-mono text-base-content/80">
                      {{ record.response_content?.slice(0, 500) }}{{ record.response_content?.length > 500 ? '...' : '' }}
                    </div>
                  </div>

                  <!-- System Prompt -->
                  <div v-if="record.system_prompt" class="space-y-1">
                    <label class="text-xs font-bold text-base-content/70">System Prompt:</label>
                    <div class="bg-base-100 p-2 rounded text-xs max-h-32 overflow-y-auto whitespace-pre-wrap break-words font-mono text-base-content/80">
                      {{ record.system_prompt?.slice(0, 300) }}{{ record.system_prompt?.length > 300 ? '...' : '' }}
                    </div>
                  </div>

                  <!-- Model Configuration -->
                  <div class="space-y-1">
                    <label class="text-xs font-bold text-base-content/70">Configuration:</label>
                    <div class="bg-base-100 p-2 rounded text-xs space-y-1">
                      <div v-if="record.temperature !== null && record.temperature !== undefined">
                        <strong>Temperature:</strong> {{ record.temperature }}
                      </div>
                      <div v-if="record.max_tokens">
                        <strong>Max Tokens:</strong> {{ record.max_tokens }}
                      </div>
                      <div v-if="record.tools && record.tools.length">
                        <strong>Tools Available:</strong> {{ record.tools.length }}
                        <div class="ml-2 mt-1 space-y-1">
                          <div v-for="tool in record.tools.slice(0, 3)" :key="tool.function?.name" class="text-base-content/60">
                            • {{ tool.function?.name }}
                          </div>
                          <div v-if="record.tools.length > 3" class="text-base-content/60">
                            • +{{ record.tools.length - 3 }} more
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Request Messages Count -->
                  <div class="space-y-1">
                    <label class="text-xs font-bold text-base-content/70">Request Messages: {{ record.request_messages?.length }}</label>
                    <div class="bg-base-100 p-2 rounded text-xs max-h-24 overflow-y-auto">
                      <div v-for="(msg, mIdx) in record.request_messages?.slice(0, 5)" :key="mIdx" class="pb-1 border-b border-base-300 last:border-0">
                        <strong class="text-base-content/70">{{ msg.role }}:</strong>
                        <div class="text-base-content/60 truncate">
                          {{ typeof msg.content === 'string' ? msg.content.slice(0, 60) : '[non-text content]' }}
                        </div>
                      </div>
                      <div v-if="record.request_messages?.length > 5" class="text-base-content/40 pt-1">
                        +{{ record.request_messages.length - 5 }} more messages
                      </div>
                    </div>
                  </div>

                  <!-- Provider Info -->
                  <div class="space-y-1">
                    <label class="text-xs font-bold text-base-content/70">Provider Info:</label>
                    <div class="bg-base-100 p-2 rounded text-xs space-y-1">
                      <div><strong>Provider:</strong> {{ record.provider }}</div>
                      <div><strong>Model:</strong> {{ record.model }}</div>
                      <div><strong>User:</strong> {{ record.username }}</div>
                    </div>
                  </div>
                </template>

                <!-- Tool Call Details -->
                <template v-else>
                  <!-- Tool Arguments -->
                  <div class="space-y-1">
                    <label class="text-xs font-bold text-base-content/70">Arguments:</label>
                    <div class="bg-base-100 p-2 rounded text-xs max-h-32 overflow-y-auto whitespace-pre-wrap break-words font-mono text-base-content/80">
                      {{ JSON.stringify(record.request_args, null, 2)?.slice(0, 500) }}
                    </div>
                  </div>

                  <!-- Tool Result -->
                  <div class="space-y-1">
                    <label class="text-xs font-bold text-base-content/70">Result:</label>
                    <div class="bg-base-100 p-2 rounded text-xs max-h-32 overflow-y-auto whitespace-pre-wrap break-words font-mono text-base-content/80">
                      {{ formatResultPreview(record.result)?.slice(0, 500) }}
                    </div>
                  </div>

                  <!-- Error Message -->
                  <div v-if="record.error_message" class="space-y-1">
                    <label class="text-xs font-bold text-error">Error:</label>
                    <div class="bg-error/10 p-2 rounded text-xs border-l-2 border-error text-error">
                      {{ record.error_message }}
                    </div>
                  </div>

                  <!-- Tool Definition -->
                  <div v-if="record.tool_definition" class="space-y-1">
                    <label class="text-xs font-bold text-base-content/70">Tool Definition:</label>
                    <div class="bg-base-100 p-2 rounded text-xs max-h-32 overflow-y-auto whitespace-pre-wrap break-words font-mono text-base-content/80">
                      {{ JSON.stringify(record.tool_definition, null, 2)?.slice(0, 400) }}...
                    </div>
                  </div>

                  <!-- Tool Metadata -->
                  <div class="space-y-1">
                    <label class="text-xs font-bold text-base-content/70">Metadata:</label>
                    <div class="bg-base-100 p-2 rounded text-xs space-y-1">
                      <div><strong>Result sent to model:</strong> <code class="text-base-content/60">{{ record.result_sent_to_model?.slice(0, 80) }}...</code></div>
                      <div><strong>Cached:</strong> {{ record.cached ? 'Yes' : 'No' }}</div>
                      <div><strong>User:</strong> {{ record.username }}</div>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>

        <!-- Pagination -->
        <div v-if="filteredRecords.length > recordsPerPage" class="flex items-center justify-center gap-2">
          <button class="btn btn-sm btn-ghost" @click="recordPage = Math.max(1, recordPage - 1)" :disabled="recordPage === 1">
            <i class="fa-solid fa-chevron-left"></i>
          </button>
          <span class="text-sm">Page {{ recordPage }} of {{ totalRecordPages }}</span>
          <button class="btn btn-sm btn-ghost" @click="recordPage = Math.min(totalRecordPages, recordPage + 1)" :disabled="recordPage === totalRecordPages">
            <i class="fa-solid fa-chevron-right"></i>
          </button>
        </div>
      </div>

      <!-- FORENSIC TAB -->
      <div v-show="activeTab === 'forensic'" class="space-y-3">
        <div class="alert alert-info gap-3">
          <i class="fa-solid fa-shield"></i>
          <div>
            <h3 class="font-bold">Forensic Audit Trail</h3>
            <p class="text-sm">Complete chronological record of all AI interactions with full request/response payloads</p>
          </div>
        </div>

        <!-- Raw JSON Export -->
        <div class="card bg-base-200 shadow-sm">
          <div class="card-body gap-3">
            <div class="flex items-center justify-between">
              <h3 class="card-title text-sm flex items-center gap-2">
                <i class="fa-solid fa-code"></i>
                Export Forensic Data
              </h3>
              <button class="btn btn-xs btn-primary" @click="exportForensicJSON">
                <i class="fa-solid fa-download"></i>
                JSON
              </button>
            </div>
            <p class="text-xs text-base-content/60">
              Download complete forensic audit trail as JSON for compliance, debugging, or analysis
            </p>
          </div>
        </div>

        <!-- Forensic Statistics -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div class="stats bg-base-200 shadow-sm">
            <div class="stat">
              <div class="stat-title text-xs">Total Records</div>
              <div class="stat-value text-xl">{{ logs.raw_log_records?.length || 0 }}</div>
            </div>
          </div>
          <div class="stats bg-base-200 shadow-sm">
            <div class="stat">
              <div class="stat-title text-xs">LLM Messages</div>
              <div class="stat-value text-xl">{{ countRecordType('message') }}</div>
            </div>
          </div>
          <div class="stats bg-base-200 shadow-sm">
            <div class="stat">
              <div class="stat-title text-xs">Tool Calls</div>
              <div class="stat-value text-xl">{{ countRecordType('tool') }}</div>
            </div>
          </div>
          <div class="stats bg-base-200 shadow-sm">
            <div class="stat">
              <div class="stat-title text-xs">Timeline</div>
              <div class="stat-value text-sm">{{ logs.first_timestamp ? '✓' : '—' }}</div>
              <div class="stat-desc text-xs">tracked</div>
            </div>
          </div>
        </div>

        <!-- Raw Records Viewer -->
        <div class="card bg-base-200 shadow-sm">
          <div class="card-body gap-3">
            <h3 class="card-title text-sm">Raw Forensic Records</h3>
            <div class="text-xs text-base-content/60 mb-2">
              Chronologically ordered complete forensic trail ({{ logs.raw_log_records?.length || 0 }} total records)
            </div>
            
            <div class="space-y-2 max-h-96 overflow-y-auto">
              <div v-if="!logs.raw_log_records || logs.raw_log_records.length === 0" class="text-center text-base-content/40 py-4">
                No forensic records available
              </div>
              <details v-for="(record, idx) in logs.raw_log_records" :key="idx" class="collapse bg-base-100 border border-base-300">
                <summary class="collapse-title p-3 cursor-pointer flex items-center justify-between">
                  <span class="flex items-center gap-2">
                    <i v-if="isArchivedMessage(record)" class="fa-solid fa-message text-primary text-xs"></i>
                    <i v-else class="fa-solid fa-wrench text-warning text-xs"></i>
                    <span class="font-mono text-xs">
                      {{ record.message_id?.slice(0, 12) }} 
                      <span class="text-base-content/60">{{ formatTimestamp(record.timestamp) }}</span>
                    </span>
                  </span>
                </summary>
                <div class="collapse-content p-3">
                  <pre class="bg-base-300 p-3 rounded text-xs overflow-x-auto max-h-64 overflow-y-auto text-base-content/70">{{ JSON.stringify(record, null, 2) }}</pre>
                </div>
              </details>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    chatId: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      logs: null,
      isLoading: false,
      error: null,
      activeTab: 'summary',
      recordTypeFilter: 'all',
      recordPage: 1,
      recordsPerPage: 10,
      expandedRecord: null
    }
  },
  computed: {
    totalStatuses() {
      if (!this.logs) return 1
      return Math.max(
        this.logs.status_distribution.success,
        this.logs.status_distribution.error,
        this.logs.status_distribution.cancelled,
        1
      )
    },
    filteredRecords() {
      if (!this.logs || !this.logs.raw_log_records) return []
      
      if (this.recordTypeFilter === 'all') {
        return this.logs.raw_log_records
      } else if (this.recordTypeFilter === 'message') {
        return this.logs.raw_log_records.filter(r => this.isArchivedMessage(r))
      } else if (this.recordTypeFilter === 'tool') {
        return this.logs.raw_log_records.filter(r => !this.isArchivedMessage(r))
      }
      return []
    },
    paginatedRecords() {
      const start = (this.recordPage - 1) * this.recordsPerPage
      const end = start + this.recordsPerPage
      return this.filteredRecords.slice(start, end)
    },
    totalRecordPages() {
      return Math.ceil(this.filteredRecords.length / this.recordsPerPage)
    }
  },
  methods: {
    async loadLogs() {
      this.isLoading = true
      this.error = null
      try {
        this.logs = await this.$storex.api.chats.getChatLogs({ id: this.chatId })
        this.recordPage = 1
      } catch (err) {
        this.error = err.message || 'Failed to load chat logs'
        console.error('Error loading chat logs:', err)
      } finally {
        this.isLoading = false
      }
    },
    async refreshLogs() {
      await this.loadLogs()
    },
    formatDuration(seconds) {
      if (!seconds) return '0s'
      if (seconds < 1) return `${Math.round(seconds * 1000)}ms`
      if (seconds < 60) return `${seconds.toFixed(1)}s`
      const mins = Math.floor(seconds / 60)
      const secs = (seconds % 60).toFixed(0)
      return `${mins}m ${secs}s`
    },
    formatNumber(num) {
      if (!num) return '0'
      return num.toLocaleString()
    },
    formatTimestamp(timestamp) {
      try {
        if (typeof timestamp === 'number') {
          const date = new Date(timestamp * 1000)
          return date.toLocaleString()
        }
        const date = new Date(timestamp)
        return date.toLocaleString()
      } catch {
        return timestamp
      }
    },
    formatResultPreview(result) {
      if (typeof result === 'string') return result
      if (typeof result === 'object') return JSON.stringify(result, null, 2)
      return String(result)
    },
    getStatusBarHeight(status) {
      const dist = this.logs.status_distribution
      const value = dist[status] || 0
      const height = (value / this.totalStatuses) * 100
      return `${Math.max(height, 5)}%`
    },
    isArchivedMessage(record) {
      return record && 'request_messages' in record && 'response_content' in record
    },
    getFilteredRecordsCount(type) {
      if (!this.logs || !this.logs.raw_log_records) return 0
      if (type === 'all') return this.logs.raw_log_records.length
      if (type === 'message') return this.logs.raw_log_records.filter(r => this.isArchivedMessage(r)).length
      if (type === 'tool') return this.logs.raw_log_records.filter(r => !this.isArchivedMessage(r)).length
      return 0
    },
    countRecordType(type) {
      if (!this.logs || !this.logs.raw_log_records) return 0
      if (type === 'message') return this.logs.raw_log_records.filter(r => this.isArchivedMessage(r)).length
      if (type === 'tool') return this.logs.raw_log_records.filter(r => !this.isArchivedMessage(r)).length
      return 0
    },
    exportForensicJSON() {
      if (!this.logs) return
      
      const dataStr = JSON.stringify(this.logs, null, 2)
      const dataBlob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(dataBlob)
      const link = document.createElement('a')
      link.href = url
      link.download = `forensic-audit-${this.chatId}-${new Date().toISOString().split('T')[0]}.json`
      link.click()
      URL.revokeObjectURL(url)
    }
  },
  mounted() {
    this.loadLogs()
  }
}
</script>

<style scoped>
.stats {
  display: flex;
  flex-direction: column;
  padding: 0.75rem;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat-title {
  font-size: 0.75rem;
  opacity: 0.6;
  font-weight: 500;
}

.stat-value {
  font-weight: bold;
  line-height: 1;
}

.stat-desc {
  display: flex;
  gap: 0.25rem;
  margin-top: 0.25rem;
}

.tabs {
  border-bottom: 2px solid hsl(var(--b2));
}

.tabs .tab {
  border: none;
  padding: 0.75rem 1rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.tabs .tab:hover {
  background-color: hsl(var(--b2));
}

.tabs .tab-active {
  border-bottom: 3px solid hsl(var(--p));
  color: hsl(var(--p));
}

.collapse-title {
  background: hsl(var(--b3));
}

.collapse-title:hover {
  background: hsl(var(--b2));
}
</style>