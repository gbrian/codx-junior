<template>
  <div>
    <div v-if="label" class="label-text text-xs font-semibold pb-1">{{ label }}</div>
    <p v-if="hint" class="text-[11px] text-base-content/50 mb-2">{{ hint }}</p>

    <!-- Select (sorted by name) + add button -->
    <div class="join w-full">
      <select
        v-model="selection"
        class="select select-sm select-bordered join-item flex-1"
        :disabled="disabled || !availableOptions.length"
        :aria-label="`Add ${label || 'profile'}`"
        @keydown.enter.prevent="add"
      >
        <option value="">
          {{ availableOptions.length ? placeholder : emptyOptionsText }}
        </option>
        <option v-for="name in availableOptions" :key="name" :value="name">
          {{ name }}
        </option>
      </select>
      <button
        type="button"
        class="btn btn-sm btn-primary join-item"
        :disabled="disabled || !selection"
        :title="addTitle"
        :aria-label="addTitle"
        @click="add"
      >
        <i class="fa-solid fa-plus"></i>
      </button>
    </div>

    <!-- Added entries, each with a remove (cross) button -->
    <ul v-if="modelValue.length" class="flex flex-col gap-1 mt-2">
      <li
        v-for="name in modelValue"
        :key="name"
        class="flex items-center gap-2 rounded-md bg-base-200 border border-base-content/10 px-2 py-1"
      >
        <i :class="icon" class="text-[10px]"></i>
        <span class="text-xs flex-1 truncate">{{ name }}</span>
        <button
          type="button"
          class="btn btn-ghost btn-xs btn-square text-error"
          :disabled="disabled"
          :title="`Remove ${name}`"
          :aria-label="`Remove ${name}`"
          @click="remove(name)"
        >
          <i class="fa-solid fa-xmark text-[10px]"></i>
        </button>
      </li>
    </ul>
    <p v-else class="text-xs text-base-content/40 mt-2">{{ emptyText }}</p>
  </div>
</template>

<script>
export default {
  name: 'ProfileMultiSelect',
  props: {
    /** Selected profile names (linked profiles or team). */
    modelValue: { type: Array, default: () => [] },
    /** Every selectable profile name (sorted by the parent). */
    options: { type: Array, default: () => [] },
    /** Names that are already used elsewhere and must not be offered. */
    exclude: { type: Array, default: () => [] },
    label: { type: String, default: '' },
    hint: { type: String, default: '' },
    placeholder: { type: String, default: 'Select a profile…' },
    emptyOptionsText: { type: String, default: 'No profiles available' },
    emptyText: { type: String, default: 'None added yet.' },
    addTitle: { type: String, default: 'Add' },
    icon: { type: String, default: 'fa-solid fa-user' },
    disabled: { type: Boolean, default: false }
  },
  emits: ['update:modelValue', 'add', 'remove'],
  data() {
    return { selection: '' }
  },
  computed: {
    // Sorted by name and never offering what is already in the list.
    availableOptions() {
      const used = new Set([...(this.modelValue || []), ...(this.exclude || [])])
      return (this.options || [])
        .filter(name => name && !used.has(name))
        .sort((a, b) => a.localeCompare(b))
    }
  },
  methods: {
    add() {
      const name = this.selection
      if (!name || this.disabled) return
      if (!this.modelValue.includes(name)) {
        this.$emit('update:modelValue', [...this.modelValue, name])
        this.$emit('add', name)
      }
      this.selection = ''
    },
    remove(name) {
      if (this.disabled) return
      this.$emit('update:modelValue', this.modelValue.filter(item => item !== name))
      this.$emit('remove', name)
    }
  }
}
</script>

<!-- Made with ❤️ by codx-junior -->