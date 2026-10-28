<script setup>
</script>

<template>
  <div class="fixed inset-0 z-[70] flex items-end sm:items-center justify-center sm:p-4">
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')"></div>

    <div
      class="relative w-full sm:max-w-2xl max-h-[90vh] bg-base-100 border border-base-content/10 rounded-t-2xl sm:rounded-2xl shadow-2xl flex flex-col overflow-hidden"
      role="dialog"
      aria-modal="true"
      :aria-label="`${name} skill details`"
    >
      <!-- Header -->
      <header class="flex items-center gap-3 px-4 py-3 border-b border-base-content/10 shrink-0">
        <div class="w-9 h-9 rounded-xl grid place-items-center bg-success/15 text-success shrink-0">
          <i class="fa-solid fa-wrench"></i>
        </div>
        <div class="min-w-0 flex-1">
          <h2 class="font-semibold font-mono text-sm truncate" :title="name">{{ name || 'Skill' }}</h2>
          <p class="text-[11px] text-base-content/50">Skill details</p>
        </div>
        <span v-if="selected" class="badge badge-sm badge-success gap-1 shrink-0">
          <i class="fa-solid fa-check text-[10px]"></i> Selected
        </span>
        <button
          type="button"
          class="btn btn-ghost btn-sm btn-square shrink-0"
          aria-label="Close skill details"
          @click="$emit('close')"
        >
          <i class="fa-solid fa-xmark"></i>
        </button>
      </header>

      <!-- Body -->
      <div class="flex-1 min-h-0 overflow-y-auto p-4 flex flex-col gap-4">
        <section v-if="description">
          <div class="text-xs font-semibold pb-1">What it does</div>
          <p class="text-sm text-base-content/70 leading-relaxed whitespace-pre-wrap">{{ description }}</p>
        </section>

        <section v-if="tags.length">
          <div class="text-xs font-semibold pb-1">Tags</div>
          <div class="flex flex-wrap gap-1">
            <span v-for="tag in tags" :key="tag" class="badge badge-sm badge-outline">{{ tag }}</span>
          </div>
        </section>

        <section v-if="parameterRows.length">
          <div class="flex items-center gap-2 pb-1">
            <span class="text-xs font-semibold">Arguments</span>
            <span class="badge badge-xs">{{ parameterRows.length }}</span>
          </div>
          <div class="rounded-lg border border-base-content/10 overflow-hidden">
            <table class="table table-xs">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in parameterRows" :key="row.name">
                  <td class="font-mono whitespace-nowrap">
                    {{ row.name }}
                    <span v-if="row.required" class="text-error" title="Required">*</span>
                  </td>
                  <td class="font-mono text-base-content/60 whitespace-nowrap">{{ row.type }}</td>
                  <td class="text-base-content/60">{{ row.description || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <details v-if="parametersJson" class="rounded-lg bg-base-200 border border-base-content/10">
          <summary class="cursor-pointer px-3 py-2 text-xs font-semibold text-base-content/70 hover:text-base-content">
            Raw arguments schema
          </summary>
          <pre class="px-3 pb-3 text-[11px] leading-relaxed whitespace-pre-wrap break-words text-base-content/60">{{ parametersJson }}</pre>
        </details>

        <details v-if="rawJson" class="rounded-lg bg-base-200 border border-base-content/10">
          <summary class="cursor-pointer px-3 py-2 text-xs font-semibold text-base-content/70 hover:text-base-content">
            Raw tool definition
          </summary>
          <pre class="px-3 pb-3 text-[11px] leading-relaxed whitespace-pre-wrap break-words text-base-content/60 max-h-64 overflow-y-auto">{{ rawJson }}</pre>
        </details>
      </div>

      <!-- Footer -->
      <footer class="flex items-center gap-2 px-4 py-3 border-t border-base-content/10 shrink-0">
        <span class="text-[11px] text-base-content/40 mr-auto truncate">Skills define what a teammate can do.</span>
        <button
          v-if="toggleable"
          type="button"
          class="btn btn-sm"
          :class="selected ? 'btn-ghost' : 'btn-primary'"
          @click="$emit('toggle', tool)"
        >
          <i class="fa-solid" :class="selected ? 'fa-minus' : 'fa-plus'"></i>
          {{ selected ? 'Remove' : 'Add' }}
        </button>
        <button type="button" class="btn btn-sm btn-ghost" @click="$emit('close')">Close</button>
      </footer>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ToolDetailsModal',
  props: {
    /** Tool entry as returned by `profiles.tools()` — `{ tool_json, tags }`. */
    tool: { type: Object, required: true },
    /** Whether the tool is currently enabled for the member being edited. */
    selected: { type: Boolean, default: false },
    /** Show the add/remove action in the footer. */
    toggleable: { type: Boolean, default: false }
  },
  emits: ['close', 'toggle'],
  computed: {
    fn() {
      return this.tool?.tool_json?.function || {}
    },
    name() {
      return this.fn.name || ''
    },
    description() {
      return this.fn.description || ''
    },
    tags() {
      return Array.isArray(this.tool?.tags) ? this.tool.tags : []
    },
    parameters() {
      return this.fn.parameters || null
    },
    // One row per documented argument; empty when the tool takes no arguments.
    parameterRows() {
      const properties = this.parameters?.properties
      if (!properties || typeof properties !== 'object') return []
      const required = Array.isArray(this.parameters.required) ? this.parameters.required : []
      return Object.entries(properties).map(([name, schema]) => ({
        name,
        type: schema?.type || (schema?.anyOf ? 'any' : '—'),
        required: required.includes(name),
        description: schema?.description || ''
      }))
    },
    parametersJson() {
      return this.parameters ? this.formatJson(this.parameters) : ''
    },
    rawJson() {
      return this.tool?.tool_json ? this.formatJson(this.tool.tool_json) : ''
    }
  },
  created() {
    window.addEventListener('keydown', this.onKeydown)
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onKeydown)
  },
  methods: {
    onKeydown(event) {
      if (event.key === 'Escape') this.$emit('close')
    },
    formatJson(value) {
      try {
        return JSON.stringify(value, null, 2)
      } catch {
        return String(value)
      }
    }
  }
}
</script>

<!-- Made with ❤️ by codx-junior -->