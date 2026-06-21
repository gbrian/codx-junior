<script setup>
import AIModelSettings from './AIModelSettings.vue'
import Chat from '../chat/Chat.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-4 p-4">
    <!-- Page header -->
    <div class="flex items-center gap-3 bg-gradient-to-r from-primary/20 to-transparent rounded-xl px-4 py-3">
      <div class="avatar placeholder">
        <div class="bg-primary text-primary-content rounded-full w-10 h-10 flex items-center justify-center">
          <i class="fa-solid fa-brain text-lg"></i>
        </div>
      </div>
      <div class="grow">
        <div class="font-bold text-xl">AI Models</div>
        <div class="text-xs text-base-content/50">{{ filteredModels.length }} of {{ aiModels.length }} model(s)</div>
      </div>
      <button class="btn btn-primary btn-sm gap-2" @click="editModel(null)">
        <i class="fa-solid fa-plus"></i> Add Model
      </button>
    </div>

    <!-- Filter bar -->
    <div class="flex flex-wrap gap-2 items-center bg-base-200 rounded-xl p-3">
      <div class="relative grow min-w-48">
        <i class="fa-solid fa-search absolute left-3 top-1/2 -translate-y-1/2 text-base-content-ERROR-40 text-xs"></i>
        <input
          v-model="filterText"
          type="text"
          placeholder="Search models..."
          class="input input-sm input-bordered w-full pl-8 bg-base-100"
        />
      </div>
      <select v-model="filterType" class="select select-sm select-bordered bg-base-100">
        <option value="">All Types</option>
        <option value="llm">LLM</option>
        <option value="embeddings">Embeddings</option>
      </select>
      <select v-model="filterProvider" class="select select-sm select-bordered bg-base-100">
        <option value="">All Providers</option>
        <option v-for="p in uniqueProviders" :key="p" :value="p">{{ p }}</option>
      </select>
      <button v-if="hasFilters" class="btn btn-ghost btn-sm gap-1 text-error" @click="clearFilters">
        <i class="fa-solid fa-xmark"></i> Clear
      </button>
    </div>

    <!-- Table -->
    <div class="overflow-x-auto rounded-xl border border-base-300 bg-base-100">
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
          <tr v-if="filteredModels.length === 0">
            <td :colspan="columns.length + 1" class="text-center py-10 text-base-content-ERROR-40">
              <i class="fa-solid fa-ghost text-2xl mb-2 block"></i>
              No models found
            </td>
          </tr>
          <template v-for="model in filteredModels" :key="model.name">
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
                    <div class="text-xs text-base-content-ERROR-40" v-if="model.ai_model && model.name !== model.ai_model">{{ model.ai_model }}</div>
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
                  <button class="btn btn-xs btn-circle btn-ghost text-info" @click="showModelInfo = model">
                    <i class="fa-solid fa-circle-info"></i>
                  </button>
                  <button class="btn btn-xs btn-circle btn-ghost" @click="editModel(model)">
                    <i class="fa-solid fa-pen-to-square"></i>
                  </button>
                  <!-- Test chat button — only for LLM models -->
                  <button
                    v-if="model.model_type === 'llm'"
                    class="btn btn-xs btn-circle btn-ghost text-success"
                    :class="quickTestModel?.name === model.name && 'text-warning'"
                    @click="toggleQuickTestChat(model)"
                    title="Test chat"
                  >
                    <i class="fa-solid fa-comment-dots"></i>
                  </button>
                  <button
                    class="btn btn-xs btn-circle btn-ghost text-secondary"
                    :class="model.loading && 'animate-pulse text-warning'"
                    @click="reloadModel(model)"
                  >
                    <i class="fa-solid fa-arrows-rotate"></i>
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
                    <button class="btn btn-xs btn-ghost ml-auto text-error" @click="closeQuickTestChat">
                      <i class="fa-solid fa-xmark"></i> Close
                    </button>
                  </div>
                  <Chat class="grow min-h-0 p-2" :chat="quickTestChat" />
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Edit modal -->
    <modal class="w-2/3 h-5/6 overflow-auto" v-if="showDialog">
      <AIModelSettings
        :aiProviders="aiProviders"
        :model="currentModel"
        @save="saveModel"
        @cancel="showDialog = false"
        @delete="confirmDelete"
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
        <p class="text-sm">Are you sure you want to delete <strong>{{ modelToDelete?.name }}</strong>?</p>
        <div class="flex justify-end gap-2">
          <button class="btn btn-ghost btn-sm" @click="showDeleteDialog = false">Cancel</button>
          <button class="btn btn-error btn-sm" @click="deleteModel">
            <i class="fa-solid fa-trash-can mr-1"></i> Delete
          </button>
        </div>
      </div>
    </modal>
  </div>
