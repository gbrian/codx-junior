<template>
  <div class="flex flex-col gap-2 h-full w-full max-w-full">
    <header class="flex flex-col 2xl:flex-row justify-between items-center">
      <div class="flex gap-1">
        <select v-model="selectedLog" @change="onLogChange"
          class="border select-xs rounded">
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
    <div class="" v-if="ignorePatterns.length">
      <i class="fa-regular fa-eye-slash"></i>
      <span @click="removeIgnore(ignore)" class="click mr-2 badge badge-warning hover:underline" v-for="ignore, ix in ignorePatterns" :key="ignore">
        {{ ignore }}
      </span>
    </div>
    <div class="grow overflow-auto" ref="logView">
      <code>
        <pre class="w-full" v-html="flog.log" :class="flog.styleClasses" v-for="(flog, ix) in formatedLogs" :key="ix"></pre>
      </code>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      selectedLog: '',
      logs: '',
      formatedLogs: null,
      autoRefresh: false,
      logNames: [],
      filter: null,
      filterMatchCount: 0
    }
  },
  mounted() {
    this.fetchLogNames()
  },
  beforeUnmount() {
    this.autoRefresh = false
  },
  computed: {
    ignorePatterns() {
      return this.$project?.log_ignore?.split(",").filter(i => i.trim().length) || []
    },
    allIgnorePatterns() {
      return ["api/logs", "/var/log/", ...this.ignorePatterns]
    }
  },
  watch: {
    autoRefresh () {
      if (this.autoRefresh) {
        this.fetchLogs()
      }
    }
  },
  methods: {
    colorMap() {
      const modules = new Set()
      this.logs?.split('\n').forEach(log => {
        const moduleMatch = this.extractModule(log)
        if (moduleMatch) {
          modules.add(moduleMatch)
        }
      })
      const colors = this.$ui.colorsMap
      const newModules = [...modules].filter(m => !colors[m])
      if (newModules) {
        newModules.forEach(module => {
          colors[module] = `#${Math.floor(Math.random()*16777215).toString(16)}` // Random color
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
        .then((response) => {
          this.logs = response.data
          this.formatedLogs = []
          this.formatFetchedLogs(this.logs?.split('\n'))
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
          this.formatedLogs.push({ log: this.formattedLog(log) }))
        requestAnimationFrame(() => this.formatFetchedLogs(logs.slice(bucket - 1)))
      }
      this.scrollToBottom()
    },
    clearLogs() {
      this.logs = null
      this.formatedLogs = null
    },
    onLogChange() {
      this.logs = ''  // Clear log output
      this.fetchLogs()
    },
    scrollToBottom() {
      const logView = this.$refs.logView
      logView.scrollTop = logView.scrollHeight
    },
    logClasses(log) {
      const classes = []
      const loweLog = log.toLowerCase() 
      const filter = this.filter?.toLowerCase()
      if (filter) {
          if (loweLog.indexOf(filter) === -1) {
            classes.push('opacity-30')
          } else {
            classes.push('font-bold')
            classes.push('match')
          }
      }
      if (this.allIgnorePatterns.find(i => loweLog.indexOf(i) !== -1)) {
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
    formattedLog(log) {
      const colorsMap = this.colorMap()
      const module = this.extractModule(log)
      const color = colorsMap[module] || 'white'
      return log.replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/'/g, "&#39;")
              .replace(/"/g, "&quot;")
              .replace(module, `<span style="color: ${color}">${module}</span>`)
    },
    extractModule(log) {
      const moduleMatch = log?.match(/\[([\w\.\:]+)\]/)
      return moduleMatch ? moduleMatch[1].split(":")[0] : ""
    },
    applyFilter() {
      this.formatedLogs?.forEach(flog => flog.styleClasses = this.logClasses(flog.log))
      this.filterMatchCount = this.formatedLogs?.filter(({ styleClasses }) => styleClasses.includes('match')).length
    },
    clearFilter() {
      this.filter = null
      this.applyFilter()
    }
  }
}
</script>