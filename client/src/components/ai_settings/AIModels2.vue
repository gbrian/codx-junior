<script setup>
import AIModelSettings from './AIModelSettings.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-3 p-4 font-mono text-sm">
    <!-- Header -->
    <div class="flex items-center justify-between border-b border-primary/30 pb-3">
      <div class="flex items-center gap-3">
        <i class="fa-solid fa-table-list text-primary text-xl"></i>
        <span class="font-bold text-lg tracking-tight">AI Model Registry</span>
        <div class="badge badge-primary badge-outline">{{ filteredModels.length }} / {{ aiModels.length }}</div>
      </div>
      <button class="btn btn-primary btn-sm" @click="editModel(null)">
        <i class="fa-solid fa-plus mr-1"></i>New Model
      </button>
    </div>

    <!-- Compact filter row -->
    <div class="flex flex-wrap gap-2 items-center">
      <!-- Search -->
      <label class="input input-sm input-bordered flex items-center gap-2 grow min-w-40 bg-base-200">
        <i class="fa-solid fa-magnifying-glass text-xs text-base-content/40"></i>
        <input v-model="filterText" type="text" placeholder="Filter..." class="grow bg-transparent outline-none" />
        <button v-if="filterText" class="text-base-content/40 hover:text-error" @click="filterText = ''">
          <i class="fa-solid fa-xmark text-xs"></i>
        </button>
      </label>
      <!-- Type toggle pills -->
      <div class="flex gap-1">
        <button
          v-for="opt in typeOptions"
          :key="opt.value"
          class="btn btn-xs rounded-full"
          :class="filterType === opt.value ? opt.activeClass : 'btn-ghost border border-base-300'"
          @click="filterType = filterType === opt.value ? '' : opt.value"
        >{{ opt.label }}</button>
      </div>
      <!-- Provider chips -->
      <div class="flex gap-1 flex-wrap">
        <button
          v-for="p in uniqueProviders"
          :key="p"
          class="btn btn-xs rounded-full"
          :class="filterProvider === p ? 'btn-secondary' : 'btn-ghost border border-base-300'"
          @click="filterProvider = filterProvider === p ? '' : p"
        >{{ p }}</button>
      </div>
      <!-- Sort selector -->
      <div class="flex items-center gap-1 ml-auto">
        <span class="text-xs text-base-content/40">Sort:</span>
        <select v-model="sortKey" class="select select-xs select-bordered bg-base-200">
          <option v-for="col in sortableColumns" :key="col.key" :value="col.key">{{ col.label }}</option>
        </select>
        <button class="btn btn-xs btn-ghost" @click="sortAsc = !sortAsc">
          <i :class="sortAsc ? 'fa-solid fa-arrow-up-a-z' : 'fa-solid fa-arrow-down-z-a'"></i>
        </button>
      </div>
    </div>

    <!-- Data grid -->
    <div class="overflow-auto rounded-lg border border-base-300 grow">
      <table class="table table-xs w-full">
        <thead class="sticky top-0 z-10 bg-base-300">
          <tr>
            <th
              v-for="col in columns"
              :key="col.key"
              class="cursor-pointer whitespace-nowrap group"
              :class="[col.width, col.align === 'center' ? 'text-center' : col.align === 'right' ? 'text-right' : '']"
              @click="toggleSort(col.key)"
            >
              <span class="inline-flex items-center gap-1">
                <i v-if="col.icon" :class="`fa-solid fa-${col.icon} text-xs`"></i>
                {{ col.label }}
                <i
                  class="fa-solid text-xs ml-0.5 transition-opacity"
                  :class="sortKey === col.key
                    ? (sortAsc ? 'fa-caret-up text-primary opacity-100' : 'fa-caret-down text-primary opacity-100')
                    : 'fa-sort text-base-content/20 opacity-0 group-hover:opacity-100'"
                ></i>
              </span>
            </th>
            <th class="text-right w-24">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="filteredModels.length === 0">
            <td :colspan="columns.length + 1" class="text-center py-12 text-base-content/30">
              <i class="fa-solid fa-inbox text-3xl block mb-2"></i>
              No models match filters
            </td>
          </tr>
          <tr
            v-for="(model, idx) in filteredModels"
            :key="model.name"
            class="hover cursor-pointer border-b border-base-200"
            :class="idx % 2 === 0 ? 'bg-base-100' : 'bg-base-200/30'"
            @click="editModel(model)"
          >
            <!-- # -->
            <td class="text-base-content/30 text-xs w-8">{{ idx + 1 }}</td>
            <!-- Name -->
            <td>
              <div class="font-bold text-primary">{{ model.name }}</div>
              <div v-if="model.ai_model && model.name !== model.ai_model" class="text-xs text-base-content/40 truncate max-w-48">{{ model.ai_model }}</div>
            </td>
            <!-- Type -->
            <td class="text-center">
              <div class="flex items-center justify-center gap-1">
                <span :class="model.model_type === 'llm' ? 'bg-warning/20 text-warning' : 'bg-info/20 text-info'"
                      class="rounded px-1.5 py-0.5 text-xs font-bold uppercase tracking-wide">
                  {{ model.model_type === 'llm' ? 'LLM' : 'EMB' }}
                </span>
              </div>
            </td>
            <!-- Provider -->
            <td>
              <span class="badge badge-ghost badge-sm">{{ model.ai_provider || '—' }}</span>
            </td>
            <!-- Temp -->
            <td class="text-center tabular-nums">
              <span v-if="model.model_type === 'llm'" class="text-orange-400">{{ model.settings?.temperature ?? '—' }}</span>
              <span v-else class="text-base-content/30">—</span>
            </td>
            <!-- Context -->
            <td class="text-center tabular-nums">
              <span v-if="model.model_type === 'llm' && model.settings?.context_length" class="text-blue-400">{{ model.settings.context_length }}K</span>
              <span v-else-if="model.model_type === 'embeddings'" class="text-teal-400">{{ model.settings?.vector_size || '—' }}</span>
              <span v-else class="text-base-content/30">—</span>
            </td>
            <!-- Chunk -->
            <td class="text-center tabular-nums">
              <span v-if="model.model_type === 'embeddings'" class="text-pink-400">{{ model.settings?.chunk_size || '—' }}</span>
              <span v-else-if="model.settings?.merge_messages" class="text-purple-400 text-xs">merge</span>
              <span v-else class="text-base-content/30">—</span>
            </td>
            <!-- Cost in -->
            <td class="text-right tabular-nums text-green-500">
              {{ model.input_k_tokens_cxjcoins ?? (model.k_tokens_cxjcoins ?? '—') }}
            </td>
            <!-- Cost out -->
            <td class="text-right tabular-nums text-blue-400">
              {{ model.output_k_tokens_cxjcoins ?? '—' }}
            </td>
            <!-- Actions -->
            <td @click.stop>
              <div class="flex justify-end gap-0.5">
                <button class="btn btn-xs btn-ghost btn-circle text-info" @click="showModelInfo = model">
                  <i class="fa-solid fa-circle-info text-xs"></i>
                </button>
                <button class="btn btn-xs btn-ghost btn-circle" @click="editModel(model)">
                  <i class="fa-solid fa-pen text-xs"></i>
                </button>
                <button
                  class="btn btn-xs btn-ghost btn-circle"
                  :class="model.loading ? 'animate-spin text-warning' : 'text-secondary'"
                  @click="reloadModel(model)"
                >
                  <i class="fa-solid fa-arrows-rotate text-xs"></i>
                </button>
                <button class="btn btn-xs btn-ghost btn-circle text-error" @click="confirmDelete(model)">
                  <i class="fa-solid fa-trash-can text-xs"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
        <!-- Summary footer -->
        <tfoot class="bg-base-300 sticky bottom-0">
          <tr>
            <td :colspan="columns.length + 1" class="text-xs text-base-content/40 px-4 py-2">
              <span class="mr-4">
                <i class="fa-solid fa-filter mr-1"></i>
                {{ filteredModels.length }} results
              </span>
              <span class="mr-4" v-if="llmCount">
                <i class="fa-solid fa-brain mr-1 text-warning"></i>{{ llmCount }} LLM
              </span>
              <span v-if="embCount">
                <i class="fa-solid fa-file mr-1 text-info"></i>{{ embCount }} Embeddings
              </span>
            </td>
          </tr>
        </tfoot>
      </table>
    </div>

    <!-- Modals -->
    <modal class="w-2/3 h-5/6 overflow-auto" v-if="showDialog">
      <AIModelSettings
        :aiProviders="aiProviders"
        :model="currentModel"
        @save="saveModel"
        @cancel="showDialog = false"
        @delete="confirmDelete"
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
        <p class="text-sm">Delete <strong>{{ modelToDelete?.name }}</strong>? This cannot be undone.</p>
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
      typeOptions: [
        { value: 'llm', label: 'LLM', activeClass: 'btn-warning' },
        { value: 'embeddings', label: 'Embeddings', activeClass: 'btn-info' }
      ],
      columns: [
        { key: '_idx', label: '#', width: 'w-8' },
        { key: 'name', label: 'Name', icon: 'tag' },
        { key: 'model_type', label: 'Type', icon: 'layer-group', align: 'center' },
        { key: 'ai_provider', label: 'Provider', icon: 'plug' },
        { key: 'temperature', label: 'Temp', align: 'center' },
        { key: 'context', label: 'Ctx/Vec', align: 'center' },
        { key: 'chunk', label: 'Chunk', align: 'center' },
        { key: 'cost_in', label: 'In ↓', align: 'right' },
        { key: 'cost_out', label: 'Out ↑', align: 'right' },
      ],
      sortableColumns: [
        { key: 'name', label: 'Name' },
        { key: 'model_type', label: 'Type' },
        { key: 'ai_provider', label: 'Provider' },
        { key: 'temperature', label: 'Temperature' },
        { key: 'cost_in', label: 'Cost In' },
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
      return list.sort((a, b) => {
        const av = this.getSortValue(a)
        const bv = this.getSortValue(b)
        if (av < bv) return this.sortAsc ? -1 : 1
        if (av > bv) return this.sortAsc ? 1 : -1
        return 0
      })
    },
    llmCount() {
      return this.filteredModels.filter(m => m.model_type === 'llm').length
    },
    embCount() {
      return this.filteredModels.filter(m => m.model_type === 'embeddings').length
    }
  },
  methods: {
    getSortValue(model) {
      const map = {
        name: model.name?.toLowerCase() || '',
        model_type: model.model_type || '',
        ai_provider: model.ai_provider?.toLowerCase() || '',
        temperature: model.settings?.temperature ?? 0,
        cost_in: model.input_k_tokens_cxjcoins ?? model.k_tokens_cxjcoins ?? 0
      }
      return map[this.sortKey] ?? ''
    },
    toggleSort(key) {
      if (key === '_idx') return
      this.sortKey === key ? (this.sortAsc = !this.sortAsc) : (this.sortKey = key, this.sortAsc = true)
    },
    editModel(model) {
      if (!model) {
        model = { settings: {}, k_tokens_cxjcoins: null, input_k_tokens_cxjcoins: null, output_k_tokens_cxjcoins: null }
        this.aiModels.push(model)
      }
      this.currentModel = model
      this.showDialog = true
    },
    saveModel() { this.showDialog = false },
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
    }
  }
}
</script>