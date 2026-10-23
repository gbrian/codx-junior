<script setup>
</script>

<template>
  <div class="icon-selector relative" @click.stop>
    <!-- Trigger — single compact button (icon only) when `buttonOnly`, else the
         full-width labelled button used across the app. -->
    <button
      v-if="buttonOnly"
      type="button"
      class="btn btn-sm btn-square shrink-0"
      :aria-expanded="open"
      aria-haspopup="true"
      :aria-label="`Choose ${label}`"
      :title="currentLabel"
      @click="toggleOpen"
    >
      <i v-if="currentClass" :class="currentClass" class="text-sm" aria-hidden="true"></i>
      <i v-else class="fa-regular fa-circle text-sm opacity-40" aria-hidden="true"></i>
    </button>

    <button
      v-else
      type="button"
      class="btn btn-sm btn-ghost border border-base-100 w-full justify-start gap-2 font-normal"
      :aria-expanded="open"
      aria-haspopup="true"
      :aria-label="`Choose ${label}`"
      @click="toggleOpen"
    >
      <span class="w-6 h-6 rounded-md bg-base-200 flex items-center justify-center shrink-0">
        <i v-if="currentClass" :class="currentClass" class="text-xs" aria-hidden="true"></i>
        <i v-else class="fa-regular fa-circle text-xs opacity-40" aria-hidden="true"></i>
      </span>
      <span class="text-xs truncate">{{ currentLabel }}</span>
      <i class="fa-solid fa-chevron-down text-[10px] ml-auto opacity-50" aria-hidden="true"></i>
    </button>

    <!-- Panel -->
    <div
      v-if="open"
      class="absolute top-full z-50 mt-1 rounded-box border border-base-100 bg-base-200 shadow-xl p-2"
      :class="buttonOnly ? 'right-0 w-72' : 'left-0 right-0'"
    >
      <!-- Search -->
      <div class="flex items-center gap-1.5">
        <label class="input input-xs input-bordered flex items-center gap-2 grow">
          <i class="fa-solid fa-magnifying-glass text-[10px] opacity-40" aria-hidden="true"></i>
          <input
            ref="searchInput"
            v-model="search"
            type="text"
            :placeholder="placeholder"
            class="grow bg-transparent outline-none text-xs min-w-0"
            @keydown.escape="close"
          />
        </label>
        <button
          v-if="modelValue"
          type="button"
          class="btn btn-xs btn-ghost text-error shrink-0"
          title="Remove icon"
          aria-label="Remove icon"
          @click="clear"
        >
          <i class="fa-solid fa-xmark text-xs" aria-hidden="true"></i>
        </button>
      </div>

      <!-- Icon grid -->
      <div class="mt-2 max-h-48 overflow-y-auto pr-0.5">
        <template v-for="group in filteredGroups" :key="group.label">
          <div class="text-[10px] font-semibold uppercase tracking-wider opacity-40 px-1 pt-2 pb-1">
            {{ group.label }}
          </div>
          <div class="grid grid-cols-8 gap-1">
            <button
              v-for="icon in group.icons"
              :key="icon"
              type="button"
              class="aspect-square rounded-md flex items-center justify-center transition-colors"
              :class="isSelected(icon)
                ? 'bg-primary text-primary-content'
                : 'hover:bg-base-300 text-base-content/70'"
              :title="icon.replace('fa-', '')"
              @click="select(icon)"
            >
              <i :class="iconClass(icon)" class="text-sm" aria-hidden="true"></i>
            </button>
          </div>
        </template>
        <div v-if="!filteredGroups.length" class="py-6 text-center text-xs opacity-40">
          No icons match “{{ search }}”
        </div>
      </div>

      <!-- Free-text class -->
      <div class="mt-2 pt-2 border-t border-base-100">
        <label class="label py-0.5">
          <span class="label-text-alt text-[10px] opacity-50">Or type any Font Awesome class</span>
        </label>
        <input
          v-model="custom"
          type="text"
          placeholder="fa-solid fa-star"
          class="input input-xs input-bordered w-full font-mono text-[11px]"
          @keydown.enter.prevent="applyCustom"
        />
      </div>
    </div>
  </div>
