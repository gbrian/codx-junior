<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import moment from 'moment'
import { $storex } from '@/store'
import MobileChatRow from '@/components/mobile/MobileChatRow.vue'

const router = useRouter()

const searchOpen = ref(false)
const search = ref('')
const searchInput = ref(null)
const filter = ref('all')
const page = ref(1)

const PAGE_SIZE = 40

const source = computed(() => {
  const recent = $storex.chats.recentChats || []
  if (recent.length) return recent
  return [...($storex.chats.allChats || [])].sort((a, b) => {
    const ta = new Date(a.lastMessageAt || a.updated_at || 0).getTime()
    const tb = new Date(b.lastMessageAt || b.updated_at || 0).getTime()
    return tb - ta
  })
})

const loading = computed(() => $storex.chats.recentChatsLoading)
const hasMore = computed(() => $storex.chats.recentChatsHasMore)
const activeChatId = computed(() =>
  $storex.chats.activeChat?.id ||
  $storex.$router?.currentRoute?.value?.params?.chatId ||
  null
)
const project = computed(() => $storex.projects.activeProject)

function isTask(chat) {
  return chat.mode === 'task' || !!chat.board
}
function isChannel(chat) {
  return chat.mode === 'channel'
}

const counts = computed(() => {
  const chats = source.value
  return {
    all: chats.length,
    chats: chats.filter(chat => !isTask(chat) && !isChannel(chat)).length,
    tasks: chats.filter(isTask).length,
    channels: chats.filter(isChannel).length
  }
})

const filters = computed(() => [
  { key: 'all', label: 'All', count: counts.value.all },
  { key: 'chats', label: 'Chats', count: counts.value.chats },
  { key: 'tasks', label: 'Tasks', count: counts.value.tasks },
  { key: 'channels', label: 'Channels', count: counts.value.channels }
])

const filteredChats = computed(() => {
  const query = search.value.trim().toLowerCase()
  return source.value.filter(chat => {
    if (filter.value === 'chats' && (isTask(chat) || isChannel(chat))) return false
    if (filter.value === 'tasks' && !isTask(chat)) return false
    if (filter.value === 'channels' && !isChannel(chat)) return false
    if (!query) return true
    return `${chat.name || ''} ${chat.description || ''}`.toLowerCase().includes(query)
  })
})

const groups = computed(() => {
  const chats = filteredChats.value
  if (search.value.trim()) return [{ key: 'results', label: `${chats.length} result${chats.length === 1 ? '' : 's'}`, chats }]

  const buckets = [
    { key: 'today', label: 'Today', chats: [] },
    { key: 'yesterday', label: 'Yesterday', chats: [] },
    { key: 'week', label: 'Earlier this week', chats: [] },
    { key: 'older', label: 'Earlier', chats: [] }
  ]

  chats.forEach(chat => {
    const timestamp = chat.lastMessageAt || chat.updated_at
    const value = timestamp ? moment(timestamp) : null
    if (!value || !value.isValid()) {
      buckets[3].chats.push(chat)
      return
    }
    if (value.isSame(moment(), 'day')) buckets[0].chats.push(chat)
    else if (value.isSame(moment().subtract(1, 'day'), 'day')) buckets[1].chats.push(chat)
    else if (value.isAfter(moment().subtract(7, 'days'))) buckets[2].chats.push(chat)
    else buckets[3].chats.push(chat)
  })

  return buckets.filter(bucket => bucket.chats.length)
})

async function load(append = false) {
  const userId = $storex.users.user?.id
  await $storex.chats.loadRecentChats({
    userId,
    page: page.value,
    pageSize: PAGE_SIZE,
    append
  })
}

function loadMore() {
  if (!hasMore.value || loading.value) return
  page.value += 1
  load(true)
}

function onScroll(event) {
  const element = event.target
  if (element.scrollHeight - element.scrollTop - element.clientHeight < 220) loadMore()
}

function openChat(chat) {
  if (!chat?.id) return
  $storex.$router?.$navigation?.chats.open(chat.id, chat.name)
}

function newChat() {
  router.push({ name: 'new-chat' })
}

function toggleSearch() {
  searchOpen.value = !searchOpen.value
  if (searchOpen.value) {
    nextTick(() => searchInput.value?.focus())
  } else {
    search.value = ''
  }
}

onMounted(() => {
  load(false)
})
</script>

