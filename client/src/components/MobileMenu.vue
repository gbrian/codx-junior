<script setup>
import ProjectDetailt from './ProjectDetailt.vue'
</script>
<template>
  <div class="flex justify-start bg-base-300/50" @click.stop="$emit('close')">
    <div class="h-full bg-base-100 shadow-lg z-50 w-1/6" @click.stop="">
      <div class="tools flex h-full gap-2 items-start p-4">
        <ProjectDetailt @click.stop=""
          :options="{ folders: true, showIcon: true }"
          @select="$projects.activeProjectChanged($event)"
        />
        <a class="click flex items-center gap-4 py-2 hover:bg-base-100 w-full" 
          :class="$ui.activeTab === 'projects' ? 'text-primary': ''"
          @click="handleToolClick('projects')">
          <i class="fa-solid fa-cubes"></i>
          <span>Projects</span>
        </a>

        <a class="click flex items-center gap-4 py-2 hover:bg-base-100 w-full"
          @click="$ui.showNewProject(true)">
          <i class="fa-solid fa-plus"></i>
          <span>Add project</span>
        </a>

        <a class="click flex items-center gap-4 py-2 hover:bg-base-100 w-full"
          :class="!$project ? 'text-slate-400' : ($ui.activeTab === 'tasks' ? 'text-primary': '')"
          @click="handleProjectToolClick('tasks')">
          <i class="fa-brands fa-trello"></i>
          <span>Kanban</span>
        </a>

        <a class="click flex items-center gap-4 py-2 hover:bg-base-100 w-full"
          v-if="$users.isProjectAdmin"
          :class="!$project ? 'text-slate-400' : ($ui.activeTab === 'profiles' ? 'text-primary': '')"
          @click="handleProjectToolClick('profiles')">
          <i class="fa-solid fa-user-group"></i>
          <span>Profiles</span>
        </a>

        <a class="click flex items-center gap-4 py-2 hover:bg-base-100 w-full"
          :class="!$project ? 'text-slate-400' : ($ui.activeTab === 'file-finder' ? 'text-primary': '')"
          @click="handleProjectToolClick('file-finder')">
          <i class="fa-solid fa-folder"></i>
          <span>File Finder</span>
        </a>

        <div class="grow"></div>
        
        <a class="click flex items-center gap-4 py-2 hover:bg-base-100 w-full"
          :class="!$project ? 'text-slate-400' : ($ui.showLogs ? 'text-primary': '')"
          @click="closable(() => $ui.toggleLogs())">
          <i class="fa-solid fa-file"></i>
          <span>Logs</span>
        </a>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  methods: {
    setActiveTab(tab) {
      this.$ui.setActiveTab(tab)
    },
    setProjectTab(tab) {
      if (this.$project) { 
        this.setActiveTab(tab)
      } else {
        this.$session.onError("No project selected")
      }
    },
    onOpenWorkspace({ workspace, app }) {
      this.$projects.openWorkspaceApp({ workspace, app })
    },
    handleToolClick(tab) {
      this.setActiveTab(tab);
      this.$emit('close');
    },
    handleProjectToolClick(tab) {
      this.setProjectTab(tab);
      this.$emit('close');
    },
    closable(cb) {
      cb()
      this.$emit('close');
    }
  },
  computed: {
    canShowBrowser() {
      return this.$users.canShowBrowser
    }
  }
}
</script>
