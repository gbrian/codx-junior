<script setup>
import Modal from '../Modal.vue'
</script>

<template>
  <div>
    <!-- Trigger button -->
    <button
      class="btn btn-sm btn-ghost gap-2"
      @click.stop="toggleGrid"
      :title="buttonTitle"
    >
      <i :class="icon"></i>
      <span class="text-xs font-semibold">{{ label }}</span>

      <!-- Single select: selected badge or "default" label -->
      <template v-if="isSingle">
        <div v-if="selectedItem" class="badge badge-sm gap-1 badge-primary">
          <img
            v-if="selectedItem.avatar"
            :src="selectedItem.avatar"
            :alt="selectedItem.name"
            class="w-3 h-3 rounded-full object-cover"
          />
          <span class="truncate text-xs max-w-[100px]">{{ selectedItem.name }}</span>
        </div>
        <div v-else-if="emptyLabel" class="badge badge-sm badge-ghost text-xs opacity-60">
          {{ emptyLabel }}
        </div>
      </template>

      <!-- Multi select: up to 1 badge + overflow count -->
      <div v-else-if="activeItems.length" class="flex gap-1 items-center">
        <div
          v-for="item in activeItems.slice(0, 1)"
          :key="item.name"
          class="badge badge-sm gap-1 badge-primary"
          :title="item.description"
        >
          <img
            v-if="item.avatar"
            :src="item.avatar"
            :alt="item.name"
            class="w-3 h-3 rounded-full object-cover"
          />
          <span class="truncate text-xs max-w-[60px]">{{ item.name }}</span>
        </div>
        <div v-if="activeItems.length > 1" class="badge badge-sm badge-primary text-xs">
          +{{ activeItems.length - 1 }}
        </div>
      </div>
    </button>

    <!-- Custom Modal Component -->
    <Modal
      v-if="isModalOpen"
      :close="true"
      class="w-11/12 max-w-2xl"
      @close="closeModal"
    >
      <!-- Header Slot -->
      <template #header>
        <h3 class="text-lg font-bold">{{ label }}</h3>
      </template>

      <!-- Body Content -->
      <!-- Filter input -->
      <input
        v-model="filterText"
        type="text"
        placeholder="Type to filter..."
        class="input input-sm input-bordered w-full mb-3"
        @click.stop
      />

      <!-- Quick tag filter (opt-in via enableTagFilter) -->
      <div
        v-if="enableTagFilter && availableTags.length"
        class="flex flex-wrap gap-1.5 mb-4"
        role="group"
        aria-label="Filter by tag"
      >
        <button
          v-for="tag in availableTags"
          :key="tag"
          type="button"
          class="btn btn-xs gap-1 normal-case"
          :class="selectedTags.includes(tag)
            ? 'btn-primary'
            : 'btn-ghost border border-base-content/15 text-base-content/70'"
          :aria-pressed="selectedTags.includes(tag)"
          @click.stop="toggleTag(tag)"
        >
          <i class="fa-solid fa-tag text-[10px]" aria-hidden="true"></i>
          {{ tag }}
        </button>
        <button
          v-if="selectedTags.length"
          type="button"
          class="btn btn-xs btn-ghost gap-1 text-error"
          @click.stop="clearTags"
        >
          <i class="fa-solid fa-xmark text-[10px]" aria-hidden="true"></i>
          clear
        </button>
      </div>

      <!-- Scrollable grid with custom slot rendering -->
      <div class="grid grid-cols-3 gap-2 overflow-y-auto max-h-96 mb-4">
        <div
          v-for="(item, ix) in filteredAndSorted"
          :key="item.name"
          class="click"
          @click="selectItem(item)"
        >
          <!-- Slot for custom rendering -->
          <slot
            :item="item"
            :ix="ix"
            :selected="isItemSelected(item.name)"
          >
            <!-- Default rendering fallback -->
            <div class="flex flex-col items-center gap-1 p-2 rounded-lg cursor-pointer transition-all hover:bg-base-300"
              :class="isItemSelected(item.name) ? 'bg-primary text-primary-content' : 'bg-base-100'"
              :title="item.description"
            >
              <div class="relative">
                <img
                  v-if="item.avatar"
                  :src="item.avatar"
                  :alt="item.name"
                  class="w-3 h-3 rounded-full object-cover"
                />
                <div
                  v-else
                  class="w-8 h-8 rounded-full bg-base-300 flex items-center justify-center"
                >
                  <i class="fa-solid fa-user text-xs"></i>
                </div>
                <div
                  v-if="isItemSelected(item.name)"
                  class="absolute -top-1 -right-1 bg-success  rounded-full w-4 h-4 flex items-center justify-center text-xs"
                >
                  ✓
                </div>
              </div>
              <span class="text-xs font-medium text-center truncate w-full">{{ item.name }}</span>
            </div>
          </slot>
        </div>
      </div>

      <!-- Footer Slot -->
      <template #footer>
        <span class="text-xs text-base-content/60 flex-1">{{ selectedCountText }}</span>
        <button
          v-if="allowDeselect && selectedItem"
          type="button"
          class="btn btn-sm btn-ghost"
          @click.stop="deselectAll"
        >
          clear
        </button>
        <button
          type="button"
          class="btn btn-sm btn-primary"
          @click.stop="confirmModal"
        >
          Done
        </button>
      </template>
    </Modal>
  </div>
