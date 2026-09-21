<script setup>
import moment from 'moment'
import ChatIcon from './ChatIcon.vue'
import ProjectIcon from '../ProjectIcon.vue'
</script>

<template>
  <div
    @click="$emit('select')"
    class="card card-compact bg-base-100 border border-base-300 hover:border-primary/50 cursor-pointer transition-all duration-200 hover:shadow-md"
    :class="isActive ? 'border-primary bg-primary/5' : 'hover:bg-base-200/50'"
  >
    <div class="card-body p-3 gap-2">
      <!-- Header: Icon, Name, Timestamp -->
      <div class="flex items-start justify-between gap-2">
        <div class="flex items-center gap-2 min-w-0">
          <ChatIcon :mode="chat?.mode" class="shrink-0" />
          <div class="min-w-0 flex-1">
            <h3 class="font-semibold text-sm truncate">{{ chat?.name || 'Untitled' }}</h3>
            <div class="text-xs text-base-content/50">
              {{ formatTime(chat?.updated_at || chat?.created_at) }}
            </div>
          </div>
        </div>
        
        <!-- Badge -->
        <div v-if="chat?.type" class="badge badge-xs" :class="`badge-${badgeColor[chat.type]}`">
          {{ chat.type }}
        </div>
      </div>

      <!-- Project indicator -->
      <div v-if="chatProject" class="flex items-center gap-2 text-xs text-base-content/60">
        <img
          v-if="chatProject?.project_icon"
          :src="chatProject.project_icon"
          :alt="chatProject.project_name"
          class="w-4 h-4 rounded shrink-0"
        />
        <span class="truncate">{{ chatProject?.project_name }}</span>
      </div>

      <!-- Message snippet -->
      <div v-if="snippet" class="text-xs text-base-content/70 line-clamp-2 leading-relaxed">
        {{ snippet }}
      </div>

      <!-- Unread badge -->
      <div v-if="chat?.unread_count > 0" class="flex items-center gap-1 text-xs text-warning">
        <i class="fa-solid fa-circle text-xs"></i>
        <span>{{ chat.unread_count }} unread</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    chat: {
      type: Object,
      required: true
    },
    isActive: {
      type: Boolean,
      default: false
    },
    chatProject: {
      type: Object,
      default: null
    },
    badgeColor: {
      type: Object,
      default: () => ({ task: 'primary', chat: 'accent' })
    },
    snippet: {
      type: String,
      default: ''
    }
  },
  emits: ['select'],
  methods: {
    formatTime(date) {
      if (!date) return ''
      const momentDate = moment(date)
      const now = moment()
      
      if (now.diff(momentDate, 'days') === 0) {
        return momentDate.format('HH:mm')
      } else if (now.diff(momentDate, 'days') === 1) {
        return 'Yesterday'
      } else if (now.diff(momentDate, 'days') < 7) {
        return momentDate.format('ddd')
      } else {
        return momentDate.format('DD/MM/YY')
      }
    }
  }
}
</script>

<style scoped>
.card {
  transition: all 0.2s ease;
}

.card:hover {
  transform: translateY(-2px);
}
</style>