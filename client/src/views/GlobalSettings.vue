<template>
  <div class="flex flex-col gap-2 h-full">
    <div class="text-xl font-medium my-2 flex justify-between">
      Global Settings
    </div>
    <div class="flex flex-col gap-4" v-if="settings">
      <div class="flex flex-col gap-2 text-xs">
        <div class="text-base">Global</div>
        <div class="flex items-center">
          <span class="w-1/4">Log AI:</span>
          <input v-model="settings.log_ai" type="checkbox" class="checkbox" />
        </div>
        <div class="flex items-center">
          <span class="w-1/4">Projects Root Path:</span>
          <input v-model="settings.projects_root_path" type="text" class="input input-bordered flex-grow" />
        </div>
      </div>
      <div class="flex flex-col gap-2 text-xs">
        <div class="text-base">AI</div>
        <div class="flex items-center">
          <span class="w-1/4">Temperature:</span>
          <input v-model="settings.ai_temperature" type="text" class="input input-bordered flex-grow" />
        </div>
        <div class="flex flex-col gap-2 text-xs">
          <div class="text-base pl-2 font-bold">OpenAI</div>
          <div class="flex items-center">
            <span class="w-1/4 pl-4">API URL:</span>
            <input v-model="settings.openai.openai_api_url" type="text" class="input input-bordered flex-grow" />
          </div>
          <div class="flex items-center">
            <span class="w-1/4 pl-4">API Key:</span>
            <input v-model="settings.openai.openai_api_key" type="text" class="input input-bordered flex-grow" />
          </div>
          <div class="flex items-center">
            <span class="w-1/4 pl-4">Model:</span>
            <input v-model="settings.openai.openai_model" type="text" class="input input-bordered flex-grow" />
          </div>  
        </div>
        <div class="flex flex-col gap-2 text-xs">
          <div class="text-base pl-2 font-bold">AnthropicAI</div>
          <div class="flex items-center">
            <span class="w-1/4 pl-4">API Key:</span>
            <input v-model="settings.anthropic_ai.anthropic_api_key" type="text" class="input input-bordered flex-grow" />
          </div>
          <div class="flex items-center">
            <span class="w-1/4 pl-4">Model:</span>
            <input v-model="settings.anthropic_ai.anthropic_model" type="text" class="input input-bordered flex-grow" />
          </div>
        </div>
      </div>
      <div class="flex justify-end gap-2">
        <button class="btn btn-sm btn-primary" @click="saveSettings">Save</button>
      </div>
    </div>
    <div class="grow relative overflow-auto">
      <div class="flex flex-col">
        <button class="btn btn-warning" @click="updateEngine">
          <i class="fa-solid fa-triangle-exclamation"></i>
          Update engine code base
        </button>
        <div class="text-xs">This action will download latest version from engine.</div>
      </div>
    </div>
  </div>
</template>

<script>
import { API } from '../api/api'
export default {
  data() {
    return {
      settings: null
    };
  },
  async created() {
    this.loadSettings()
  },
  methods: {
    async loadSettings() {
      const { data } = await API.settings.global.read()
      this.settings = data
    },
    async saveSettings() {
      await API.settings.global.write(this.settings)
      this.loadSettings()
    },
    updateEngine() {
      API.engine.update()
    },
  },
};
</script>