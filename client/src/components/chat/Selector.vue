<script setup>
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
      <template v-if="isSingleSelect">
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

    <!-- Dropdown panel (when modal is disabled) -->
    <div
      v-if="!useModal"
      v-show="showGrid"
      class="absolute left-0 bottom-full mb-2 bg-base-200 rounded-lg border border-base-300 shadow-lg z-50 w-full"
      @click.stop
    >
      <div class="p-3 flex flex-col gap-2">
        <div class="text-sm font-semibold">{{ label }}</div>

        <!-- Filter input -->
        <input
          v-model="filterText"
          type="text"
          placeholder="Type to filter..."
          class="input input-sm input-bordered w-full"
          @click.stop
        />

        <!-- Scrollable grid with custom slot rendering -->
        <div class="grid grid-cols-3 gap-2 overflow-y-auto max-h-56">
          <div
            v-for="(item, ix) in filteredAndSorted"
            :key="item.name"
            :class="isItemSelected(item.name) ? 'ring-2 ring-primary' : ''"
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
                    class="absolute -top-1 -right-1 bg-success text-white rounded-full w-4 h-4 flex items-center justify-center text-xs"
                  >
                    ✓
                  </div>
                </div>
                <span class="text-xs font-medium text-center truncate w-full">{{ item.name }}</span>
              </div>
            </slot>
          </div>
        </div>

        <!-- Footer: count or deselect hint -->
        <div class="text-xs text-base-content/60 border-t border-base-300 pt-2 flex justify-between items-center">
          <span>{{ selectedCountText }}</span>
          <button
            v-if="allowDeselect && selectedItem"
            class="btn btn-xs btn-ghost"
            @click.stop="deselectAll"
          >
            clear
          </button>
        </div>
      </div>
    </div>

    <!-- DaisyUI Modal (when useModal is true) -->
    <dialog
      v-if="useModal"
      ref="selectorModal"
      class="modal"
      @click.stop="handleModalBackdropClick"
    >
      <div class="modal-box w-11/12 max-w-2xl">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold">{{ label }}</h3>
          <button
            type="button"
            class="btn btn-sm btn-circle btn-ghost"
            @click.stop="closeModal"
          >
            ✕
          </button>
        </div>

        <!-- Filter input -->
        <input
          v-model="filterText"
          type="text"
          placeholder="Type to filter..."
          class="input input-sm input-bordered w-full mb-4"
          @click.stop
        />

        <!-- Scrollable grid with custom slot rendering -->
        <div class="grid grid-cols-4 gap-2 overflow-y-auto max-h-96 mb-4">
          <div
            v-for="(item, ix) in filteredAndSorted"
            :key="item.name"
            :class="isItemSelected(item.name) ? 'ring-2 ring-primary' : ''"
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
                    class="absolute -top-1 -right-1 bg-success text-white rounded-full w-4 h-4 flex items-center justify-center text-xs"
                  >
                    ✓
                  </div>
                </div>
                <span class="text-xs font-medium text-center truncate w-full">{{ item.name }}</span>
              </div>
            </slot>
          </div>
        </div>

        <!-- Footer: count or deselect hint -->
        <div class="flex justify-between items-center border-t border-base-300 pt-4">
          <span class="text-xs text-base-content/60">{{ selectedCountText }}</span>
          <div class="flex gap-2">
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
          </div>
        </div>
      </div>

      <!-- Modal backdrop with form method for native close -->
      <form method="dialog" class="modal-backdrop">
        <button type="button">close</button>
      </form>
    </dialog>
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
    allowDeselect: {
      type: Boolean,
      default: false
    },
    emptyLabel: {
      type: String,
      default: ''
    },
    useModal: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      internalSelected: [],
      showGrid: false,
      filterText: '',
      tempSelected: []
    }
  },
  computed: {
    filteredAndSorted() {
      const q = this.filterText.toLowerCase()
      return (this.items || [])
        .filter(item => item.name.toLowerCase().includes(q))
        .sort((a, b) => a.name.localeCompare(b.name))
    },
    activeItems() {
      return (this.items || []).filter(item => this.internalSelected.includes(item.name))
    },
    selectedItem() {
      if (!this.isSingleSelect || !this.internalSelected.length) return null
      return (this.items || []).find(item => item.name === this.internalSelected[0]) || null
    },
    buttonTitle() {
      if (this.isSingleSelect) {
        return this.selectedItem ? this.selectedItem.name : (this.emptyLabel || `Select ${this.label}`)
      }
      return this.activeItems.length ? `${this.activeItems.length} selected` : `Select ${this.label.toLowerCase()}`
    },
    selectedCountText() {
      if (this.isSingleSelect) {
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
  mounted() {
    document.addEventListener('click', this.handleDocumentClick)
  },
  unmounted() {
    document.removeEventListener('click', this.handleDocumentClick)
  },
  methods: {
    toggleGrid() {
      if (this.useModal) {
        this.showGrid ? this.closeModal() : this.openModal()
      } else {
        this.showGrid = !this.showGrid
        if (this.showGrid) {
          this.filterText = ''
          this.$emit('open')
        }
      }
    },
    openModal() {
      this.showGrid = true
      this.filterText = ''
      this.tempSelected = [...this.internalSelected]
      this.$emit('open')
      this.$nextTick(() => {
        this.$refs.selectorModal?.showModal()
      })
    },
    closeModal() {
      this.showGrid = false
      this.internalSelected = [...this.tempSelected]
      this.$refs.selectorModal?.close()
    },
    confirmModal() {
      this.showGrid = false
      this.emitSelectionChange()
      this.$refs.selectorModal?.close()
    },
    handleModalBackdropClick(event) {
      if (event.target === this.$refs.selectorModal) {
        this.closeModal()
      }
    },
    emitSelectionChange() {
      const updated = (this.items || []).filter(i => this.internalSelected.includes(i.name))
      this.$emit('update:selected-items', updated)
    },
    isItemSelected(itemName) {
      return this.internalSelected.includes(itemName)
    },
    selectItem(item) {
      if (this.isSingleSelect) {
        if (this.allowDeselect && this.internalSelected[0] === item.name) {
          this.internalSelected = []
        } else {
          this.internalSelected = [item.name]
        }
        if (!this.useModal) {
          this.emitSelectionChange()
          this.closeModal()
        }
      } else {
        const idx = this.internalSelected.indexOf(item.name)
        if (idx > -1) {
          this.internalSelected.splice(idx, 1)
        } else {
          this.internalSelected.push(item.name)
        }
        if (!this.useModal) {
          this.emitSelectionChange()
        }
      }
    },
    deselectAll() {
      this.internalSelected = []
      if (!this.useModal) {
        this.emitSelectionChange()
      }
    },
    handleDocumentClick(event) {
      if (this.useModal) return
      if (!this.$el.contains(event.target)) this.showGrid = false
    }
  }
}
</script>