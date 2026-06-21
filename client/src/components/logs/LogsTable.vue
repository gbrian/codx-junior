<script setup>
</script>

<template>
  <div class="card bg-base-100 shadow">
    <div class="card-body p-4">
      <!-- Header -->
      <div class="flex items-center justify-between mb-3">
        <h2 class="card-title text-base flex items-center gap-2">
          <i class="fa-solid fa-table-list text-primary"></i>
          Log Entries
          <span class="badge badge-sm badge-ghost">{{ total }}</span>
        </h2>
        <div class="flex items-center gap-2">
          <label class="flex items-center gap-1 cursor-pointer">
            <input type="checkbox" v-model="groupByRequest" class="toggle toggle-xs toggle-primary" />
            <span class="text-xs text-base-content/60">Group pairs</span>
          </label>
          <select v-model="localPageSize" class="select select-bordered select-xs w-20" @change="onPageSizeChange">
            <option :value="25">25</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
          <span class="text-xs text-base-content/50">per page</span>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="!loading && logs.length === 0" class="flex flex-col items-center py-12 text-base-content-ERROR-40">
        <i class="fa-solid fa-inbox text-6xl"></i>
        <p class="mt-3 text-sm">No log entries found</p>
        <p class="text-xs mt-1">Try adjusting your filters</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="table table-sm w-full">
          <thead>
            <tr class="text-xs">
              <th>Timestamp</th>
              <th>Dir</th>
              <th>User</th>
              <th>Project</th>
              <th>Model</th>
              <th>Provider</th>
              <th>Request ID</th>
              <th>Session</th>
              <th>Tags</th>
              <th class="text-right">Duration</th>
              <th>Preview</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <!-- Loading row -->
            <tr v-if="loading">
              <td colspan="12" class="text-center py-8">
                <span class="loading loading-spinner loading-md text-primary"></span>
              </td>
            </tr>

            <template v-for="row in displayedRows" :key="row.key">
              <!-- Main row — highlighted red if any error present -->
              <tr
                class="hover cursor-pointer text-sm"
                :class="[
                  row.isPaired && row.expanded ? 'bg-base-200/50' : '',
                  rowHasError(row) ? 'bg-error/10 hover:bg-error/20' : ''
                ]"
                @click="$emit('select', row.log)"
              >
                <td class="font-mono text-xs text-base-content/60 whitespace-nowrap">
                  {{ formatTs(row.log.timestamp) }}
                </td>

                <!-- Direction badge -->
                <td>
                  <div class="flex items-center gap-1">
                    <span
                      class="badge badge-xs"
                      :class="row.log.direction === 'request' ? 'badge-success' : row.log.direction === 'response' ? 'badge-warning' : 'badge-ghost'"
                    >
                      <i
                        class="text-xs mr-0.5"
                        :class="row.log.direction === 'request' ? 'fa-solid fa-arrow-up' : 'fa-solid fa-arrow-down'"
                      ></i>
                      {{ row.log.direction || '?' }}
                    </span>
                    <!-- Error icon with tooltip for primary row error -->
                    <div v-if="row.log.error_type" class="tooltip tooltip-right" :data-tip="`${row.log.error_type}: ${row.log.error_message}`">
                      <i class="fa-solid fa-circle-exclamation text-error text-xs animate-pulse"></i>
                    </div>
                    <!-- Error icon for sibling (paired) error -->
                    <div v-else-if="row.sibling && row.sibling.error_type" class="tooltip tooltip-right" :data-tip="`${row.sibling.error_type}: ${row.sibling.error_message}`">
                      <i class="fa-solid fa-circle-exclamation text-error text-xs animate-pulse"></i>
                    </div>
                  </div>
                </td>

                <!-- User -->
                <td>
                  <div class="flex items-center gap-1">
                    <div class="avatar placeholder">
                      <div class="bg-neutral text-neutral-content rounded-full w-5">
                        <span class="text-xs">{{ (row.log.username || '?').charAt(0).toUpperCase() }}</span>
                      </div>
                    </div>
                    <span class="text-xs truncate max-w-20" :title="row.log.username">{{ row.log.username }}</span>
                  </div>
                </td>

                <td class="text-xs text-base-content/70 truncate max-w-24" :title="row.log.project">
                  {{ row.log.project || '—' }}
                </td>

                <td>
                  <span class="badge badge-xs badge-primary truncate max-w-28" :title="row.log.model">
                    {{ row.log.model || '—' }}
                  </span>
                </td>

                <td>
                  <span class="badge badge-xs badge-secondary">{{ row.log.provider || '—' }}</span>
                </td>

                <!-- Request ID with pair indicator -->
                <td class="font-mono text-xs">
                  <div class="flex items-center gap-1">
                    <span
                      class="truncate max-w-20 text-base-content/50"
                      :title="row.log.request_id"
                    >{{ row.log.request_id ? row.log.request_id.slice(0, 8) + '…' : '—' }}</span>
                    <button
                      v-if="row.isPaired && groupByRequest"
                      class="btn btn-xs btn-ghost btn-circle"
                      :title="row.expanded ? 'Collapse pair' : 'Expand paired response'"
                      @click.stop="togglePair(row.log.request_id)"
                    >
                      <i class="fa-solid text-info text-xs" :class="row.expanded ? 'fa-chevron-up' : 'fa-link'"></i>
                    </button>
                    <button
                      v-if="row.log.parent_request_id"
                      class="btn btn-xs btn-ghost btn-circle"
                      title="Has parent request — click to navigate"
                      @click.stop="$emit('navigate-request', row.log.parent_request_id)"
                    >
                      <i class="fa-solid fa-turn-up text-warning text-xs"></i>
                    </button>
                  </div>
                </td>

                <td class="font-mono text-xs text-base-content/50" :title="row.log.session_id">
                  {{ row.log.session_id ? row.log.session_id.slice(0, 8) + '…' : '—' }}
                </td>

                <td class="text-xs text-base-content/50 truncate max-w-20" :title="row.log.tags">
                  {{ row.log.tags || '—' }}
                </td>

                <td class="text-right text-xs font-mono text-base-content/60">
                  {{ row.log.duration_seconds != null ? row.log.duration_seconds.toFixed(2) + 's' : '—' }}
                </td>

                <!-- Preview + inline error message if present -->
                <td class="text-xs max-w-40">
                  <div v-if="rowHasError(row)" class="flex flex-col gap-0.5">
                    <span class="text-error font-semibold truncate" :title="errorSummary(row)">
                      <i class="fa-solid fa-triangle-exclamation text-xs mr-0.5"></i>{{ errorSummary(row) }}
                    </span>
                  </div>
                  <span v-else class="text-base-content-ERROR-40 truncate block" :title="row.log.payload_preview">
                    {{ row.log.payload_preview || '—' }}
                  </span>
                </td>

                <td>
                  <button class="btn btn-xs btn-ghost" @click.stop="$emit('select', row.log)">
                    <i class="fa-solid fa-eye text-xs"></i>
                  </button>
                </td>
              </tr>

              <!-- Inline paired sibling row -->
              <tr
                v-if="row.isPaired && row.expanded && groupByRequest && row.sibling"
                :key="row.key + '_sibling'"
                class="border-l-4 cursor-pointer text-sm"
                :class="row.sibling.error_type ? 'bg-error/10 hover:bg-error/20 border-error/50' : 'bg-info/5 border-info/40 hover:bg-info/10'"
                @click="$emit('select', row.sibling)"
              >
                <td class="font-mono text-xs text-base-content-ERROR-40 whitespace-nowrap pl-6">
                  ↳ {{ formatTs(row.sibling.timestamp) }}
                </td>
                <td>
                  <div class="flex items-center gap-1">
                    <span
                      class="badge badge-xs"
                      :class="row.sibling.direction === 'request' ? 'badge-success' : 'badge-warning'"
                    >
                      <i class="text-xs mr-0.5" :class="row.sibling.direction === 'request' ? 'fa-solid fa-arrow-up' : 'fa-solid fa-arrow-down'"></i>
                      {{ row.sibling.direction }}
                    </span>
                    <!-- Sibling error icon tooltip -->
                    <div v-if="row.sibling.error_type" class="tooltip tooltip-right" :data-tip="`${row.sibling.error_type}: ${row.sibling.error_message}`">
                      <i class="fa-solid fa-circle-exclamation text-error text-xs animate-pulse"></i>
                    </div>
                  </div>
                </td>
                <td colspan="7" class="text-xs truncate">
                  <span v-if="row.sibling.error_type" class="text-error font-semibold">
                    <i class="fa-solid fa-triangle-exclamation text-xs mr-0.5"></i>
                    {{ row.sibling.error_type }}: {{ row.sibling.error_message }}
                  </span>
                  <span v-else class="text-base-content/50">{{ row.sibling.payload_preview || '—' }}</span>
                </td>
                <td class="text-right text-xs font-mono text-base-content/60">
                  {{ row.sibling.duration_seconds != null ? row.sibling.duration_seconds.toFixed(2) + 's' : '—' }}
                </td>
                <td></td>
                <td>
                  <button class="btn btn-xs btn-ghost" @click.stop="$emit('select', row.sibling)">
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
          Page {{ page }} of {{ totalPages }} — {{ total }} entries
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
  emits: ['select', 'page', 'page-size', 'navigate-request'],
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
      groupByRequest: true,
      expandedPairs: {}
    }
  },
  computed: {
    totalPages() { return Math.ceil(this.total / this.localPageSize) || 1 },
    visiblePages() {
      const total = this.totalPages, cur = this.page, delta = 3, pages = []
      for (let i = Math.max(1, cur - delta); i <= Math.min(total, cur + delta); i++) pages.push(i)
      return pages
    },

    pairMap() {
      const map = {}
      for (const log of this.logs) {
        if (!log.request_id) continue
        if (!map[log.request_id]) map[log.request_id] = []
        map[log.request_id].push(log)
      }
      return map
    },

    displayedRows() {
      if (!this.groupByRequest) {
        return this.logs.map(log => ({
          key: log.log_id,
          log,
          isPaired: false,
          expanded: false,
          sibling: null
        }))
      }

      const seen = new Set()
      const rows = []

      for (const log of this.logs) {
        const rid = log.request_id
        if (!rid) {
          rows.push({ key: log.log_id, log, isPaired: false, expanded: false, sibling: null })
          continue
        }
        if (seen.has(log.log_id)) continue

        const siblings = this.pairMap[rid] || []
        const sibling = siblings.find(s => s.log_id !== log.log_id) || null

        seen.add(log.log_id)
        if (sibling) seen.add(sibling.log_id)

        const primary = log.direction === 'request' || !sibling ? log : (sibling.direction === 'request' ? sibling : log)
        const sec = sibling?.log_id === primary.log_id ? log : sibling

        rows.push({
          key: primary.log_id,
          log: primary,
          isPaired: !!sec,
          expanded: !!this.expandedPairs[rid],
          sibling: sec
        })
      }

      return rows
    }
  },
  methods: {
    formatTs(ts) {
      if (!ts) return '—'
      try {
        return new Date(ts).toLocaleString('en-US', {
          month: '2-digit', day: '2-digit',
          hour: '2-digit', minute: '2-digit', second: '2-digit'
        })
      } catch { return ts }
    },
    onPageSizeChange() { this.$emit('page-size', this.localPageSize) },
    togglePair(requestId) {
      this.expandedPairs = {
        ...this.expandedPairs,
        [requestId]: !this.expandedPairs[requestId]
      }
    },
    // True if primary log or its sibling has an error
    rowHasError(row) {
      return !!(row.log.error_type || (row.sibling && row.sibling.error_type))
    },
    // Short error summary for preview cell — prefer response error over request
    errorSummary(row) {
      const err = (row.sibling?.error_type ? row.sibling : null) || (row.log.error_type ? row.log : null)
      if (!err) return ''
      return `${err.error_type}: ${err.error_message}`
    }
  }
}
</script>