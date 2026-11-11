<script setup>
</script>

<template>
  <!-- Teleported to <body> on purpose: the explorer lives inside panel
       containers that clip their content and, sometimes, inside a transformed
       ancestor — where `position: fixed` is resolved against that ancestor
       instead of the viewport and the menu appeared far away from the pointer.
       `menuStyle` / `submenuStyle` clamp both panels inside the viewport (see
       placeMenu / placeSubmenu). -->
  <Teleport to="body">
    <div
      v-if="isVisible"
      ref="menu"
      class="fixed z-[100] bg-base-100 border border-base-content/10 rounded-lg shadow-lg py-1 min-w-48 max-w-[calc(100vw-1rem)] max-h-[calc(100vh-1rem)] overflow-y-auto"
      :style="menuStyle"
      @click.stop
      @contextmenu.prevent.stop
    >
      <!-- Upload files to the folder currently open in the explorer -->
      <button
        class="w-full px-4 py-2 text-sm text-left hover:bg-base-200 flex items-center gap-2 transition-colors"
        @click="handleUpload"
        title="Upload files to the current folder"
      >
        <i class="fa-solid fa-arrow-up-from-bracket w-4"></i>
        <span>Upload files</span>
      </button>

      <div class="divider my-1"></div>

      <!-- Create new file -->
      <button
        class="w-full px-4 py-2 text-sm text-left hover:bg-base-200 flex items-center gap-2 transition-colors"
        @click="handleCreate(false)"
        title="Create a new file"
      >
        <i class="fa-solid fa-file-plus w-4"></i>
        <span>New File</span>
      </button>

      <!-- Create new folder -->
      <button
        class="w-full px-4 py-2 text-sm text-left hover:bg-base-200 flex items-center gap-2 transition-colors"
        @click="handleCreate(true)"
        title="Create a new folder"
      >
        <i class="fa-solid fa-folder-plus w-4"></i>
        <span>New Folder</span>
      </button>

      <!-- Register the folder (or the folder being viewed) as a codx-junior project -->
      <button
        v-if="canCreateProject"
        class="w-full px-4 py-2 text-sm text-left hover:bg-base-200 flex items-center gap-2 transition-colors"
        @click="handleCreateProject"
        title="Create a codx-junior project in this folder"
      >
        <i class="fa-solid fa-diagram-project w-4"></i>
        <span>New codx-junior project</span>
      </button>

      <!-- Git actions, grouped in a submenu (see the panel below) -->
      <div class="divider my-1" v-if="gitAvailable"></div>
      <button
        v-if="gitAvailable"
        class="w-full px-4 py-2 text-sm text-left hover:bg-base-200 flex items-center justify-between gap-2 transition-colors"
        :class="submenu === 'git' && 'bg-base-200'"
        aria-haspopup="menu"
        :aria-expanded="submenu === 'git'"
        title="Git actions for the selection (or this folder)"
        @click.stop="toggleSubmenu('git', $event)"
        @mouseenter="openSubmenu('git', $event)"
        @mouseleave="scheduleCloseSubmenu"
      >
        <span class="flex items-center gap-2">
          <i class="fa-brands fa-git-alt w-4"></i>
          <span>Git</span>
          <span
            v-if="gitStatus"
            class="text-[10px] font-bold font-mono"
            :class="gitStatus.color"
          >{{ gitStatus.badge }}</span>
        </span>
        <i class="fa-solid fa-chevron-right text-[10px] opacity-60"></i>
      </button>

      <div class="divider my-1" v-if="hasSelection"></div>

      <!-- Rename -->
      <button
        v-if="hasSelection && !isMultiSelect"
        class="w-full px-4 py-2 text-sm text-left hover:bg-base-200 flex items-center gap-2 transition-colors"
        @click="handleRename"
        title="Rename file or folder"
      >
        <i class="fa-solid fa-pen-to-square w-4"></i>
        <span>Rename</span>
      </button>

      <!-- Move to another folder (single or multiple selection) -->
      <button
        v-if="hasSelection"
        class="w-full px-4 py-2 text-sm text-left hover:bg-base-200 flex items-center gap-2 transition-colors"
        @click="handleMove"
        title="Move selected items to another folder"
      >
        <i class="fa-solid fa-folder-tree w-4"></i>
        <span>Move to… {{ isMultiSelect ? `(${selectionCount})` : '' }}</span>
      </button>

      <!-- Jump to the folder that contains the selection (useful from search results) -->
      <button
        v-if="hasSelection"
        class="w-full px-4 py-2 text-sm text-left hover:bg-base-200 flex items-center gap-2 transition-colors"
        @click="handleGoToFolder"
        title="Open the folder that contains this item"
      >
        <i class="fa-solid fa-folder-open w-4"></i>
        <span>Go to folder</span>
      </button>

      <div class="divider my-1"></div>

      <!-- Copy the absolute path (selection, or the current folder on blank area) -->
      <button
        class="w-full px-4 py-2 text-sm text-left hover:bg-base-200 flex items-center gap-2 transition-colors"
        @click="handleCopyPath"
        title="Copy the absolute path to the clipboard"
      >
        <i class="fa-regular fa-copy w-4"></i>
        <span>Copy path{{ isMultiSelect ? ` (${selectionCount})` : '' }}</span>
      </button>

      <!-- Copy the project relative path, prefixed with the project name -->
      <button
        class="w-full px-4 py-2 text-sm text-left hover:bg-base-200 flex items-center gap-2 transition-colors"
        @click="handleCopyRelativePath"
        title="Copy the path relative to the project root (prefixed with the project name)"
      >
        <i class="fa-solid fa-link w-4"></i>
        <span>Copy relative path{{ isMultiSelect ? ` (${selectionCount})` : '' }}</span>
      </button>

      <!-- Delete -->
      <button
        v-if="hasSelection"
        class="w-full px-4 py-2 text-sm text-left hover:bg-error/10 text-error flex items-center gap-2 transition-colors"
        @click="handleDelete"
        title="Delete selected items"
      >
        <i class="fa-solid fa-trash w-4"></i>
        <span>Delete {{ isMultiSelect ? `(${selectionCount})` : '' }}</span>
      </button>
    </div>

    <!-- Git submenu: opens beside its parent item and flips to the other side
         (or upwards) when there is no room at the edge of the window. -->
    <div
      v-if="isVisible && submenu === 'git'"
      ref="submenu"
      class="fixed z-[110] bg-base-100 border border-base-content/10 rounded-lg shadow-xl py-1 min-w-44 max-w-[calc(100vw-1rem)] max-h-[calc(100vh-1rem)] overflow-y-auto"
      :style="submenuStyle"
      role="menu"
      @click.stop
      @contextmenu.prevent.stop
      @mouseenter="keepSubmenu"
    >
      <div class="px-3 pt-1 pb-1 text-[10px] font-semibold uppercase tracking-wide opacity-50 flex items-center gap-1">
        <i class="fa-brands fa-git-alt"></i>
        <span>{{ gitStatus ? gitStatus.label : 'Working tree' }}</span>
      </div>

      <button
        v-for="action in gitActions"
        :key="action.id"
        class="w-full px-4 py-2 text-sm text-left hover:bg-base-200 flex items-center gap-2 transition-colors disabled:opacity-40 disabled:pointer-events-none"
        :class="action.danger && 'text-error hover:bg-error/10'"
        :disabled="action.disabled"
        :title="action.title"
        @click="handleGitAction(action.id)"
      >
        <i :class="[action.icon, 'w-4']"></i>
        <span>{{ action.label }}</span>
      </button>
    </div>
  </Teleport>
