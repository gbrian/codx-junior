<script setup>
import CodxJunior from './CodxJunior.vue';
import MainMenu from '@/components/main-menu/MainMenu.vue';
</script>
<template>
<div class="h-full flex flex-col">
    <MainMenu />
    <div class="grow relative">
        <CodxJunior class="absolutr top-0 left-0 right-0 bottom-0 overflow-auto" />
    </div>
</div>
</template>
<script>
export default {}
</script>