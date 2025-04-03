<script setup>
import RequestMetrics from './metrics/RequestMetrics.vue'
import TimeSelector from './TimeSelector.vue'
import Markdown from './Markdown.vue';
</script>

<template>
  <div class="px-2 pt-4 gap-2 w-full max-w-full overflow-auto flex flex-col relative">
    <header class="flex flex-row justify-between items-center">
      <h1 class="text-xl font-semibold">Dashboard</h1>
      <button class="btn btn-sm" :class="showMetrics && 'btn-outline'" @click="showMetrics = !showMetrics">
        Metrics
      </button>
      <TimeSelector
        :start="timeSelection?.start"
        :end="timeSelection?.end"
        :times="logTimes"
        @time-change="onTimeSelectorChanged"
        @reset="showTimeFilter = false"
        v-if="showTimeFilter"
      />
      <button class="btn btn-sm" @click="toggleTimeFilter">
        <i class="fa-regular fa-clock"></i>
      </button>
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
    <div class="grow overflow-auto">
      <div class="p-2" v-if="showMetrics">
        <RequestMetrics :title="'Requests'" :subtitle="'Requests path'"
          @filter-module="toggleProfilerVisible"
          :logs="requestLogs" class="mb-6" />
        <RequestMetrics :title="'Profiler'" :subtitle="'Method'"
          @filter-module="toggleProfilerVisible"
          :logs="profilerLogs" class="mb-6" />
      </div>
      <header class="flex flex-row justify-between items-center">
        <div class="flex gap-1 items-center">
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
        <div class="grow"></div>
      </header>
      <div class="my-2 flex flex-col gap-2 overflow-auto" style="height:600px" ref="logView">
        <div v-for="(log, ix) in filteredLogs" :key="ix">
          <div :title="log.id" class="flex flex-col w-full p-1 hover:bg-base-100" :class="log.styleClasses">
            <div class="flex gap-2">
              <div>{{ log.timestamp }}</div>
              <div class="font-bold" :class="logLevelColors[log.level]">{{ log.level }}</div> 
              <div :style="{ color: $ui.colorsMap[log.module] }"
                class="click"
                @click="toggleModuleVisible(log.module)" 
              >
                [{{ log.module }}]</div> 
              <div>(Line: {{ log.line }})</div>
            </div> 
            <div class="overflow-hidden click" :class="!log.showMore && 'max-h-40'" 
              @dblclick="log.editable = log.showMore = true"
              @keydown.esc="log.editable = false"
              @click="!log.editable && (log.showMore = !log.showMore)">
              <pre class="text-wrap" :contenteditable="log.editable">{{ log.content }}</pre>
              <pre class="text-warning text-wrap"
                :contenteditable="log.editable"
                v-if="Object.keys(log.data).length">{{ JSON.stringify(log.data, null, 2) }}</pre>
              <pre v-if="log.data.profiler">{{ log.data.profiler.profile_stats  }}</pre>
            </div>
          </div>
        </div>
        <div class="text-xs click" v-for="event in events" :key="event.ts"
          @click="event.collapsed = !event.collapsed"
        >
          <div class="p-2 bg-warning text-warning-content rounded-md font-medium">
            <i class="fa-solid fa-bolt"></i> [{{ new Date(event.ts).toISOString() }}] [{{ event.event }}]
          </div>
          <div class="mt-2 bg-base-100 p-2" v-if="event.collapsed === true">
            <Markdown :text="event.data.message.content" v-if="event.data.message.content" />
            <pre>{{ JSON.stringify({ ...event.data, message: undefined }, null, 2) }}</pre>
          </div>
        </div>
        <div class="h-1 w-full" ref="logViewBottom"></div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      showMetrics: false,
      showTimeFilter: false,
      selectedLog: '',
      logs: [],
      autoRefresh: false,
      logNames: [],
      filter: null,
      filterMatchCount: 0,
      logModules: {},
      visibleModules: [],
      profilerModuleFilter: [],
      tailSize: 100,
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
    },
    events(newValue) {
      if (newValue.length) {
        this.scrollToBottom()
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
        if (log.hidden || log.data.url?.includes("/api/logs")) {
          return false
        }
        if (this.timeSelection) {
          const { start, end } = this.timeSelection
          if ((start && log.timestamp < start) || (end && log.timestamp > end)) {
            return false
          }
        }
        if (this.profilerModuleFilter.length) {
          return this.profilerModuleFilter.includes(
            `${log.data?.profiler?.module}.${log.data?.profiler?.method}`) 
        }
        if (this.visibleModules.length) {
          return this.visibleModules.includes(log.module)
        }
        return true
      }
      return this.logs?.filter(isLogVisible)
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
    events() {
      return $storex.session.events
      .filter(e => !e.data.message)
      .reduce((acc, ev) => {
        const lastEv = acc[acc.length -1]
        if (lastEv && 
            lastEv?.data.message &&
            ev.data.message?.id &&
            lastEv?.data.message?.id === ev.data.message?.id
          ) {
            lastEv.data.message.content += ev.data.message.content 
        } else {
          acc.push(ev)
        }
        return acc
      }, [])
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
        const response = await this.$storex.api.logs.list()
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
      const { data } = await this.$storex.api.logs.read(this.selectedLog, this.tailSize)
      const newLogs = data.filter(l =>
        !["api/logs", "/var/log/"].some(pattern => l.content.includes(pattern)) &&
        !this.logs.find(ll => ll.id === l.id))
        .sort((a, b) => a.timestamp < b.timestamp ? -1 : 1)
      this.logs.push(...newLogs)
      this.logModules = {}
      this.logs.forEach(({ module }) => {
        this.logModules[module] = { visible: true }
      })
      this.applyFilter()
      this.scrollToBottom(forceScroll)
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
    scrollToBottom() {
      if (true || !this.$refs.logViewBottom?.checkVisibility()) {
        return
      }
      const { logView } = this.$refs
      if (logView) {
        logView.scrollTop = logView.scrollHeight
      }
      this.$el.scrollTop = this.$el.scrollHeight
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
      log.styleClasses = classes
    },
    ignorePattern() {
      this.$projects.addLogIgnore(this.filter?.toLowerCase())
      this.filter = null
    },
    applyFilter() {
      this.logs.forEach(flog => this.logClasses(flog))
      this.filterMatchCount = this.logs.filter(({ styleClasses }) => styleClasses.includes('match')).length
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