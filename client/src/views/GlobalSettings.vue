<template>
  <div class="flex flex-col gap-2 p-4 overflow-auto">
    <div class="text-xl font-medium my-2 flex justify-between">
      Global Settings
    </div>
    <div class="flex flex-col gap-4" v-if="settings">
      <div class="flex flex-col gap-2 text-xs">
        <div class="text-xl font-bold">Global</div>
        <div class="ml-6 p-2 flex flex-col gap-2">

          <div class="flex items-center">
            <span class="w-1/4">codx-junior Avatar:</span>
            <input v-model="settings.codx_junior_avatar" type="text" class="input input-bordered flex-grow" />
          </div>
          <div class="flex items-center">
            <span class="w-1/4">Projects Root Path:</span>
            <input v-model="settings.projects_root_path" type="text" class="input input-bordered flex-grow" />
          </div>
        </div>
      </div>
      <div class="flex flex-col gap-2 text-xs">
        <div class="text-xl font-bold">Git</div>
        <div class="ml-6 p-2 flex flex-col gap-2">

          <div class="flex items-center">
            <span class="w-1/4">Username:</span>
            <input v-model="settings.git.username" type="text" class="input input-bordered flex-grow" />
          </div>
          <div class="flex items-center">
            <span class="w-1/4">Email:</span>
            <input v-model="settings.git.email" type="text" class="input input-bordered flex-grow" />
          </div>
        </div>
      </div>
      <div class="flex flex-col gap-2 text-xs">
        <div class="text-xl font-bold">AI</div>
        <div class="ml-6 p-2 flex flex-col gap-2">
          <div class="flex items-center">
            <span class="w-1/4">Log AI:</span>
            <input v-model="settings.log_ai" type="checkbox" class="checkbox" />
          </div>
          <div class="font-bold">Embeddings</div>
          <div class="ml-6 p-2 flex flex-col gap-2">
            <div class="flex items-center">
              <span class="w-1/4">Provider:</span>
              <input v-model="settings.embeddings_ai_settings.provider" type="text" class="input input-bordered" />
            </div>
            <div class="flex items-center">
              <span class="w-1/4">Model:</span>
              <input v-model="settings.embeddings_ai_settings.model" type="text" class="input input-bordered" />
            </div>
            <div class="flex items-center">
              <span class="w-1/4">Api url:</span>
              <input v-model="settings.embeddings_ai_settings.api_url" type="text" class="input input-bordered" />
            </div>
            <div class="flex items-center">
              <span class="w-1/4">Api key:</span>
              <input v-model="settings.embeddings_ai_settings.api_key" type="text" class="input input-bordered" />
            </div>
            <div class="flex items-center">
              <span class="w-1/4">Vector size:</span>
              <input v-model="settings.embeddings_ai_settings.vector_size" type="text" class="input input-bordered" />
            </div>
          </div>
          <div class="font-bold">Default AI provider</div>
          <div class="ml-6 p-2 flex flex-col gap-2">
            <div class="flex items-center">
              <span class="w-1/4">Provider:</span>
              <input v-model="settings.ai_provider" type="text" class="input input-bordered" />
            </div>
            <div class="flex items-center">
              <span class="w-1/4">Model:</span>
              <input v-model="settings.ai_model" type="text" class="input input-bordered" />
            </div>
          </div>
        </div>
        <div class="flex flex-col gap-2 text-xs">
          <div class="text-xl font-bold pl-2 font-bold">OpenAI</div>
          <div class="ml-6 p-2 flex flex-col gap-2">

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
        </div>
        <div class="flex flex-col gap-2 text-xs">
          <div class="text-xl font-bold pl-2 font-bold">MistralAI</div>
          <div class="ml-6 p-2 flex flex-col gap-2">

            <div class="flex items-center">
              <span class="w-1/4 pl-4">API URL:</span>
              <input v-model="settings.mistral_ai.mistral_api_url" type="text" class="input input-bordered flex-grow" />
            </div>
            <div class="flex items-center">
              <span class="w-1/4 pl-4">API Key:</span>
              <input v-model="settings.mistral_ai.mistral_api_key" type="text" class="input input-bordered flex-grow" />
            </div>
            <div class="flex items-center">
              <span class="w-1/4 pl-4">Model:</span>
              <input v-model="settings.mistral_ai.mistral_model" type="text" class="input input-bordered flex-grow" />
            </div>
          </div>
        </div>
        <div class="flex flex-col gap-2 text-xs">
          <div class="text-xl font-bold pl-2 font-bold">AnthropicAI</div>
          <div class="ml-6 p-2 flex flex-col gap-2">

            <div class="flex items-center">
              <span class="w-1/4 pl-4">API Key:</span>
              <input v-model="settings.anthropic_ai.anthropic_api_key" type="text"
                class="input input-bordered flex-grow" />
            </div>
            <div class="flex items-center">
              <span class="w-1/4 pl-4">Model:</span>
              <input v-model="settings.anthropic_ai.anthropic_model" type="text"
                class="input input-bordered flex-grow" />
            </div>
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