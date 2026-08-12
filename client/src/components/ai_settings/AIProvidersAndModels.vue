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
    </div>

    <!-- Providers and Models list -->
    <div class="flex flex-col gap-4">
      <div
        v-for="provider in filteredProviders"
        :key="provider.name"
        class="border border-base-300 rounded-xl bg-base-100 overflow-hidden"
      >
        <!-- Provider header -->
        <div
          class="flex items-center justify-between p-4 bg-base-200 hover:bg-base-300 cursor-pointer transition-colors"
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

        <!-- Provider models (expanded) -->
        <div v-if="expandedProviders.includes(provider.name)" class="border-t border-base-300">
          <!-- Models table for this provider -->
          <div class="overflow-x-auto">
            <table class="table table-sm w-full">
              <thead class="bg-base-200">
                <tr>
                  <th
                    v-for="col in columns"
                    :key="col.key"
                    class="cursor-pointer hover:bg-base-300 transition-colors select-none"
                    :class="col.align === 'right' ? 'text-right' : ''"
                    @click="toggleSort(col.key)"
                  >
                    <div class="flex items-center gap-1" :class="col.align === 'right' ? 'justify-end' : ''">
                      <span>{{ col.label }}</span>
                      <span class="w-3 text-primary">
                        <i v-if="sortKey === col.key" :class="sortAsc ? 'fa-solid fa-sort-up' : 'fa-solid fa-sort-down'"></i>
                        <i v-else class="fa-solid fa-sort text-base-content/20"></i>
                      </span>
                    </div>
                  </th>
                  <th class="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="filteredModelsForProvider(provider).length === 0">
                  <td :colspan="columns.length + 1" class="text-center py-4 text-base-content/40">
                    No models found
                  </td>
                </tr>
                <template v-for="model in filteredModelsForProvider(provider)" :key="model.name">
                  <tr
                    class="hover:bg-base-200 cursor-pointer transition-colors"
                    @click="editModel(model)"
                  >
                    <!-- Name -->
                    <td>
                      <div class="flex items-center gap-2">
                        <div :class="model.model_type === 'llm' ? 'bg-warning/20 text-warning' : 'bg-info/20 text-info'"
                             class="rounded-full w-7 h-7 flex items-center justify-center text-xs shrink-0">
                          <i :class="model.model_type === 'llm' ? 'fa-solid fa-brain' : 'fa-solid fa-file'"></i>
                        </div>
                        <div>
                          <div class="font-semibold text-primary text-sm">{{ model.name }}</div>
                          <div class="text-xs text-base-content/40" v-if="model.ai_model && model.name !== model.ai_model">{{ model.ai_model }}</div>
                        </div>
                      </div>
                    </td>
                    <!-- Type -->
                    <td>
                      <span :class="model.model_type === 'llm' ? 'badge-warning' : 'badge-info'" class="badge badge-xs">
                        {{ model.model_type === 'llm' ? 'LLM' : 'Embeddings' }}
                      </span>
                    </td>
                    <!-- Provider -->
                    <td class="text-sm text-base-content/70">{{ model.ai_provider || '-' }}</td>
                    <!-- Temperature / Vector -->
                    <td class="text-sm text-center">
                      <span v-if="model.model_type === 'llm'">{{ model.settings?.temperature ?? '-' }}</span>
                      <span v-else class="text-xs text-base-content/60">{{ model.settings?.vector_size || '-' }}</span>
                    </td>
                    <!-- Context / Chunk -->
                    <td class="text-sm text-center">
                      <span v-if="model.model_type === 'llm'">{{ model.settings?.context_length ? model.settings.context_length + ' KB' : '-' }}</span>
                      <span v-else class="text-xs text-base-content/60">{{ model.settings?.chunk_size || '-' }}</span>
                    </td>
                    <!-- Model File -->
                    <td class="text-center">
                      <i v-if="model.model_file" class="fa-solid fa-file-code text-secondary text-sm" title="Custom model file"></i>
                      <span v-else class="text-base-content/30 text-xs">-</span>
                    </td>
                    <!-- Cost -->
                    <td class="text-right">
                      <div class="flex flex-col items-end gap-0.5 text-xs">
                        <template v-if="model.input_k_tokens_cxjcoins != null || model.output_k_tokens_cxjcoins != null">
                          <span v-if="model.input_k_tokens_cxjcoins != null" class="text-green-500">
                            ↓ {{ model.input_k_tokens_cxjcoins }}
                          </span>
                          <span v-if="model.output_k_tokens_cxjcoins != null" class="text-blue-500">
                            ↑ {{ model.output_k_tokens_cxjcoins }}
                          </span>
                        </template>
                        <span v-else-if="model.k_tokens_cxjcoins != null" class="text-yellow-500">
                          {{ model.k_tokens_cxjcoins }} /1K
                        </span>
                        <template v-else-if="getProviderPrice(model)">
                          <span class="text-green-400 opacity-80">
                            ↓ ${{ getProviderPrice(model).input_price_per_1k_tokens }}
                          </span>
                          <span class="text-blue-400 opacity-80">
                            ↑ ${{ getProviderPrice(model).output_price_per_1k_tokens }}
                          </span>
                          <span class="text-base-content/30 text-[10px] flex items-center gap-0.5">
                            <i class="fa-solid fa-list-ul"></i> provider
                          </span>
                        </template>
                        <span v-else class="text-base-content/30">-</span>
                      </div>
                    </td>
                    <!-- Actions -->
                    <td @click.stop>
                      <div class="flex justify-end gap-1">
                        <button class="btn btn-xs btn-circle btn-ghost text-info" @click.stop="showModelInfo = model">
                          <i class="fa-solid fa-circle-info"></i>
                        </button>
                        <button class="btn btn-xs btn-circle btn-ghost" @click.stop="editModel(model)">
                          <i class="fa-solid fa-pen-to-square"></i>
                        </button>
                        <!-- Test chat button — only for LLM models -->
                        <button
                          v-if="model.model_type === 'llm'"
                          class="btn btn-xs btn-circle btn-ghost text-success"
                          :class="quickTestModel?.name === model.name && 'text-warning'"
                          @click.stop="toggleQuickTestChat(model)"
                          title="Test chat"
                        >
                          <i class="fa-solid fa-comment-dots"></i>
                        </button>
                        <button
                          class="btn btn-xs btn-circle btn-ghost text-secondary"
                          :class="model.loading && 'animate-pulse text-warning'"
                          @click.stop="reloadModel(model)"
                        >
                          <i class="fa-solid fa-arrows-rotate"></i>
                        </button>
                        <button class="btn btn-xs btn-circle btn-ghost text-error" @click.stop="confirmDeleteModel(model)">
                          <i class="fa-solid fa-trash"></i>
                        </button>
                      </div>
                    </td>
                  </tr>
                  <!-- Inline quick test chat row -->
                  <tr v-if="quickTestModel?.name === model.name && quickTestChat" @click.stop>
                    <td :colspan="columns.length + 1" class="p-0">
                      <div class="bg-base-200 border-t border-base-300 flex flex-col" style="height: 420px">
                        <div class="flex items-center gap-2 px-3 py-2 bg-base-300 text-xs text-base-content/60">
                          <i class="fa-solid fa-comment-dots text-success"></i>
                          <span class="font-semibold">Testing: <span class="text-primary">{{ model.name }}</span></span>
                          <button class="btn btn-xs btn-ghost ml-auto text-error" @click.stop="closeQuickTestChat">
                            <i class="fa-solid fa-xmark"></i> Close
                          </button>
                        </div>
                        <div class="grow min-h-0 p-2">
                          <Chat :chat="quickTestChat"/>
                        </div>
                      </div>
                    </td>
                  </tr>
                </template>

                <!-- Add new model row -->
                <tr class="hover:bg-base-200 cursor-pointer transition-colors" @click="addModelForProvider(provider)">
                  <td colspan="7" class="py-3 text-center">
                    <div class="flex items-center justify-center gap-2 text-primary/70 hover:text-primary">
                      <i class="fa-solid fa-plus"></i>
                      Add new model for {{ provider.name }}
                    </div>
                  </td>
                  <td class="text-right"></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Add new provider row -->
      <div
        class="flex items-center justify-center gap-2 p-4 border border-dashed border-base-300 rounded-xl text-primary/70 hover:text-primary cursor-pointer transition-colors"
        @click="editProvider({})"
      >
        <i class="fa-solid fa-plus"></i>
        Add new provider
      </div>
    </div>

    <!-- Edit modal -->
    <modal class="w-2/3 h-5/6 overflow-auto" v-if="showDialog">
      <AIProviderSettings
        :model-value="currentProvider"
        @save="saveProvider"
        @cancel="showDialog = false"
        @delete="confirmDelete"
      />
    </modal>

    <!-- Edit model modal -->
    <modal class="w-2/3 h-5/6 overflow-auto" v-if="showModelDialog">
      <AIModelSettings
        :aiProviders="aiProviders"
        :model="currentModel"
        @save="saveModel"
        @cancel="showModelDialog = false"
        @delete="confirmDeleteModel"
      />
    </modal>

    <!-- Info modal -->
    <modal class="w-1/3 h-2/3" close="true" @close="showModelInfo = null" v-if="showModelInfo">
      <div class="flex items-center gap-2 mb-3">
        <i class="fa-solid fa-circle-info text-info"></i>
        <div class="text-xl font-bold">{{ showModelInfo.name }}</div>
      </div>
      <pre class="overflow-auto text-xs bg-base-300 p-3 rounded-lg">{{ showModelInfo.metadata?.info }}</pre>
    </modal>

    <!-- Delete confirm modal -->
    <modal v-if="showDeleteDialog">
      <div class="flex flex-col gap-4">
        <div class="flex items-center gap-2 text-error">
          <i class="fa-solid fa-triangle-exclamation text-xl"></i>
          <span class="font-bold text-lg">Confirm Delete</span>
        </div>
        <p class="text-sm">Are you sure you want to delete <strong>{{ providerToDelete?.name }}</strong>?</p>
        <div class="flex justify-end gap-2">
          <button class="btn btn-ghost btn-sm" @click="showDeleteDialog = false">Cancel</button>
          <button class="btn btn-error btn-sm" @click="deleteProvider">
            <i class="fa-solid fa-trash-can mr-1"></i> Delete
          </button>
        </div>
      </div>
    </modal>

    <!-- Delete model confirm modal -->
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

    <!-- Iframe admin view -->
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
      currentProvider: {},
      providerToDelete: null,
      currentModel: null,
      modelToDelete: null,
      showModelInfo: null,
      adminUrl: null,
      globalFilterText: '',
      expandedProviders: [],
      sortKey: 'name',
      sortAsc: true,
      quickTestModel: null,
      quickTestChat: null,
      columns: [
        { key: 'name', label: 'Model' },
        { key: 'model_type', label: 'Type' },
        { key: 'ai_provider', label: 'Provider' },
        { key: 'temperature', label: 'Temp / Vector', align: 'center' },
        { key: 'context', label: 'Context / Chunk', align: 'center' },
        { key: 'model_file', label: 'File', align: 'center' },
        { key: 'cost', label: 'Cost (cxj)', align: 'right' }
      ]
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
    }
  },
  mounted() {
    // Expand all providers by default
    this.expandedProviders = (this.aiProviders || []).map(p => p.name)
  },
  methods: {
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
    // Mask API key: show first 6 and last 5 chars, hide middle with dots
    maskApiKey(key) {
      if (!key || key.length < 11) return key.slice(0, 6) + '•'.repeat(Math.max(0, key.length - 6))
      const first = key.slice(0, 6)
      const last = key.slice(-5)
      const hiddenLength = key.length - 11
      return `${first}${'•'.repeat(4)}${last}`
    },
    // Count how many models are assigned to a given provider name
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
    toggleSort(key) {
      if (this.sortKey === key) {
        this.sortAsc = !this.sortAsc
      } else {
        this.sortKey = key
        this.sortAsc = true
      }
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
      const idx = this.aiProviders.findIndex(p => p.name === this.providerToDelete.name)
      if (idx !== -1) {
        this.aiProviders.splice(idx, 1)
      }
      this.showDeleteDialog = false
      // Remove the provider from expandedProviders if needed
      const index = this.expandedProviders.indexOf(this.providerToDelete.name)
      if (index !== -1) {
        this.expandedProviders.splice(index, 1)
      }
    },
    addModelForProvider(provider) {
      const model = {
        ai_provider: provider.name,
        settings: {},
        k_tokens_cxjcoins: null,
        input_k_tokens_cxjcoins: null,
        output_k_tokens_cxjcoins: null,
        model_file: null
      }
      this.currentModel = model
      this.showModelDialog = true
    },
    editModel(model) {
      this.currentModel = model
      this.showModelDialog = true
    },
    saveModel() {
      // Save the model - will be handled by AIModelSettings component
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
  }
}
</script>