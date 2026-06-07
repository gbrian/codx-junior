<script setup>
import moment from 'moment'
import QuickBar from './project/QuickBar.vue'
import MainMenu from './main-menu/MainMenu.vue'
import EventBar from './EventBar.vue';
</script>
<template>
    <div class="relative flex p-1 bg-base-100">
      
      <MainMenu />
      
      <div class="grow flex gap-4 justify-center">
        <QuickBar></QuickBar>
      </div>
      <EventBar />
    </div>
</template>
<script>
export default {
}
</script>