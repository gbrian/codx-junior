<script setup>
import { computed } from 'vue'
import moment from 'moment'
import { $storex } from '@/store'

const props = defineProps({
  chat: { type: Object, required: true },
  active: { type: Boolean, default: false }
})

defineEmits(['open'])

const MODE_ICONS = {
  task: 'fa-regular fa-file-lines',
  chat: 'fa-regular fa-comment',
  code: 'fa-solid fa-code',
  channel: 'fa-solid fa-hashtag',
  topic: 'fa-regular fa-comments',
  browser: 'fa-brands fa-chrome',
  answer: 'fa-solid fa-check-double',
  prview: 'fa-solid fa-code-pull-request',
  slides: 'fa-solid fa-chalkboard',
  vibe: 'fa-solid fa-hand-sparkles'
}

const STATUS_DOTS = {
  todo: 'bg-info',
  doing: 'bg-primary',
  onhold: 'bg-warning',
  done: 'bg-success',
  rejected: 'bg-error'
}

const project = computed(() =>
  $storex.projects.allProjectsById?.[props.chat.project_id || props.chat.owner_project_id] ||
  $storex.projects.activeProject
)

const modeIcon = computed(() => MODE_ICONS[props.chat.mode] || MODE_ICONS.chat)
const statusDot = computed(() => STATUS_DOTS[props.chat.status] || STATUS_DOTS.todo)
const updating = computed(() => $storex.chats.isChatUpdating(props.chat.id))
const isTask = computed(() => props.chat.mode === 'task' || !!props.chat.board)

const lastMessage = computed(() => {
  const messages = props.chat.messages || []
  if (!messages.length) return null
  return [...messages].sort((a, b) => {
    const ta = new Date(a.updated_at || a.timestamp || a.created_at || 0).getTime()
    const tb = new Date(b.updated_at || b.timestamp || b.created_at || 0).getTime()
    return tb - ta
  })[0]
})

function plainText(content) {
  return `${content || ''}`
    .replace(/<file_change[\s\S]*?<\/file_change>/gi, ' [file change] ')
    .replace(/```[\s\S]*?```/g, ' [code] ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

const preview = computed(() => {
  const text = plainText(lastMessage.value?.content)
  if (text) return text.length > 140 ? `${text.slice(0, 140)}…` : text
  const description = plainText(props.chat.description)
  if (description) return description
  return 'No messages yet'
})

const timeLabel = computed(() => {
  const timestamp = props.chat.lastMessageAt || props.chat.updated_at
  if (!timestamp) return ''
  const value = moment(timestamp)
  if (!value.isValid()) return ''
  if (value.isSame(moment(), 'day')) return value.format('HH:mm')
  if (value.isSame(moment().subtract(1, 'day'), 'day')) return 'Yesterday'
  if (value.isAfter(moment().subtract(7, 'days'))) return value.format('ddd')
  return value.format('MMM D')
})
</script>

<template>
  <button
    type="button"
    class="flex w-full gap-3 px-4 py-3 text-left transition-colors active:bg-base-200/80"
    :class="active ? 'bg-primary/10' : ''"
    @click="$emit('open', chat)"
  >
    <span class="relative block shrink-0 self-start">
      <span class="grid h-11 w-11 place-items-center overflow-hidden rounded-2xl border border-base-content/10 bg-base-200">
        <img
          v-if="project?.project_icon"
          :src="project.project_icon"
          :alt="project.project_name"
          class="h-full w-full object-cover"
        />
        <i v-else :class="modeIcon" class="text-base text-base-content/50" aria-hidden="true"></i>
      </span>
      <span
        class="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full ring-2 ring-base-300"
        :class="statusDot"
        :title="chat.status || 'todo'"
        aria-hidden="true"
      ></span>
    </span>

    <span class="min-w-0 flex-1">
      <span class="flex items-baseline gap-2">
        <span class="min-w-0 flex-1 truncate text-[13px] font-semibold leading-tight text-base-content">
          {{ chat.name || 'Untitled chat' }}
        </span>
        <span class="shrink-0 text-[10px] tabular-nums text-base-content/40">{{ timeLabel }}</span>
      </span>

      <span class="mt-0.5 line-clamp-2 block text-[11px] leading-snug text-base-content/50">
        {{ preview }}
      </span>

      <span class="mt-1 flex min-w-0 items-center gap-1.5">
        <span
          v-if="project"
          class="max-w-[8rem] truncate rounded-full bg-base-content/5 px-1.5 py-0.5 text-[9px] font-medium text-base-content/45"
        >
          {{ project.project_name }}
        </span>
        <span
          v-if="isTask"
          class="rounded-full bg-info/10 px-1.5 py-0.5 text-[9px] font-medium text-info"
        >
          Task
        </span>
        <span
          v-if="updating"
          class="flex items-center gap-1 rounded-full bg-primary/10 px-1.5 py-0.5 text-[9px] font-medium text-primary"
        >
          <span class="loading loading-dots loading-xs"></span>
          Working
        </span>
      </span>
    </span>
  </button>
</template>
