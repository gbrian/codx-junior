<script setup>
import moment from 'moment'
import AppBar from './apps/AppBar.vue'
import MainMenu from './main-menu/MainMenu.vue'
</script>
<template>
    <div class="relative flex p-1 bg-base-100">
      
      <MainMenu />
      
      <div class="grow flex justify-center">
        <AppBar></AppBar>
      </div>
      
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
      <div class="relative">
        <div class="absolute right-0 bottom-0 flex flex-col gap-1 z-10 bg-base-100/40 rounded-lg p-2">
          <div class="click" v-for="notification in $ui.notifications" 
            :key="notification.ts" 
            @click="$ui.removeNotification(notification)">
            <pre><span class="click hover:underline">(X)</span>[{{ notification.ts }}] {{ notification.text }}</pre>
          </div>
        </div>
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