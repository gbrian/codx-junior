<template>
  <div class="space-y-3">
    <!-- Selected dependencies as chips: resolved projects show their icon, while
         names that no longer match a project stay visible (and removable) so a
         stale entry is never dropped silently -->
    <div class="flex flex-wrap gap-2" v-if="entries.length">
      <span
        v-for="entry in entries"
        :key="entry.name"
        class="badge badge-lg gap-2"
        :class="entry.project ? 'badge-primary badge-outline' : 'badge-warning'"
        :title="entry.project ? entry.project.abs_project_path : `No project matches '${entry.name}'`"
      >
        <img
          v-if="entry.project?.project_icon"
          :src="entry.project.project_icon"
          :alt="entry.name"
          class="w-4 h-4 rounded"
        />
        <i v-else :class="entry.icon"></i>
        <span class="font-mono text-xs">{{ entry.project?.project_name || entry.name }}</span>
        <i
          class="fa-solid fa-xmark cursor-pointer opacity-60 hover:opacity-100"
          @click="removeDependency(entry.name)"
        ></i>
      </span>
    </div>
    <div v-else class="text-sm text-base-content/60 italic">
      No dependencies yet.
    </div>

    <!-- Selection reuses ProjectDetailt so picking a dependency behaves exactly
         like every other project picker (parent / children / search sections).
         Its model is intentionally not bound: a selection is only an "add"
         action, the chips above hold the real value. -->
    <ProjectDetailt
      :model-value="null"
      placeholder="Add a dependency project"
      :display-limit="6"
      @select="addDependency"
    />

    <p v-if="feedback" class="text-xs text-warning flex items-center gap-1">
      <i class="fa-solid fa-circle-info"></i>
      <span>{{ feedback }}</span>
    </p>

    <p class="text-xs text-base-content/60">
      Dependency projects are searched together with this one: their knowledge, wiki and
      files are part of the results. Entries flagged in yellow no longer match a known project.
    </p>
  </div>
</template>

<script>
import ProjectDetailt from '@/components/ProjectDetailt.vue'

/**
 * Editor for `settings.project_dependencies`.
 *
 * The setting is persisted as a comma separated string of project names (legacy
 * format shared with the client store), so the component keeps that contract in
 * `v-model` and only translates it to project objects for the UI.
 */
export default {
  name: 'ProjectDependenciesEditor',
  components: { ProjectDetailt },
  props: {
    modelValue: {
      type: String,
      default: ''
    }
  },
  emits: ['update:modelValue'],
  data() {
    return {
      // Message shown when a selection cannot be added (self or duplicate)
      feedback: ''
    }
  },
  computed: {
    allProjects() {
      return this.$storex?.projects?.allProjects || []
    },
    currentProjectId() {
      return this.$project?.project_id || this.$storex?.projects?.activeProject?.project_id
    },
    names() {
      return (this.modelValue || '')
        .split(',')
        .map(name => name.trim())
        .filter((name, index, list) => name && list.indexOf(name) === index)
    },
    entries() {
      return this.names.map(name => {
        const project = this.allProjects.find(p => p.project_name === name)
        return {
          name,
          project,
          icon: project ? 'fa-solid fa-cube' : 'fa-solid fa-triangle-exclamation'
        }
      })
    }
  },
  methods: {
    updateModel(names) {
      this.$emit('update:modelValue', names.join(','))
    },
    addDependency(project) {
      if (!project?.project_name) return

      if (project.project_id === this.currentProjectId) {
        this.feedback = 'A project cannot depend on itself.'
        return
      }
      if (this.names.includes(project.project_name)) {
        this.feedback = `"${project.project_name}" is already a dependency.`
        return
      }

      this.feedback = ''
      this.updateModel([...this.names, project.project_name])
    },
    removeDependency(name) {
      this.feedback = ''
      this.updateModel(this.names.filter(current => current !== name))
    }
  }
}
</script>
