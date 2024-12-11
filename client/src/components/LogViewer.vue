<template>
  <div class="flex flex-col gap-2 h-full w-full max-w-full">
    <header class="flex flex-col 2xl:flex-row justify-between items-center">
      <div class="flex gap-1">
        <select v-model="selectedLog" @change="onLogChange"
          class="border select-xs rounded">
          <option v-for="log in logNames" :key="log" :value="log">{{ log }}</option>
        </select>
        <label class="input input-xs input-bordered flex items-center gap-2">
          <input type="text" class="grow" placeholder="Search" v-model="filter" />
          <span class="click" @click="filter = null" v-if="filter"><i class="fa-regular fa-circle-xmark"></i></span>
          <span v-else>
            <i class="fa-solid fa-magnifying-glass"></i>
          </span>
          <span class="click" @click="ignorePattern">
            <i class="fa-regular fa-eye-slash"></i>
          </span>
        </label>
      </div>
      <div class="flex gap-2">
        <button class="btn btn-sm" @click="logs = null">
          Clear
        </button>
        <button class="btn btn-sm" @click="fetchLogs">
          Refresh
        </button>
        <label class="flex items-center space-x-2">
          <input type="checkbox" v-model="autoRefresh" @change="toggleAutoRefresh" class="form-checkbox" />
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
        <pre class="w-96" :class="logClass(log)" v-for="log, ix in logs?.split('\n')">{{ log }}</pre>
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
      autoRefresh: false,
      refreshInterval: null,
      logNames: [],
      filter: null,
    };
  },
  computed: {
    ignorePatterns () {
      return this.$project?.log_ignore?.split(",").filter(i => i.trim().length)
        || []
    },
    allIgnorePatterns () {
      return ["api/logs", "/var/log/", ...this.ignorePatterns]
    }
  },
  methods: {
    async fetchLogNames() {
      try {
        const response = await API.logs.list();
        this.logNames = response.data;
        if (this.logNames.length) {
          this.selectedLog = this.logNames[0];
          this.fetchLogs();
        }
      } catch (error) {
        console.error('Error fetching log names:', error);
      }
    },
    fetchLogs() {
      API.logs.read(this.selectedLog)
        .then((response) => {
          this.logs = response.data;
          requestAnimationFrame(() =>  this.scrollToBottom());
        })
        .catch(console.error);
    },
    onLogChange() {
      this.logs = '';  // Clear log output
      this.fetchLogs();
    },
    toggleAutoRefresh() {
      if (this.autoRefresh) {
        this.refreshInterval = setInterval(this.fetchLogs, 2000);
      } else {
        clearInterval(this.refreshInterval);
      }
    },
    scrollToBottom() {
      const logView = this.$refs.logView;
      logView.scrollTop = logView.scrollHeight;navigation
    },
    logClass(log) {
      const classes = []
      const loweLog = log.toLowerCase() 
      const filter = this.filter?.toLowerCase()
      if (filter) {
          if (loweLog.indexOf(filter) === -1) {
            classes.push('opacity-30')
          } else {
            classes.push('font-bold')
          }
      }
      if (this.allIgnorePatterns.find(i => loweLog.indexOf(i) !== -1)) {
        classes.push('hidden')
      }
      return classes
    },
    ignorePattern () {
      this.$projects.addLogIgnore(this.filter?.toLowerCase())
      this.filter = null
    },
    removeIgnore(ignore) {
      this.$projects.removeLogIgnore(ignore)
    }
  },
  mounted() {
    this.fetchLogNames();
  },
  beforeUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }
};
</script>