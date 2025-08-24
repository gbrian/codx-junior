<script setup>
import RequestMetrics from './metrics/RequestMetrics.vue'
</script>

<template>
  <div class="px-2 pt-4 gap-2 w-full max-w-full overflow-auto flex flex-col relative">
    <header class="flex flex-row justify-between items-center">
      <h1 class="text-xl font-semibold">Dashboard</h1>
      <div class="flex gap-2 items-center">
        <button class="btn btn-sm" @click="clearLogs">
          <i class="fa-solid fa-trash-can"></i>
        </button>
        <button class="btn btn-sm" @click="fetchLogs">
          <i class="fa-solid fa-rotate"></i>
        </button>
        <label class="flex items-center space-x-2">
          <input type="checkbox" @click="toggleAutoRefresh" :cheked="$storex.logs.autoRefresh" class="checkbox checkbox-xs" />
          <span>Auto-refresh</span>
        </label>
        <label class="flex items-center space-x-2">
          <input type="checkbox" @click="follow = !follow" :cheked="follow" class="checkbox checkbox-xs" />
          <span>Follow</span>
        </label>
        <div class="grow"></div>
        <div>
          <input class="input input-xs w-10" v-model="tailSize" />
        </div>
        <div class="px-2">({{ $storex.logs.filteredLogs.length }})</div>
      </div>
    </header>
    <div class="grid grid-cols-4 gap-1 my-2">
      <div 
        v-for="module in visibleModules" 
        :key="module" 
        @click="toggleModuleVisible(module)"
        :style="{ color: $ui.colorsMap[module] }"
        :class="['click badge badge-sm', logModules[module]?.visible ? 'border border-white': 'badge-outline']"
      >
        {{ module }}
      </div>
      <div 
        v-for="module in profilerModuleFilter" 
        :key="module" 
        @click="toggleProfilerVisible(module)"
        :style="{ color: $ui.colorsMap[module] }"
        :class="['click badge badge-sm', logModules[module]?.visible ? 'border border-white': 'badge-outline']"
      >
        {{ module }}
      </div>
    </div>
    <div class="grow overflow-auto flex flex-col">
      <div class="p-2" v-if="showMetrics">
        <RequestMetrics :title="'Requests'" :subtitle="'Requests path'"
          @filter-module="toggleProfilerVisible"
          :logs="requestLogs" class="mb-6" />
        <RequestMetrics :title="'Profiler'" :subtitle="'Method'"
          @filter-module="toggleProfilerVisible"
          :logs="profilerLogs" class="mb-6" />
      </div>
      <select @change="onLogChange" class="border select-xs rounded w-1/3">
        <option :selected="log === $storex.logs.selectedLog" 
          v-for="log in $storex.logs.logNames" :key="log" :value="log">{{ log }}</option>
      </select>
      <header class="flex flex-row justify-between items-center mt-2">
        <div class="flex gap-1 items-center">
          <input class="input input-xs input-bordered" placeholder="CSV patterns to discard"
            v-model="discardPatterns" />
          <label class="input input-xs input-bordered flex items-center gap-2">
            <input type="text" class="grow" placeholder="Search" v-model="filter" @keydown.enter="applyFilter" />
            <span v-if="filter">{{ matchCount }}</span>
            <span class="click" @click="clearFilter" v-if="filter"><i class="fa-regular fa-circle-xmark"></i></span>
            <span @click="applyFilter" v-else>
              <i class="fa-solid fa-magnifying-glass"></i>
            </span>
            <span class="click" @click="ignorePattern">
              <i class="fa-regular fa-eye-slash"></i>
            </span>
          </label>
        </div>
        <div class="grow"></div>
      </header>
      <div class="grow my-2 overflow-auto"
        style="height:600px" ref="logView">
        <!--div class="" v-for="log in filteredLogs" :key="log"
          :class="logClasses(log)"
        >
            {{ log }}
        </div-->
        <pre class="-mb-3 text-wrap" v-for="log, ix in filteredLogs" :key="`${log}-${ix}`"
          :class="log.includes('MATCH') && 'text-success'"
        >
          {{ log  }}
        </pre>
        <div class="h-20 text-primary animate-pulse w-full">
          ...
        </div>
      </div>
    </div>
  </div>
</template>

