<script setup>
import Iframe from '../Iframe.vue'
import AIProviderSettings from './AIProviderSettings.vue'
import AIModelSettings from './AIModelSettings.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-4 p-4">
    <!-- Global filter bar -->
    <div class="flex flex-wrap gap-2 items-center bg-base-200 rounded-xl p-3">
      <div class="relative grow min-w-48">
        <i class="fa-solid fa-search absolute left-3 top-1/2 -translate-y-1/2 text-base-content/40 text-xs"></i>
        <input
          v-model="globalFilterText"
          type="text"
          placeholder="Search providers and models..."
          class="input input-sm input-bordered w-full pl-8 bg-base-100"
        />
      </div>
      <div class="badge badge-outline badge-sm">CARD GRID VIEW</div>
      <div class="flex gap-2 ml-auto">
        <button
          class="btn btn-sm btn-ghost gap-1"
          :class="loading && 'loading'"
          :disabled="loading || saving"
          @click="reloadSettings"
          title="Reload from server"
        >
          <i class="fa-solid fa-arrows-rotate"></i> Reload
        </button>
        <button
          class="btn btn-sm btn-ghost gap-1"
          :disabled="loading || saving"
          @click="showHistoryDialog = true"
          title="View version history"
        >
          <i class="fa-solid fa-history"></i> History
        </button>
        <button
          class="btn btn-sm btn-primary gap-1"
          :class="saving && 'loading'"
          :disabled="loading || saving"
          @click="saveSettings"
        >
          <i class="fa-solid fa-floppy-disk"></i> Save Changes
        </button>
      </div>
    </div>

    <!-- Providers and Models list -->
    <div class="flex flex-col gap-6">
      <div
        v-for="provider in filteredProviders"
        :key="provider.name"
        class="space-y-3"
      >
        <!-- Provider header -->
        <div
          class="flex items-center justify-between px-4 py-3 bg-base-200 hover:bg-base-300 cursor-pointer transition-colors rounded-xl"
          @click="toggleProvider(provider)"
        >
          <div class="flex items-center gap-3">
            <i
              :class="expandedProviders.includes(provider.name) ? 'fa-solid fa-chevron-down' : 'fa-solid fa-chevron-right'"
              class="text-base-content/50 w-4"
            ></i>
            <div class="flex items-center gap-2">
              <div class="bg-primary/10 text-primary rounded-lg w-8 h-8 flex items-center justify-center text-xs font-bold shrink-0">
                {{ provider.name?.charAt(0)?.toUpperCase() }}
              </div>
              <div>
                <div class="font-semibold text-primary">{{ provider.name }}</div>
                <div class="badge badge-ghost badge-xs font-mono mt-0.5">{{ provider.provider }}</div>
              </div>
            </div>
          </div>
          
          <div class="flex items-center gap-2">
            <div class="text-xs text-base-content/60">
              {{ getModelCount(provider) }} models
            </div>
            <button
              v-if="provider.admin_url"
              class="btn btn-xs btn-circle btn-ghost text-info"
              @click.stop="navigateAdmin(provider)"
              title="Admin Panel"
            >
              <i class="fa-solid fa-link"></i>
            </button>
            <button class="btn btn-xs btn-circle btn-ghost" @click.stop="editProvider(provider)">
              <i class="fa-solid fa-pen-to-square"></i>
            </button>
            <button class="btn btn-xs btn-circle btn-ghost text-error" @click.stop="confirmDelete(provider)">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </div>

        <!-- Provider models grid (expanded) -->
        <div v-if="expandedProviders.includes(provider.name)">
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <!-- Model Card -->
            <div
              v-for="model in filteredModelsForProvider(provider)"
              :key="model.name"
              class="card bg-base-100 border border-base-300 hover:border-primary/50 transition-all hover:shadow-lg cursor-pointer group"
              @click="editModel(model)"
            >
              <div class="card-body p-4 gap-3">
                <!-- Header: Icon + Type Badge -->
                <div class="flex items-start justify-between">
                  <div :class="model.model_type === 'llm' ? 'bg-warning/20 text-warning' : 'bg-info/20 text-info'"
                       class="rounded-lg w-10 h-10 flex items-center justify-center text-lg shrink-0">
                    <i :class="model.model_type === 'llm' ? 'fa-solid fa-brain' : 'fa-solid fa-file'"></i>
                  </div>
                  <span :class="model.model_type === 'llm' ? 'badge-warning' : 'badge-info'" class="badge badge-sm">
                    {{ model.model_type === 'llm' ? 'LLM' : 'Embed' }}
                  </span>
                </div>

                <!-- Model Name (Primary) -->
                <div>
                  <h3 class="font-bold text-base leading-tight text-primary line-clamp-2">{{ model.name }}</h3>
                  <p v-if="model.ai_model && model.name !== model.ai_model" class="text-xs text-base-content/50 mt-1 line-clamp-1 font-mono">
                    {{ model.ai_model }}
                  </p>
                </div>

                <!-- Quick Stats -->
                <div class="grid grid-cols-2 gap-2 text-xs bg-base-200/50 rounded-lg p-2">
                  <div>
                    <div class="text-base-content/60">{{ model.model_type === 'llm' ? 'Temp' : 'Vector' }}</div>
                    <div class="font-semibold text-base-content">{{ model.model_type === 'llm' ? model.settings?.temperature ?? '-' : model.settings?.vector_size || '-' }}</div>
                  </div>
                  <div>
                    <div class="text-base-content/60">{{ model.model_type === 'llm' ? 'Context' : 'Chunk' }}</div>
                    <div class="font-semibold text-base-content">{{ model.model_type === 'llm' ? (model.settings?.context_length ? model.settings.context_length + ' KB' : '-') : model.settings?.chunk_size || '-' }}</div>
                  </div>
                </div>

                <!-- Cost -->
                <div class="text-xs text-right space-y-0.5 bg-base-200/30 rounded-lg p-2">
                  <template v-if="model.input_k_tokens_cxjcoins != null">
                    <div class="text-green-500">↓ {{ model.input_k_tokens_cxjcoins }}</div>
                    <div class="text-blue-500">↑ {{ model.output_k_tokens_cxjcoins }}</div>
                  </template>
                  <template v-else-if="model.k_tokens_cxjcoins != null">
                    <div class="text-yellow-500 font-semibold">{{ model.k_tokens_cxjcoins }} /1K</div>
                  </template>
                  <template v-else-if="getProviderPrice(model)">
                    <div class="text-green-400">↓ ${{ getProviderPrice(model).input_price_per_1k_tokens }}</div>
                    <div class="text-blue-400">↑ ${{ getProviderPrice(model).output_price_per_1k_tokens }}</div>
                  </template>
                  <div v-else class="text-base-content/30">-</div>
                </div>

                <!-- Custom model file indicator -->
                <div v-if="model.model_file" class="flex items-center gap-1 text-secondary text-xs">
                  <i class="fa-solid fa-file-code"></i>
                  Custom file
                </div>

                <!-- Actions -->
                <div class="flex gap-1 mt-2 pt-2 border-t border-base-300 justify-end opacity-0 group-hover:opacity-100 transition-opacity" @click.stop>
                  <button class="btn btn-xs btn-circle btn-ghost text-info" @click.stop="showModelInfo = model" title="Info">
                    <i class="fa-solid fa-circle-info"></i>
                  </button>
                  <button class="btn btn-xs btn-circle btn-ghost" @click.stop="editModel(model)" title="Edit">
                    <i class="fa-solid fa-pen-to-square"></i>
                  </button>
                  <button
                    v-if="model.model_type === 'llm'"
                    class="btn btn-xs btn-circle btn-ghost text-success"
                    :class="quickTestModel?.name === model.name && 'text-warning'"
                    @click.stop="toggleQuickTestChat(model)"
                    title="Test"
                  >
                    <i class="fa-solid fa-comment-dots"></i>
                  </button>
                  <button
                    class="btn btn-xs btn-circle btn-ghost text-secondary"
                    :class="model.loading && 'animate-pulse text-warning'"
                    @click.stop="reloadModel(model)"
                    title="Reload"
                  >
                    <i class="fa-solid fa-arrows-rotate"></i>
                  </button>
                  <button class="btn btn-xs btn-circle btn-ghost text-error" @click.stop="confirmDeleteModel(model)" title="Delete">
                    <i class="fa-solid fa-trash"></i>
                  </button>
                </div>
              </div>
            </div>

            <!-- Add new model card -->
            <div
              class="card bg-base-100 border-2 border-dashed border-base-300 hover:border-primary/50 transition-colors hover:bg-base-200 cursor-pointer flex items-center justify-center min-h-64"
              @click="addModelForProvider(provider)"
            >
              <div class="flex flex-col items-center justify-center text-primary/70 hover:text-primary gap-2">
                <i class="fa-solid fa-plus text-2xl"></i>
                <span class="text-sm font-semibold">Add Model</span>
              </div>
            </div>
          </div>

          <!-- Quick test chat for provider -->
          <div v-if="quickTestModel?.ai_provider === provider.name && quickTestChat" class="mt-6 card bg-base-200 border border-base-300">
            <div class="card-body p-4">
              <div class="flex items-center gap-2 mb-4">
                <i class="fa-solid fa-comment-dots text-success"></i>
                <span class="font-semibold">Testing: <span class="text-primary">{{ quickTestModel.name }}</span></span>
                <button class="btn btn-xs btn-ghost ml-auto text-error" @click="closeQuickTestChat">
                  <i class="fa-solid fa-xmark"></i> Close
                </button>
              </div>
              <div style="height: 400px" class="overflow-hidden">
                <Chat :chat="quickTestChat"/>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Add new provider -->
      <div
        class="flex items-center justify-center gap-2 p-4 border-2 border-dashed border-base-300 rounded-xl text-primary/70 hover:text-primary cursor-pointer transition-colors"
        @click="editProvider({})"
      >
        <i class="fa-solid fa-plus"></i>
        Add new provider
      </div>
    </div>

    <!-- Modals (identical to variant 1) -->
    <modal class="w-2/3 h-5/6 overflow-auto" v-if="showDialog">
      <AIProviderSettings
        :model-value="currentProvider"
        @save="saveProvider"
        @cancel="showDialog = false"
        @delete="confirmDelete"
      />
    </modal>

    <modal class="w-2/3 h-5/6 overflow-auto" v-if="showModelDialog">
      <AIModelSettings
        :aiProviders="aiProviders"
        :model="currentModel"
        @save="saveModel"
        @cancel="showModelDialog = false"
        @delete="confirmDeleteModel"
      />
    </modal>

    <modal class="w-1/3 h-2/3" close="true" @close="showModelInfo = null" v-if="showModelInfo">
      <div class="flex items-center gap-2 mb-3">
        <i class="fa-solid fa-circle-info text-info"></i>
        <div class="text-xl font-bold">{{ showModelInfo.name }}</div>
      </div>
      <pre class="overflow-auto text-xs bg-base-300 p-3 rounded-lg">{{ showModelInfo.metadata?.info }}</pre>
    </modal>

    <modal v-if="showDeleteDialog">
      <div class="flex flex-col gap-4">
        <div class="flex items-center gap-2 text-error">
          <i class="fa-solid fa-triangle-exclamation text-xl"></i>
          <span class="font-bold text-lg">Confirm Delete</span>
        </div>
        <p class="text-sm">Are you sure you want to delete <strong>{{ providerToDelete?.name }}</strong>?</p>
        <p v-if="modelsCount > 0" class="text-sm text-warning">
          <i class="fa-solid fa-info-circle mr-1"></i>
          This will also delete <strong>{{ modelsCount }}</strong> associated model(s).
        </p>
        <div class="flex justify-end gap-2">
          <button class="btn btn-ghost btn-sm" @click="showDeleteDialog = false">Cancel</button>
          <button class="btn btn-error btn-sm" @click="deleteProvider">
            <i class="fa-solid fa-trash-can mr-1"></i> Delete
          </button>
        </div>
      </div>
    </modal>

    <modal v-if="showDeleteModelDialog">
      <div class="flex flex-col gap-4">
        <div class="flex items-center gap-2 text-error">
          <i class="fa-solid fa-triangle-exclamation text-xl"></i>
          <span class="font-bold text-lg">Confirm Delete</span>
        </div>
        <p class="text-sm">Are you sure you want to delete <strong>{{ modelToDelete?.name }}</strong>?</p>
        <div class="flex justify-end gap-2">
          <button class="btn btn-ghost btn-sm" @click="showDeleteModelDialog = false">Cancel</button>
          <button class="btn btn-error btn-sm" @click="deleteModel">
            <i class="fa-solid fa-trash-can mr-1"></i> Delete
          </button>
        </div>
      </div>
    </modal>

    <modal class="w-2/3 h-4/5 overflow-auto" v-if="showHistoryDialog" close="true" @close="showHistoryDialog = false">
      <div class="flex flex-col gap-4">
        <div class="flex items-center gap-2">
          <i class="fa-solid fa-history text-info"></i>
          <h2 class="text-xl font-bold">Version History</h2>
        </div>

        <div class="divider my-2">Providers</div>
        <div v-if="providersHistory.length === 0" class="text-base-content/50 text-sm">No history available</div>
        <div v-else class="flex flex-col gap-2">
          <div
            v-for="version in providersHistory"
            :key="version.timestamp"
            class="flex items-center justify-between p-3 bg-base-200 rounded-lg hover:bg-base-300 transition-colors"
          >
            <div>
              <div class="font-semibold text-sm">{{ formatDate(version.timestamp) }}</div>
              <div class="text-xs text-base-content/60">{{ version.timestamp }}</div>
            </div>
            <button
              class="btn btn-xs btn-ghost"
              @click="rollbackProviders(version.timestamp)"
              :disabled="loadingHistory"
            >
              <i class="fa-solid fa-reply"></i> Rollback
            </button>
          </div>
        </div>

        <div class="divider my-2">Models</div>
        <div v-if="modelsHistory.length === 0" class="text-base-content/50 text-sm">No history available</div>
        <div v-else class="flex flex-col gap-2">
          <div
            v-for="version in modelsHistory"
            :key="version.timestamp"
            class="flex items-center justify-between p-3 bg-base-200 rounded-lg hover:bg-base-300 transition-colors"
          >
            <div>
              <div class="font-semibold text-sm">{{ formatDate(version.timestamp) }}</div>
              <div class="text-xs text-base-content/60">{{ version.timestamp }}</div>
            </div>
            <button
              class="btn btn-xs btn-ghost"
              @click="rollbackModels(version.timestamp)"
              :disabled="loadingHistory"
            >
              <i class="fa-solid fa-reply"></i> Rollback
            </button>
          </div>
        </div>
      </div>
    </modal>

    <modal class="w-5/6 h-5/6" v-if="adminUrl" close="true" @close="adminUrl = null">
      <Iframe :url="adminUrl" />
    </modal>
  </div>