</template>

<script>
// Curated catalogue of Font Awesome 6 free solid icons, grouped for scanning.
// Names are stored as `fa-<name>` (the `fa-solid` style prefix is added when
// rendering). Any other class can still be entered manually in the panel.
const ICON_CATALOG = [
  {
    label: 'Status',
    icons: [
      'fa-circle-dot', 'fa-circle-play', 'fa-circle-pause', 'fa-circle-check',
      'fa-circle-xmark', 'fa-circle', 'fa-circle-half-stroke', 'fa-circle-notch',
      'fa-spinner', 'fa-hourglass-half', 'fa-flag', 'fa-flag-checkered',
      'fa-check', 'fa-xmark', 'fa-ban', 'fa-bell'
    ]
  },
  {
    label: 'Tasks & Planning',
    icons: [
      'fa-list', 'fa-list-check', 'fa-list-ul', 'fa-list-ol', 'fa-table-list',
      'fa-layer-group', 'fa-diagram-project', 'fa-sitemap', 'fa-tasks',
      'fa-clipboard-list', 'fa-clipboard-check', 'fa-bars-progress', 'fa-inbox',
      'fa-bullseye', 'fa-crosshairs', 'fa-boxes-stacked', 'fa-rocket', 'fa-bolt',
      'fa-fire', 'fa-bookmark', 'fa-thumbtack', 'fa-star', 'fa-arrow-trend-up',
      'fa-wand-magic-sparkles'
    ]
  },
  {
    label: 'Code & Dev',
    icons: [
      'fa-code', 'fa-code-branch', 'fa-code-merge', 'fa-terminal', 'fa-bug',
      'fa-wrench', 'fa-screwdriver-wrench', 'fa-gear', 'fa-gears', 'fa-database',
      'fa-server', 'fa-microchip', 'fa-plug', 'fa-puzzle-piece', 'fa-file-code',
      'fa-laptop-code', 'fa-robot', 'fa-brain', 'fa-shield-halved', 'fa-lock',
      'fa-key', 'fa-fingerprint'
    ]
  },
  {
    label: 'Files & Data',
    icons: [
      'fa-file', 'fa-file-lines', 'fa-file-image', 'fa-file-pdf', 'fa-folder',
      'fa-folder-open', 'fa-folder-plus', 'fa-floppy-disk', 'fa-download',
      'fa-upload', 'fa-cloud', 'fa-cloud-arrow-up', 'fa-paperclip', 'fa-link',
      'fa-image', 'fa-images', 'fa-camera', 'fa-video', 'fa-music', 'fa-photo-film'
    ]
  },
  {
    label: 'Communication',
    icons: [
      'fa-comment', 'fa-comments', 'fa-comment-dots', 'fa-message', 'fa-envelope',
      'fa-paper-plane', 'fa-bullhorn', 'fa-phone', 'fa-headset', 'fa-at',
      'fa-hashtag', 'fa-share-nodes', 'fa-reply', 'fa-quote-left', 'fa-bell-concierge'
    ]
  },
  {
    label: 'People & Teams',
    icons: [
      'fa-user', 'fa-users', 'fa-user-gear', 'fa-user-plus', 'fa-user-check',
      'fa-user-clock', 'fa-people-group', 'fa-person', 'fa-person-running',
      'fa-handshake', 'fa-hand-holding-heart', 'fa-id-badge', 'fa-address-book',
      'fa-crown', 'fa-user-shield'
    ]
  },
  {
    label: 'Time',
    icons: [
      'fa-calendar', 'fa-calendar-days', 'fa-calendar-check', 'fa-calendar-plus',
      'fa-calendar-week', 'fa-clock', 'fa-stopwatch', 'fa-hourglass', 'fa-history',
      'fa-timeline'
    ]
  },
  {
    label: 'Analytics',
    icons: [
      'fa-chart-line', 'fa-chart-bar', 'fa-chart-column', 'fa-chart-pie',
      'fa-chart-area', 'fa-gauge', 'fa-gauge-high', 'fa-table', 'fa-table-cells',
      'fa-percent', 'fa-calculator', 'fa-magnifying-glass-chart', 'fa-coins',
      'fa-sack-dollar', 'fa-wallet', 'fa-money-bill-trend-up', 'fa-scale-balanced'
    ]
  },
  {
    label: 'Design',
    icons: [
      'fa-palette', 'fa-pen-nib', 'fa-brush', 'fa-paintbrush', 'fa-pen',
      'fa-pen-to-square', 'fa-pencil', 'fa-vector-square', 'fa-shapes',
      'fa-object-group', 'fa-crop', 'fa-wand-magic', 'fa-icons', 'fa-font',
      'fa-text-height', 'fa-highlighter'
    ]
  },
  {
    label: 'General',
    icons: [
      'fa-lightbulb', 'fa-circle-info', 'fa-triangle-exclamation',
      'fa-circle-exclamation', 'fa-circle-question', 'fa-eye', 'fa-eye-slash',
      'fa-unlock', 'fa-globe', 'fa-location-dot', 'fa-map', 'fa-compass', 'fa-home',
      'fa-building', 'fa-graduation-cap', 'fa-trophy', 'fa-medal', 'fa-award',
      'fa-magnet', 'fa-anchor', 'fa-compress', 'fa-expand', 'fa-arrows-rotate'
    ]
  }
]

