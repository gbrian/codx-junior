<script setup>
</script>

<template>
  <!-- Quick project switcher: list of pinned projects (Slack/Discord style) -->
  <div
    v-if="pinnedProjects.length"
    class="px-2 py-2 shrink-0 border-b border-base-content/5"
  >
    <div
      v-if="!isCollapsed"
      class="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wide text-base-content/40"
    >
      Pinned
    </div>

    <div class="flex flex-col gap-1" :class="isCollapsed && 'items-center'">
      <button
        v-for="project in pinnedProjects"
        :key="project.project_id"
        class="group relative flex items-center gap-2 rounded-lg text-sm transition-colors cursor-pointer w-full focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
        :class="[
          isCollapsed ? 'justify-center w-auto p-1.5' : 'px-3 py-2',
          isActive(project)
            ? 'bg-primary/15 text-primary'
            : 'text-base-content/70 hover:bg-white/5 hover:text-base-content'
        ]"
        :title="project.project_name"
        @click="switchProject(project)"
      >
        <img
          v-if="project.project_icon"
          :src="project.project_icon"
          :alt="project.project_name"
          class="w-5 h-5 rounded-md shrink-0 object-cover"
        />
        <i v-else class="fa-solid fa-cube w-5 text-center shrink-0"></i>

        <template v-if="!isCollapsed">
          <span class="truncate flex-1 text-left">{{ project.project_name }}</span>

          <!-- Unpin (kept out of the layout flow of the icon rail) -->
          <span
            class="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-white/10 text-base-content/40 hover:text-error transition-all cursor-pointer"
            title="Unpin project"
            @click.stop="unpinProject(project)"
          >
            <i class="fa-solid fa-xmark text-xs"></i>
          </span>

          <!-- Active indicator -->
          <span
            v-if="isActive(project)"
            class="w-1 h-4 rounded-full bg-primary shrink-0"
          ></span>
        </template>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    isCollapsed: { type: Boolean, default: false }
  },
  computed: {
    pinnedProjects() {
      return this.$storex.ui.pinnedProjectsList || []
    },
    activeProjectId() {
      return this.$storex.projects.activeProject?.project_id
    }
  },
  methods: {
    isActive(project) {
      return !!project && project.project_id === this.activeProjectId
    },
    // Reuse the canonical project-switch flow (loading overlay, chats reload,
    // route sync) so the switcher behaves exactly like the project selector.
    switchProject(project) {
      if (this.isActive(project)) return
      this.$storex.projects.activeProjectChanged(project)
    },
    unpinProject(project) {
      this.$storex.ui.unpinProject(project.project_id)
    }
  }
}
</script>