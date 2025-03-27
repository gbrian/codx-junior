<script setup>
import AISettings from './AISettings.vue'
import AgentSettings from '@/components/ai_settings/AgentSettings.vue'
import ModelSelector from '@/components/ai_settings/ModelSelector.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-2 p-4 overflow-auto">
    <div class="text-xl font-medium my-2 flex justify-between">
      Global Settings
      <div class="flex justify-end gap-2 items-center">
        <button class="btn btn-sm" @click="reloadSettings">Reload</button>
        <button class="btn btn-sm btn-primary" @click="saveSettings">Save</button>
        <div class="dropdown dropdown-hover dropdown-bottom dropdown-end">
          <div tabindex="0" role="button" class="btn btn-sm m-1"><i class="fa-solid fa-bars"></i></div>
          <ul tabindex="0" class="dropdown-content menu bg-base-300 rounded-box z-50 w-52 p-2 shadow-sm">
            <li @click="exportSettings"><a>Export</a></li>
            <li @click="importSettings"><a>Import</a></li>
          </ul>
        </div>
      </div>
    </div>
    <div role="tablist" class="tabs tabs-bordered">
      <button
        class="tab tab-lifted"
        :class="{ 'tab-active': activeTab === 'Settings' }"
        @click="activeTab = 'Settings'"
      >
        General
      </button>
      <button
        class="tab tab-lifted"
        :class="{ 'tab-active': activeTab === 'AI Models' }"
        @click="activeTab = 'AI Models'"
      >
        AI Models
      </button>
      <button
        class="tab tab-lifted"
        :class="{ 'tab-active': activeTab === 'Agents' }"
        @click="activeTab = 'Agents'"
      >
        Agents
      </button>
    </div>
    <div v-if="activeTab === 'Settings'" class="flex flex-col gap-4">
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
            <div class="text-xs">Converts project's documents into embeddings for knowledge search</div>
            <div class="flex flex-col gap-2">
              <div class="flex items-center">
                <span class="p-6 w-1/4">Model:</span>
                <ModelSelector v-model="settings.embeddings_model" />
              </div>
            </div>
            <div class="font-bold">Knowledge search</div>
            <div class="text-xs">Scores knowledge results based on user's request</div>
            <div class="flex flex-col gap-2">
              <div class="flex items-center">
                <span class="p-6 w-1/4">Model:</span>
                <ModelSelector v-model="settings.rag_model" />
              </div>
            </div>
            <div class="font-bold">Reasoning</div>
            <div class="text-xs">Default Reasoning model</div>
            <div class="flex flex-col gap-2">
              <div class="flex items-center">
                <span class="p-6 w-1/4">Model:</span>
                <ModelSelector v-model="settings.llm_model" />
              </div>
            </div>
            <div class="font-bold">WIKI</div>
            <div class="text-xs">Generates wiki documents from project's knowledge</div>
            <div class="flex flex-col gap-2">
              <div class="flex items-center">
                <span class="p-6 w-1/4">Model:</span>
                <ModelSelector v-model="settings.wiki_model" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-if="activeTab === 'AI Models'" class="flex flex-col gap-4">
      <AISettings />
    </div>
    <div v-if="activeTab === 'Agents'" class="flex flex-col gap-4">
      <AgentSettings />
    </div>
    <modal v-if="showImport" :close="true" @close="showImport = false">
      <div class="flex flex-col gap-2">
        <div class="text-xl">Paste your JSON settings here</div>
        <textarea v-model="importData" class="textarea textarea-bordered w-full"></textarea>
        <button class="btn btn-sm btn-primary" @click="submit">Import</button>
      </div>
    </modal>
  </div>
</template>

<script>
export default {
  data () {
    return {
      activeTab: 'Settings',
      settings: null,
      importData: '',
      showImport: false
    }
  },
  created () {
    this.loadSettings()
  },
  methods: {
    async loadSettings() {
      const { data } = await this.$storex.api.settings.global.read()
      this.settings = data
    },
    async saveSettings() {
      await this.$storex.api.settings.global.write(this.settings)
      this.loadSettings()
    },
    reloadSettings() {
      this.loadSettings()
    },
    exportSettings() {
      const settingsText = JSON.stringify(this.settings, null, 2)
      this.$ui.copyTextToClipboard(settingsText)
    },
    importSettings() {
      this.showImport = true
    },
    async submit() {
      try {
        const imported = JSON.parse(this.importData)
        this.settings = { ...this.settings, ...imported }
      } catch (e) {
        console.error('Import failed', e)
      }
      this.showImport = false
    }
  }
}
</script>