<template>
  <div class="relative flex h-full min-h-0 flex-col bg-base-300">
    <!-- ── Header ─────────────────────────────────────────────────── -->
    <header class="shrink-0 border-b border-base-content/10 bg-base-200/85 backdrop-blur-md">
      <div class="px-4 pb-2 pt-3">
        <div class="flex items-start gap-2">
          <div class="min-w-0 flex-1">
            <h1 class="text-[22px] font-bold leading-tight tracking-tight text-base-content">Chats</h1>
            <p class="mt-0.5 flex items-center gap-1.5 truncate text-[11px] text-base-content/45">
              <img
                v-if="project?.project_icon"
                :src="project.project_icon"
                :alt="project.project_name"
                class="h-4 w-4 rounded object-cover"
              />
              <span class="truncate">{{ project?.project_name || 'Your project' }}</span>
              <span aria-hidden="true">·</span>
              <span>{{ counts.all }} conversation{{ counts.all === 1 ? '' : 's' }}</span>
            </p>
          </div>

          <button
            type="button"
            class="mobile-icon-btn mt-0.5"
            :class="searchOpen ? 'bg-primary/15 text-primary' : ''"
            :aria-label="searchOpen ? 'Close search' : 'Search chats'"
            :aria-pressed="searchOpen"
            @click="toggleSearch"
          >
            <i :class="searchOpen ? 'fa-solid fa-xmark' : 'fa-solid fa-magnifying-glass'" class="text-sm"></i>
          </button>

        </div>

        <div v-if="searchOpen" class="mt-2.5">
          <label class="flex h-10 items-center gap-2 rounded-xl border border-base-content/10 bg-base-100 px-3 focus-within:border-primary/50">
            <i class="fa-solid fa-magnifying-glass text-[11px] text-base-content/40" aria-hidden="true"></i>
            <input
              ref="searchInput"
              v-model="search"
              type="search"
              enterkeyhint="search"
              placeholder="Search conversations"
              class="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-base-content/35"
              aria-label="Search conversations"
            />
            <button
              v-if="search"
              type="button"
              class="grid h-6 w-6 place-items-center rounded-full bg-base-content/10 text-[10px]"
              aria-label="Clear search"
              @click="search = ''"
            >
              <i class="fa-solid fa-xmark"></i>
            </button>
          </label>
        </div>
      </div>

      <!-- Filters -->
      <div class="no-scrollbar flex gap-1.5 overflow-x-auto px-4 pb-2.5">
        <button
          v-for="item in filters"
          :key="item.key"
          type="button"
          class="flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-medium transition-colors"
          :class="filter === item.key
            ? 'border-primary/40 bg-primary/15 text-primary'
            : 'border-base-content/10 bg-base-100 text-base-content/55'"
          :aria-pressed="filter === item.key"
          @click="filter = item.key"
        >
          {{ item.label }}
          <span
            class="rounded-full px-1.5 text-[9px] tabular-nums"
            :class="filter === item.key ? 'bg-primary/20' : 'bg-base-content/5'"
          >{{ item.count }}</span>
        </button>
      </div>
    </header>

    <!-- ── Conversation list ──────────────────────────────────────── -->
    <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain" @scroll="onScroll">
      <section v-for="group in groups" :key="group.key">
        <h2 class="sticky top-0 z-10 border-b border-base-content/5 bg-base-300/95 px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider text-base-content/40 backdrop-blur">
          {{ group.label }}
        </h2>
        <MobileChatRow
          v-for="chat in group.chats"
          :key="chat.id"
          :chat="chat"
          :active="chat.id === activeChatId"
          @open="openChat"
        />
        <div class="h-px bg-base-content/5" aria-hidden="true"></div>
      </section>

      <!-- Loading skeleton -->
      <div v-if="loading && !source.length" class="space-y-1 px-4 py-3">
        <div v-for="index in 6" :key="index" class="flex gap-3 py-2">
          <div class="skeleton h-11 w-11 shrink-0 rounded-2xl"></div>
          <div class="flex-1 space-y-2">
            <div class="skeleton h-3 w-1/2 rounded-full"></div>
            <div class="skeleton h-2.5 w-5/6 rounded-full"></div>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div
        v-else-if="!loading && !filteredChats.length"
        class="flex flex-col items-center justify-center gap-4 px-8 py-20 text-center"
      >
        <span class="grid h-16 w-16 place-items-center rounded-3xl bg-base-content/5 text-base-content/25">
          <i class="fa-regular fa-comments text-2xl"></i>
        </span>
        <div>
          <p class="text-sm font-semibold text-base-content/70">
            {{ search ? 'No conversations match your search' : 'No conversations yet' }}
          </p>
          <p class="mt-1 text-xs text-base-content/40">
            {{ search ? 'Try another name or clear the search.' : 'Start a chat and it will show up here.' }}
          </p>
        </div>
        <button
          v-if="!search"
          type="button"
          class="btn btn-primary btn-sm h-10 rounded-xl px-4"
          @click="newChat"
        >
          <i class="fa-solid fa-plus text-xs"></i> New chat
        </button>
      </div>

      <!-- Pagination -->
      <div v-if="filteredChats.length && hasMore" class="px-4 py-3">
        <button
          type="button"
          class="btn btn-ghost btn-sm h-10 w-full rounded-xl text-xs"
          :disabled="loading"
          @click="loadMore"
        >
          <span v-if="loading" class="loading loading-spinner loading-xs"></span>
          <span v-else>Load more</span>
        </button>
      </div>

      <div class="h-24" aria-hidden="true"></div>
    </div>

    <!-- Floating compose button above the tab bar -->
    <button
      v-if="source.length"
      type="button"
      class="absolute bottom-4 right-4 z-20 grid h-14 w-14 place-items-center rounded-2xl bg-primary text-primary-content shadow-xl shadow-primary/25 transition-transform active:scale-95"
      aria-label="New chat"
      @click="newChat"
    >
      <i class="fa-solid fa-plus text-lg" aria-hidden="true"></i>
    </button>
  </div>
</template>
