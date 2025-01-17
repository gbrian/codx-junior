<script setup>
import RequestMetrics from './metrics/RequestMetrics.vue'
</script>
<template>
  <div class="p-2 gap-2 w-full max-w-full overflow-auto">
    <header class="flex flex-row justify-between items-center">
      <h1 class="text-xl font-semibold mb-4">Metrics Dashboard</h1>
      <div class="flex gap-2">
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
        <button class="btn btn-sm" @click="$ui.toggleLogs">
          Close
        </button>
      </div>
    </header>
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
    <div class="flex flex-col gap-2" ref="logView">
      <div v-for="(log, ix) in filteredFormatedLogs" :key="ix">
        <div class="flex flex-col w-full p-1 hover:bg-base-100" :class="log.styleClasses">
          <div class="flex gap-2">
            <div>{{ log.timestamp }}</div>
            <div class="font-bold">{{ log.level }}</div> 
            <div :style="{color: $ui.colorsMap[log.module]}"
              class="click"
              @click="toggleModuleVisible(log.module)" 
            >
              [{{ log.module }}]</div> 
            <div>(Line: {{ log.line }})</div>
          </div> 
          <pre>{{ log.content }}</pre>
          <pre class="text-warning"
            v-if="Object.keys(log.data).length">{{ JSON.stringify(log.data, null, 2) }}</pre>
        </div>
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
      formatedLogs: [],
      autoRefresh: false,
      logNames: [],
      filter: null,
      filterMatchCount: 0,
      logModules: {},
      visibleModules: []
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
      return ["api/logs", "/var/log/", ...this.ignorePatterns]
    },
    filteredFormatedLogs () {
      return this.formatedLogs?.filter(flog => 
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
    fetchLogs() {
      API.logs.read(this.selectedLog)
        .then(response => {
          this.logs = response.data
          this.logModules = {}
          this.logs.forEach(({ module }) => {
            this.logModules[module] = { visible: true }
          })
          this.formatedLogs = []
          this.formatFetchedLogs(this.logs)
          this.applyFilter()
          requestAnimationFrame(() => this.scrollToBottom())
          if (this.autoRefresh) {
            setTimeout(() => this.fetchLogs(), 3000)
          }
        })
        .catch(console.error)
    },
    formatFetchedLogs(logs) {
      const bucket = 50
      if (logs?.length) {
        logs.slice(0, bucket).forEach(log =>
          this.formatedLogs.push({ ...log, styleClasses: [] }))
        requestAnimationFrame(() => this.formatFetchedLogs(logs.slice(bucket)))
      }
      this.scrollToBottom()
    },
    clearLogs() {
      this.logs = []
      this.formatedLogs = []
    },
    onLogChange() {
      this.logs = []
      this.fetchLogs()
    },
    scrollToBottom() {
      const logView = this.$refs.logView
      logView.scrollTop = logView.scrollHeight
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
      if (!this.logModules[log.module]?.visible) {
        classes.push('hidden')
      }
      if (this.allIgnorePatterns.find(i => lowerLogContent.indexOf(i) !== -1)) {
        classes.push('hidden')
      }
      return classes
    },
    ignorePattern() {
      this.$projects.addLogIgnore(this.filter?.toLowerCase())
      this.filter = null
    },
    removeIgnore(ignore) {
      this.$projects.removeLogIgnore(ignore)
    },
    applyFilter() {
      this.formatedLogs?.forEach(flog => flog.styleClasses = this.logClasses(flog))
      this.filterMatchCount = this.formatedLogs?.filter(({ styleClasses }) => styleClasses.includes('match')).length
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