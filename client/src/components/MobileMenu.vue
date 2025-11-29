<script setup>
import ProjectDetailt from './ProjectDetailt.vue'
import WorkspacesSelector from './workspaces/WorkspacesSelector.vue'
</script>
<template>
  <div class="absolute top-0 left-0 right-0 bottom-0 z-50 flex bg-base-300/50" @click.stop="$emit('close')">
    <div class="h-full bg-base-100 shadow-lg z-50">
      <div class="tools flex flex-col gap-2 items-start p-4">
        <ProjectDetailt 
          :project="$project" 
          :options="{ folders: true, showIcon: true }"
          @select="$projects.setActiveProject($event)"
        />
        <a class="flex items-center gap-4 py-2 hover:bg-base-100 w-full" 
          :class="$ui.activeTab === 'projects' ? 'text-primary': ''"
          @click="handleToolClick('projects')">
          <i class="fa-solid fa-cubes"></i>
          <span>Projects</span>
        </a>

        <a class="flex items-center gap-4 py-2 hover:bg-base-100 w-full"
          :class="$ui.activeTab === 'home' ? 'text-primary': ''"
          @click="handleToolClick('home')">
          <i class="fa-solid fa-plus"></i>
          <span>Add project</span>
        </a>

        <a class="flex items-center gap-4 py-2 hover:bg-base-100 w-full"
          :class="!$project ? 'text-slate-400' : ($ui.activeTab === 'tasks' ? 'text-primary': '')"
          @click="handleProjectToolClick('tasks')">
          <i class="fa-brands fa-trello"></i>
          <span>Kanban</span>
        </a>

        <a class="flex items-center gap-4 py-2 hover:bg-base-100 w-full"
          v-if="$users.isProjectAdmin"
          :class="!$project ? 'text-slate-400' : ($ui.activeTab === 'profiles' ? 'text-primary': '')"
          @click="handleProjectToolClick('profiles')">
          <i class="fa-solid fa-user-group"></i>
          <span>Profiles</span>
        </a>

        <a class="flex items-center gap-4 py-2 hover:bg-base-100 w-full"
          :class="!$project ? 'text-slate-400' : ($ui.activeTab === 'file-finder' ? 'text-primary': '')"
          @click="handleProjectToolClick('file-finder')">
          <i class="fa-solid fa-folder"></i>
          <span>File Finder</span>
        </a>

        <div class="dropdown w-full" v-if="$projects.workspaces.length">
          <div tabindex="0" role="button" class="flex items-center gap-4 py-2 hover:bg-base-100">
            <i class="fa-solid fa-grip"></i>
            <span>Workspaces</span>
          </div>
          <WorkspacesSelector tabindex="0"
            class="dropdown-content bg-base-100 rounded-box z-1 w-full p-2 shadow-sm font-bold"
            :workspaces="$projects.workspaces"
            @select="onOpenWorkspace"
            v-if="$projects.workspaces">
          </WorkspacesSelector>
        </div>

        <a class="flex items-center gap-4 py-2 hover:bg-base-100 w-full"
          v-if="canShowBrowser"
          :class="$ui.appActives.includes('browser') ? 'text-primary': ''"
          @click.stop="toggleBrowser('browser')">
          <i class="fa-brands fa-firefox"></i>
          <span>Show Display</span>
        </a>

        <a class="flex items-center gap-4 py-2 hover:bg-base-100 w-full"
          :class="$ui.appActives.includes('coder') ? 'text-primary': ''"
          @click.stop="toggleCoder('coder')">
          <i class="fa-solid fa-code"></i>
          <span>Show Coder</span>
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
    toggleBrowser() {
      this.$emit('close');
      this.$ui.setShowBrowser(!this.$ui.appActives.includes('browser'))
    },
    toggleCoder() {
      this.$emit('close');
      this.$ui.setShowCoder(!this.$ui.appActives.includes('coder'))
    }
  },
  computed: {
    canShowBrowser() {
      return this.$users.canShowBrowser
    }
  }
}
</script>