</template>

<script>
export default {
  props: ['settings'],
  data() {
    return {
      showDialog: false,
      showModelDialog: false,
      showDeleteDialog: false,
      showDeleteModelDialog: false,
      showHistoryDialog: false,
      currentProvider: {},
      providerToDelete: null,
      currentModel: null,
      modelToDelete: null,
      showModelInfo: null,
      adminUrl: null,
      globalFilterText: '',
      expandedProviders: [],
      quickTestModel: null,
      quickTestChat: null,
      loading: false,
      saving: false,
      loadingHistory: false,
      providersHistory: [],
      modelsHistory: []
    }
  },
  computed: {
    aiProviders() {
      return this.settings.ai_providers || []
    },
    aiModels() {
      return this.settings.ai_models || []
    },
    filteredProviders() {
      if (!this.globalFilterText) {
        return this.aiProviders
      }
      
      const q = this.globalFilterText.toLowerCase()
      return this.aiProviders.filter(p => 
        p.name?.toLowerCase().includes(q) ||
        p.provider?.toLowerCase().includes(q) ||
        p.api_url?.toLowerCase().includes(q)
      )
    },
    filteredModels() {
      if (!this.globalFilterText) {
        return this.aiModels
      }
      
      const q = this.globalFilterText.toLowerCase()
      return this.aiModels.filter(m => 
        m.name?.toLowerCase().includes(q) ||
        m.ai_model?.toLowerCase().includes(q) ||
        m.ai_provider?.toLowerCase().includes(q)
      )
    },
    modelsCount() {
      if (!this.providerToDelete) return 0
      return this.aiModels.filter(m => m.ai_provider === this.providerToDelete.name).length
    }
  },
  async mounted() {
    await this.loadSettings()
  },
  methods: {
    async loadSettings() {
      this.loading = true
      try {
        const [providers, models] = await Promise.all([
          this.$storex.api.settings.global.section('ai_providers'),
          this.$storex.api.settings.global.section('ai_models')
        ])
        this.settings.ai_providers = providers || []
        this.settings.ai_models = models || []
        this.expandedProviders = (this.aiProviders || []).map(p => p.name)
      } catch (err) {
        console.error('Failed to load settings:', err)
        this.$toast.error('Failed to load settings')
      } finally {
        this.loading = false
      }
    },
    async saveSettings() {
      this.saving = true
      try {
        await Promise.all([
          this.$storex.api.settings.global.saveSection('ai_providers', this.aiProviders),
          this.$storex.api.settings.global.saveSection('ai_models', this.aiModels)
        ])
        this.$toast.success('Settings saved successfully')
      } catch (err) {
        console.error('Failed to save settings:', err)
        this.$toast.error('Failed to save settings')
      } finally {
        this.saving = false
      }
    },
    async reloadSettings() {
      await this.loadSettings()
      this.$toast.success('Settings reloaded')
    },
    async loadHistory() {
      this.loadingHistory = true
      try {
        const [providersHist, modelsHist] = await Promise.all([
          this.$storex.api.settings.global.history('ai_providers'),
          this.$storex.api.settings.global.history('ai_models')
        ])
        this.providersHistory = providersHist || []
        this.modelsHistory = modelsHist || []
      } catch (err) {
        console.error('Failed to load history:', err)
        this.$toast.error('Failed to load history')
      } finally {
        this.loadingHistory = false
      }
    },
    async rollbackProviders(timestamp) {
      try {
        await this.$storex.api.settings.global.rollback('ai_providers', timestamp)
        await this.loadSettings()
        this.$toast.success('Providers rolled back successfully')
        this.showHistoryDialog = false
      } catch (err) {
        console.error('Failed to rollback providers:', err)
        this.$toast.error('Failed to rollback')
      }
    },
    async rollbackModels(timestamp) {
      try {
        await this.$storex.api.settings.global.rollback('ai_models', timestamp)
        await this.loadSettings()
        this.$toast.success('Models rolled back successfully')
        this.showHistoryDialog = false
      } catch (err) {
        console.error('Failed to rollback models:', err)
        this.$toast.error('Failed to rollback')
      }
    },
    formatDate(timestamp) {
      try {
        return new Date(timestamp).toLocaleString()
      } catch {
        return timestamp
      }
    },
    toggleProvider(provider) {
      const index = this.expandedProviders.indexOf(provider.name)
      if (index === -1) {
        this.expandedProviders.push(provider.name)
      } else {
        this.expandedProviders.splice(index, 1)
      }
    },
    filteredModelsForProvider(provider) {
      return this.filteredModels.filter(m => m.ai_provider === provider.name)
    },
    getModelCount(provider) {
      const models = this.aiModels.filter(m => m.ai_provider === provider.name).length
      const modelList = (provider.price_list || []).length
      return `${models} / ${modelList}`
    },
    getProviderPrice(model) {
      const provider = (this.aiProviders || []).find(p => p.name === model.ai_provider)
      if (!provider?.price_list?.length) return null
      const lookupName = model.ai_model || model.name
      return provider.price_list.find(entry => entry.model_name === lookupName) || null
    },
    editProvider(provider) {
      this.currentProvider = { ...provider }
      this.showDialog = true
    },
    saveProvider(updated) {
      const idx = this.aiProviders.findIndex(p => p.name === updated.name)
      if (idx !== -1) {
        this.aiProviders.splice(idx, 1, updated)
      } else {
        this.aiProviders.push(updated)
      }
      this.showDialog = false
    },
    confirmDelete(provider) {
      this.providerToDelete = provider
      this.showDeleteDialog = true
    },
    deleteProvider() {
      const providerName = this.providerToDelete.name
      const idx = this.aiProviders.findIndex(p => p.name === providerName)
      if (idx !== -1) {
        this.aiProviders.splice(idx, 1)
      }
      const modelsToDelete = this.aiModels.filter(m => m.ai_provider === providerName)
      modelsToDelete.forEach(model => {
        const modelIdx = this.aiModels.indexOf(model)
        if (modelIdx !== -1) {
          this.aiModels.splice(modelIdx, 1)
        }
      })
      this.showDeleteDialog = false
      const expandIdx = this.expandedProviders.indexOf(providerName)
      if (expandIdx !== -1) {
        this.expandedProviders.splice(expandIdx, 1)
      }
    },
    addModelForProvider(provider) {
      const model = {
        name: '',
        ai_provider: provider.name,
        ai_model: '',
        model_type: 'llm',
        settings: {
          temperature: 0.7,
          context_length: 2048,
          merge_messages: false,
          vector_size: 1536,
          chunk_size: 8190
        },
        system: '',
        prompt_template: '',
        model_file: null,
        url: '',
        k_tokens_cxjcoins: null,
        input_k_tokens_cxjcoins: null,
        output_k_tokens_cxjcoins: null
      }
      this.currentModel = model
      this.showModelDialog = true
    },
    editModel(model) {
      this.currentModel = { ...model }
      this.showModelDialog = true
    },
    saveModel(model) {
      const existingIdx = this.aiModels.findIndex(m => m.name === model.name)
      
      if (existingIdx !== -1) {
        this.aiModels.splice(existingIdx, 1, model)
      } else {
        this.aiModels.push(model)
      }
      
      this.showModelDialog = false
    },
    confirmDeleteModel(model) {
      this.modelToDelete = model
      this.showDeleteModelDialog = true
    },
    deleteModel() {
      const index = this.aiModels.findIndex(m => m.name === this.modelToDelete.name)
      if (index !== -1) this.aiModels.splice(index, 1)
      this.showDeleteModelDialog = false
    },
    navigateAdmin(provider) {
      this.adminUrl = provider.admin_url
    },
    async reloadModel(model) {
      model.loading = true
      try {
        const info = await this.$storex.api.projects.ai.models.reload(model)
        model.metadata = { ...model.metadata || {}, info }
        this.showModelInfo = model
      } finally {
        model.loading = false
      }
    },
    async toggleQuickTestChat(model) {
      if (this.quickTestModel?.name === model.name) {
        this.closeQuickTestChat()
        return
      }
      this.quickTestModel = model
      this.quickTestChat = null
      try {
        const chat = await this.$chats.createNewChat({
          name: `Test: ${model.name}`,
          llm_model: model.name,
          temp: true,
          test: true
        })
        chat.llm_model = model.name
        this.quickTestChat = chat
      } catch (err) {
        console.error('Failed to create quick test chat', err)
        this.quickTestModel = null
      }
    },
    closeQuickTestChat() {
      this.quickTestModel = null
      this.quickTestChat = null
    }
  },
  watch: {
    showHistoryDialog(newVal) {
      if (newVal) {
        this.loadHistory()
      }
    }
  }
}
</script>