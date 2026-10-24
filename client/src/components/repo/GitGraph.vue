<script setup>
import moment from 'moment'
import {
  GRAPH_LANE_WIDTH,
  GRAPH_ROW_HEIGHT,
  buildGraphLayout,
  filterCommitsByRef,
  laneColor
} from '@/api/models/gitGraph'
</script>

<template>
  <div class="flex flex-col h-full min-h-0 w-full overflow-hidden bg-base-100">
    <!-- ── Toolbar ──────────────────────────────────────────────────────── -->
    <div class="flex items-center gap-2 px-2 py-1.5 border-b border-base-content/10 shrink-0 flex-wrap">
      <i class="fa-solid fa-diagram-project text-warning text-xs"></i>
      <span class="text-xs font-bold uppercase tracking-wide opacity-50">Graph</span>

      <select
        v-model="branchFilter"
        class="select select-xs select-bordered max-w-[190px]"
        title="Show all branches or graph a single one"
        aria-label="Graph branch"
      >
        <option value="">Show All</option>
        <option v-for="branch in branchOptions" :key="branch" :value="branch">{{ branch }}</option>
      </select>

      <label class="flex items-center gap-1 text-[11px] cursor-pointer select-none" title="Show or hide remote branches">
        <input v-model="showRemote" type="checkbox" class="checkbox checkbox-xs" />
        Show remote branches
      </label>

      <input
        v-model="search"
        type="text"
        class="input input-xs input-bordered w-44"
        placeholder="Filter commits..."
        aria-label="Filter commits"
      />

      <div class="grow"></div>

      <span class="badge badge-xs badge-ghost gap-1" title="Commits loaded in the graph">
        <i class="fa-solid fa-code-commit text-[9px]"></i> {{ rawCommits.length }}
      </span>

      <button class="btn btn-xs btn-ghost" :disabled="loading" title="Reload graph" aria-label="Reload graph" @click="load">
        <i class="fa-solid fa-rotate-right text-[10px]" :class="{ 'animate-spin': loading }"></i>
      </button>
    </div>

    <!-- ── Feedback ─────────────────────────────────────────────────────── -->
    <div v-if="error" class="alert alert-error rounded-none py-1 px-2 text-[11px] flex items-center gap-2 shrink-0">
      <i class="fa-solid fa-triangle-exclamation"></i>
      <span class="grow break-words">{{ error }}</span>
      <button class="btn btn-ghost btn-xs" aria-label="Dismiss error" @click="error = null">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>

    <!-- ── Column headers ───────────────────────────────────────────────── -->
    <div class="flex items-center gap-2 px-2 py-1 border-b border-base-content/10 bg-base-200/50 text-[10px] font-bold uppercase tracking-wide opacity-60 shrink-0">
      <span class="shrink-0" :style="{ width: graphWidth + 'px' }">Graph</span>
      <span class="grow">Description</span>
      <span class="w-32 shrink-0">Date</span>
      <span class="w-24 shrink-0">Author</span>
      <span class="w-16 shrink-0">Commit</span>
    </div>

    <!-- ── Rows ─────────────────────────────────────────────────────────── -->
    <div class="grow min-h-0 overflow-auto">
      <div v-if="loading && !rows.length" class="p-3 text-xs opacity-50 flex items-center gap-2">
        <i class="fa-solid fa-spinner animate-spin"></i> Loading graph...
      </div>
      <div v-else-if="!rows.length" class="p-3 text-xs opacity-40 flex items-center gap-2">
        <i class="fa-solid fa-circle-info"></i> No commits to display
      </div>

      <button
        v-for="row in rows"
        :key="row.commit.hash"
        type="button"
        class="w-full flex items-center gap-2 px-2 text-left transition-colors"
        :class="[
          selectedHash === row.commit.hash ? 'bg-primary/15' : 'hover:bg-base-200/60',
          isDimmed(row) ? 'opacity-30' : ''
        ]"
        :style="{ height: rowHeight + 'px' }"
        :title="`${row.commit.subject} — ${row.commit.author.name} · ${row.commit.short}`"
        @click="selectRow(row)"
      >
        <!-- Lanes -->
        <div class="shrink-0 relative h-full" :style="{ width: graphWidth + 'px' }">
          <svg
            :width="graphWidth"
            :height="rowHeight"
            class="absolute inset-0 overflow-visible pointer-events-none"
            aria-hidden="true"
          >
            <path
              v-for="(edge, edgeIndex) in rowEdges(row)"
              :key="edgeIndex"
              :d="edge.d"
              :stroke="edge.color"
              stroke-width="2"
              fill="none"
              stroke-linecap="round"
            />
            <circle
              :cx="laneX(row.lane)"
              :cy="rowHeight / 2"
              :r="selectedHash === row.commit.hash ? 5 : 3.5"
              :fill="row.color"
              stroke="#111111"
              stroke-width="1.5"
            />
          </svg>
        </div>

        <!-- Description -->
        <div class="flex items-center gap-1.5 grow min-w-0">
          <span v-if="row.commit.isHead" class="badge badge-xs badge-success gap-1 shrink-0" title="Checked out branch">
            <i class="fa-solid fa-check text-[8px]"></i> HEAD
          </span>
          <span
            v-for="ref in visibleRefs(row.commit.refs)"
            :key="`${row.commit.hash}-${ref.name}`"
            class="badge badge-xs shrink-0 font-mono"
            :class="refClass(ref)"
            :title="`${ref.type} ref: ${ref.name}`"
          >
            <i class="fa-solid text-[8px]" :class="refIcon(ref)"></i> {{ ref.name }}
          </span>
          <span class="text-xs truncate" :title="row.commit.subject">{{ row.commit.subject }}</span>
        </div>

        <span class="w-32 shrink-0 text-[11px] opacity-60 truncate">{{ formatDate(row.commit.date) }}</span>
        <span class="w-24 shrink-0 text-[11px] opacity-60 truncate" :title="row.commit.author.email">
          {{ row.commit.author.name }}
        </span>
        <span class="w-16 shrink-0 font-mono text-[11px] opacity-50 truncate" :title="row.commit.hash">
          {{ row.commit.short }}
        </span>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'GitGraph',
  props: {
    // Project API instance (the graph is scoped by the project codx_path)
    api: { type: Object, required: true },
    // Branches offered by the branch filter
    branches: { type: Array, default: () => [] },
    currentBranch: { type: String, default: '' },
    defaultBranch: { type: String, default: '' },
    // Bumped by the parent view after a git operation to reload the graph
    refreshToken: { type: Number, default: 0 }
  },
  emits: ['select-commit'],
  data() {
    return {
      loading: false,
      error: null,
      // Normalized commits of the whole repository (before filtering)
      rawCommits: [],
      rows: [],
      laneCount: 1,
      branchFilter: '',
      showRemote: true,
      search: '',
      limit: 150,
      selectedHash: null,
      rowHeight: GRAPH_ROW_HEIGHT,
      laneSpacing: GRAPH_LANE_WIDTH
    }
  },
  computed: {
    graphWidth() {
      return Math.max(this.laneCount, 1) * this.laneSpacing + 12
    },
    branchOptions() {
      return this.branches
        .filter(branch => this.showRemote || !/^(origin|upstream)\//.test(branch))
        .sort((a, b) => (a > b ? 1 : -1))
    },
    searchTerm() {
      return this.search.trim().toLowerCase()
    }
  },
  watch: {
    api: {
      immediate: false,
      handler() {
        this.load()
      }
    },
    branchFilter() {
      this.applyFilter()
    },
    showRemote() {
      // A selected remote branch may disappear from the filter options
      if (this.branchFilter && !this.branchOptions.includes(this.branchFilter)) {
        this.branchFilter = ''
      }
      // Remote commits are only returned when requested
      this.load()
    },
    // Checkout, merge or rebase: the lanes and hashes change
    currentBranch() {
      this.load()
    },
    refreshToken() {
      this.load()
    }
  },
  created() {
    this.load()
  },
  methods: {
    // ── Loading ─────────────────────────────────────────────────────────
    async load() {
      if (!this.api?.repo?.graph) {
        this.error = 'Repository API not available'
        return
      }
      this.loading = true
      this.error = null
      try {
        const graph = await this.api.repo.graph({ limit: this.limit, includeRemote: this.showRemote })
        this.rawCommits = graph?.commits || []
        this.applyFilter()
      } catch (ex) {
        this.rawCommits = []
        this.rows = []
        this.laneCount = 1
        this.error = ex?.response?.data?.detail || ex?.message || String(ex)
      } finally {
        this.loading = false
      }
    },

    /** Re-lay out the rows for the current branch filter */
    applyFilter() {
      const commits = this.branchFilter
        ? filterCommitsByRef(this.rawCommits, this.branchFilter)
        : this.rawCommits
      const layout = buildGraphLayout(commits)
      this.rows = layout.rows
      this.laneCount = layout.laneCount
      const stillThere = commits.some(commit => commit.hash === this.selectedHash)
      if (!stillThere) this.selectedHash = null
    },

    // ── Geometry ────────────────────────────────────────────────────────
    laneX(lane) {
      return 8 + Math.max(Number(lane) || 0, 0) * this.laneSpacing
    },

    /**
     * Turn the row edges into SVG paths. A same-lane edge is a straight line,
     * a lane change becomes a smooth bezier so branches curve like in VSCode.
     */
    rowEdges(row) {
      const height = this.rowHeight
      return (row.edges || []).map(edge => {
        const x1 = this.laneX(edge.fromLane)
        const x2 = this.laneX(edge.toLane)
        const y1 = edge.fromY * height
        const y2 = edge.toY * height
        if (x1 === x2) {
          return { d: `M ${x1} ${y1} L ${x1} ${y2}`, color: edge.color }
        }
        const curve = (y2 - y1) * 0.5
        return {
          d: `M ${x1} ${y1} C ${x1} ${y1 + curve} ${x2} ${y2 - curve} ${x2} ${y2}`,
          color: edge.color
        }
      })
    },

    // ── Refs ────────────────────────────────────────────────────────────
    visibleRefs(refs) {
      return (refs || []).filter(ref => {
        if (ref.type === 'head') return true
        if (!this.showRemote) return ref.type !== 'remote'
        return true
      })
    },

    refClass(ref) {
      const styles = {
        local: 'badge-success',
        remote: 'badge-info badge-outline',
        tag: 'badge-warning badge-outline',
        head: 'badge-success'
      }
      return styles[ref.type] || 'badge-ghost'
    },

    refIcon(ref) {
      const icons = {
        local: 'fa-code-branch',
        remote: 'fa-cloud',
        tag: 'fa-tag',
        head: 'fa-check'
      }
      return icons[ref.type] || 'fa-code-branch'
    },

    // ── Row state ───────────────────────────────────────────────────────
    isDimmed(row) {
      if (!this.searchTerm) return false
      const { subject, short, hash, author } = row.commit
      return ![subject, short, hash, author?.name].some(value =>
        String(value || '').toLowerCase().includes(this.searchTerm)
      )
    },

    formatDate(date) {
      const value = moment(date)
      return value.isValid() ? value.format('DD MMM YYYY HH:mm') : (date || '')
    },

    selectRow(row) {
      this.selectedHash = row.commit.hash
      this.$emit('select-commit', row.commit)
    }
  }
}
</script>