<script setup>
import RequestMetrics from './metrics/RequestMetrics.vue'
</script>
<template>
  <div class="p-2 gap-2 w-full max-w-full overflow-auto flex flex-col">
    <header class="flex flex-row justify-between items-center">
      <h1 class="text-xl font-semibold mb-4">Metrics Dashboard</h1>
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
        <div class="">
          <input class="input input-xs w-10" v-model="tailSize" />
        </div>
      </div>
    </header>
    <div class="grow overflow-auto">
      <div class="p-2">
        <RequestMetrics :title="'Requests'" :subtitle="'Requests path'"
          :logs="requestLogs" class="mb-6" />
        <RequestMetrics :title="'Profiler'" :subtitle="'Method'"
          :logs="profilerLogs" class="mb-6" />
      </div>
      <header class="flex flex-row justify-between items-center">
        <div class="flex gap-1">
          <select v-model="selectedLog" @change="onLogChange" class="border select-xs rounded">
            <option v-for="log in logNames" :key="log" :value="log">{{ log }}</option>
          </select>
          <label class="input input-xs input-bordered flex items-center gap-2">
            <input type="text" class="grow" placeholder="Search" v-model="filter" @keydown.enter="applyFilter" />
            <span v-if="filterMatchCount">{{ filterMatchCount }}</span>
            <span class="click" @click="clearFilter" v-if="filter"><i class="fa-regular fa-circle-xmark"></i></span>
            <span @click="applyFilter" v-else>
              <i class="fa-solid fa-magnifying-glass"></i>
            </span>
            <span class="click" @click="ignorePattern">
              <i class="fa-regular fa-eye-slash"></i>
            </span>
          </label>
        </div>
      </header>
      <div class="grid grid-cols-4 gap-1 my-2">
        <div 
          v-for="module in visibleModules" 
          :key="module" 
          @click="toggleModuleVisible(module)"
          :style="`color:${$ui.colorsMap[module]}`"
          :class="['click badge badge-sm', logModules[module]?.visible ? 'border border-white': 'badge-outline']"
        >
          {{ module }}
        </div>
      </div>
      <div v-if="ignorePatterns.length">
        <i class="fa-regular fa-eye-slash"></i>
        <span @click="removeIgnore(ignore)" class="click mr-2 badge badge-warning hover:underline" v-for="ignore in ignorePatterns" :key="ignore">
          {{ ignore }}
        </span>
      </div>
      <div class="flex flex-col gap-2 overflow-auto" style="height:600px" ref="logView">
        <div v-for="(log, ix) in filteredLogs" :key="ix">
          <div :title="log.id" class="flex flex-col w-full p-1 hover:bg-base-100" :class="log.styleClasses">
            <div class="flex gap-2">
              <div>{{ log.timestamp }}</div>
              <div class="font-bold" :class="logLevelColors[log.level]">{{ log.level }}</div> 
              <div :style="{color: $ui.colorsMap[log.module]}"
                class="click"
                @click="toggleModuleVisible(log.module)" 
              >
                [{{ log.module }}]</div> 
              <div>(Line: {{ log.line }})</div>
            </div> 
            <pre class="overflow-hidden click" :class="!log.showMore && 'max-h-40'" @click="log.showMore = !log.showMore">{{ log.content }}</pre>
            <pre class="text-warning"
              v-if="Object.keys(log.data).length">{{ JSON.stringify(log.data, null, 2) }}</pre>
          </div>
        </div>
        <div ref="scrollEnd"></div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      selectedLog: '',
      logs: [],
      autoRefresh: false,
      logNames: [],
      filter: null,
      filterMatchCount: 0,
      logModules: {},
      visibleModules: [],
      tailSize: 100,
      logLevelColors: {
        "INFO": "text-success",
        "DEBUG": "text-blue-600",
        "ERROR": "text-error",
        "WARNING": "text-warning"
      }
    }
  },
  watch: {
    autoRefresh (newVal) {
      if (newVal) {
        this.fetchLogs()
      }
    }
  },
  computed: {
    distinctModules() {
      return [...new Set(this.logs.map(log => log.module))]
    },
    ignorePatterns() {
      return this.$project?.log_ignore?.split(",").filter(i => i.trim().length) || []
    },
    allIgnorePatterns() {
      return this.ignorePatterns
    },
    filteredLogs () {
      return this.logs?.filter(flog => !flog.hidden &&
        (!this.visibleModules.length || this.visibleModules.includes(flog.module)) &&
          (!flog.data?.url || flog.data.url.indexOf("/api/logs") === -1))
    },
    requestLogs () {
      return this.logs.filter(log => log.data.request)
                      .map(({ timestamp, data: { request: { url, time_taken }}}) => ({ timestamp, path: new URL(url).pathname , time_taken}))
    },
    profilerLogs () {
      return this.logs.filter(log => log.data.profiler)
                      .map(({ timestamp, data: { profiler: { module, method, time_taken }}}) => 
                                            ({ timestamp, path: `${module?.replace('codx.junior.', '')}.${method}` , time_taken}))
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
    async fetchLogNames() {
      try {
        const response = await API.logs.list()
        this.logNames = response.data
        if (this.logNames.length) {
          this.selectedLog = this.logNames[0]
          this.fetchLogs()
        }
      } catch (error) {
        console.error('Error fetching log names:', error)
      }
    },
    async fetchLogs() {
      const forceScroll = this.logs.length === 0
      const { data } = await this.$storex.api.logs.read(this.selectedLog, Math.floor(this.tailSize + (this.tailSize / 3)))
      const newLogs = data.filter(l =>
        !["api/logs", "/var/log/"].some(pattern => l.content.includes(pattern)) &&
        !this.logs.find(ll => ll.id === l.id))
        .sort((a, b) => a.timestamp < b.timestamp ? -1: 1)
      this.logs.push(...newLogs)
      this.logModules = {}
      this.logs.forEach(({ module }) => {
        this.logModules[module] = { visible: true }
      })
      this.applyFilter()
      requestAnimationFrame(() => this.scrollToBottom(forceScroll))
      if (this.autoRefresh) {
        setTimeout(() => this.fetchLogs(), 3000)
      }
    },
    clearLogs() {
      this.logs = []
    },
    onLogChange() {
      this.logs = []
      this.fetchLogs()
    },
    scrollToBottom(force) {
      const { logView, scrollEnd } = this.$refs
      if (logView && scrollEnd) {
        logView.scrollTop = logView.scrollHeight
      }
    },
    logClasses(log) {
      const classes = []
      const lowerLogContent = log.content?.toLowerCase() || ""
      const filter = this.filter?.toLowerCase()
      if (filter) {
        if (lowerLogContent.indexOf(filter) === -1) {
          classes.push('opacity-30')
        } else {
          classes.push('font-bold', 'match')
        }
      }
      log.hidden = false
      if (!this.logModules[log.module]?.visible) {
        log.hidden = true
      }
      if (this.allIgnorePatterns.find(i => lowerLogContent.indexOf(i) !== -1)) {
        log.hidden = true
      }
      log.styleClasses = classes
    },
    ignorePattern() {
      this.$projects.addLogIgnore(this.filter?.toLowerCase())
      this.filter = null
    },
    removeIgnore(ignore) {
      this.$projects.removeLogIgnore(ignore)
    },
    applyFilter() {
      this.logs.forEach(flog => this.logClasses(flog))
      this.filterMatchCount = this.logs.filter(({ styleClasses }) => styleClasses.includes('match')).length
    },
    clearFilter() {
      this.filter = null
      this.applyFilter()
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