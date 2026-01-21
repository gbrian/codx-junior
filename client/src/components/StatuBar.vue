<script setup>
import moment from 'moment';
import AppBar from './apps/AppBar.vue';
</script>
<template>
    <div class="relative flex p-1 bg-base-100">
      <AppBar></AppBar>
      <div class="grow"></div>
      <div class="absolute top-0 right-0 h-full flex justify-end" v-if="$session.apiCalls">
        <div class="w-60 px-1 bg-gradient-to-r from-transparent to-codx-secondary/70 animate-pulse text-right">
        </div> 
      </div>
      <div class="flex gap-1 text-xs items-center h-full text-nowrap max-w-96 overflow-hidden text-ellipsis tooltip"
        :data-tip="lastEvent" :title="lastEvent"
        v-if="lastEvent"
      >
        <span class="text-info"><i class="fa-solid fa-circle-info"></i></span>
        {{  lastEvent }}
      </div>
    </div>
</template>
<script>
export default {

  computed: {
    lastEvent() {
      const { lastEvent } = this.$storex.session
      if (lastEvent) {
        const messageType = lastEvent.data?.event_type || lastEvent.data?.type || lastEvent.type || ""
        let message = lastEvent.message?.content || lastEvent.text || ""
        if (messageType === 'loaded') {
          message = lastEvent.file_path
        }
        if (message) {
          return `[${moment(lastEvent.ts).format('HH:mm:ss')}] ${messageType} ${message}`
        }
      }
      return null
    }
  }
}
</script>