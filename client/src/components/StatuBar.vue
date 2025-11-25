<script setup>
import moment from 'moment';
</script>
<template>
    <div class="relative h-6 bg-white/10">
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
        let message = lastEvent.data?.message?.content || lastEvent.data?.text || ""
        if (messageType === 'loaded') {
          message = lastEvent.file_path
        }
        return `[${moment(lastEvent.ts).format('HH:mm:ss')}] ${messageType} ${message}`
      }
      return null
    }
  }
}
</script>