<script setup>
import moment from 'moment'
import ProjectIcon from '@/components/ProjectIcon.vue'
</script>

<template>
  <div
    :class="[
      'p-3 rounded-xl border transition-all duration-200 cursor-pointer flex flex-col gap-2.5 relative overflow-hidden group',
      isActive
        ? 'bg-primary/10 border-primary/40 text-base-content shadow-sm ring-1 ring-primary/20'
        : 'bg-base-300/30 border-base-content/5 hover:bg-base-300/60 hover:border-base-content/10'
    ]"
    @click="onClick"
  >
    <!-- Top Row: Project context with working project indicator -->
    <div class="flex items-center justify-between gap-2">
      <div class="flex items-center gap-2 min-w-0">
        <!-- Project Icon with visual integration -->
        <div class="shrink-0">
          <ProjectIcon 
            :project="chatWorkingProject"
            :width="5"
            :icon-only="true"
          />
        </div>
        
        <span class="text-[11px] font-semibold text-base-content/50 truncate max-w-[120px]">
          {{ chatWorkingProject?.project_name || 'No Project' }}
          <span v-if="chat.board" class="text-base-content/30 mx-0.5">/</span>
          <span v-if="chat.board" class="text-base-content/70 font-bold">{{ chat.board }}</span>
        </span>
      </div>

      <!-- Mode/Badge with enhanced styling -->
      <div class="flex items-center gap-1 shrink-0">
        <span
          v-if="chat.mode"
          :class="`badge badge-xs badge-outline text-[9px] px-1.5 py-0.5 font-semibold border-base-content/25 badge-${badgeColor[chat.mode] || 'ghost'}`"
        >
          {{ chat.mode }}
        </span>
      </div>
    </div>

    <!-- Middle Row: Chat initials, name and status -->
    <div class="flex items-center gap-2.5 min-w-0">
      <div
        class="w-8 h-8 rounded-lg flex items-center justify-center text-[10px] font-bold shrink-0 transition-all duration-200 overflow-hidden relative border border-base-content/10 group-hover:scale-105"
        :class="isActive
          ? 'bg-primary text-primary-content font-extrabold'
          : 'bg-base-300 text-base-content'"
      >
        {{ getInitials(chat.name) }}
      </div>

      <div class="flex-1 min-w-0">
        <div class="text-xs font-bold truncate text-base-content" :title="chat.name">
          {{ chat.name || 'Unnamed Chat' }}
        </div>
        <div class="text-[10px] text-base-content/40 font-medium">
          {{ formattedDate }}
        </div>
      </div>

      <!-- Active indicator dot -->
      <div
        v-if="isActive"
        class="w-2 h-2 bg-success rounded-full border border-base-100 shrink-0 animate-pulse"
      ></div>
    </div>

    <!-- Bottom Row: Snippet with enhanced styling -->
    <div class="text-[10px] text-base-content/60 leading-relaxed bg-base-300/20 rounded-lg p-2 border border-base-content/5 line-clamp-2 group-hover:bg-base-300/30 transition-colors">
      {{ snippet }}
    </div>

    <!-- Template Metadata Footer (if applicable) -->
    <div v-if="showMetadata" class="flex items-center justify-between text-[9px] text-base-content/40 pt-1 border-t border-base-content/5">
      <span v-if="messageCount">📝 {{ messageCount }} messages</span>
      <span v-else>Template</span>
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
    badgeColor: {
      type: Object,
      default: () => ({
        task: 'primary',
        chat: 'accent'
      })
    },
    snippet: {
      type: String,
      default: ''
    },
    messageCount: {
      type: Number,
      default: null
    },
    showMetadata: {
      type: Boolean,
      default: true
    }
  },
  computed: {
    formattedDate() {
      if (!this.chat.updated_at) return 'Never'
      return moment(this.chat.updated_at).fromNow()
    },
    chatWorkingProject() {
      return this.$chats.getChatWorkingProject(this.chat)
    }
  },
  methods: {
    onClick() {
      this.$emit('select')
    },
    getInitials(name) {
      if (!name) return 'CH'
      const cleanName = name.replace(/[^\w\s-]/g, '').trim()
      const words = cleanName.split(/\s+/)
      if (words.length >= 2) {
        return (words[0][0] + words[1][0]).toUpperCase()
      }
      return name.substring(0, 2).toUpperCase()
    }
  }
}
</script>