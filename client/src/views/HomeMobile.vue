<script setup>
import MainMenu from '@/components/main-menu/MainMenu.vue';
import KanbanContainer from '@/components/kanban/KanbanContainer.vue';
import EventBar from '@/components/EventBar.vue';
</script>
<template>
<div class="h-full flex flex-col">
    <MainMenu v-if="!$chats.activeChat" />
    <div class="grow relative">
        <div class="absolute top-0 left-0 right-0 bottom-0">
            <KanbanContainer />
        </div>
    </div>
    <EventBar class="h-6 border-t border-slate-700 shrink-0" />
</div>
</template>
<script>
export default {}
</script>