<script>
// codx: logView $refs.logView scrolled to bottom after detecting changes in fileterdLogs if it was at bottom 
export default {
  data() {
    return {
      showMetrics: false,
      showTimeFilter: false,
      logs: [],
      discardPatterns: '',
      logModules: {},
      visibleModules: [],
      profilerModuleFilter: [],
      tailSize: 250,
      filter: null,
      logLevelColors: {
        "INFO": "text-success",
        "DEBUG": "text-blue-600",
        "ERROR": "text-error",
        "WARNING": "text-warning"
      },
      timeSelection: null,
      follow: false
    }
  },
  created() {
  },
  computed: {
    requestLogs() {
      return this.logs.filter(log => log.data.request)
                      .map(({ timestamp, data: { request: { url, time_taken }}}) => ({ timestamp, path: new URL(url).pathname , time_taken }))
    },
    profilerLogs() {
      return this.$storex.logs.filteredLogs.filter(log => log.data.profiler)
                      .map(({ timestamp, data: { profiler: { module, method, time_taken }}}) => 
                                            ({ timestamp, path: `${module}.${method}` , time_taken }))
    },
    filteredLogs() {
      const discards = this.discardPatterns?.toLowerCase().split(",")
      const filters = this.filter?.toLowerCase().split(",")
      return this.$storex.logs.rawLogs?.filter(log => !discards?.length ||
        !discards.find(d => log.toLowerCase().includes(d)))
        .map(log => !filters ? log : 
            filters.find(f => log.toLocaleLowerCase().includes(f)) ?
              `[MATCH] ${log}` : log)
    },
    matchCount() {
      return this.filteredLogs.filter(l => l.includes("[MATCH]")).length
    }
  },
  watch: {
    filteredLogs() {
      if (this.follow) {
        const { logView } = this.$refs
        requestAnimationFrame(() => logView.scrollTo(0, logView.scrollHeight))
      }
    }
  },
  methods: {
    toggleModuleVisible(module) {
      const ix = this.visibleModules.indexOf(module)
      if (ix !== -1) {
        this.visibleModules.splice(ix, 1)
      } else {
        this.visibleModules.push(module)
      }
    },
    toggleTimeFilter() {
      this.showTimeFilter = !this.showTimeFilter
    },

    async fetchLogNames() {
      try {
        await this.$storex.logs.fetchLogNames()
        this.fetchLogs()
      } catch (error) {
        console.error('Error fetching log names:', error)
      }
    },
    
    async fetchLogs() {
      await this.$storex.logs.fetchLogs(this.tailSize)
    },
    toggleAutoRefresh() {
      this.$storex.logs.setAutoRefresh(!this.$storex.logs.autoRefresh)
      this.fetchLogs()
    },
    clearLogs() {
      this.$storex.logs.clearLogs()
    },
    
    onLogChange(ev) {
      this.$storex.logs.setSelectedLog(ev.target.value)
      this.clearLogs()
      this.fetchLogs()
    },
    
    scrollToBottom() {
      const { logView } = this.$refs
      if (logView) {
        logView.scrollTop = logView.scrollHeight
      }
      this.$el.scrollTop = this.$el.scrollHeight
    },
    
    logClasses(log) {
      const classes = []
      if (this.filter && this.isFilterMatch(log)) {
        classes.push("text-success")
      }
      const isError = log.toLocaleLowerCase().includes("error")
      if (isError) {
        classes.push("text-error")
      }
      return classes
    },

    isFilterMatch(log) {
      if (!this.filter) {
        return true
      }
      const lowerLog = log.toLowerCase()
      return this.filter.toLowerCase().split(",").find(e => lowerLog.includes(e))
    },
    
    ignorePattern() {
      this.$projects.addLogIgnore(this.filter?.toLowerCase())
      this.filter = null
    },

    applyFilter() {
      // Implementation for applying filter
    },
    
    clearFilter() {
      this.filter = null
      this.applyFilter()
    },
    
    toggleProfilerVisible(module) {
      if (this.profilerModuleFilter.includes(module)) {
        this.profilerModuleFilter.splice(this.profilerModuleFilter.indexOf(module), 1)
      } else {
        this.profilerModuleFilter.push(module)
      }
    }
  },
  mounted() {
    this.fetchLogNames()
  },
  beforeUnmount() {
    this.$storex.logs.setAutoRefresh(false)
  }
}
</script>
