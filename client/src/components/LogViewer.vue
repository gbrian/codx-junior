<template>
  <div class="flex flex-col gap-2 h-2/3 w-full max-w-full">
    <header class="flex justify-between items-center mb-4">
      <select v-model="selectedLog" @change="onLogChange" class="border rounded px-3 py-2">
        <option v-for="log in logNames" :key="log" :value="log">{{ log }}</option>
      </select>
      <label class="flex items-center space-x-2">
        <input type="checkbox" v-model="autoRefresh" @change="toggleAutoRefresh" class="form-checkbox" />
        <span>Auto-refresh</span>
      </label>
    </header>
    <div class="grow overflow-auto" ref="logView">
      <pre class="w-96">{{ logs }}</pre>
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
      logNames: []  // Now fetched from API
    };
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
          this.logs += response.data;
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
        this.refreshInterval = setInterval(this.fetchLogs, 10000);
      } else {
        clearInterval(this.refreshInterval);
      }
    },
    scrollToBottom() {
      const logView = this.$refs.logView;
      logView.scrollTop = logView.scrollHeight;
    }
  },
  mounted() {
    this.fetchLogNames();
  },
  beforeDestroy() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }
};
</script>