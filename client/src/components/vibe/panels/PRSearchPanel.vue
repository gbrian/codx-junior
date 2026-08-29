<script setup>
</script>

<template>
  <div class="flex flex-col h-full overflow-hidden bg-base-100">
    <!-- Search header -->
    <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 shrink-0 border-b border-base-content/10">
      <i class="fa-solid fa-magnifying-glass text-info text-sm"></i>
      <span class="text-sm font-bold truncate grow">Search in Changes</span>
      <button class="btn btn-xs btn-ghost" @click="$emit('close')" title="Close">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>

    <!-- Search input -->
    <div class="px-2 py-2 border-b border-base-content/10 bg-base-200/30 shrink-0">
      <div class="flex items-center gap-2">
        <div class="relative grow">
          <i class="fa-solid fa-magnifying-glass absolute left-2 top-1/2 -translate-y-1/2 text-[11px] text-base-content/40"></i>
          <input
            type="text"
            v-model="query"
            placeholder="Search in PR files..."
            class="input input-sm input-bordered w-full pl-7 pr-8"
            @keydown.enter="runSearch"
            @keydown.escape="cancelSearch"
            ref="searchInput"
          />
          <button
            v-if="searching"
            class="absolute right-2 top-1/2 -translate-y-1/2 btn btn-xs btn-ghost h-5 w-5 p-0 text-error"
            @click="cancelSearch"
            title="Cancel search"
          >
            <i class="fa-solid fa-stop text-[9px]"></i>
          </button>
        </div>
        <button
          class="btn btn-sm shrink-0"
          :class="searching ? 'btn-error' : 'btn-primary'"
          @click="searching ? cancelSearch() : runSearch()"
          :disabled="!query.trim() && !searching"
        >
          <i :class="searching ? 'fa-solid fa-stop' : 'fa-solid fa-search'"></i>
        </button>
      </div>

      <!-- Options -->
      <div class="flex items-center flex-wrap gap-x-3 gap-y-1 mt-2 text-xs">
        <label class="flex items-center gap-1 cursor-pointer">
          <input type="checkbox" v-model="caseSensitive" class="checkbox checkbox-xs" />
          <span>Case sensitive</span>
        </label>
        <label class="flex items-center gap-1 cursor-pointer">
          <input type="checkbox" v-model="useRegex" class="checkbox checkbox-xs" />
          <span>Regex</span>
        </label>
        <label class="flex items-center gap-1 cursor-pointer">
          <input type="checkbox" v-model="changedLinesOnly" class="checkbox checkbox-xs" />
          <span>Changed lines only</span>
        </label>
      </div>

      <!-- File filter -->
      <div v-if="files && files.length" class="flex items-center gap-2 mt-2">
        <div class="relative grow">
          <i class="fa-solid fa-filter absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-base-content/40"></i>
          <input
            type="text"
            v-model="fileFilter"
            placeholder="Filter files (e.g. *.vue)..."
            class="input input-xs input-bordered w-full pl-6"
            :class="{ 'input-warning': isFileFilterActive }"
          />
        </div>
        <span class="text-[10px] shrink-0" :class="isFileFilterActive ? 'text-warning font-semibold' : 'text-base-content/40'">
          {{ filteredFiles.length }}/{{ files.length }}
        </span>
        <button
          v-if="isFileFilterActive"
          class="btn btn-xs btn-ghost text-warning shrink-0"
          @click="fileFilter = ''"
          title="Clear file filter"
        >
          <i class="fa-solid fa-xmark text-[9px]"></i>
        </button>
      </div>

      <!-- Scoped search notice -->
      <div
        v-if="isFileFilterActive"
        class="flex items-center gap-1 mt-1.5 text-[10px] text-warning/80 bg-warning/10 rounded px-2 py-1"
      >
        <i class="fa-solid fa-filter text-[9px]"></i>
        <span>Search scoped to <strong>{{ filteredFiles.length }}</strong> filtered file{{ filteredFiles.length !== 1 ? 's' : '' }}</span>
      </div>
    </div>

    <!-- Search progress -->
    <div v-if="searching" class="flex items-center gap-2 px-2 py-1.5 bg-info/10 border-b border-info/20 shrink-0">
      <span class="loading loading-spinner loading-xs text-info"></span>
      <span class="text-xs text-info">Searching...</span>
      <button class="btn btn-xs btn-ghost text-error ml-auto" @click="cancelSearch">
        <i class="fa-solid fa-stop text-[9px]"></i> Cancel
      </button>
    </div>

    <!-- Results summary -->
    <div v-else-if="hasSearched" class="flex items-center gap-2 px-2 py-1 bg-base-200/20 border-b border-base-content/10 shrink-0 text-[11px] text-base-content/60">
      <template v-if="searchError">
        <i class="fa-solid fa-triangle-exclamation text-warning"></i>
        <span class="text-warning">{{ searchError }}</span>
      </template>
      <template v-else-if="wasCancelled">
        <i class="fa-solid fa-ban text-warning"></i>
        <span>Search cancelled — {{ totalMatches }} match{{ totalMatches !== 1 ? 'es' : '' }} in {{ results.length }} file{{ results.length !== 1 ? 's' : '' }} (partial)</span>
      </template>
      <template v-else-if="totalMatches > 0">
        <i class="fa-solid fa-circle-check text-success"></i>
        <span>{{ totalMatches }} match{{ totalMatches !== 1 ? 'es' : '' }} in {{ results.length }} file{{ results.length !== 1 ? 's' : '' }}</span>
        <span v-if="isFileFilterActive" class="text-warning ml-1">(filtered)</span>
      </template>
      <template v-else>
        <i class="fa-solid fa-circle-xmark text-error"></i>
        <span>No matches found for "{{ lastQuery }}"</span>
        <span v-if="isFileFilterActive" class="text-warning ml-1">in filtered files</span>
      </template>

      <!-- Copy results button -->
      <button
        v-if="totalMatches > 0"
        class="btn btn-xs btn-ghost ml-auto gap-1"
        :class="copied ? 'text-success' : 'text-base-content/60'"
        @click="copyResultsToClipboard"
        title="Copy results to clipboard"
      >
        <i :class="copied ? 'fa-solid fa-check' : 'fa-regular fa-copy'" class="text-[9px]"></i>
        <span class="text-[9px]">{{ copied ? 'Copied!' : 'Copy' }}</span>
      </button>
      <button v-else class="btn btn-xs btn-ghost ml-auto" @click="clearResults" title="Clear results">
        <i class="fa-solid fa-broom text-[9px]"></i>
      </button>
    </div>

    <!-- No files state -->
    <div v-if="!files || !files.length" class="grow flex flex-col items-center justify-center gap-2 text-base-content/40">
      <i class="fa-solid fa-file-slash text-3xl"></i>
      <span class="text-sm">No PR files available</span>
    </div>

    <!-- Results list -->
    <div v-else class="grow overflow-y-auto">
      <!-- Not yet searched -->
      <div v-if="!hasSearched && !searching" class="flex flex-col items-center justify-center h-full gap-2 text-base-content/30">
        <i class="fa-solid fa-magnifying-glass text-3xl"></i>
        <span class="text-sm">Enter a query and press search</span>
        <span class="text-xs opacity-60">
          Searches across <strong>{{ filteredFiles.length }}</strong>
          {{ isFileFilterActive ? 'filtered' : '' }} PR file{{ filteredFiles.length !== 1 ? 's' : '' }}
          <template v-if="isFileFilterActive"> ({{ files.length }} total)</template>
        </span>
      </div>

      <!-- Empty results -->
      <div v-else-if="hasSearched && !searching && !results.length && !wasCancelled" class="flex flex-col items-center justify-center h-full gap-2 text-base-content/30">
        <i class="fa-solid fa-file-circle-question text-3xl"></i>
        <span class="text-sm">No results for "{{ lastQuery }}"</span>
        <span v-if="isFileFilterActive" class="text-xs text-warning/70">
          Searched in {{ filteredFiles.length }} filtered file{{ filteredFiles.length !== 1 ? 's' : '' }}.
          <button class="btn btn-xs btn-ghost text-warning" @click="fileFilter = ''">Clear filter</button>
        </span>
      </div>

      <!-- File results -->
      <div v-else-if="results.length" class="divide-y divide-base-content/10">
        <div v-for="fileResult in results" :key="fileResult.fileFullName" class="file-result">
          <!-- File header -->
          <div
            class="flex items-center gap-2 px-2 py-1.5 bg-base-200/50 cursor-pointer hover:bg-base-200/80 sticky top-0 z-10"
            @click="toggleFileExpand(fileResult.fileFullName)"
          >
            <i
              :class="fileExpanded[fileResult.fileFullName] ? 'fa-solid fa-chevron-down' : 'fa-solid fa-chevron-right'"
              class="text-[10px] text-base-content/40 shrink-0"
            ></i>
            <i class="fa-solid fa-file text-[11px] shrink-0" :class="getFileIconClass(fileResult)"></i>
            <span class="font-mono text-xs truncate grow" :title="fileResult.fileFullName">{{ fileResult.fileFullName }}</span>
            <span class="badge badge-xs badge-info shrink-0">{{ fileResult.matches.length }}</span>
            <button
              class="btn btn-xs btn-ghost h-5 w-5 p-0 shrink-0"
              @click.stop="copyFileResultsToClipboard(fileResult)"
              title="Copy file results"
            >
              <i class="fa-regular fa-copy text-[9px]"></i>
            </button>
            <button
              class="btn btn-xs btn-ghost h-5 w-5 p-0 shrink-0"
              @click.stop="$emit('select-file', fileResult)"
              title="Go to file"
            >
              <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
            </button>
          </div>

          <!-- Match lines -->
          <div v-if="fileExpanded[fileResult.fileFullName]" class="match-lines bg-base-100">
            <div
              v-for="(match, idx) in fileResult.matches"
              :key="idx"
              class="flex items-start gap-2 px-3 py-1 hover:bg-base-200/40 cursor-pointer group border-b border-base-content/5"
              @click="$emit('jump-to-match', { file: fileResult, match })"
            >
              <!-- Line number -->
              <span class="text-[10px] font-mono text-base-content/40 shrink-0 w-10 text-right pt-0.5 select-none">
                {{ match.lineNumber }}
              </span>
              <!-- Diff indicator -->
              <span
                class="shrink-0 text-[10px] font-mono w-4 text-center pt-0.5 select-none"
                :class="match.type === 'add' ? 'text-success' : match.type === 'del' ? 'text-error' : 'text-base-content/30'"
              >
                {{ match.type === 'add' ? '+' : match.type === 'del' ? '-' : ' ' }}
              </span>
              <!-- Match count badge -->
              <span
                v-if="match.matchCount > 1"
                class="badge badge-xs badge-warning shrink-0 mt-0.5"
                :title="`${match.matchCount} matches on this line`"
              >{{ match.matchCount }}</span>
              <div class="grow min-w-0">
                <div
                  class="font-mono text-[11px] whitespace-pre-wrap break-all"
                  :class="getMatchLineClass(match)"
                  v-html="highlightMatch(match.content, lastQuery)"
                ></div>
              </div>
              <i class="fa-solid fa-arrow-right text-[9px] text-info opacity-0 group-hover:opacity-100 shrink-0 mt-0.5"></i>
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
    files: { type: Array, default: () => [] },
    project: { type: Object, default: null }
  },
  emits: ['close', 'select-file', 'jump-to-match'],
  data() {
    return {
      query: '',
      lastQuery: '',
      caseSensitive: false,
      useRegex: false,
      changedLinesOnly: false,
      fileFilter: '',
      results: [],
      hasSearched: false,
      searching: false,
      wasCancelled: false,
      searchError: null,
      fileExpanded: {},
      searchVersion: 0,
      copied: false,
      copiedTimeout: null
    }
  },
  mounted() {
    this.$nextTick(() => this.$refs.searchInput?.focus())
  },
  computed: {
    totalMatches() {
      return this.results.reduce((sum, r) => sum + r.matches.length, 0)
    },
    isFileFilterActive() {
      return !!this.fileFilter.trim()
    },
    filteredFiles() {
      if (!this.files) return []
      if (!this.isFileFilterActive) return this.files
      const pattern = this.fileFilter.trim().toLowerCase().replace(/\*/g, '.*')
      try {
        const regex = new RegExp(pattern)
        return this.files.filter(f => regex.test(f.fileFullName.toLowerCase()))
      } catch {
        return this.files.filter(f => f.fileFullName.toLowerCase().includes(this.fileFilter.toLowerCase()))
      }
    }
  },
  methods: {
    cancelSearch() {
      if (this.searching) {
        this.searchVersion++
        this.searching = false
        this.wasCancelled = true
      }
    },

    clearResults() {
      this.results = []
      this.hasSearched = false
      this.wasCancelled = false
      this.searchError = null
      this.lastQuery = ''
    },

    async runSearch() {
      const q = this.query.trim()
      if (!q || this.searching) return

      this.searchVersion++
      const currentVersion = this.searchVersion

      this.lastQuery = q
      this.results = []
      this.hasSearched = false
      this.searching = true
      this.wasCancelled = false
      this.searchError = null
      this.fileExpanded = {}

      try {
        const apiResults = await this.searchViaApi(q, currentVersion)
        if (currentVersion !== this.searchVersion) return

        if (apiResults !== null) {
          this.results = apiResults
        } else {
          await this.searchPerFile(q, currentVersion)
        }
      } catch (err) {
        if (currentVersion === this.searchVersion) {
          this.searchError = err.message || 'Search failed'
        }
      } finally {
        if (currentVersion === this.searchVersion) {
          this.searching = false
          this.hasSearched = true
        }
      }
    },

    async searchViaApi(query, version) {
      const api = this.project?.$api
      if (!api?.files?.searchContent) return null

      try {
        const response = await api.files.searchContent({
          query,
          caseSensitive: this.caseSensitive,
          useRegex: this.useRegex,
          rawSearch: false,
          pageSize: 500
        })
        if (version !== this.searchVersion) return null
        return this.mapBulkApiResponse(response)
      } catch {
        return null
      }
    },

    mapBulkApiResponse(response) {
      if (!response?.results?.length) return []

      return response.results
        .map(fileResult => {
          const prFile = this.filteredFiles.find(f =>
            f.fileFullName === fileResult.file_path ||
            f.fileFullName.endsWith(fileResult.rel_path) ||
            fileResult.file_path.endsWith(f.fileName)
          ) || {}

          const matches = (fileResult.matches || []).map(m => {
            const lineType = this.getDiffLineType(prFile, m.line_number)
            return {
              lineNumber: m.line_number,
              content: m.line_content,
              matchCount: m.match_count || 1,
              type: lineType
            }
          }).filter(m => {
            if (this.changedLinesOnly && m.type === 'context') return false
            if (this.changedLinesOnly && !m.type) return false
            return true
          })

          if (!matches.length) return null

          return {
            fileFullName: fileResult.file_path,
            fileName: fileResult.rel_path,
            isNewFile: prFile.isNewFile || false,
            isDeleted: prFile.isDeleted || false,
            isChanged: prFile.isChanged !== undefined ? prFile.isChanged : true,
            matches
          }
        })
        .filter(Boolean)
        .map(r => {
          this.fileExpanded[r.fileFullName] = true
          return r
        })
    },

    getDiffLineType(prFile, lineNumber) {
      if (!prFile?.diffLines) return null
      const line = prFile.diffLines.find(l =>
        l.newLineNumber === lineNumber || l.oldLineNumber === lineNumber
      )
      return line?.type || null
    },

    async searchPerFile(query, currentVersion) {
      const filesToSearch = this.filteredFiles
      for (let i = 0; i < filesToSearch.length; i++) {
        if (currentVersion !== this.searchVersion) {
          this.wasCancelled = true
          break
        }
        const file = filesToSearch[i]
        const matches = this.searchInDiffLines(file, query)
        if (matches.length) {
          this.results.push({ ...file, matches })
          this.fileExpanded[file.fileFullName] = true
        }
      }
    },

    searchInDiffLines(file, query) {
      const lines = file.diffLines || []
      let regex
      try {
        const flags = this.caseSensitive ? 'g' : 'gi'
        regex = this.useRegex
          ? new RegExp(query, flags)
          : new RegExp(this.escapeRegex(query), flags)
      } catch {
        return []
      }
      return lines
        .filter(line => {
          if (line.type === 'hunk') return false
          if (this.changedLinesOnly && line.isContext) return false
          regex.lastIndex = 0
          return regex.test(line.content)
        })
        .map(line => ({
          ...line,
          lineNumber: line.newLineNumber ?? line.oldLineNumber,
          content: line.content,
          matchCount: 1
        }))
    },

    /** Build plain-text representation of all results for clipboard */
    buildResultsText(resultsToFormat) {
      const lines = [`Search results for: "${this.lastQuery}"`, '']
      resultsToFormat.forEach(fileResult => {
        lines.push(`## ${fileResult.fileFullName} (${fileResult.matches.length} match${fileResult.matches.length !== 1 ? 'es' : ''})`)
        fileResult.matches.forEach(m => {
          const indicator = m.type === 'add' ? '+' : m.type === 'del' ? '-' : ' '
          lines.push(`  ${String(m.lineNumber).padStart(5)} ${indicator} ${m.content}`)
        })
        lines.push('')
      })
      return lines.join('\n')
    },

    /** Copy all search results to clipboard */
    async copyResultsToClipboard() {
      const text = this.buildResultsText(this.results)
      console.log("Copy results", text)
      await this.$storex.ui.copyTextToClipboard(text)
      this.showCopiedFeedback()
    },

    /** Copy a single file's results to clipboard */
    async copyFileResultsToClipboard(fileResult) {
      const text = this.buildResultsText([fileResult])
      console.log("Copy results", text)
      await this.$storex.ui.copyTextToClipboard(text)
      this.showCopiedFeedback()
    },

    showCopiedFeedback() {
      this.copied = true
      clearTimeout(this.copiedTimeout)
      this.copiedTimeout = setTimeout(() => { this.copied = false }, 2000)
    },

    toggleFileExpand(fileFullName) {
      this.fileExpanded[fileFullName] = !this.fileExpanded[fileFullName]
    },

    highlightMatch(content, query) {
      if (!query) return this.escapeHtml(content)
      try {
        const escaped = this.escapeHtml(content)
        const flags = this.caseSensitive ? 'g' : 'gi'
        const pattern = this.useRegex ? query : this.escapeRegex(query)
        const regex = new RegExp(this.escapeRegex(this.escapeHtml(pattern)), flags)
        return escaped.replace(
          regex,
          match => `<mark class="bg-warning/70 text-base-content rounded-sm px-0.5">${match}</mark>`
        )
      } catch {
        return this.escapeHtml(content)
      }
    },

    escapeHtml(str) {
      return String(str ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
    },

    escapeRegex(str) {
      return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    },

    getMatchLineClass(match) {
      if (match.type === 'add') return 'text-success/90'
      if (match.type === 'del') return 'text-error/90'
      return 'text-base-content/80'
    },

    getFileIconClass(file) {
      if (file.isNewFile) return 'text-success'
      if (file.isDeleted) return 'text-error'
      return 'text-warning'
    }
  }
}
</script>