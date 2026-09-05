<script setup>
import ProfileAvatar from '../profile/ProfileAvatar.vue'
</script>

<template>
  <div class="card bg-base-100 shadow">
    <div class="card-body p-4">
      <!-- Header -->
      <div class="flex items-center justify-between mb-3">
        <h2 class="card-title text-base flex items-center gap-2">
          <i class="fa-solid fa-comments text-primary"></i>
          Chat Sessions
          <span class="badge badge-sm badge-ghost">{{ total }}</span>
        </h2>
        <div class="flex items-center gap-2">
          <select v-model="localPageSize" class="select select-bordered select-xs w-20" @change="onPageSizeChange">
            <option :value="25">25</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
          <span class="text-xs text-base-content/50">per page</span>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="!loading && logs.length === 0" class="flex flex-col items-center py-12 text-base-content/40">
        <i class="fa-solid fa-inbox text-6xl"></i>
        <p class="mt-3 text-sm">No chat sessions found</p>
        <p class="text-xs mt-1">Try adjusting your filters</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="table table-sm w-full">
          <thead>
            <tr class="text-xs">
              <th>Date</th>
              <th>Chat Name</th>
              <th>User</th>
              <th>Project</th>
              <th>Model</th>
              <th>Provider</th>
              <th>Mode</th>
              <th>Profiles</th>
              <th>Tools</th>
              <th class="text-right">Duration</th>
              <th class="text-right">Tokens</th>
              <th class="text-right">LLM Calls</th>
              <th class="text-right">Cost</th>
              <th class="text-center">Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <!-- Loading row -->
            <tr v-if="loading">
              <td colspan="15" class="text-center py-8">
                <span class="loading loading-spinner loading-md text-primary"></span>
              </td>
            </tr>

            <template v-for="log in logs" :key="log.id">
              <tr
                class="hover cursor-pointer text-sm"
                :class="log.error ? 'bg-error/10 hover:bg-error/20' : log.cancelled ? 'bg-warning/10 hover:bg-warning/20' : ''"
                @click="$emit('select', log)"
              >
                <!-- Date -->
                <td class="font-mono text-xs text-base-content/60 whitespace-nowrap">
                  {{ formatDate(log.iso_date) }}
                </td>

                <!-- Chat Name / Title -->
                <td class="text-xs max-w-40">
                  <div class="flex items-center gap-2">
                    <span class="truncate" :title="log.chat_name">{{ log.chat_name || '—' }}</span>
                    <div v-if="log.error" class="tooltip tooltip-right" :data-tip="log.error">
                      <i class="fa-solid fa-circle-exclamation text-error text-xs animate-pulse"></i>
                    </div>
                  </div>
                </td>

                <!-- User -->
                <td>
                  <div class="flex items-center gap-1">
                    <div class="avatar placeholder">
                      <div class="bg-neutral text-neutral-content rounded-full w-5">
                        <span class="text-xs">{{ (log.username || '?').charAt(0).toUpperCase() }}</span>
                      </div>
                    </div>
                    <span class="text-xs truncate max-w-20" :title="log.username">{{ log.username }}</span>
                  </div>
                </td>

                <!-- Project -->
                <td class="text-xs text-base-content/70 truncate max-w-24" :title="log.project_name">
                  {{ log.project_name || '—' }}
                </td>

                <!-- Model -->
                <td>
                  <span class="badge badge-xs badge-primary truncate max-w-28" :title="log.llm_model">
                    {{ log.llm_model || '—' }}
                  </span>
                </td>

                <!-- Provider -->
                <td>
                  <span class="badge badge-xs badge-secondary">{{ log.provider || '—' }}</span>
                </td>

                <!-- Mode -->
                <td>
                  <span class="badge badge-xs" :class="log.mode === 'chat' ? 'badge-info' : 'badge-ghost'">
                    {{ log.mode || '—' }}
                  </span>
                </td>

                <!-- Profiles with Avatar Component -->
                <td>
                  <div class="flex -space-x-3">
                    <ProfileAvatar
                      :key="profile.name"
                      :profile="profile"
                      width="6",
                      v-for="profile in log.profiles"
                    />
                  </div>
                </td>

                <!-- Tools -->
                <td>
                  <div v-if="log.tool_calls > 0" class="badge badge-xs badge-warning">
                    <i class="fa-solid fa-wrench text-xs mr-1"></i>
                    {{ log.tool_calls }}
                  </div>
                  <span v-else class="text-xs text-base-content/40">—</span>
                </td>

                <!-- Duration -->
                <td class="text-right text-xs font-mono text-base-content/60">
                  {{ log.duration_seconds != null ? log.duration_seconds.toFixed(2) + 's' : '—' }}
                </td>

                <!-- Total Tokens -->
                <td class="text-right text-xs font-mono text-base-content/60">
                  <div class="flex flex-col items-end gap-0.5">
                    <span title="Total tokens">{{ formatNumber(log.total_tokens) }}</span>
                    <span class="text-xs text-base-content/40">
                      <span :title="'Input: ' + formatNumber(log.total_input_tokens)">{{ formatNumber(log.total_input_tokens) }}</span>
                      /
                      <span :title="'Output: ' + formatNumber(log.total_output_tokens)">{{ formatNumber(log.total_output_tokens) }}</span>
                    </span>
                  </div>
                </td>

                <!-- LLM Calls -->
                <td class="text-right text-xs font-mono text-base-content/60">
                  {{ log.llm_calls || 0 }}
                </td>

                <!-- Cost (CXJ Coins) -->
                <td class="text-right text-xs font-mono">
                  <span class="text-accent font-semibold">{{ log.total_cxjcoins ? log.total_cxjcoins.toFixed(4) : '0' }}</span>
                  <span class="text-base-content/40 text-xs">cx</span>
                </td>

                <!-- Status -->
                <td class="text-center text-xs">
                  <div class="flex items-center justify-center gap-1">
                    <span
                      v-if="log.cancelled"
                      class="badge badge-sm badge-warning"
                      title="Session cancelled"
                    >
                      <i class="fa-solid fa-ban text-xs"></i>
                    </span>
                    <span
                      v-else-if="log.error"
                      class="badge badge-sm badge-error"
                      title="Session error"
                    >
                      <i class="fa-solid fa-triangle-exclamation text-xs"></i>
                    </span>
                    <span
                      v-else
                      class="badge badge-sm badge-success"
                      title="Session completed"
                    >
                      <i class="fa-solid fa-check text-xs"></i>
                    </span>
                    <button
                      v-if="log.parent_chat_id"
                      class="btn btn-xs btn-ghost btn-circle ml-1"
                      title="Has parent session — click to navigate"
                      @click.stop="$emit('navigate-session', log.parent_chat_id)"
                    >
                      <i class="fa-solid fa-turn-up text-warning text-xs"></i>
                    </button>
                  </div>
                </td>

                <!-- Action -->
                <td>
                  <button class="btn btn-xs btn-ghost" @click.stop="$emit('select', log)">
                    <i class="fa-solid fa-eye text-xs"></i>
                  </button>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="flex items-center justify-between mt-4">
        <span class="text-xs text-base-content/50">
          Page {{ page }} of {{ totalPages }} — {{ total }} sessions
        </span>
        <div class="join">
          <button class="join-item btn btn-xs" :disabled="page <= 1" @click="$emit('page', page - 1)">
            <i class="fa-solid fa-chevron-left"></i>
          </button>
          <button
            v-for="p in visiblePages"
            :key="p"
            class="join-item btn btn-xs"
            :class="{ 'btn-active btn-primary': p === page }"
            @click="$emit('page', p)"
          >{{ p }}</button>
          <button class="join-item btn btn-xs" :disabled="!hasMore" @click="$emit('page', page + 1)">
            <i class="fa-solid fa-chevron-right"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LogsTable',
  emits: ['select', 'page', 'page-size', 'navigate-session'],
  props: {
    logs: { type: Array, default: () => [] },
    total: { type: Number, default: 0 },
    page: { type: Number, default: 1 },
    pageSize: { type: Number, default: 50 },
    hasMore: { type: Boolean, default: false },
    loading: { type: Boolean, default: false },
  },
  data() {
    return {
      localPageSize: this.pageSize,
    }
  },
  computed: {
    totalPages() { return Math.ceil(this.total / this.localPageSize) || 1 },
    visiblePages() {
      const total = this.totalPages, cur = this.page, delta = 3, pages = []
      for (let i = Math.max(1, cur - delta); i <= Math.min(total, cur + delta); i++) pages.push(i)
      return pages
    }
  },
  methods: {
    formatDate(isoDate) {
      if (!isoDate) return '—'
      try {
        return new Date(isoDate).toLocaleDateString('en-US', {
          month: '2-digit', day: '2-digit', year: '2-digit'
        })
      } catch { return isoDate }
    },
    formatNumber(num) {
      if (num == null) return '0'
      if (num < 1000) return num.toString()
      if (num < 1000000) return (num / 1000).toFixed(1) + 'k'
      return (num / 1000000).toFixed(1) + 'm'
    },
    onPageSizeChange() { this.$emit('page-size', this.localPageSize) }
  }
}
</script>