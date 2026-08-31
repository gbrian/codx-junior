<script setup>
</script>

<template>
  <div class="flex flex-col gap-5 w-full">
    <!-- Header banner -->
    <div class="flex items-center gap-3 bg-gradient-to-r from-primary/20 to-transparent rounded-xl px-4 py-3">
      <div class="avatar placeholder">
        <div class="bg-primary text-primary-content rounded-full w-10 h-10 flex items-center justify-center">
          <i class="fa-solid fa-robot text-lg"></i>
        </div>
      </div>
      <div class="flex flex-col min-w-0 flex-grow mr-3">
        <div class="font-bold text-base truncate">{{ provider.name || 'New Provider' }}</div>
        <div class="flex items-center gap-2 mt-1 flex-wrap">
          <!-- Type / Protocol -->
          <span class="badge badge-ghost badge-sm font-mono uppercase py-2 px-3">{{ provider.provider || 'N/A' }}</span>
          
          <!-- URL with ellipsis for space efficiency -->
          <span class="text-xs text-base-content/60 truncate max-w-[15rem]" :title="provider.api_url">
            {{ shortUrl }}
          </span>
        </div>
      </div>
      
      <div class="shrink-0 ml-auto self-center">
        <span :class="isValid ? 'badge badge-success' : 'badge badge-warning'" class="text-xs gap-1 px-3 py-2">
          <i :class="isValid ? 'fa-solid fa-circle-check' : 'fa-solid fa-triangle-exclamation'" class="mr-1"></i>
          {{ isValid ? 'Ready' : 'Incomplete' }}
        </span>
      </div>
    </div>

    <!-- Tabs -->
    <div role="tablist" class="tabs tabs-bordered">
      <a role="tab" class="tab" :class="{ 'tab-active': activeTab === 'settings' }" @click="activeTab = 'settings'">
        <i class="fa-solid fa-gear mr-1"></i> Settings
      </a>
      <a role="tab" class="tab" :class="{ 'tab-active': activeTab === 'pricing' }" @click="activeTab = 'pricing'">
        <i class="fa-solid fa-tags mr-1"></i> Price List
        <span v-if="provider.price_list && provider.price_list.length" class="badge badge-sm badge-primary ml-1">
          {{ provider.price_list.length }}
        </span>
      </a>
    </div>

    <!-- Tab: Settings -->
    <div v-if="activeTab === 'settings'" class="flex flex-col gap-5">
      <!-- Row 1: Name & Protocol -->
      <div class="grid grid-cols-2 gap-3">
        <div class="form-control">
          <label class="label py-1">
            <span class="label-text text-xs font-semibold uppercase tracking-wide text-base-content/60">
              <i class="fa-solid fa-tag mr-1 text-primary"></i>Name
            </span>
          </label>
          <input class="input input-bordered input-sm" v-model="provider.name" placeholder="Provider Name" />
        </div>
        <div class="form-control">
          <label class="label py-1">
            <span class="label-text text-xs font-semibold uppercase tracking-wide text-base-content/60">
              <i class="fa-solid fa-code-branch mr-1 text-secondary"></i>Protocol
            </span>
          </label>
          <input class="input input-bordered input-sm" v-model="provider.provider" placeholder="e.g. openai" />
        </div>
      </div>

      <!-- Row 2: URLs -->
      <div class="flex flex-col gap-3 p-3 bg-base-200 rounded-lg">
        <div class="text-xs font-bold uppercase tracking-widest text-info flex items-center gap-1">
          <i class="fa-solid fa-network-wired"></i> Network
        </div>
        <div class="form-control">
          <label class="label py-1">
            <span class="label-text text-xs">API URL</span>
            <span v-if="provider.api_url" class="label-text-alt text-success text-xs">
              <i class="fa-solid fa-circle-check"></i>
            </span>
          </label>
          <input class="input input-bordered input-sm font-mono text-xs" v-model="provider.api_url" placeholder="https://api.example.com/v1" />
        </div>
        <div class="form-control">
          <label class="label py-1">
            <span class="label-text text-xs">Admin URL</span>
            <span v-if="provider.admin_url" class="label-text-alt text-success text-xs">
              <i class="fa-solid fa-circle-check"></i>
            </span>
          </label>
          <input class="input input-bordered input-sm font-mono text-xs" v-model="provider.admin_url" placeholder="https://admin.example.com" />
        </div>
      </div>

      <!-- Row 3: API Key & Cost -->
      <div class="flex flex-col gap-3 p-3 bg-base-200 rounded-lg">
        <div class="text-xs font-bold uppercase tracking-widest text-warning flex items-center gap-1 col-span-2">
          <i class="fa-solid fa-lock"></i> Security & Billing
        </div>
        <!-- API Key -->
        <div class="form-control">
          <label class="label py-1">
            <span class="label-text text-xs"><i class="fa-solid fa-key mr-1 text-warning"></i>API Key</span>
          </label>
          <div class="relative">
            <input
              :type="showKey ? 'text' : 'password'"
              class="input input-bordered input-sm font-mono text-xs w-full pr-10"
              v-model="provider.api_key"
              placeholder="sk-..."
            />
            <button class="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-base-content hover:text-base-content" @click="showKey = !showKey">
              <i :class="showKey ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye'"></i>
            </button>
          </div>
        </div>
        <!-- Billing: input / output -->
        <div class="grid grid-cols-2 gap-3">
          <div class="form-control">
            <label class="label py-1">
              <span class="label-text text-xs">
                <i class="fa-solid fa-arrow-right-to-bracket mr-1 text-green-500"></i>Input / 1K tokens
              </span>
            </label>
            <div class="flex items-center gap-1">
              <input class="input input-bordered input-sm w-full" type="number" step="0.0001" v-model.number="provider.input_k_tokens_cxjcoins" placeholder="0.0000" />
              <span class="text-xs text-base-content/50 shrink-0">cxj</span>
            </div>
          </div>
          <div class="form-control">
            <label class="label py-1">
              <span class="label-text text-xs">
                <i class="fa-solid fa-arrow-right-from-bracket mr-1 text-blue-500"></i>Output / 1K tokens
              </span>
            </label>
            <div class="flex items-center gap-1">
              <input class="input input-bordered input-sm w-full" type="number" step="0.0001" v-model.number="provider.output_k_tokens_cxjcoins" placeholder="0.0000" />
              <span class="text-xs text-base-content/50 shrink-0">cxj</span>
            </div>
          </div>
        </div>
        <!-- Tool Limits -->
        <div class="grid grid-cols-2 gap-3 pt-2 border-t border-base-300">
          <div class="form-control">
            <label class="label py-1">
              <span class="label-text text-xs"><i class="fa-solid fa-toolbox mr-1 text-secondary"></i>Max Tool Calls</span>
            </label>
            <input class="input input-bordered input-sm" type="number" v-model.number="provider.max_tool_calls" placeholder="Leave empty for default" step="1" />
          </div>
          <div class="form-control">
            <label class="label py-1">
              <span class="label-text text-xs"><i class="fa-solid fa-repeat mr-1 text-secondary"></i>Max Iterations</span>
            </label>
            <input class="input input-bordered input-sm" type="number" v-model.number="provider.max_iterations" placeholder="Leave empty for default" step="1" />
          </div>
        </div>
      </div>
    </div>

    <!-- Tab: Price List -->
    <div v-if="activeTab === 'pricing'" class="flex flex-col gap-4">
      <div class="flex flex-col gap-2 p-3 bg-base-200 rounded-lg">
        <div class="text-xs font-bold uppercase tracking-widest text-info flex items-center gap-1">
          <i class="fa-solid fa-tags"></i> Price List JSON
        </div>
        <div class="text-xs text-base-content/50">
          Paste or edit the JSON price list. Expected fields per entry:
          <code class="bg-base-300 px-1 rounded">model_name</code>,
          <code class="bg-base-300 px-1 rounded">input_price_per_1k_tokens</code>,
          <code class="bg-base-300 px-1 rounded">output_price_per_1k_tokens</code>
        </div>

        <!-- Null values warning -->
        <div v-if="nullWarningCount > 0" class="alert alert-warning py-2 text-xs flex items-center gap-2">
          <i class="fa-solid fa-triangle-exclamation"></i>
          <span>
            <strong>{{ nullWarningCount }}</strong> entries have null price values and will be excluded on save.
            <button class="btn btn-xs btn-ghost ml-1" @click="fixNullEntries">Fix nulls (set to 0)</button>
          </span>
        </div>

        <!-- JSON editor -->
        <div class="form-control">
          <textarea
            class="textarea textarea-bordered font-mono text-xs w-full min-h-32 max-h-48 resize-none overflow-y-auto"
            :class="jsonError ? 'textarea-error' : ''"
            v-model="priceListJson"
            placeholder='[{"model_name": "...", "input_price_per_1k_tokens": 0.001, "output_price_per_1k_tokens": 0.005}]'
            @input="onJsonInput"
          ></textarea>
          <div v-if="jsonError" class="label py-1">
            <span class="label-text-alt text-error text-xs">
              <i class="fa-solid fa-triangle-exclamation mr-1"></i>{{ jsonError }}
            </span>
          </div>
        </div>

        <!-- Actions row -->
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <button class="btn btn-xs btn-ghost" @click="formatJson" title="Format JSON">
              <i class="fa-solid fa-indent mr-1"></i> Format
            </button>
            <button class="btn btn-xs btn-ghost text-warning" @click="fixNullEntries" title="Replace nulls with 0">
              <i class="fa-solid fa-wrench mr-1"></i> Fix Nulls
            </button>
            <button class="btn btn-xs btn-ghost text-error" @click="clearPriceList" title="Clear list">
              <i class="fa-solid fa-trash-can mr-1"></i> Clear
            </button>
          </div>
          <button class="btn btn-xs btn-primary" :disabled="!!jsonError" @click="applyPriceList">
            <i class="fa-solid fa-check mr-1"></i> Apply
          </button>
        </div>
      </div>

      <!-- Preview table: scrollable container with fixed max height -->
      <div v-if="parsedPriceList.length" class="rounded-lg border border-base-300 overflow-hidden">
        <div class="overflow-y-auto max-h-64">
          <table class="table table-xs w-full">
            <thead class="sticky top-0 z-10">
              <tr class="bg-base-200">
                <th class="text-xs">#</th>
                <th class="text-xs">Model Name</th>
                <th class="text-xs text-green-500">Input / 1K</th>
                <th class="text-xs text-blue-500">Output / 1K</th>
                <th class="text-xs text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(entry, idx) in parsedPriceList"
                :key="idx"
                class="hover"
                :class="hasNullPrices(entry) ? 'bg-warning/10' : ''"
              >
                <td class="text-xs text-base-content">{{ idx + 1 }}</td>
                <td class="font-mono text-xs">{{ entry.model_name }}</td>
                <td class="text-xs" :class="entry.input_price_per_1k_tokens == null ? 'text-warning' : 'text-green-500'">
                  <span v-if="entry.input_price_per_1k_tokens != null">${{ entry.input_price_per_1k_tokens }}</span>
                  <span v-else class="flex items-center gap-1"><i class="fa-solid fa-triangle-exclamation"></i> null</span>
                </td>
                <td class="text-xs" :class="entry.output_price_per_1k_tokens == null ? 'text-warning' : 'text-blue-500'">
                  <span v-if="entry.output_price_per_1k_tokens != null">${{ entry.output_price_per_1k_tokens }}</span>
                  <span v-else class="flex items-center gap-1"><i class="fa-solid fa-triangle-exclamation"></i> null</span>
                </td>
                <td class="text-right">
                  <button class="btn btn-ghost btn-xs text-error" @click="removeEntry(idx)">
                    <i class="fa-solid fa-xmark"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <!-- Entry count footer -->
        <div class="bg-base-200 px-3 py-1 text-xs text-base-content/50 flex items-center gap-1 border-t border-base-300">
          <i class="fa-solid fa-list-ul"></i>
          {{ parsedPriceList.length }} {{ parsedPriceList.length === 1 ? 'entry' : 'entries' }}
          <span v-if="nullWarningCount > 0" class="text-warning ml-2">
            <i class="fa-solid fa-triangle-exclamation"></i> {{ nullWarningCount }} with null values
          </span>
        </div>
      </div>

      <div v-else class="text-center text-base-content text-xs py-6">
        <i class="fa-solid fa-table-list text-2xl mb-2 block"></i>
        No price entries yet. Paste JSON above and click Apply.
      </div>
    </div>

    <!-- Actions -->
    <div class="flex justify-between items-center pt-1">
      <button class="btn btn-ghost btn-sm text-error" @click="$emit('cancel')">
        <i class="fa-solid fa-trash-can mr-1"></i> Discard
      </button>
      <button class="btn btn-primary btn-sm" :disabled="!isValid" @click="onSave">
        <i class="fa-solid fa-floppy-disk mr-1"></i> Save Provider
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: ['modelValue'],
  emits: ['save', 'cancel', 'update:modelValue'],
  data() {
    return {
      provider: { ...this.modelValue },
      showKey: false,
      activeTab: 'settings',
      priceListJson: '',
      jsonError: null,
      parsedPriceList: []
    }
  },
  computed: {
    isValid() {
      return !!(this.provider.name && this.provider.provider && this.provider.api_url)
    },
    // Count entries with any null price field
    nullWarningCount() {
      return this.parsedPriceList.filter(e => this.hasNullPrices(e)).length
    },
    // Display URL in header with ellipsis if too long
    shortUrl() {
      const url = this.provider.api_url || ''
      if (!url) return 'No URL set'
      const maxLen = 40
      if (url.length <= maxLen) return url
      // Truncate by replacing middle part to show domain and end path
      if (url.length > maxLen + 5) {
        return url.substring(0, 20) + '...' + url.substring(url.length - 15)
      }
      return url.substring(0, maxLen) + '...'
    }
  },
  watch: {
    modelValue(val) {
      this.provider = { ...val }
      this.syncPriceListFromProvider()
    },
    activeTab(tab) {
      if (tab === 'pricing') this.syncPriceListFromProvider()
    }
  },
  methods: {
    hasNullPrices(entry) {
      return entry.input_price_per_1k_tokens == null || entry.output_price_per_1k_tokens == null
    },

    // Replace null price values with 0 in the parsed list
    fixNullEntries() {
      this.parsedPriceList = this.parsedPriceList.map(e => ({
        ...e,
        input_price_per_1k_tokens: e.input_price_per_1k_tokens ?? 0,
        output_price_per_1k_tokens: e.output_price_per_1k_tokens ?? 0
      }))
      this.priceListJson = JSON.stringify(this.parsedPriceList, null, 2)
      this.provider.price_list = [...this.parsedPriceList]
    },

    // Sanitize price list before emitting save — strips null price entries
    sanitizePriceList(list) {
      return (list || []).map(e => ({
        ...e,
        input_price_per_1k_tokens: e.input_price_per_1k_tokens ?? 0,
        output_price_per_1k_tokens: e.output_price_per_1k_tokens ?? 0
      }))
    },

    onSave() {
      const toSave = {
        ...this.provider,
        price_list: this.sanitizePriceList(this.provider.price_list)
      }
      this.$emit('save', toSave)
    },

    syncPriceListFromProvider() {
      const list = this.provider.price_list || []
      this.parsedPriceList = [...list]
      this.priceListJson = list.length ? JSON.stringify(list, null, 2) : ''
      this.jsonError = null
    },

    onJsonInput() {
      if (!this.priceListJson.trim()) {
        this.jsonError = null
        this.parsedPriceList = []
        return
      }
      try {
        const parsed = JSON.parse(this.priceListJson)
        if (!Array.isArray(parsed)) throw new Error('Expected a JSON array')
        this.jsonError = null
        this.parsedPriceList = parsed
      } catch (e) {
        this.jsonError = e.message
      }
    },

    formatJson() {
      if (this.jsonError) return
      try {
        const parsed = JSON.parse(this.priceListJson)
        this.priceListJson = JSON.stringify(parsed, null, 2)
      } catch (_) {}
    },

    applyPriceList() {
      if (this.jsonError) return
      this.provider.price_list = [...this.parsedPriceList]
    },

    clearPriceList() {
      this.priceListJson = ''
      this.parsedPriceList = []
      this.jsonError = null
      this.provider.price_list = []
    },

    removeEntry(idx) {
      this.parsedPriceList.splice(idx, 1)
      this.provider.price_list = [...this.parsedPriceList]
      this.priceListJson = this.parsedPriceList.length
        ? JSON.stringify(this.parsedPriceList, null, 2)
        : ''
    }
  },
  mounted() {
    this.syncPriceListFromProvider()
  }
}
</script>