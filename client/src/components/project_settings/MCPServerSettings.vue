<template>
  <div class="border border-base-300 rounded-lg p-6 space-y-4">
    <div class="flex justify-between items-start gap-4">
      <div class="flex-1 space-y-4">
        <div>
          <label class="label-text block font-semibold mb-2">Server name</label>
          <input
            v-model="server.name"
            type="text"
            placeholder="e.g., My MCP Server"
            class="input input-bordered w-full"
          />
        </div>
        <div>
          <label class="label-text block font-semibold mb-2">Server URL</label>
          <input
            v-model="server.url"
            type="text"
            placeholder="e.g., http://localhost:3000"
            class="input input-bordered w-full"
          />
        </div>
        <div>
          <label class="label-text block font-semibold mb-2">API Key</label>
          <input
            v-model="server.api_key"
            type="password"
            placeholder="Server API key"
            class="input input-bordered w-full"
          />
        </div>
      </div>
      <button @click="$emit('remove')" class="btn btn-error">
        <i class="fa-solid fa-trash"></i>
      </button>
    </div>
    <div class="flex items-center gap-3 pt-2 border-t border-base-300">
      <input v-model="server.active" type="checkbox" class="toggle" />
      <label class="label-text">Active</label>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    modelValue: {
      type: Object,
      required: true
    }
  },
  emits: ['update:modelValue', 'remove'],
  computed: {
    server: {
      get() {
        return this.modelValue
      },
      set(value) {
        this.$emit('update:modelValue', value)
      }
    }
  }
}
</script>