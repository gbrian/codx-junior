<script setup>
import MainMenu from '@/components/main-menu/MainMenu.vue';
import KanbanContainer from '@/components/kanban/KanbanContainer.vue';
import ProjectDetailt from '@/components/ProjectDetailt.vue';
</script>
<template>
<div class="h-full flex flex-col">
    <div class="p-2 flex justify-between items-center"
        v-if="!$chats.activeChat"
    >
        <MainMenu />
        <ProjectDetailt 
            @select="$projects.activeProjectChanged($event)"
        />
    </div>
    <div class="grow relative">
        <div class="absolute top-0 left-0 right-0 bottom-0">
            <KanbanContainer class="pt-1" />
        </div>
    </div>
</div>
</template>
<script>
export default {}
</script>