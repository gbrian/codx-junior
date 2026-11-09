<script>
import RepoBranchList from '@/components/repo/RepoBranchList.vue'
import GitContextMenu from '@/components/repo/GitContextMenu.vue'
import { contextMenuMixin } from '@/mixins/contextMenu'

/**
 * Source/target branch picker used by the Review tab.
 *
 * The picker reuses the Repository branch list (`RepoBranchList`) so branches
 * look and behave the same everywhere. It is collapsible: the compact summary
 * stays visible while the branch list opens on demand, and choosing the target
 * collapses it again once both sides are selected.
 */
export default {
  name: 'BranchSelector',
  components: { RepoBranchList, GitContextMenu },
  mixins: [contextMenuMixin],
  props: {
    project: { type: Object, default: null },
    currentBranch: { type: String, default: 'main' },
    compareBranch: { type: String, default: 'local' },
    availableBranches: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false }
  },
  emits: ['branch-changed', 'compare-branch-changed', 'context-menu-notice', 'context-menu-error'],
  data() {
    return {
      // Which side the shared branch list is editing
      activeSide: 'source',
      branchFilter: '',
      // Start collapsed when the pair is already selected; otherwise open the
      // list so the user can complete the missing side. `autoExpanded` lets the
      // picker collapse itself once both sides arrive from the parent state.
      expanded: !(this.currentBranch && this.compareBranch),
      autoExpanded: !(this.currentBranch && this.compareBranch)
    }
  },
  computed: {
    branches() {
      return (this.availableBranches || []).filter(branch => branch && branch !== 'local')
    },
    activeBranch() {
      return this.activeSide === 'target' ? this.compareBranch : this.currentBranch
    },
    canCollapse() {
      return !!(this.currentBranch && this.compareBranch)
    },
    toggleTitle() {
      return this.expanded ? 'Hide branch list' : 'Choose branches'
    }
  },
  watch: {
    currentBranch() {
      this.branchFilter = ''
      this.syncAutoExpanded()
    },
    compareBranch() {
      this.branchFilter = ''
      this.syncAutoExpanded()
    },
    activeSide() {
      this.branchFilter = ''
    }
  },
  methods: {
    /** Collapse a picker that was auto-opened only because a side was missing */
    syncAutoExpanded() {
      if (!this.currentBranch || !this.compareBranch) {
        this.expanded = true
        this.autoExpanded = true
        return
      }
      if (this.autoExpanded) {
        this.expanded = false
        this.autoExpanded = false
      }
    },

    toggleExpanded() {
      this.autoExpanded = false
      this.expanded = !this.expanded
    },

    openSide(side) {
      this.autoExpanded = false
      this.activeSide = side
      this.expanded = true
    },

    selectSide(side) {
      this.activeSide = side
    },

    /** Select a branch for the active side (source or target) */
    selectBranch(branch) {
      if (!branch) return
      // The user took over: never auto-collapse while completing the pair.
      this.autoExpanded = false
      if (this.activeSide === 'target') {
        this.$emit('compare-branch-changed', branch)
        // Both sides are set now: collapse back to the compact summary.
        this.expanded = false
        this.autoExpanded = false
        return
      }
      this.$emit('branch-changed', branch)
      // Keep the list open and move to the target side so the pair can be
      // completed in one pass.
      this.activeSide = 'target'
    },

    /** Branch option context menu: choose the side of the comparison */
    openBranchOptionContextMenu(event, branch) {
      if (!branch) return
      const items = []
      // "local" is the working-tree sentinel: it can only be the target side
      if (branch !== 'local') {
        items.push(this.contextMenuItem('source', 'Use as source', 'fa-arrow-right', () => this.onCurrentBranchChange(branch), { disabled: this.currentBranch === branch }))
      }
      items.push(
        this.contextMenuItem('target', 'Use as target', 'fa-arrow-left', () => this.onCompareBranchChange(branch), { disabled: this.compareBranch === branch }),
        this.contextMenuDivider('branch-copy'),
        this.contextMenuItem('copy', 'Copy branch name', 'fa-copy', () => this.copyText(branch, 'Branch name copied'))
      )
      this.openContextMenu(event, branch, items)
    },

    onCurrentBranchChange(branch) {
      if (!branch) return
      this.$emit('branch-changed', branch)
      if (this.compareBranch) {
        this.expanded = false
        this.autoExpanded = false
      }
    },

    onCompareBranchChange(branch) {
      if (!branch) return
      this.$emit('compare-branch-changed', branch)
      if (this.currentBranch) {
        this.expanded = false
        this.autoExpanded = false
      }
    }
  }
}
</script>

