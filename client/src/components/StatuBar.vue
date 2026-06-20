<script setup>
import EventBar from './EventBar.vue'
import ProjectDetailt from './ProjectDetailt.vue'
</script>
<template>
  <div class="relative flex p-1 bg-base-100 items-center">
   
    <div class="click py-2 px-3 text-xl select-none font-bold leading-none border border-white/30 rounded flex items-center justify-between gap-2 indicator">
      <span class="text-error animate-pulse"
        v-if="!$storex.session.connected">
        <i class="fa-solid fa-circle-exclamation"></i>
      </span>
      <ProjectDetailt @click.stop=""
        :options="{ folders: true, showIcon: true }"
        @select="$projects.setActiveProject($event)"
      />
    </div>
    <div class="grow"></div>
    <EventBar />
  </div>
</template>
<script>
export default {
}
</script>