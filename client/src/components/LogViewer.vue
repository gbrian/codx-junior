<script setup>
import RequestMetrics from './metrics/RequestMetrics.vue'
import TimeSelector from './TimeSelector.vue'
import Markdown from './Markdown.vue'
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
          <input type="checkbox" v-model="autoRefresh" class="checkbox checkbox-xs" />
          <span>Auto-refresh</span>
        </label>
        <div class="grow"></div>
        <div>
          <input class="input input-xs w-10" v-model="tailSize" />
        </div>
        <div class="px-2">({{ filteredLogs.length }})</div>
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
      <select v-model="selectedLog" @change="onLogChange" class="border select-xs rounded w-1/3">
        <option v-for="log in logNames" :key="log" :value="log">{{ log }}</option>
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
      <div class="grow my-2 flex flex-col gap-2 overflow-auto"
        style="height:600px" ref="logView">
        <div class="" v-for="log in filteredLogs" :key="log"
          :class="logClasses(log)"
          ref="logView"
        >
            {{ log }}
        </div>
        <div class="h-20 text-primary animate-pulse w-full">
          ...
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      rawLogs: [],
      showMetrics: false,
      showTimeFilter: false,
      selectedLog: '',
      logs: [],
      autoRefresh: false,
      logNames: [],
      filter: null,
      logModules: {},
      visibleModules: [],
      profilerModuleFilter: [],
      tailSize: 100,
      discardPatterns: '',
      logLevelColors: {
        "INFO": "text-success",
        "DEBUG": "text-blue-600",
        "ERROR": "text-error",
        "WARNING": "text-warning"
      },
      timeSelection: null
    }
  },
  watch: {
    autoRefresh(newVal) {
      if (newVal) {
        this.fetchLogs()
      }
    }
  },
  computed: {
    logTimes() {
      return new Set(this.logs.map(l => l.timestamp.split(",")[0]))
    },
    distinctModules() {
      return [...new Set(this.logs.map(log => log.module))]
    },
    filteredLogs() {
      const isLogVisible = log => {
        if (this.discardPatterns?.length) {
          const patterns = this.discardPatterns.split(',').map(p => p.trim().toLowerCase())
          return !patterns.some(pattern => log.toLowerCase().includes(pattern))
        }
        return true
      }
      return this.rawLogs?.filter(isLogVisible)
    },
    requestLogs() {
      return this.logs.filter(log => log.data.request)
                      .map(({ timestamp, data: { request: { url, time_taken }}}) => ({ timestamp, path: new URL(url).pathname , time_taken }))
    },
    profilerLogs() {
      return this.filteredLogs.filter(log => log.data.profiler)
                      .map(({ timestamp, data: { profiler: { module, method, time_taken }}}) => 
                                            ({ timestamp, path: `${module}.${method}` , time_taken }))
    },
    matchCount() {
      return this.filter ? 
          this.rawLogs?.filter(this.isFilterMatch.bind(this)).length : 0
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

    // Function to map log modules to colors
    colorMap() {
      const modules = new Set()
      this.logs.forEach(log => {
        if (log.module) {
          modules.add(log.module)
        }
      })
      const colors = this.$ui.colorsMap
      const newModules = [...modules].filter(m => !colors[m])
      if (newModules) {
        newModules.forEach(module => {
          colors[module] = `#${Math.floor(Math.random() * 16777215).toString(16)}`
        })
        this.$ui.setColorsMap(colors)
      }
      return this.$ui.colorsMap
    },
    
    // Fetch and set available log names
    async fetchLogNames() {
      try {
        this.logNames = await this.$storex.api.logs.list()
        if (this.logNames.length) {
          this.selectedLog = this.logNames[0]
          this.fetchLogs()
        }
      } catch (error) {
        console.error('Error fetching log names:', error)
      }
    },
    
    // Fetch logs based on selection
    async fetchLogs() {
      const data = await this.$storex.api.logs.read(this.selectedLog, this.tailSize)
      if (!this.autoRefresh) {
        this.rawLogs = []
      }
      this.rawLogs = [
        ...this.rawLogs,
        ...data.filter(l => !this.rawLogs.includes(l))
      ]
      if (this.autoRefresh) {
        setTimeout(() => this.fetchLogs(), 3000)
      }

      // Check if the bottom element is visible, then scroll the parent container
      const { scrollTop, clientHeight, scrollHeight } = this.$refs.logView
      if (scrollTop + clientHeight >= scrollHeight - 1) {
        setTimeout(() => this.scrollToBottom(), 100)
      }
    },
    
    clearLogs() {
      this.rawLogs = []
    },
    
    onLogChange() {
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
    
    isFilterMatch(log) {
      return log.toLowerCase().includes(this.filter.toLowerCase())
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
    
    ignorePattern() {
      this.$projects.addLogIgnore(this.filter?.toLowerCase())
      this.filter = null
    },
    
    applyFilter() {
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
    },
    
    onTimeSelectorChanged(selection) {
      this.timeSelection = selection
    }
  },
  mounted() {
    this.fetchLogNames()
  },
  beforeUnmount() {
    this.autoRefresh = false
  }
}
</script>