</template>

<script>
// Panel margin kept free at every edge of the viewport
const VIEWPORT_MARGIN = 8

export default {
  name: 'ContextMenu',
  props: {
    isVisible: {
      type: Boolean,
      default: false
    },
    // Pointer position in viewport (clientX / clientY) coordinates
    position: {
      type: Object,
      default: () => ({ x: 0, y: 0 })
    },
    hasSelection: {
      type: Boolean,
      default: false
    },
    isMultiSelect: {
      type: Boolean,
      default: false
    },
    selectionCount: {
      type: Number,
      default: 0
    },
    // True when the target of the context menu is a folder (or the folder being
    // viewed), so it can be registered as a codx-junior project.
    canCreateProject: {
      type: Boolean,
      default: false
    },
    // True when the project is a git checkout, so git actions are available
    gitAvailable: {
      type: Boolean,
      default: false
    },
    // Git status of the target (`{ badge, label, color, staged, unstaged }`),
    // null when the target has no pending change
    gitStatus: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      // Applied once the panel has been measured (see placeMenu)
      menuStyle: { left: '0px', top: '0px' },
      submenu: null,
      submenuStyle: { left: '0px', top: '0px' },
      // Viewport rectangle of the item that opened the submenu
      submenuAnchor: null,
      submenuTimer: null
    }
  },
  computed: {
    gitActions() {
      const suffix = this.isMultiSelect ? ` (${this.selectionCount})` : ''
      const status = this.gitStatus
      return [
        {
          id: 'stage',
          label: `Stage${suffix}`,
          icon: 'fa-solid fa-plus',
          // Everything already in the index: nothing left to stage
          disabled: !!status && status.staged && !status.unstaged,
          title: 'Stage the selected changes (git add)'
        },
        {
          id: 'unstage',
          label: `Unstage${suffix}`,
          icon: 'fa-solid fa-minus',
          disabled: !!status && !status.staged,
          title: 'Remove the selected paths from the index (git reset)'
        },
        {
          id: 'discard',
          label: `Discard changes${suffix}`,
          icon: 'fa-solid fa-rotate-left',
          danger: true,
          disabled: !!status && !status.unstaged,
          title: 'Roll the selected paths back to their last committed version'
        },
        {
          id: 'gitignore',
          label: `Add to .gitignore${suffix}`,
          icon: 'fa-solid fa-ban',
          title: 'Add the selected items (or this folder) to .gitignore'
        }
      ]
    }
  },
  watch: {
    isVisible: {
      immediate: true,
      handler(visible) {
        if (visible) {
          this.placeMenu()
        } else {
          this.reset()
        }
      }
    },
    position: {
      deep: true,
      handler() {
        this.placeMenu()
      }
    }
  },
  beforeUnmount() {
    clearTimeout(this.submenuTimer)
    this.submenuTimer = null
  },
  methods: {
    reset() {
      this.submenu = null
      this.submenuAnchor = null
      clearTimeout(this.submenuTimer)
      this.submenuTimer = null
    },

    // ── Placement ──────────────────────────────────────────────────────────
    /**
     * Keep the menu next to the pointer, shifted (never pushed away from it)
     * when it would overflow the right or the bottom edge of the window.
     */
    placeMenu() {
      // First paint at the pointer, so the menu never flashes in a corner: the
      // measured pass below only corrects the edges of the window.
      const requestedLeft = this.position?.x || 0
      const requestedTop = this.position?.y || 0
      this.menuStyle = { left: `${requestedLeft}px`, top: `${requestedTop}px` }
      this.$nextTick(() => {
        const el = this.$refs.menu
        if (!el) return
        const { left, top } = this.clampWithinViewport(el, requestedLeft, requestedTop)
        this.menuStyle = { left: `${left}px`, top: `${top}px` }
      })
    },
    /**
     * Center a floating panel inside the viewport.
     *
     * @param {HTMLElement} el - Panel to measure.
     * @param {number} left - Requested left (viewport px).
     * @param {number} top - Requested top (viewport px).
     * @returns {{left: number, top: number}} Clamped coordinates.
     */
    clampWithinViewport(el, left, top) {
      const viewportWidth = window.innerWidth || document.documentElement.clientWidth
      const viewportHeight = window.innerHeight || document.documentElement.clientHeight
      const bounds = el.getBoundingClientRect()
      const width = bounds.width || el.offsetWidth || 0
      const height = bounds.height || el.offsetHeight || 0
      const maxLeft = Math.max(VIEWPORT_MARGIN, viewportWidth - width - VIEWPORT_MARGIN)
      const maxTop = Math.max(VIEWPORT_MARGIN, viewportHeight - height - VIEWPORT_MARGIN)
      return {
        left: Math.min(Math.max(VIEWPORT_MARGIN, left), maxLeft),
        top: Math.min(Math.max(VIEWPORT_MARGIN, top), maxTop)
      }
    },
    /**
     * Open the submenu beside the item that owns it: to the right when there is
     * room, to the left when the menu sits against the right edge of the window.
     */
    openSubmenu(name, event) {
      const target = event?.currentTarget
      if (!name || !target) return
      const bounds = target.getBoundingClientRect()
      this.submenuAnchor = { top: bounds.top, left: bounds.left, right: bounds.right }
      // Painted beside the item first; placeSubmenu() only corrects the edges
      this.submenuStyle = { left: `${bounds.right + 2}px`, top: `${bounds.top}px` }
      this.submenu = name
      this.keepSubmenu()
      this.$nextTick(() => this.placeSubmenu())
    },
    placeSubmenu() {
      const el = this.$refs.submenu
      const anchor = this.submenuAnchor
      if (!el || !anchor) return
      const viewportWidth = window.innerWidth || document.documentElement.clientWidth
      const viewportHeight = window.innerHeight || document.documentElement.clientHeight
      const bounds = el.getBoundingClientRect()
      const width = bounds.width || el.offsetWidth || 0
      const height = bounds.height || el.offsetHeight || 0

      let left = anchor.right + 2
      if (left + width + VIEWPORT_MARGIN > viewportWidth) {
        left = anchor.left - width - 2
      }
      left = Math.min(
        Math.max(VIEWPORT_MARGIN, left),
        Math.max(VIEWPORT_MARGIN, viewportWidth - width - VIEWPORT_MARGIN)
      )
      const top = Math.min(
        Math.max(VIEWPORT_MARGIN, anchor.top),
        Math.max(VIEWPORT_MARGIN, viewportHeight - height - VIEWPORT_MARGIN)
      )
      this.submenuStyle = { left: `${left}px`, top: `${top}px` }
    },
    toggleSubmenu(name, event) {
      if (this.submenu === name) {
        this.closeSubmenu()
        return
      }
      this.openSubmenu(name, event)
    },
    // Closing is delayed so the pointer can travel from the item to the panel
    scheduleCloseSubmenu() {
      clearTimeout(this.submenuTimer)
      this.submenuTimer = setTimeout(() => {
        this.submenu = null
      }, 300)
    },
    keepSubmenu() {
      clearTimeout(this.submenuTimer)
      this.submenuTimer = null
    },
    closeSubmenu() {
      this.keepSubmenu()
      this.submenu = null
    },

    // ── Actions ────────────────────────────────────────────────────────────
    handleUpload() {
      this.$emit('upload')
    },
    handleCreate(isDir) {
      this.$emit('create', { isDir })
    },
    handleCreateProject() {
      this.$emit('create-project')
    },
    handleGitAction(action) {
      this.$emit('git-action', { action })
    },
    handleRename() {
      this.$emit('rename')
    },
    handleMove() {
      this.$emit('move')
    },
    handleGoToFolder() {
      this.$emit('go-to-folder')
    },
    handleCopyPath() {
      this.$emit('copy-path')
    },
    handleCopyRelativePath() {
      this.$emit('copy-relative-path')
    },
    handleDelete() {
      this.$emit('delete')
    }
  }
}
</script>
