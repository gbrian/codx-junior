<script setup>
</script>

<template>
  <!--
    Single, repeatable way to say "this row comes from <project>".
    Every table cell / list item / card in the management dashboard renders one
    of these, so the source project is never implied: it is always visible
    (colour dot or icon) AND named when there is horizontal space.
  -->
  <span class="inline-flex items-center gap-1 min-w-0 align-middle" :class="sizeClasses" :title="title">
    <img v-if="iconUrl" :src="iconUrl" :alt="theProject.name"
         class="rounded-sm object-cover shrink-0" :class="iconClasses" />
    <span v-else class="rounded-sm shrink-0" :class="dotClasses"
          :style="{ background: dotColor }" aria-hidden="true"></span>
    <span v-if="!iconOnly" class="truncate" :class="nameClasses">{{ theProject.name }}</span>
  </span>
</template>

<script>
export default {
  name: 'ProjectTag',
  props: {
    // Normalised project ({ id, name, color, icon }) — preferred input.
    project: { type: Object, default: null },
    // Loose inputs, so rows can pass what the API gave them.
    projectId: { type: [String, Number], default: null },
    name: { type: String, default: '' },
    color: { type: String, default: '' },
    // xxs | xs | sm | md — anything else falls back to xs.
    size: { type: String, default: 'xs' },
    // Dot/icon only, no label (used in dense rows).
    iconOnly: { type: Boolean, default: false },
    // Slightly dimmer label (secondary metadata position).
    muted: { type: Boolean, default: false }
  },
  computed: {
    theProject() {
      const id = this.project?.id || this.project?.project_id || this.projectId
      const rawName = this.project?.name || this.project?.project_name || this.name
      const all = this.$storex?.projects?.allProjects || []
      const live = id ? this.$storex?.projects?.allProjectsById?.[id] : null
      const found = live || all.find(p =>
        (id && p.project_id === id) || (rawName && p.project_name === rawName)
      )
      return {
        id: id || found?.project_id || null,
        name: rawName || found?.project_name || '—',
        color: this.project?.color || this.project?.project_color ||
               this.color || found?.project_color || null,
        icon: this.project?.icon || found?.project_icon || null
      }
    },
    // Only real URLs become an <img>; emoji / html project icons fall back to
    // the colour dot so nothing ever renders as a broken image.
    iconUrl() {
      const icon = this.theProject.icon
      if (typeof icon !== 'string' || !icon) return null
      const isUrl = /^(https?:)?\/\//.test(icon) || icon.startsWith('/') || icon.startsWith('data:')
      return isUrl ? icon : null
    },
    dotColor() {
      return this.theProject.color || 'currentColor'
    },
    title() {
      return `Project: ${this.theProject.name}`
    },
    sizeClasses() {
      return { xxs: 'text-[10px]', xs: 'text-[11px]', sm: 'text-xs', md: 'text-sm' }[this.size] || 'text-[11px]'
    },
    iconClasses() {
      return { xxs: 'w-2.5 h-2.5', xs: 'w-3 h-3', sm: 'w-3.5 h-3.5', md: 'w-4 h-4' }[this.size] || 'w-3 h-3'
    },
    dotClasses() {
      return { xxs: 'w-1.5 h-1.5', xs: 'w-2 h-2', sm: 'w-2.5 h-2.5', md: 'w-3 h-3' }[this.size] || 'w-2 h-2'
    },
    nameClasses() {
      return this.muted ? 'opacity-70' : ''
    }
  }
}
</script>
