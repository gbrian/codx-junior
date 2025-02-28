<script setup>
</script>

<template>
  <div class="w-full h-full flex flex-col gap-4 p-4">
    <h2 class="text-xl font-bold">Global Agent Settings</h2>
    <div class="form-control w-full max-w-xs">
      <label class="label" for="max-agent-interactions">
        <span class="label-text">Max Agent Interactions:</span>
      </label>
      <input type="number" id="max-agent-interactions" v-model="agentSettings.max_agent_iteractions" class="input input-bordered w-full max-w-xs" />
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
    }
  },
  computed: {
    agentSettings() {
      return this.$storex.api.globalSettings.agent_settings
    }
  },
  methods: {
    updateGlobalSettings() {
      // Logic to update and save global settings
    }
  }
}
</script>