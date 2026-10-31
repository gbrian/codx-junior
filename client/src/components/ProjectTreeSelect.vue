<script setup>
import { v4 as uuidv4 } from 'uuid'
import ProjectTag from '@/components/management/ProjectTag.vue'
</script>

<template>
  <!--
    Reusable project selector: a SEARCHABLE TREE rendered inside a native popover.

    Reuse it anywhere a project (or a set of projects) has to be chosen:

      <ProjectTreeSelect :projects="projects" v-model="selectedIds" />
      <ProjectTreeSelect :projects="projects" :multiple="false" v-model="projectId" />

    The tree is built from the projects themselves (`parent_id`, or the
    filesystem `abs_project_path` when the payload only carries paths), so
    nested projects — a project living inside another project's folder — are
    shown as children instead of a flat, unsorted wall of names.

    EVENTS — they differ on purpose, `multiple` changes the VALUE SHAPE:
      multiple = true
        • update:modelValue → Array<string>      (v-model)
        • select-many       → Array<string>      (full new selection)
      multiple = false
        • update:modelValue → string | null      (v-model)
        • select-one        → the picked project object | null
    Both modes also emit `all` / `none` when those explicit actions are used.

    The panel is a NATIVE POPOVER, so it is painted in the browser's top layer:
    it can never be covered by the cards/tables/<select> below the header and it
    cannot be clipped by an `overflow-hidden` parent. Light dismiss (click
    outside / Escape) comes free, so there is no click-away layer.
  -->
  <div class="project-tree-select relative">
    <!-- ── Trigger ──────────────────────────────────────────────────────── -->
    <button type="button"
            class="gap-1.5"
            :class="[buttonClass, triggerTone]"
            :popovertarget="panelId"
            :style="`anchor-name:--${panelId}-anchor`"
            :disabled="disabled"
            aria-haspopup="true"
            :aria-expanded="open ? 'true' : 'false'"
            :aria-label="`${label}: ${summary}`">
      <i :class="icon" class="text-xs"></i>
      <span class="hidden sm:inline">{{ label }}</span>
      <span class="badge badge-xs"
            :class="[hasFilter ? 'badge-primary' : 'badge-ghost', multiple ? '' : 'max-w-28 truncate']">
        {{ summary }}
      </span>
      <i class="fa-solid fa-chevron-down text-[10px] opacity-50"></i>
    </button>

    <!-- ── Panel ────────────────────────────────────────────────────────── -->
    <div :id="panelId"
         ref="panel"
         popover
         role="dialog"
         :aria-label="label"
         class="project-tree-panel rounded-box border border-base-300 bg-base-100 shadow-2xl"
         :class="panelWidth"
         :style="`position-anchor:--${panelId}-anchor`"
         @toggle="onToggle">
      <!-- title, bulk actions, search -->
      <div class="shrink-0 space-y-1.5 border-b border-base-300 p-2 pb-1.5">
        <div class="flex items-center gap-1">
          <span class="flex-1 truncate text-[10px] uppercase tracking-wider opacity-60">{{ label }}</span>
          <template v-if="multiple && showActions">
            <button type="button" class="btn btn-xs btn-ghost" :disabled="!nodes.length" @click="selectAll">All</button>
            <button type="button" class="btn btn-xs btn-ghost" :disabled="!selection.length" @click="selectNone">None</button>
          </template>
          <button type="button" class="btn btn-xs btn-ghost btn-square" aria-label="Close" @click="close">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <label v-if="searchable" class="input input-sm input-bordered flex w-full items-center gap-2">
          <i class="fa-solid fa-magnifying-glass text-[11px] opacity-50"></i>
          <input ref="searchInput"
                 v-model="query"
                 type="text"
                 class="grow bg-transparent text-xs outline-none"
                 autocomplete="off"
                 :placeholder="searchPlaceholder"
                 :aria-label="searchPlaceholder"
                 @keydown.down.prevent="moveHighlight(1)"
                 @keydown.up.prevent="moveHighlight(-1)"
                 @keydown.enter.prevent="pickHighlighted" />
          <button v-if="query" type="button" class="text-[10px] opacity-50 hover:opacity-100"
                  aria-label="Clear search" @click="query = ''">
            <i class="fa-solid fa-circle-xmark"></i>
          </button>
        </label>
      </div>

      <!-- tree -->
      <div class="min-h-0 flex-1 overflow-y-auto py-1"
           role="tree"
           :aria-multiselectable="multiple ? 'true' : 'false'"
           :aria-label="label">
        <p v-if="!rows.length" class="px-2 py-3 text-xs opacity-60">
          {{ query ? `No project matches “${query}”` : emptyLabel }}
        </p>

        <div v-for="(row, index) in rows"
             :key="row.id"
             role="treeitem"
             :aria-level="row.depth + 1"
             :aria-checked="multiple ? (row.partial ? 'mixed' : row.selected ? 'true' : 'false') : undefined"
             :aria-selected="multiple ? undefined : (row.selected ? 'true' : 'false')"
             :aria-expanded="row.hasChildren ? (row.expanded ? 'true' : 'false') : undefined"
             :tabindex="index === highlight ? 0 : -1"
             :data-row-index="index"
             class="project-tree-row"
             :class="{ 'is-selected': row.selected, 'is-active': index === highlight }"
             :style="{ paddingLeft: `${0.375 + row.depth * 0.8}rem` }"
             @click="onRowClick(row)"
             @mouseenter="highlight = index"
             @keydown.enter.prevent="onRowClick(row)"
             @keydown.space.prevent="onRowClick(row)">
          <span v-if="row.hasChildren"
                class="grid h-4 w-3.5 shrink-0 cursor-pointer place-items-center"
                @click.stop="toggleExpand(row)">
            <i class="fa-solid fa-chevron-right text-[9px] opacity-60 transition-transform duration-150"
               :class="row.expanded ? 'rotate-90' : ''"></i>
          </span>
          <span v-else class="h-4 w-3.5 shrink-0"></span>

          <input v-if="multiple"
                 type="checkbox"
                 tabindex="-1"
                 aria-hidden="true"
                 class="checkbox checkbox-xs checkbox-primary pointer-events-none shrink-0"
                 :checked="row.selected"
                 :indeterminate="row.partial" />
          <span v-else
                class="grid h-3 w-3 shrink-0 place-items-center rounded-full"
                :class="row.selected ? 'ring-2 ring-primary' : 'border border-base-content/30'">
            <span v-if="row.selected" class="h-1.5 w-1.5 rounded-full bg-primary"></span>
          </span>

          <ProjectTag :project="row.project" size="xs" class="min-w-0 flex-1" />
        </div>
      </div>

      <!-- footer -->
      <div class="flex shrink-0 items-center gap-2 border-t border-base-300 px-2 py-1.5 text-[11px] opacity-60">
        <span>{{ selection.length }} of {{ nodes.length }} selected</span>
        <span class="flex-1"></span>
        <span v-if="!nodes.length">no projects</span>
        <span v-else-if="!selection.length" class="text-warning">nothing selected</span>
        <span v-else-if="multiple && !hasFilter">all projects</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ProjectTreeSelect',
  // The event NAME and the payload follow `multiple` on purpose (see the header
  // comment): a multi-select consumer listens to `select-many` and receives an
  // array, a single-select consumer listens to `select-one` and receives the
  // project itself. `update:modelValue` mirrors the same shape for v-model.
  emits: ['update:modelValue', 'select-many', 'select-one', 'all', 'none'],
  props: {
    /**
     * Flat project list. Each entry accepts either shape:
     * `{ id | project_id, name | project_name, color, icon,
     *    parent_id | parentId, abs_project_path | path }`.
     */
    projects: { type: Array, default: () => [] },
    /** Selected ids (Array) when `multiple`, one id otherwise. */
    modelValue: { type: [Array, String, Number], default: null },
    /** Checkbox tree (several projects) vs. single choice (radio behaviour). */
    multiple: { type: Boolean, default: true },
    label: { type: String, default: 'Projects' },
    icon: { type: String, default: 'fa-solid fa-filter' },
    /** Extra trigger classes; the tone (ghost/primary) is added by the component. */
    buttonClass: { type: String, default: 'btn btn-sm' },
    panelWidth: { type: String, default: 'w-72' },
    searchable: { type: Boolean, default: true },
    searchPlaceholder: { type: String, default: 'Search projects…' },
    emptyLabel: { type: String, default: 'No projects' },
    /** Show the "All" / "None" actions (multi-select only). */
    showActions: { type: Boolean, default: true },
    /** Depth expanded on first render: 0 = roots collapsed, 1 = roots open. */
    defaultExpandDepth: { type: Number, default: 1 },
    disabled: { type: Boolean, default: false }
  },
  data() {
    return {
      // Keeps several instances (welcome page + dockview panel) apart, each with
      // its own popover id and its own anchor name.
      uid: uuidv4(),
      open: false,
      query: '',
      highlight: 0,
      // Per-node override of `defaultExpandDepth`; `{}` = not touched yet.
      expanded: {}
    }
  },
  computed: {
    panelId() {
      return `project-tree-${this.uid}`
    },
    /** Normalised projects with their parent resolved (id-based hierarchy). */
    nodes() {
      const list = (this.projects || [])
        .map((raw) => {
          const id = raw?.id ?? raw?.project_id ?? raw?.project_name ?? raw?.name
          const name = raw?.name || raw?.project_name ||
            (id === undefined || id === null ? '' : String(id))
          return {
            id: id === undefined || id === null ? null : String(id),
            name,
            color: raw?.color || raw?.project_color || null,
            icon: raw?.icon || raw?.project_icon || null,
            parentId: raw?.parent_id || raw?.parentId || null,
            path: raw?.abs_project_path || raw?.path || null,
            raw
          }
        })
        .filter(node => node.id)

      // Aggregated payloads often carry display fields only; the project itself
      // lives in the store, which knows where it sits in the hierarchy.
      list.forEach((node) => {
        const live = this.liveProject(node.id, node.name)
        node.parentId = node.parentId || live?.parent_id || null
        node.path = node.path || live?.abs_project_path || null
      })

      const index = {}
      list.forEach((node) => { index[node.id] = node })
      return list.map(node => ({ ...node, parentId: this.resolveParent(node, index) }))
    },
    byId() {
      const map = {}
      this.nodes.forEach((node) => { map[node.id] = node })
      return map
    },
    rawById() {
      const map = {}
      this.nodes.forEach((node) => { map[node.id] = node.raw })
      return map
    },
    /** Roots with nested `children`, alphabetically sorted at every level. */
    tree() {
      const index = {}
      this.nodes.forEach((node) => { index[node.id] = { ...node, children: [] } })

      const roots = []
      this.nodes.forEach((node) => {
        const target = index[node.id]
        const parent = node.parentId ? index[node.parentId] : null
        // A parent chain looping back to the node is broken data: promoting it
        // to a root keeps every project reachable instead of dropping it.
        if (parent && !this.hasAncestor(node.parentId, node.id)) parent.children.push(target)
        else roots.push(target)
      })

      const sortLevel = (level) => {
        level.sort((a, b) => String(a.name).localeCompare(String(b.name)))
        level.forEach(item => sortLevel(item.children))
      }
      sortLevel(roots)
      return roots
    },
    /** Current selection as an array, whatever shape `modelValue` arrived in. */
    selection() {
      return this.normaliseIds(this.modelValue)
    },
    selectedIdSet() {
      return new Set(this.selection)
    },
    hasFilter() {
      if (!this.nodes.length) return false
      if (!this.multiple) return this.selection.length > 0
      return this.nodes.some(node => !this.selectedIdSet.has(node.id))
    },
    summary() {
      const total = this.nodes.length
      if (!total) return '0'
      if (this.multiple) return this.hasFilter ? `${this.selection.length}/${total}` : `all ${total}`
      const only = this.selection[0] ? this.byId[this.selection[0]] : null
      return only ? only.name : 'none'
    },
    triggerTone() {
      return this.hasFilter ? 'btn-primary btn-outline' : 'btn-ghost'
    },
    /** Ids to keep visible for the current query (`null` = no search). */
    matchingIds() {
      const needle = this.query.trim().toLowerCase()
      if (!needle) return null
      const set = new Set()
      this.nodes.forEach((node) => {
        if (!String(node.name).toLowerCase().includes(needle)) return
        // Keep the whole ancestry so a match is shown in its context.
        let current = node
        let guard = 0
        while (current && guard < 200) {
          if (set.has(current.id)) break
          set.add(current.id)
          current = current.parentId ? this.byId[current.parentId] : null
          guard += 1
        }
      })
      return set
    },
    /** Flattened, render-ready rows (`depth` drives the indentation). */
    rows() {
      const selected = this.selectedIdSet
      const visibleIds = this.matchingIds
      const result = []

      const walk = (level, depth) => {
        level.forEach((node) => {
          if (visibleIds && !visibleIds.has(node.id)) return
          const children = visibleIds
            ? node.children.filter(child => visibleIds.has(child.id))
            : node.children
          const hasChildren = children.length > 0
          // A search always shows its matches expanded; otherwise the node's
          // own state decides.
          const expanded = this.isNodeExpanded(node, depth)
          result.push({
            id: node.id,
            depth,
            hasChildren,
            expanded,
            selected: selected.has(node.id),
            // Children in scope while the parent is not: shown as `mixed`, so a
            // collapsed parent never hides the fact that it contributes rows.
            partial: !selected.has(node.id) && this.hasSelectedDescendant(node, selected),
            project: { id: node.id, name: node.name, color: node.color, icon: node.icon }
          })
          if (hasChildren && expanded) walk(children, depth + 1)
        })
      }

      walk(this.tree, 0)
      return result
    }
  },
  watch: {
    // Rows shrink when a filter is typed: keep the keyboard cursor in range.
    rows(rows) {
      if (this.highlight >= rows.length) this.highlight = 0
    }
  },
  methods: {
    /** The same project as the store knows it (colour, icon, hierarchy). */
    liveProject(id, name) {
      const projects = this.$storex?.projects?.allProjects || []
      const byId = id ? this.$storex?.projects?.allProjectsById?.[id] : null
      return byId || projects.find(entry =>
        (id && entry.project_id === id) || (name && entry.project_name === name)) || null
    },
    /**
     * Parent of a node: the explicit `parent_id` when it is part of the list,
     * otherwise the deepest project whose folder contains this one.
     */
    resolveParent(node, index) {
      const explicit = node.parentId ? String(node.parentId) : null
      if (explicit && explicit !== node.id && index[explicit]) return explicit
      if (!node.path) return null

      const childPath = node.path.endsWith('/') ? node.path : `${node.path}/`
      let best = null
      Object.values(index).forEach((other) => {
        if (other.id === node.id || !other.path) return
        const parentPath = other.path.endsWith('/') ? other.path : `${other.path}/`
        if (parentPath === childPath || !childPath.startsWith(parentPath)) return
        const bestLength = best
          ? (best.path.endsWith('/') ? best.path.length : best.path.length + 1)
          : -1
        if (parentPath.length > bestLength) best = other
      })
      return best ? best.id : null
    },
    /** True when `ancestorId` is above `candidateId` (cycle guard for the tree). */
    hasAncestor(candidateId, ancestorId) {
      let current = this.byId[candidateId]?.parentId
      let guard = 0
      while (current && guard < 200) {
        if (current === ancestorId) return true
        current = this.byId[current]?.parentId
        guard += 1
      }
      return false
    },
    hasSelectedDescendant(node, selected) {
      return (node.children || []).some(child =>
        selected.has(child.id) || this.hasSelectedDescendant(child, selected))
    },
    isNodeExpanded(node, depth) {
      const stored = this.expanded[node.id]
      if (stored !== undefined) return !!stored
      return depth < this.defaultExpandDepth
    },
    toggleExpand(row) {
      this.expanded = { ...this.expanded, [row.id]: !row.expanded }
    },
    onRowClick(row) {
      if (this.disabled) return
      if (this.multiple) {
        const next = this.selection.includes(row.id)
          ? this.selection.filter(id => id !== row.id)
          : [...this.selection, row.id]
        this.emitSelection(next)
        return
      }
      this.emitSelection([row.id])
      this.close()
    },
    /** Emits the shape that matches `multiple` (array vs. single id). */
    emitSelection(ids) {
      const unique = [...new Set(this.normaliseIds(ids))]
      if (this.multiple) {
        this.$emit('update:modelValue', unique)
        this.$emit('select-many', unique)
        return
      }
      const id = unique.length ? unique[unique.length - 1] : null
      this.$emit('update:modelValue', id)
      this.$emit('select-one', id ? (this.rawById[id] || { id }) : null)
    },
    selectAll() {
      this.emitSelection(this.nodes.map(node => node.id))
      this.$emit('all')
    },
    selectNone() {
      this.emitSelection([])
      this.$emit('none')
    },
    moveHighlight(delta) {
      if (!this.rows.length) return
      this.highlight = (this.highlight + delta + this.rows.length) % this.rows.length
      this.$nextTick(() => {
        const element = this.$el?.querySelector?.(`[data-row-index="${this.highlight}"]`)
        element?.scrollIntoView({ block: 'nearest' })
      })
    },
    pickHighlighted() {
      const row = this.rows[this.highlight]
      if (row) this.onRowClick(row)
    },
    // The popover owns the open state; mirror it for aria-expanded and reset the
    // transient bits (search text, keyboard cursor) on every open/close.
    onToggle(event) {
      this.open = event.newState === 'open'
      this.query = ''
      this.highlight = 0
      if (this.open) this.$nextTick(() => this.$refs.searchInput?.focus())
    },
    close() {
      const panel = this.$refs.panel
      if (panel?.hidePopover && panel.matches(':popover-open')) panel.hidePopover()
      this.open = false
    },
    normaliseIds(value) {
      if (Array.isArray(value)) return value.map(id => String(id)).filter(Boolean)
      if (value === null || value === undefined || value === '') return []
      return [String(value)]
    }
  }
}
</script>

