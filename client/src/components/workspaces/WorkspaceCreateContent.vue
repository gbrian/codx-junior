<script setup>
import WorkspaceAppBuilder from './WorkspaceAppBuilder.vue'
import WorkspaceProjectSelector from './WorkspaceProjectSelector.vue'
import WorkspaceTemplateSelector from './WorkspaceTemplateSelector.vue'
</script>

<template>
  <div class="flex-1 overflow-y-auto p-8">
    
    <!-- Section: Workspace Type Selection -->
    <section v-if="activeSection === 'workspace'" class="space-y-6 max-w-2xl">
      <div class="space-y-2 mb-6">
        <h3 class="text-xl font-bold flex items-center gap-2">
          <i class="fa-solid fa-cube text-primary"></i>
          Choose Workspace Type
        </h3>
        <p class="text-sm text-base-content/60">
          Select a template that matches your development needs. You can customize everything after creation.
        </p>
      </div>

      <WorkspaceTemplateSelector
        :templates="templates"
        :selected="templates[form.template]"
        @select="form.template = $event.id"
      />

      <!-- Template Details -->
      <div v-if="form.template" class="card bg-base-200/50 border border-base-200">
        <div class="card-body">
          <h4 class="font-semibold">{{ templates[form.template].name }} Details</h4>
          <p class="text-sm text-base-content/70">{{ templates[form.template].details }}</p>
        </div>
      </div>
    </section>

    <!-- Section: Basic Information -->
    <section v-else-if="activeSection === 'basic'" class="space-y-6 max-w-2xl">
      <div class="space-y-2 mb-6">
        <h3 class="text-xl font-bold flex items-center gap-2">
          <i class="fa-solid fa-info-circle text-warning"></i>
          Basic Information
        </h3>
        <p class="text-sm text-base-content/60">
          Give your workspace a name and set its configuration folder.
        </p>
      </div>

      <!-- Workspace Name -->
      <div class="form-control">
        <label class="label">
          <span class="label-text font-semibold">Workspace Name *</span>
        </label>
        <input
          v-model="form.name"
          type="text"
          placeholder="e.g., Vue Frontend App"
          class="input input-bordered input-lg"
          required
        />
        <label class="label">
          <span class="label-text-alt">Used as the workspace identifier</span>
        </label>
      </div>

      <!-- Description -->
      <div class="form-control">
        <label class="label">
          <span class="label-text font-semibold">Description</span>
        </label>
        <textarea
          v-model="form.description"
          placeholder="What's this workspace for? (optional)"
          class="textarea textarea-bordered textarea-md"
          rows="3"
        ></textarea>
      </div>

    </section>

    <!-- Section: Configuration -->
    <section v-else-if="activeSection === 'configure'" class="space-y-6 max-w-4xl">
      <div class="space-y-2 mb-6">
        <h3 class="text-xl font-bold flex items-center gap-2">
          <i class="fa-solid fa-sliders text-secondary"></i>
          Configuration
        </h3>
        <p class="text-sm text-base-content/60">
          Configure projects, applications, and resources for this workspace.
        </p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        <!-- Projects Section -->
        <div v-if="form.template !== 'custom'" class="card bg-base-100 border border-base-200">
          <div class="card-body space-y-4">
            <h4 class="font-semibold flex items-center gap-2">
              <i class="fa-solid fa-folder text-warning"></i>
              Projects to Mount
            </h4>
            <WorkspaceProjectSelector
              :selected="form.project_ids"
              :project="project"
              @update="form.project_ids = $event"
            />
          </div>
        </div>

        <!-- Applications Section -->
        <div v-if="form.template !== 'custom'" class="card bg-base-100 border border-base-200">
          <div class="card-body space-y-4">
            <h4 class="font-semibold flex items-center gap-2">
              <i class="fa-solid fa-layer-group text-info"></i>
              Applications
            </h4>
            <WorkspaceAppBuilder
              :apps="form.apps"
              @update="form.apps = $event"
            />
          </div>
        </div>

        <!-- Resources Section (dev-stack only) -->
        <div v-if="form.template === 'dev-stack'" class="card bg-base-100 border border-base-200">
          <div class="card-body space-y-4">
            <h4 class="font-semibold flex items-center gap-2">
              <i class="fa-solid fa-microchip text-success"></i>
              Resources
            </h4>
            <div class="grid grid-cols-2 gap-3">
              <div class="form-control">
                <label class="label">
                  <span class="label-text text-sm">CPU Limit</span>
                </label>
                <input
                  v-model="form.resources.cpus"
                  type="text"
                  placeholder="e.g., 2"
                  class="input input-bordered input-sm"
                />
              </div>
              <div class="form-control">
                <label class="label">
                  <span class="label-text text-sm">Memory Limit</span>
                </label>
                <input
                  v-model="form.resources.memory"
                  type="text"
                  placeholder="e.g., 4g"
                  class="input input-bordered input-sm"
                />
              </div>
            </div>
            <label class="label cursor-pointer">
              <span class="label-text">Enable Sysbox Runtime</span>
              <input v-model="form.use_sysbox" type="checkbox" class="checkbox" />
            </label>
          </div>
        </div>

        <!-- Custom Template Info -->
        <div v-if="form.template === 'custom'" class="lg:col-span-2">
          <div class="alert alert-warning">
            <i class="fa-solid fa-wrench"></i>
            <div>
              <h4 class="font-semibold">Custom Workspace</h4>
              <p class="text-sm">You'll need to manually create the docker-compose.yaml, Dockerfile, and configuration files after workspace creation.</p>
            </div>
          </div>
        </div>

      </div>
    </section>

  </div>
</template>

<script>
export default {
  props: {
    form: Object,
    activeSection: String,
    templates: Object,
    allProjects: Array,
    allUsers: Array,
    project: Object
  },
  emits: ['update-form'],
  watch: {
    'form.name'(newVal) {
      if (!this.form.folder_path || !this.form.folder_path.trim()) {
        this.form.folder_path = newVal
          .toLowerCase()
          .replace(/\s+/g, '-')
          .replace(/[^a-z0-9-]/g, '')
      }
    }
  }
}
</script>