<script setup>
</script>

<template>
  <div
    v-if="suggestions.length"
    class="absolute bottom-full left-0 right-0 z-50"
  >
    <!-- Suggestion pills row -->
    <div class="flex flex-wrap gap-1 p-2 bg-base-200 border border-base-300 rounded-lg shadow-lg">
      <!-- Keyboard hint -->
      <div class="w-full flex items-center gap-2 text-xs text-base-content/80 pb-1 border-b border-base-300">
        <kbd class="kbd kbd-xs">Tab</kbd> accept
        <kbd class="kbd kbd-xs">↑↓</kbd> navigate
        <kbd class="kbd kbd-xs">Esc</kbd> dismiss
        <span class="ml-auto opacity-60">{{ suggestions.length }} suggestion{{ suggestions.length > 1 ? 's' : '' }}</span>
      </div>

      <!-- Suggestion items -->
      <div
        v-for="(s, i) in visibleSuggestions"
        :key="i"
        class="flex items-center gap-1 px-2 py-0.5 rounded cursor-pointer text-xs transition-all"
        :class="i === activeIndex
          ? 'bg-info text-info-content shadow'
          : 'bg-base-300 hover:bg-base-100 text-base-content'"
        @mousedown.prevent="$emit('select', s)"
        @mouseover="$emit('hover', i)"
      >
        <!-- Avatar / icon -->
        <img v-if="s.avatar" :src="s.avatar" class="w-4 h-4 rounded-full object-cover" />
        <i v-else-if="s.user" class="fa-solid fa-user text-[10px]" />
        <i v-else-if="s.profile" class="fa-solid fa-robot text-[10px]" />
        <i v-else-if="s.project" class="fa-solid fa-diagram-project text-[10px]" />
        <i v-else-if="s.file" class="fa-solid fa-file-code text-[10px]" />

        <!-- Name with fuzzy highlight -->
        <span class="tooltip" :data-tip="s.tooltip" v-html="highlightMatch(s.name, query)" />

        <!-- File path hint -->
        <span v-if="s.file" class="opacity-40 truncate max-w-24">{{ shortPath(s.file) }}</span>

        <!-- Active badge -->
        <span v-if="i === activeIndex" class="ml-1 opacity-60 text-[10px]">↵ Tab</span>
      </div>

      <!-- Overflow indicator -->
      <div v-if="suggestions.length > maxVisible" class="text-xs text-base-content/40 self-center px-1">
        +{{ suggestions.length - maxVisible }} more
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
  emits: ['select', 'hover'],
  computed: {
    visibleSuggestions() {
      return this.suggestions.slice(0, this.maxVisible)
    }
  },
  methods: {
    shortPath(file) {
      return file?.split('/').slice(-2).join('/')
    },
    // Wraps matched chars in <mark> for fuzzy highlight
    highlightMatch(name, query) {
      if (!query || query.length < 2) return name
      const q = query.toLowerCase()
      let result = ''
      let qi = 0
      for (let i = 0; i < name.length; i++) {
        const ch = name[i]
        if (qi < q.length && ch.toLowerCase() === q[qi]) {
          result += `<mark class="bg-warning/40 text-inherit rounded-sm">${ch}</mark>`
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