<style scoped>
/* Anchored under the trigger, right edges aligned (the trigger usually sits at
   the end of a header). `flip-*` keeps the panel inside a narrow dockview panel
   instead of overflowing it. */
.project-tree-panel {
  position: fixed;
  inset: auto;
  top: anchor(bottom);
  right: anchor(right);
  margin: 0.5rem 0 0 0;
  max-height: min(32rem, calc(100vh - 6rem));
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position-try-fallbacks: flip-block, flip-inline;
}

/* Author styles beat the UA `[popover]:not(:popover-open) { display: none }`,
   so the closed state has to be restored explicitly. */
.project-tree-panel:not(:popover-open) {
  display: none;
}

.project-tree-row {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  width: 100%;
  padding: 0.25rem 0.5rem 0.25rem 0;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  text-align: left;
  cursor: pointer;
  transition: background-color 120ms ease;
}
.project-tree-row:hover,
.project-tree-row.is-active {
  background-color: color-mix(in srgb, currentColor 10%, transparent);
}
.project-tree-row.is-selected {
  background-color: color-mix(in srgb, currentColor 16%, transparent);
}
.project-tree-row:focus-visible {
  outline: 2px solid color-mix(in srgb, currentColor 55%, transparent);
  outline-offset: -1px;
}
</style>