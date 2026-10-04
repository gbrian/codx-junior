<script setup>
import Modal from '../Modal.vue'
</script>

<template>
  <div class="flex gap-2">
    <button
      type="button"
      class="btn btn-sm btn-ghost gap-1"
      title="Export providers and models as JSON"
      @click="openExport"
    >
      <i class="fa-solid fa-file-export"></i> Export
    </button>
    <button
      type="button"
      class="btn btn-sm btn-ghost gap-1"
      title="Import providers and models from JSON"
      @click="openImport"
    >
      <i class="fa-solid fa-file-import"></i> Import
    </button>

    <!-- Export modal -->
    <Modal v-if="showExport" :close="true" class="w-11/12 max-w-2xl" @close="showExport = false">
      <template #header>
        <h3 class="text-lg font-bold flex items-center gap-2">
          <i class="fa-solid fa-file-export text-primary"></i> Export AI Settings
        </h3>
      </template>

      <div class="flex flex-col gap-4">
        <p class="text-sm text-base-content/70">
          Export all <strong>{{ providers.length }}</strong> provider(s) and
          <strong>{{ models.length }}</strong> model(s) as a single JSON document.
        </p>

        <!-- Include API keys toggle -->
        <label class="flex items-start gap-3 p-3 rounded-lg bg-base-200 cursor-pointer">
          <input type="checkbox" class="toggle toggle-sm toggle-warning mt-0.5" v-model="includeKeys" />
          <span class="flex flex-col">
            <span class="text-sm font-medium">Include API keys</span>
            <span class="text-xs text-base-content/60">
              When disabled, keys are omitted. Re-importing later will keep the keys already stored locally.
            </span>
          </span>
        </label>

        <div
          v-if="includeKeys"
          class="flex items-center gap-2 px-3 py-2 rounded-lg bg-warning/10 text-warning text-xs"
          role="note"
        >
          <i class="fa-solid fa-triangle-exclamation"></i>
          The exported file will contain secrets — store and share it carefully.
        </div>

        <!-- JSON preview -->
        <div class="form-control">
          <label class="label py-1">
            <span class="label-text text-xs">JSON preview</span>
          </label>
          <textarea
            readonly
            :value="exportJson"
            class="textarea textarea-bordered text-xs font-mono h-56 w-full"
          ></textarea>
        </div>
      </div>

      <template #footer>
        <button type="button" class="btn btn-sm btn-ghost" @click="downloadExport">
          <i class="fa-solid fa-download mr-1"></i> Download file
        </button>
        <button type="button" class="btn btn-sm btn-primary" @click="copyExport">
          <i class="fa-solid fa-copy mr-1"></i> Copy JSON
        </button>
      </template>
    </Modal>

    <!-- Import modal -->
    <Modal v-if="showImport" :close="true" class="w-11/12 max-w-2xl" @close="showImport = false">
      <template #header>
        <h3 class="text-lg font-bold flex items-center gap-2">
          <i class="fa-solid fa-file-import text-primary"></i> Import AI Settings
        </h3>
      </template>

      <div class="flex flex-col gap-4">
        <!-- Mode -->
        <div class="form-control">
          <label class="label py-1">
            <span class="label-text text-xs font-bold uppercase tracking-wide">Import mode</span>
          </label>
          <div class="flex flex-col sm:flex-row gap-2">
            <label
              class="flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer grow border transition-colors"
              :class="importMode === 'merge' ? 'border-primary bg-primary/10' : 'border-base-content/10'"
            >
              <input type="radio" class="radio radio-sm radio-primary" value="merge" v-model="importMode" />
              <span class="flex flex-col">
                <span class="text-sm font-medium">Merge</span>
                <span class="text-xs text-base-content/60">Add new and deep-merge existing — keeps your local keys</span>
              </span>
            </label>
            <label
              class="flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer grow border transition-colors"
              :class="importMode === 'replace' ? 'border-error bg-error/10' : 'border-base-content/10'"
            >
              <input type="radio" class="radio radio-sm radio-error" value="replace" v-model="importMode" />
              <span class="flex flex-col">
                <span class="text-sm font-medium">Replace</span>
                <span class="text-xs text-base-content/60">Remove items missing from the import — local keys still kept</span>
              </span>
            </label>
          </div>
        </div>

        <!-- File input -->
        <div class="form-control">
          <label class="label py-1">
            <span class="label-text text-xs">Choose a JSON file</span>
          </label>
          <input
            type="file"
            accept="application/json,.json"
            class="file-input file-input-bordered file-input-sm w-full"
            @change="onFileSelected"
          />
        </div>

        <!-- Paste -->
        <div class="form-control">
          <label class="label py-1">
            <span class="label-text text-xs">…or paste JSON</span>
          </label>
          <textarea
            v-model="importText"
            class="textarea textarea-bordered text-xs font-mono h-40 w-full"
            placeholder='{ "ai_providers": [ ... ], "ai_models": [ ... ] }'
          ></textarea>
        </div>

        <!-- Error -->
        <div
          v-if="importError"
          class="flex items-center gap-2 px-3 py-2 rounded-lg bg-error/10 text-error text-sm"
          role="alert"
        >
          <i class="fa-solid fa-circle-exclamation"></i>
          {{ importError }}
        </div>

        <!-- Save reminder -->
        <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-info/10 text-info text-xs" role="note">
          <i class="fa-solid fa-circle-info"></i>
          Imported changes are applied to the editor only — click <strong>Save Changes</strong> to persist them.
        </div>
      </div>

      <template #footer>
        <button type="button" class="btn btn-sm btn-ghost" @click="showImport = false">Cancel</button>
        <button
          type="button"
          class="btn btn-sm"
          :class="importMode === 'replace' ? 'btn-error' : 'btn-primary'"
          @click="confirmImport"
        >
          <i class="fa-solid fa-file-import mr-1"></i>
          {{ importMode === 'replace' ? 'Replace' : 'Merge' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<script>
const EXPORT_TYPE = 'codx-junior.ai-settings'
const EXPORT_VERSION = 1

export default {
  props: {
    providers: { type: Array, default: () => [] },
    models: { type: Array, default: () => [] }
  },
  emits: ['import'],
  data() {
    return {
      showExport: false,
      showImport: false,
      includeKeys: true,
      importText: '',
      importMode: 'merge',
      importError: null
    }
  },
  computed: {
    // Full payload written on export (secrets optionally stripped)
    exportPayload() {
      return {
        type: EXPORT_TYPE,
        version: EXPORT_VERSION,
        exported_at: new Date().toISOString(),
        ai_providers: this.stripKeys(this.providers),
        ai_models: this.models
      }
    },
    exportJson() {
      return JSON.stringify(this.exportPayload, null, 2)
    },
    exportFileName() {
      const stamp = new Date().toISOString().slice(0, 10)
      return `codx-junior-ai-settings-${stamp}.json`
    }
  },
  methods: {
    // Blank the API key when the user opts out of sharing secrets
    stripKeys(providers) {
      if (this.includeKeys) return providers
      return (providers || []).map(({ api_key, ...rest }) => ({ ...rest, api_key: '' }))
    },
    openExport() {
      this.showExport = true
    },
    openImport() {
      this.importText = ''
      this.importError = null
      this.importMode = 'merge'
      this.showImport = true
    },
    async copyExport() {
      await this.$ui.copyTextToClipboard(this.exportJson)
      this.$toast.success('AI settings copied to clipboard')
    },
    downloadExport() {
      const blob = new Blob([this.exportJson], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = this.exportFileName
      link.click()
      URL.revokeObjectURL(url)
      this.$toast.success('AI settings exported')
    },
    onFileSelected(event) {
      const file = event.target.files && event.target.files[0]
      if (!file) return
      const reader = new FileReader()
      reader.onload = () => { this.importText = String(reader.result || '') }
      reader.onerror = () => { this.importError = 'Failed to read the selected file.' }
      reader.readAsText(file)
    },
    // Validate & normalize the pasted/uploaded JSON
    parseImport() {
      const text = (this.importText || '').trim()
      if (!text) {
        this.importError = 'Nothing to import — paste JSON or choose a file.'
        return null
      }
      let data
      try {
        data = JSON.parse(text)
      } catch (err) {
        this.importError = `Invalid JSON: ${err.message}`
        return null
      }
      const hasProviders = Array.isArray(data?.ai_providers)
      const hasModels = Array.isArray(data?.ai_models)
      if (!hasProviders && !hasModels) {
        this.importError = 'JSON must contain an "ai_providers" and/or "ai_models" array.'
        return null
      }
      return {
        providers: this.validEntries(hasProviders ? data.ai_providers : []),
        models: this.validEntries(hasModels ? data.ai_models : []),
        hasProviders,
        hasModels
      }
    },
    // Keep only plain object entries
    validEntries(list) {
      return (list || []).filter(item => item && typeof item === 'object' && !Array.isArray(item))
    },
    isPlainObject(value) {
      return !!value && typeof value === 'object' && !Array.isArray(value)
    },
    // Deep-merge imported fields onto an existing entry.
    // Imported values win, EXCEPT empty ones (undefined / null / '') which keep
    // the existing value — this is what lets a key-less export reuse local keys.
    mergeEntry(existing, incoming) {
      const base = this.isPlainObject(existing) ? existing : {}
      const result = { ...base }
      Object.keys(incoming || {}).forEach(key => {
        result[key] = this.mergeValue(base[key], incoming[key])
      })
      return result
    },
    mergeValue(existing, incoming) {
      if (incoming === undefined || incoming === null || incoming === '') return existing
      if (this.isPlainObject(existing) && this.isPlainObject(incoming)) {
        return this.mergeEntry(existing, incoming)
      }
      return incoming
    },
    // Upsert by name: new items are added, matching ones are deep-merged
    mergeByName(current, incoming) {
      const result = (current || []).map(entry => ({ ...entry }))
      incoming.forEach(item => {
        const idx = result.findIndex(entry => entry.name === item.name)
        if (idx === -1) {
          result.push(item)
        } else {
          result.splice(idx, 1, this.mergeEntry(result[idx], item))
        }
      })
      return result
    },
    // Merge matching entries; when dropMissing, discard items absent from the import
    buildResult(current, incoming, dropMissing) {
      const merged = this.mergeByName(current, incoming)
      if (!dropMissing) return merged
      const names = new Set((incoming || []).map(entry => entry.name))
      return merged.filter(entry => names.has(entry.name))
    },
    confirmImport() {
      const parsed = this.parseImport()
      if (!parsed) return
      const dropMissing = this.importMode === 'replace'
      // Sections absent from the file are left untouched
      const providers = parsed.hasProviders
        ? this.buildResult(this.providers, parsed.providers, dropMissing)
        : this.providers
      const models = parsed.hasModels
        ? this.buildResult(this.models, parsed.models, dropMissing)
        : this.models
      this.importError = null
      this.showImport = false
      this.$emit('import', { providers, models, mode: this.importMode })
    }
  }
}
</script>