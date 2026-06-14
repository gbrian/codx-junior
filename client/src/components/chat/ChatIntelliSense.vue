<script setup>
</script>

<template>
  <div
    v-if="suggestions.length"
    class="absolute bottom-full left-0 right-0 z-50"
  >
    <div class="flex flex-wrap gap-1 p-2 bg-base-200 border rounded-lg shadow-lg">
      <!-- Keyboard hint -->
      <div class="w-full flex items-center gap-2 text-base-content/80 pb-1 border-b border-base-300">
        <kbd class="kbd kbd-xs">Tab</kbd> accept
        <kbd class="kbd kbd-xs">Space</kbd> select
        <kbd class="kbd kbd-xs">Esc</kbd> dismiss
        <span v-if="selectedItems.length" class="ml-1 text-info font-semibold flex items-center gap-1">
          {{ selectedItems.length }} selected
          <button class="btn btn-xs btn-info ml-1" @mousedown.prevent="$emit('accept-multi', selectedItems)">
            Add all
          </button>
        </span>
        <span class="ml-auto opacity-60">{{ suggestions.length }} suggestion{{ suggestions.length > 1 ? 's' : '' }}</span>
      </div>

      <!-- Project filter pills -->
      <div v-if="uniqueProjects.length > 1" class="w-full flex flex-wrap items-center gap-1 pb-1 border-b border-base-300">
        <span class="text-base-content/50 self-center text-xs">Filter:</span>
        <button
          class="badge badge-xs cursor-pointer transition-colors"
          :class="!activeProject ? 'badge-info' : 'badge-ghost'"
          @mousedown.prevent="activeProject = null"
        >All</button>
        <button
          v-for="proj in uniqueProjects"
          :key="proj.project_id"
          class="flex items-center gap-1 px-2 py-0.5 rounded-full cursor-pointer transition-colors text-xs"
          :class="activeProject === proj.project_id ? 'bg-info/20 text-info' : 'bg-base-300 hover:bg-base-100'"
          @mousedown.prevent="activeProject = proj.project_id"
        >
          <img :src="proj.project_icon" class="w-3 h-3 rounded-full object-cover" />
          {{ proj.project_name }}
        </button>
      </div>

      <!-- Scrollable suggestion list -->
      <div ref="listRef" class="w-full flex flex-col gap-0.5 overflow-y-auto max-h-52 pr-1">
        <div
          v-for="(s, i) in filteredSuggestions"
          :key="i"
          :ref="el => { if (i === activeIndex) activeEl = el }"
          class="w-full flex items-center gap-1.5 px-2 h-6 rounded cursor-pointer transition-colors ring-1 ring-transparent flex-none"
          :class="itemClass(s, i)"
          @mousedown.prevent="onItemClick($event, s, i)"
          @mouseover="hoveredIndex = i; $emit('hover', i)"
          @mouseleave="hoveredIndex = null"
        >
          <!-- Multi-select checkbox -->
          <input
            type="checkbox"
            class="checkbox checkbox-xs flex-none"
            :checked="isSelected(s)"
            @mousedown.stop
            @change.prevent="toggleSelected(s)"
          />

          <!-- Avatar / icon -->
          <span class="flex-none w-4 flex items-center justify-center">
            <img v-if="s.avatar" :src="s.avatar" class="w-4 h-4 rounded-full object-cover" />
            <i v-else-if="s.user" class="fa-solid fa-user text-[10px]" />
            <i v-else-if="s.profile" class="fa-solid fa-robot text-[10px]" />
            <i v-else-if="s.project" class="fa-solid fa-diagram-project text-[10px]" />
            <i v-else-if="s.file" class="fa-solid fa-file-code text-[10px]" />
          </span>

          <!-- Name with fuzzy highlight -->
          <span class="flex-1 truncate text-xs" v-html="highlightMatch(s.name, query)" />

          <!-- Project badge -->
          <span
            v-if="s.project && s.project.project_name"
            class="flex-none flex items-center gap-1 opacity-50 text-[9px] badge badge-ghost badge-xs"
          >
            <img
              :src="s.project.project_icon || '/only_icon.png'"
              class="w-2.5 h-2.5 rounded-full object-cover"
            />
            {{ s.project.project_name }}
          </span>

          <!-- File path hint -->
          <span v-if="s.file" class="flex-none opacity-40 truncate max-w-24 text-[10px]">{{ shortPath(s.file) }}</span>

          <!-- Tab hint -->
          <span class="flex-none w-10 text-right opacity-50 text-[10px]">
            <template v-if="i === activeIndex && !selectedItems.length">↵ Tab</template>
          </span>
        </div>
      </div>

      <!-- Result count footer -->
      <div class="w-full text-base-content/40 text-xs text-right pt-1 border-t border-base-300">
        {{ filteredSuggestions.length }} result{{ filteredSuggestions.length !== 1 ? 's' : '' }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    suggestions: { type: Array, default: () => [] },
    activeIndex: { type: Number, default: 0 },
    query: { type: String, default: '' },
    maxVisible: { type: Number, default: 8 }
  },
  emits: ['select', 'hover', 'accept-multi'],
  data() {
    return {
      activeProject: null,
      hoveredIndex: null,
      selectedItems: [],
      activeEl: null
    }
  },
  watch: {
    suggestions() {
      this.selectedItems = []
      this.hoveredIndex = null
    },
    // Scroll active item into view when navigating with keyboard
    activeIndex() {
      this.$nextTick(() => {
        if (this.activeEl) {
          this.activeEl.scrollIntoView({ block: 'nearest' })
        }
      })
    }
  },
  computed: {
    uniqueProjects() {
      const seen = new Set()
      return this.suggestions
        .map(s => s.project)
        .filter(p => p?.project_id && !seen.has(p.project_id) && seen.add(p.project_id))
    },
    filteredSuggestions() {
      if (!this.activeProject) return this.suggestions
      return this.suggestions.filter(s => s.project?.project_id === this.activeProject)
    }
  },
  methods: {
    shortPath(file) {
      return file?.split('/').slice(-2).join('/')
    },
    itemKey(s) {
      return (s.file || '') + '|' + (s.name || '')
    },
    isSelected(s) {
      return this.selectedItems.some(x => this.itemKey(x) === this.itemKey(s))
    },
    toggleSelected(s) {
      if (this.isSelected(s)) {
        this.selectedItems = this.selectedItems.filter(x => this.itemKey(x) !== this.itemKey(s))
      } else {
        this.selectedItems = [...this.selectedItems, s]
      }
    },
    onItemClick(event, s, i) {
      if (this.selectedItems.length > 0 || event.shiftKey || event.ctrlKey) {
        this.toggleSelected(s)
      } else {
        this.$emit('select', s)
      }
    },
    itemClass(s, i) {
      const isActive = i === this.activeIndex
      const isHovered = i === this.hoveredIndex
      const selected = this.isSelected(s)

      if (selected) return 'bg-info/15 ring-info/60 text-base-content'
      if (isActive) return 'bg-info/30 ring-info/40 text-base-content font-medium'
      if (isHovered) return 'bg-base-300/60 ring-base-content/10 text-base-content'
      return 'bg-base-300/30 text-base-content/80'
    },
    highlightMatch(name, query) {
      if (!query || query.length < 2) return name
      const q = query.toLowerCase()
      let result = ''
      let qi = 0
      for (let i = 0; i < name.length; i++) {
        const ch = name[i]
        if (qi < q.length && ch.toLowerCase() === q[qi]) {
          result += `<span class="font-bold">${ch}</span>`
          qi++
        } else {
          result += ch
        }
      }
      return result
    }
  }
}
</script>