</template>

<script>
export default {
  props: {
    items: {
      type: Array,
      default: () => []
    },
    selectedItems: {
      type: Array,
      default: () => []
    },
    label: {
      type: String,
      required: true
    },
    icon: {
      type: String,
      required: true
    },
    isSingleSelect: {
      type: Boolean,
      default: false
    },
    single: {
      type: Boolean,
      default: false
    },
    allowDeselect: {
      type: Boolean,
      default: false
    },
    emptyLabel: {
      type: String,
      default: ''
    },
    // When enabled, a quick filter bar is shown using each item's `tags` array
    enableTagFilter: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:selected-items', 'open', 'select'],
  data() {
    return {
      internalSelected: [],
      filterText: '',
      tempSelected: [],
      isModalOpen: false,
      selectedTags: []
    }
  },
  computed: {
    isSingle() {
      return this.single || this.isSingleSelect
    },
    // Unique tags across items, used to render the quick filter bar
    availableTags() {
      if (!this.enableTagFilter) return []
      const tags = new Set()
      ;(this.items || []).forEach(item => {
        (item.tags || []).forEach(tag => tags.add(tag))
      })
      return [...tags].sort((a, b) => a.localeCompare(b))
    },
    filteredAndSorted() {
      const q = this.filterText.toLowerCase()
      const activeTags = this.selectedTags.map(t => t.toLowerCase())
      return (this.items || [])
        .filter(item => {
          if (q && !item.name.toLowerCase().includes(q)) return false
          if (!activeTags.length) return true
          // AND semantics: the item must carry every selected tag
          const itemTags = (item.tags || []).map(t => t.toLowerCase())
          return activeTags.every(tag => itemTags.includes(tag))
        })
        .sort((a, b) => a.name.localeCompare(b.name))
    },
    activeItems() {
      return (this.items || []).filter(item => this.internalSelected.includes(item.name))
    },
    selectedItem() {
      if (!this.isSingle || !this.internalSelected.length) return null
      // Resolve against the full list so the trigger badge survives tag filtering
      return (this.items || []).find(item => item.name === this.internalSelected[0]) || null
    },
    buttonTitle() {
      if (this.isSingle) {
        return this.selectedItem ? this.selectedItem.name : (this.emptyLabel || `Select ${this.label}`)
      }
      return this.activeItems.length ? `${this.activeItems.length} selected` : `Select ${this.label.toLowerCase()}`
    },
    selectedCountText() {
      if (this.isSingle) {
        return this.selectedItem ? `Selected: ${this.selectedItem.name}` : (this.emptyLabel ? `Using ${this.emptyLabel}` : 'None selected')
      }
      return `${this.internalSelected.length} selected`
    }
  },
  watch: {
    selectedItems: {
      handler(newVal) {
        this.internalSelected = newVal.map(item => typeof item === 'string' ? item : item.name)
        this.tempSelected = [...this.internalSelected]
      },
      deep: true,
      immediate: true
    }
  },
  methods: {
    toggleGrid() {
      this.openModal()
    },
    openModal() {
      this.filterText = ''
      this.selectedTags = []
      this.tempSelected = [...this.internalSelected]
      this.$emit('open')
      this.isModalOpen = true
    },
    closeModal() {
      this.internalSelected = [...this.tempSelected]
      this.isModalOpen = false
    },
    confirmModal() {
      this.emitSelectionChange()
      this.isModalOpen = false
    },
    emitSelectionChange() {
      const updated = (this.items || []).filter(i => this.internalSelected.includes(i.name))
      this.$emit('update:selected-items', updated)
    },
    isItemSelected(itemName) {
      return this.internalSelected.includes(itemName)
    },
    selectItem(item) {
      if (this.isSingle) {
        // Single mode: only one item can be selected at a time
        if (this.allowDeselect && this.internalSelected[0] === item.name) {
          this.internalSelected = []
        } else {
          this.internalSelected = [item.name]
        }
        // Notify listeners with the selected item (or null when cleared)
        this.$emit('select', this.selectedItem)
      } else {
        const idx = this.internalSelected.indexOf(item.name)
        if (idx > -1) {
          this.internalSelected.splice(idx, 1)
        } else {
          this.internalSelected.push(item.name)
        }
      }
    },
    // Toggle a quick-filter tag on/off
    toggleTag(tag) {
      const idx = this.selectedTags.indexOf(tag)
      if (idx > -1) {
        this.selectedTags.splice(idx, 1)
      } else {
        this.selectedTags.push(tag)
      }
    },
    clearTags() {
      this.selectedTags = []
    },
    deselectAll() {
      this.internalSelected = []
      if (this.isSingle) {
        this.$emit('select', null)
      }
    }
  }
}
</script>