<script setup>
import Iframe from '../Iframe.vue'
import AIProviderSettings from './AIProviderSettings.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-4 p-4">
    <!-- Page header -->
    <div class="flex items-center gap-3 bg-gradient-to-r from-primary/20 to-transparent rounded-xl px-4 py-3">
      <div class="avatar placeholder">
        <div class="bg-primary text-primary-content rounded-full w-10 h-10 flex items-center justify-center">
          <i class="fa-solid fa-robot text-lg"></i>
        </div>
      </div>
      <div class="grow">
        <div class="font-bold text-xl">AI Providers</div>
        <div class="text-xs text-base-content/50">{{ filteredProviders.length }} of {{ aiProviders.length }} provider(s)</div>
      </div>
      <button class="btn btn-primary btn-sm gap-2" @click="editProvider({})">
        <i class="fa-solid fa-plus"></i> New Provider
      </button>
    </div>

    <!-- Filter bar -->
    <div class="flex flex-wrap gap-2 items-center bg-base-200 rounded-xl p-3">
      <div class="relative grow min-w-48">
        <i class="fa-solid fa-search absolute left-3 top-1/2 -translate-y-1/2 text-base-content/40 text-xs"></i>
        <input
          v-model="filterText"
          type="text"
          placeholder="Search providers..."
          class="input input-sm input-bordered w-full pl-8 bg-base-100"
        />
      </div>
      <select v-model="filterProvider" class="select select-sm select-bordered bg-base-100">
        <option value="">All Types</option>
        <option v-for="p in uniqueProviderTypes" :key="p" :value="p">{{ p }}</option>
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
          <tr v-if="filteredProviders.length === 0">
            <td :colspan="columns.length + 1" class="text-center py-10 text-base-content/40">
              <i class="fa-solid fa-ghost text-2xl mb-2 block"></i>
              No providers found
            </td>
          </tr>
          <tr
            v-for="provider in filteredProviders"
            :key="provider.name"
            class="hover:bg-base-200 cursor-pointer transition-colors"
            @click="editProvider(provider)"
          >
            <!-- Name -->
            <td>
              <div class="flex items-center gap-2">
                <div class="bg-primary/10 text-primary rounded-lg w-7 h-7 flex items-center justify-center text-xs font-bold shrink-0">
                  {{ provider.name?.charAt(0)?.toUpperCase() }}
                </div>
                <div>
                  <div class="font-semibold text-primary text-sm">{{ provider.name }}</div>
                  <div class="badge badge-ghost badge-xs font-mono mt-0.5">{{ provider.provider }}</div>
                </div>
              </div>
            </td>
            <!-- URL -->
            <td>
              <div class="flex items-center gap-2 bg-base-200 rounded-lg px-2 py-1 max-w-xs">
                <i class="fa-solid fa-network-wired text-xs text-info shrink-0"></i>
                <span class="font-mono text-xs text-base-content/60 truncate" :title="provider.api_url">
                  {{ provider.api_url || 'No URL' }}
                </span>
              </div>
            </td>
            <!-- API Key -->
            <td>
              <span v-if="provider.api_key" class="flex items-center gap-1 text-xs">
                <i class="fa-solid fa-key text-warning"></i>
                {{ provider.api_key?.slice(0, 4) }}••••
              </span>
              <span v-else class="text-xs text-error/60">
                <i class="fa-solid fa-ban mr-1"></i>No key
              </span>
            </td>
            <!-- Models count -->
            <td class="text-right">
              <div class="flex items-center justify-end gap-1">
                <span>
                  {{ getModelCount(provider) }}
                </span>
              </div>
            </td>
            <!-- Actions -->
            <td @click.stop>
              <div class="flex justify-end gap-1">
                <button
                  v-if="provider.admin_url"
                  class="btn btn-xs btn-circle btn-ghost text-info"
                  @click="navigateAdmin(provider)"
                  title="Admin Panel"
                >
                  <i class="fa-solid fa-link"></i>
                </button>
                <button class="btn btn-xs btn-circle btn-ghost" @click="editProvider(provider)">
                  <i class="fa-solid fa-pen-to-square"></i>
                </button>
                <button class="btn btn-xs btn-circle btn-ghost text-error" @click="confirmDelete(provider)">
                  <i class="fa-solid fa-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Iframe admin view -->
    <modal class="w-5/6 h-5/6" v-if="adminUrl" close="true" @close="adminUrl = null">
      <Iframe :url="adminUrl" />
    </modal>

    <!-- Edit modal -->
    <modal class="w-2/3 h-5/6 overflow-auto" v-if="showDialog">
      <AIProviderSettings
        :model-value="currentProvider"
        @save="saveProvider"
        @cancel="showDialog = false"
      />
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
  </div>
</template>

<script>
export default {
  props: ['settings'],
  data() {
    return {
      showDialog: false,
      showDeleteDialog: false,
      currentProvider: {},
      providerToDelete: null,
      adminUrl: null,
      filterText: '',
      filterProvider: '',
      sortKey: 'name',
      sortAsc: true,
      columns: [
        { key: 'name', label: 'Provider' },
        { key: 'api_url', label: 'Endpoint' },
        { key: 'api_key', label: 'API Key' },
        { key: 'models', label: 'Models', align: 'right' },
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
    uniqueProviderTypes() {
      return [...new Set(this.aiProviders.map(p => p.provider).filter(Boolean))]
    },
    hasFilters() {
      return this.filterText || this.filterProvider
    },
    filteredProviders() {
      let list = [...this.aiProviders]
      // text filter across name, provider, api_url
      if (this.filterText) {
        const q = this.filterText.toLowerCase()
        list = list.filter(p =>
          p.name?.toLowerCase().includes(q) ||
          p.provider?.toLowerCase().includes(q) ||
          p.api_url?.toLowerCase().includes(q)
        )
      }
      if (this.filterProvider) list = list.filter(p => p.provider === this.filterProvider)
      // sorting
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
    // Count how many models are assigned to a given provider name
    getModelCount(provider) {
      const models = this.aiModels.filter(m => m.ai_provider === provider.name).length
      const modelList = (provider.price_list || []).length
      return `${models} / ${modelList}`
    },
    getSortValue(provider) {
      const map = {
        name: provider.name?.toLowerCase() || '',
        api_url: provider.api_url?.toLowerCase() || '',
        api_key: provider.api_key ? '1' : '0',
        models: this.getModelCount(provider).split("/")[0]
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
      this.filterProvider = ''
    },
    editProvider(provider) {
      this.currentProvider = { ...provider }
      this.showDialog = true
    },
    saveProvider(updated) {
      const idx = this.aiProviders.findIndex(p => p.name === updated.name)
      idx !== -1 ? this.aiProviders.splice(idx, 1, updated) : this.aiProviders.push(updated)
      this.showDialog = false
    },
    confirmDelete(provider) {
      this.providerToDelete = provider
      this.showDeleteDialog = true
    },
    deleteProvider() {
      const idx = this.aiProviders.findIndex(p => p.name === this.providerToDelete.name)
      if (idx !== -1) this.aiProviders.splice(idx, 1)
      this.showDeleteDialog = false
    },
    navigateAdmin(provider) {
      this.adminUrl = provider.admin_url
    }
  }
}
</script>