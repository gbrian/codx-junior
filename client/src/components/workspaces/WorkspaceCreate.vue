<script setup>
import WorkspaceCreateSidebar from './WorkspaceCreateSidebar.vue'
import WorkspaceCreateContent from './WorkspaceCreateContent.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col bg-base-100">
    
    <!-- Header Bar -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-base-200 bg-base-100 shrink-0">
      <div class="flex items-center gap-3">
        <button 
          class="btn btn-ghost btn-sm btn-circle"
          @click="$emit('close')"
          title="Back to workspaces"
        >
          <i class="fa-solid fa-arrow-left"></i>
        </button>
        <div class="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
          <i class="fa-solid fa-cube"></i>
        </div>
        <div>
          <h2 class="text-2xl font-bold">Create Workspace</h2>
          <p class="text-xs text-base-content/50">Set up a new development environment</p>
        </div>
      </div>
    </div>

    <!-- Main Layout: Sidebar + Content -->
    <div class="flex-1 flex gap-0 overflow-hidden">
      <WorkspaceCreateSidebar
        :active-section="activeSection"
        :form="form"
        :is-valid="isFormValid"
        @select-section="goToSection"
      />

      <WorkspaceCreateContent
        :form="form"
        :active-section="activeSection"
        :templates="templates"
        :all-projects="allProjects"
        :all-users="allUsers"
        @update-form="updateForm"
      />
    </div>

    <!-- Footer Bar -->
    <div class="flex items-center justify-between px-6 py-4 border-t border-base-200 bg-base-100 shrink-0">
      <div class="flex gap-2">
        <button 
          class="btn btn-ghost btn-md"
          @click="previousSection"
          :disabled="activeSection === 'workspace'"
        >
          <i class="fa-solid fa-arrow-left"></i>
          Back
        </button>
      </div>
      <div class="flex gap-3">
        <button 
          class="btn btn-ghost btn-md"
          @click="resetForm"
        >
          Reset
        </button>
        <button
          v-if="activeSection !== 'configure'"
          class="btn btn-primary btn-md gap-2"
          :disabled="!canProceedToNext"
          @click="nextSection"
        >
          Next
          <i class="fa-solid fa-arrow-right"></i>
        </button>
        <button
          v-else
          class="btn btn-success btn-md gap-2"
          :disabled="!isFormValid || isCreating"
          @click="createWorkspace"
        >
          <span v-if="isCreating" class="loading loading-spinner loading-sm"></span>
          <i v-else class="fa-solid fa-check"></i>
          Create Workspace
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['project'],
  emits: ['close', 'created'],
  data() {
    return {
      activeSection: 'workspace',
      isCreating: false,
      allProjects: [],
      allUsers: [],
      templates: {
        'static-site': {
          id: 'static-site',
          name: 'Static Site',
          icon: 'fa-globe',
          description: 'Single container running a web site / dev server (e.g., Vue, React, Next.js)',
          details: 'Perfect for frontend projects. Includes Node.js, npm, and a dev server. No Docker-in-Docker support.',
          color: 'info'
        },
        'dev-stack': {
          id: 'dev-stack',
          name: 'Full-Stack Dev',
          icon: 'fa-cube',
          description: 'Sysbox container with systemd + inner Docker for full-stack development',
          details: 'Advanced environment with systemd and Docker daemon. Ideal for microservices, backend testing, and multi-container apps.',
          color: 'warning'
        },
        'custom': {
          id: 'custom',
          name: 'Custom',
          icon: 'fa-wrench',
          description: 'Empty workspace, admin provides all files',
          details: 'Blank slate. You define the entire docker-compose.yaml, Dockerfile, and runtime configuration.',
          color: 'secondary'
        }
      },
      form: {
        name: '',
        description: '',
        folder_path: '',
        template: '',
        project_ids: [],
        user_ids: [],
        apps: [],
        resources: {
          cpus: '',
          memory: '',
          shm_size: '512m'
        },
        use_sysbox: false
      }
    }
  },
  computed: {
    canProceedToNext() {
      if (this.activeSection === 'workspace') {
        return this.form.template
      }
      if (this.activeSection === 'basic') {
        return this.form.name && this.form.folder_path
      }
      return true
    },
    isFormValid() {
      return this.form.name && this.form.folder_path && this.form.template
    }
  },
  async mounted() {
    await this.loadProjects()
    await this.loadUsers()
    this.initializeFormDefaults()
  },
  methods: {
    async loadProjects() {
      try {
        this.allProjects = await this.project.$api.projects.list() || []
      } catch (error) {
        console.error('Failed to load projects', error)
      }
    },
    async loadUsers() {
      try {
        await this.$storex.users.loadUsers()
        this.allUsers = this.$storex.users.users || []
      } catch (error) {
        console.error('Failed to load users', error)
      }
    },
    initializeFormDefaults() {
      this.form.apps = [{
        name: 'App',
        icon: 'fa-globe',
        path: '/app',
        port: 3000,
        roles: ['admin'],
        is_vnc: false,
        scheme: 'http'
      }]
    },
    updateForm(updates) {
      Object.assign(this.form, updates)
    },
    goToSection(section) {
      this.activeSection = section
    },
    nextSection() {
      const sections = ['workspace', 'basic', 'configure']
      const idx = sections.indexOf(this.activeSection)
      if (idx < sections.length - 1) {
        this.activeSection = sections[idx + 1]
      }
    },
    previousSection() {
      const sections = ['workspace', 'basic', 'configure']
      const idx = sections.indexOf(this.activeSection)
      if (idx > 0) {
        this.activeSection = sections[idx - 1]
      }
    },
    resetForm() {
      if (confirm('Reset all fields?')) {
        this.form = {
          name: '',
          description: '',
          folder_path: '',
          template: '',
          project_ids: [],
          user_ids: [],
          apps: [{
            name: 'App',
            icon: 'fa-globe',
            path: '/app',
            port: 3000,
            roles: ['admin'],
            is_vnc: false,
            scheme: 'http'
          }],
          resources: {
            cpus: '',
            memory: '',
            shm_size: '512m'
          },
          use_sysbox: false
        }
        this.activeSection = 'workspace'
      }
    },
    async createWorkspace() {
      if (!this.isFormValid) return
      this.isCreating = true
      try {
        const workspace = await this.project.$api.projects.workspaces.create({
          ...this.form,
          status: 'stopped'
        })
        this.$emit('created', workspace)
      } catch (error) {
        alert(`Failed to create workspace: ${error.message}`)
      } finally {
        this.isCreating = false
      }
    }
  }
}
</script>