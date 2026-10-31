<script setup>
import ProjectTreeSelect from '@/components/ProjectTreeSelect.vue'
</script>

<template>
  <!--
    Dashboard adapter around the reusable `ProjectTreeSelect`.

    The dashboard keeps its own selection model (`useManagementDashboard` owns
    the ids and reloads the sections), so this component only:

      • maps its props onto the generic tree selector,
      • translates the selector's "here is the complete new selection" event
        into the dashboard's existing vocabulary (`all` / `none` / one `toggle`
        per id that actually changed).

    Nothing about the tree, the search, the multiple/single behaviour or the
    popover lives here any more: all of it is reused from
    `components/ProjectTreeSelect.vue`.
  -->
  <ProjectTreeSelect :projects="projects"
                     :model-value="selected"
                     multiple
                     label="Projects"
                     icon="fa-solid fa-filter"
                     button-class="btn btn-sm gap-1.5"
                     panel-width="w-72"
                     empty-label="No projects loaded yet"
                     @select-many="onSelectMany" />
</template>

<script>
export default {
  name: 'ProjectFilter',
  emits: ['change', 'toggle', 'all', 'none'],
  props: {
    // Normalised list: [{ id, name, color, icon }]
    projects: { type: Array, default: () => [] },
    // Selected project ids
    selected: { type: Array, default: () => [] }
  },
  methods: {
    /** Ids of every project the filter can show (the "all selected" baseline). */
    allIds() {
      return this.projects
        .map(project => project?.id ?? project?.project_id)
        .filter(Boolean)
        .map(String)
    },
    normalise(ids) {
      return [...new Set((ids || []).map(String).filter(Boolean))]
    },
    /**
     * The tree emits the complete new selection. The dashboard works by
     * toggling one id at a time, so replay only the difference — additions
     * first, then removals (the two sets are disjoint, so order cannot corrupt
     * the resulting state) and the composable's debounce still coalesces them
     * into a single reload.
     */
    onSelectMany(ids) {
      const next = this.normalise(ids)
      const previous = this.normalise(this.selected)
      this.$emit('change', next)

      if (!next.length) {
        this.$emit('none')
        return
      }

      const all = this.allIds()
      if (all.length && next.length === all.length && all.every(id => next.includes(id))) {
        this.$emit('all')
        return
      }

      next.filter(id => !previous.includes(id)).forEach(id => this.$emit('toggle', id))
      previous.filter(id => !next.includes(id)).forEach(id => this.$emit('toggle', id))
    }
  }
}
</script>