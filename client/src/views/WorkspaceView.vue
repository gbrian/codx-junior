<script setup>
import WorkspaceAppLoader from '@/components/quick-chat/WorkspaceAppLoader.vue';
</script>
<template>
    <WorkspaceAppLoader
        v-if="selectedWorkspaceApp"
        :app="selectedWorkspaceApp"
        :showHeader="false"
    />
</template>
<script>
export default {
    computed: {
        workspaceId() {
            return this.$router.$navigation.getWorkspaceId()
        },
        selectedWorkspaceApp() {
            return this.$projects.projectApps.find(app => app.key === this.workspaceId)
        }
    }
}
</script>