<template>
  <div class="branch-selector relative shrink-0 border-b border-base-content/10 px-2 py-1.5 bg-base-200/30">
    <div class="flex items-center gap-2 text-xs min-w-0">
      <!-- Source -->
      <button
        class="btn btn-xs btn-ghost min-w-0 max-w-[45%] justify-start gap-1"
        :class="activeSide === 'source' && expanded ? 'btn-active' : ''"
        :disabled="loading"
        :title="`Source branch: ${currentBranch}`"
        @click="openSide('source')"
      >
        <i class="fa-solid fa-code-branch text-success text-[10px] shrink-0"></i>
        <span class="font-mono truncate">{{ currentBranch || 'source' }}</span>
      </button>

      <div class="flex items-center gap-1 text-base-content/40 shrink-0">
        <i class="fa-solid fa-arrow-right text-[10px]"></i>
        <i class="fa-solid fa-angles-right text-[10px]"></i>
      </div>

      <!-- Target -->
      <button
        class="btn btn-xs btn-ghost min-w-0 max-w-[45%] justify-start gap-1"
        :class="activeSide === 'target' && expanded ? 'btn-active' : ''"
        :disabled="loading"
        :title="`Target branch: ${compareBranch}`"
        @click="openSide('target')"
      >
        <i
          class="fa-solid text-[10px] shrink-0"
          :class="compareBranch === 'local' ? 'fa-laptop-file text-warning' : 'fa-code-branch text-warning'"
        ></i>
        <span class="font-mono truncate">{{ compareBranch || 'target' }}</span>
      </button>

      <i v-if="loading" class="fa-solid fa-spinner animate-spin text-[10px] text-base-content/40"></i>

      <div class="grow"></div>

      <button
        class="btn btn-xs btn-ghost gap-1 shrink-0"
        :disabled="loading"
        :title="toggleTitle"
        :aria-expanded="expanded"
        @click="toggleExpanded"
      >
        <span class="hidden sm:inline">{{ expanded ? 'Done' : 'Branches' }}</span>
        <i class="fa-solid text-[10px]" :class="expanded ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
      </button>
    </div>

    <!-- Shared branch list: same component/visuals as the Repository sidebar.
         Floating dropdown: it must overlay the diff instead of growing the
         parent Review header. -->
    <div
      v-if="expanded"
      class="absolute left-2 top-full z-50 mt-1 w-[min(380px,calc(100vw-2rem))] border border-base-content/10 rounded-lg overflow-hidden bg-base-100 shadow-xl"
    >
      <div class="join w-full border-b border-base-content/10">
        <button
          class="join-item btn btn-xs flex-1"
          :class="activeSide === 'source' ? 'btn-primary' : 'btn-ghost'"
          @click="selectSide('source')"
        >
          <i class="fa-solid fa-code-branch text-[10px]"></i> Source
        </button>
        <button
          class="join-item btn btn-xs flex-1"
          :class="activeSide === 'target' ? 'btn-primary' : 'btn-ghost'"
          @click="selectSide('target')"
        >
          <i class="fa-solid fa-bullseye text-[10px]"></i> Target
        </button>
      </div>
      <div class="h-52">
        <RepoBranchList
          :branches="branches"
          :current-branch="activeSide === 'source' ? currentBranch : ''"
          :selected-branch="activeBranch"
          :loading="loading"
          :include-local="activeSide === 'target'"
          v-model:filter="branchFilter"
          :show-filter="true"
          :filter-placeholder="activeSide === 'source' ? 'Filter source branches...' : 'Filter target branches...'"
          :empty-label="activeSide === 'source' ? 'No branches' : 'No target branches'"
          @select="selectBranch"
          @contextmenu="openBranchOptionContextMenu"
        />
      </div>
      <div class="px-2 py-1 text-[10px] text-base-content/50 border-t border-base-content/10">
        {{ activeSide === 'source' ? 'Pick the branch that will be merged' : 'Pick where the source is merged into (local reviews the working tree)' }}
        <span v-if="canCollapse" class="opacity-70"> · selecting the target collapses this list</span>
      </div>
    </div>

    <GitContextMenu
      :visible="contextMenuState.visible"
      :position="contextMenuState.position"
      :title="contextMenuState.title"
      :items="contextMenuState.items"
      @select="onContextMenuSelect"
      @close="closeContextMenu"
    />
  </div>
</template>
