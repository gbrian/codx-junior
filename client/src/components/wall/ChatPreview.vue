<script setup>
import moment from 'moment'
import ChatEntry from '../ChatEntry.vue'
import ProjectIcon from '../ProjectIcon.vue'
</script>
<template>
  <div class="border border-slate-700 hover:border-slate-400 rounded-lg my-2 click group">
    <div class="flex gap-2 items-center bg-slate-800 px-2 rounded-t-lg border-b border-slate-600">
      <ProjectIcon inline="true" :project="project" v-if="project" />
      <div class="divider"></div>
      <div class="flex gap-2 items-center">
        {{ chat.board }} / {{ chat.column }} / {{ chat.name }} 
      </div>
      <div class="grow"></div>
      <span class="badge badge-outline">{{ moment(chat.updated_at).fromNow() }} </span>
    </div>      
    <div class="relative p-2">
      <ChatEntry
        class="rounded-b-lg overflow-auto opacity-60 h-60 group-hover:opacity-100" 
        :menu-less="true" 
        :message="chat.messages[0]" :chat="chat"
        v-if="chat.messages[0]"
        />
        <div v-else>
          {{ chat.description }}
        </div>
      <div class="absolute top-0 left-0 right-0 bottom-0 z-20"></div>
    </div>
  </div>
</template>
<script>
export default {
  props: ['project', 'chat']
}
</script>
