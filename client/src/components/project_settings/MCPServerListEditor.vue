<template>
  <div class="space-y-6">
    <p class="text-sm text-base-content/60">Configure Model Context Protocol servers for this project.</p>
    <button @click="addServer" class="btn btn-sm btn-outline">
      <i class="fa-solid fa-plus"></i>
      Add server
    </button>
    <div v-if="servers.length === 0" class="text-sm text-base-content/60 italic">
      No MCP servers configured yet.
    </div>
    <MCPServerSettings
      v-for="(server, index) in servers"
      :key="index"
      v-model="servers[index]"
      @remove="removeServer(index)"
    />
  </div>
</template>

<script>
import MCPServerSettings from './MCPServerSettings.vue'
import MCPServer from '@/models/MCPServer'

export default {
  components: {
    MCPServerSettings
  },
  props: {
    modelValue: {
      type: Array,
      required: true
    }
  },
  emits: ['update:modelValue'],
  computed: {
    servers: {
      get() {
        return this.modelValue || []
      },
      set(value) {
        this.$emit('update:modelValue', value)
      }
    }
  },
  methods: {
    addServer() {
      this.servers = [...this.servers, new MCPServer()]
    },
    removeServer(index) {
      this.servers.splice(index, 1)
      this.$emit('update:modelValue', this.servers)
    }
  }
}
</script>