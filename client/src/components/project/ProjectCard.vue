<script setup>
import moment from 'moment';
import HeatMap from '../metrics/HeatMap.vue';
</script>
<template>
  <div class="p-4 rounded-md flex flex-col gap-2 bg-base-200 click">
    <div class="font-bold flex gap-2 items-start">
      <img class="w-6 h-6 rounded-full bg-white" :src="project.project_icon" />
      {{ project.project_name }}
    </div>
    <div class="text-xs flex gap-1 tooltip -mt-1 click hover:underline hover:text-info" 
        @click.stop="$ui.coderOpenPath(project)" 
        :data-tip="project.project_path">
      <span class="text-nowrap overflow-hidden text-ellipsis">{{ project.project_path }}</span>
    </div>
    <div class="grow"></div>
    <div class="text-xs" v-if="metrics?.last_update">
      {{ moment(metrics?.last_update).fromNow() }}
    </div>
    <div class="flex gap-2 items-center">
      <div class="text-xs text-info flex gap-1 items-center">
        <div class="flex gap-2 items-center">
          <i class="fa-solid fa-file-lines"></i> {{ metrics.file_count || 0 }}
        </div>
        <div class="text-error rounded font-bold" v-if="metrics.total_pending_changes">
          ( {{ metrics.total_pending_changes }} )
        </div>
      </div>
      <div class="text-xs text-success flex gap-1 items-center">
        <i class="fa-brands fa-trello"></i> {{ metrics.number_of_chats || 0 }}
      </div>      
    </div>
    <div class="text-xs text-error" v-if="project._error">
      <i class="fa-solid fa-exclamation"></i> {{ project._error }}
    </div>
    <HeatMap :data="heatmap" />
  </div>
</template>
<script>
export default {
  props: ['project'],
  created() {
  },
  computed: {
    metrics () {
      return this.project.metrics || {}
    },
    heatmap() {
      const heatmap = this.project.metrics?.heatmap
      return heatmap ? Object.keys(heatmap).map(dt => ({ date: dt, count: heatmap[dt] })) : []
    },
  },
  methods: {
  }
}
</script>