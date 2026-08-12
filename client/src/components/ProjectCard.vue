<script setup>
import moment from 'moment'
</script>

<template>
  <div class="border-b border-base-300">
    <button
      @click="handleRowClick"
      class="w-full text-left px-4 py-3 hover:bg-base-300/50 transition-colors active:bg-base-300 flex items-center justify-between gap-3 group"
      :class="{ 'bg-primary/10 border-l-4 border-l-primary': isCurrent }"
    >
      <!-- Left Content: Icon + Project Info -->
      <div class="flex items-center gap-3 flex-1 min-w-0">
        <!-- Project Icon -->
        <div class="flex-shrink-0 w-10 h-10 rounded-lg overflow-hidden bg-base-200 border border-base-300">
          <img
            :src="project.project_icon"
            :alt="project.project_name"
            class="w-full h-full object-cover"
          />
        </div>

        <!-- Project Metadata -->
        <div class="flex-1 min-w-0">
          <!-- Project Name + Current Badge -->
          <div class="flex items-center gap-2 mb-1">
            <h3 class="font-bold text-sm truncate group-hover:text-primary transition-colors">
              {{ project.project_name }}
            </h3>
            <span v-if="isCurrent" class="badge badge-primary badge-xs flex-shrink-0">
              Active
            </span>
          </div>

          <!-- Path Info -->
          <p class="text-xs text-base-content/60 truncate mb-1 tooltip tooltip-bottom"
            :data-tip="project.abs_project_path">
            {{ project.abs_project_path }}
          </p>

          <!-- Last Access Time -->
          <div v-if="lastAccessText" class="flex items-center gap-1 text-xs text-base-content/50">
            <i class="fa-solid fa-clock text-xs"></i>
            <span>{{ lastAccessText }}</span>
          </div>
        </div>
      </div>
    </button>
  </div>
</template>

<script>
export default {
  props: {
    project: {
      type: Object,
      required: true
    },
    isCurrent: {
      type: Boolean,
      default: false
    },
    currentProject: {
      type: Object,
      default: null
    }
  },
  emits: ['select', 'open-folder'],
  computed: {
    lastAccessText() {
      if (!this.project?.last_access_time) return null
      try {
        return moment(this.project.last_access_time).fromNow()
      } catch {
        return null
      }
    }
  },
  methods: {
    handleRowClick() {
      this.$emit('select', this.project)
    }
  }
}
</script>