<script setup>
import WorkspacesList from './WorkspacesList.vue'
import WorkspaceCreate from './WorkspaceCreate.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col">
    <!-- CHANGED: WorkspacesList is always rendered; it manages create/edit dialogs internally.
         If opened with { create: true } we signal it to open the create dialog immediately. -->
    <WorkspacesList
      :project="project"
      :auto-open-create="autoOpenCreate"
      @workspace-created="onWorkspaceCreated"
    />
  </div>
</template>

<script>
export default {
  props: {
    // project prop: passed when used inside a project context
    project: {
      default: null
    },
    // ADDED: params injected by the app shell (from $ui.showApp params)
    params: {
      type: Object,
      default: () => ({})
    }
  },
  computed: {
    // ADDED: derive autoOpenCreate from the params passed via WorkspacesMenu
    autoOpenCreate() {
      return !!this.params?.create
    }
  },
  methods: {
    onWorkspaceCreated(workspace) {
      this.$emit('workspace-created', workspace)
    }
  }
}
</script>