</template>

<script>
export default {
  props: ['settings'],
  data() {
    return {
      showDialog: false,
      showDeleteDialog: false,
      currentModel: null,
      modelToDelete: null,
      showModelInfo: null,
      filterText: '',
      filterType: '',
      filterProvider: '',
      sortKey: 'name',
      sortAsc: true,
      // Quick inline test chat
      quickTestModel: null,
      quickTestChat: null,
      columns: [
        { key: 'name', label: 'Model' },
        { key: 'model_type', label: 'Type' },
        { key: 'ai_provider', label: 'Provider' },
        { key: 'temperature', label: 'Temp / Vector', align: 'center' },
        { key: 'context', label: 'Context / Chunk', align: 'center' },
        { key: 'cost', label: 'Cost (cxj)', align: 'right' },
      ]
    }
  },
  computed: {
    aiModels() {
      return this.settings.ai_models
    },
    aiProviders() {
      return this.settings.ai_providers
    },
    uniqueProviders() {
      return [...new Set(this.aiModels.map(m => m.ai_provider).filter(Boolean))]
    },
    hasFilters() {
      return this.filterText || this.filterType || this.filterProvider
    },
    filteredModels() {
      let list = [...this.aiModels]
      if (this.filterText) {
        const q = this.filterText.toLowerCase()
        list = list.filter(m =>
          m.name?.toLowerCase().includes(q) ||
          m.ai_model?.toLowerCase().includes(q) ||
          m.ai_provider?.toLowerCase().includes(q)
        )
      }
      if (this.filterType) list = list.filter(m => m.model_type === this.filterType)
      if (this.filterProvider) list = list.filter(m => m.ai_provider === this.filterProvider)
      list.sort((a, b) => {
        const av = this.getSortValue(a)
        const bv = this.getSortValue(b)
        if (av < bv) return this.sortAsc ? -1 : 1
        if (av > bv) return this.sortAsc ? 1 : -1
        return 0
      })
      return list
    }
  },
  methods: {
    getProviderPrice(model) {
      const provider = (this.aiProviders || []).find(p => p.name === model.ai_provider)
      if (!provider?.price_list?.length) return null
      const lookupName = model.ai_model || model.name
      return provider.price_list.find(entry => entry.model_name === lookupName) || null
    },
    getSortValue(model) {
      const map = {
        name: model.name?.toLowerCase() || '',
        model_type: model.model_type || '',
        ai_provider: model.ai_provider?.toLowerCase() || '',
        temperature: model.settings?.temperature ?? 0,
        context: model.settings?.context_length ?? model.settings?.vector_size ?? 0,
        cost: model.k_tokens_cxjcoins ?? model.input_k_tokens_cxjcoins ?? 0
      }
      return map[this.sortKey] ?? ''
    },
    toggleSort(key) {
      if (this.sortKey === key) {
        this.sortAsc = !this.sortAsc
      } else {
        this.sortKey = key
        this.sortAsc = true
      }
    },
    clearFilters() {
      this.filterText = ''
      this.filterType = ''
      this.filterProvider = ''
    },
    editModel(model) {
      if (!model) {
        model = { settings: {}, k_tokens_cxjcoins: null, input_k_tokens_cxjcoins: null, output_k_tokens_cxjcoins: null }
        this.aiModels.push(model)
      }
      this.currentModel = model
      this.showDialog = true
    },
    saveModel() {
      this.showDialog = false
    },
    confirmDelete(model) {
      this.showDialog = false
      this.modelToDelete = model
      this.showDeleteDialog = true
    },
    deleteModel() {
      const index = this.aiModels.findIndex(m => m.name === this.modelToDelete.name)
      if (index !== -1) this.aiModels.splice(index, 1)
      this.showDeleteDialog = false
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
    // Toggle inline test chat for a model row
    async toggleQuickTestChat(model) {
      // Close if same model clicked again
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
        // Ensure model is assigned
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