export default {
  name: 'IconSelector',
  props: {
    // Selected Font Awesome class. Accepts a full class ("fa-solid fa-star"),
    // a prefixed name ("fa-star") or a bare name ("star").
    modelValue: { type: String, default: '' },
    // Label used for the trigger's accessible name
    label: { type: String, default: 'Icon' },
    placeholder: { type: String, default: 'Search icons…' },
    // When true the trigger is a compact square icon-only button (used inline,
    // e.g. next to an input) instead of the full-width labelled button.
    buttonOnly: { type: Boolean, default: false }
  },
  emits: ['update:modelValue'],
  data() {
    return {
      open: false,
      search: '',
      custom: '',
      catalog: ICON_CATALOG
    }
  },
  computed: {
    // Normalized Font Awesome class for the currently selected value
    currentClass() {
      return this.iconClass(this.modelValue)
    },
    currentLabel() {
      return this.modelValue || 'No icon'
    },
    // Catalogue filtered by the search text (groups with no match are dropped)
    filteredGroups() {
      const q = this.search.trim().toLowerCase()
      return this.catalog
        .map(group => ({
          label: group.label,
          icons: group.icons.filter(icon => !q || icon.includes(q))
        }))
        .filter(group => group.icons.length)
    }
  },
  mounted() {
    // Close the panel when clicking anywhere outside the component
    document.addEventListener('click', this.onDocumentClick)
  },
  unmounted() {
    document.removeEventListener('click', this.onDocumentClick)
  },
  methods: {
    // Build a full Font Awesome class out of any of the supported inputs.
    iconClass(name) {
      if (!name) return null
      const value = String(name).trim()
      if (/^fa-(solid|regular|brands|light|thin|duotone|sharp)\b/.test(value)) return value
      if (value.startsWith('fa-')) return `fa-solid ${value}`
      return `fa-solid fa-${value}`
    },
    isSelected(icon) {
      return this.currentClass === `fa-solid ${icon}`
    },
    toggleOpen() {
      this.open = !this.open
      if (this.open) this.$nextTick(() => this.$refs.searchInput?.focus())
    },
    close() {
      this.open = false
      this.search = ''
      this.custom = ''
    },
    onDocumentClick() {
      if (this.open) this.close()
    },
    select(icon) {
      this.$emit('update:modelValue', `fa-solid ${icon}`)
      this.close()
    },
    clear() {
      this.$emit('update:modelValue', '')
      this.close()
    },
    // Persist a manually typed class (e.g. "fa-brands fa-trello")
    applyCustom() {
      const value = this.custom.trim()
      if (!value) return
      this.$emit('update:modelValue', this.iconClass(value))
      this.close()
    }
  }
}
</script>