<script setup>
import UserInfo from '@/components/UserInfo.vue'
import RecentChatsQuickAccess from '@/components/chats/RecentChatsQuickAccess.vue'
</script>

<template>
  <div class="flex flex-col h-full w-full bg-[#111111] overflow-hidden text-white">

    <!-- ── Top Bar ── -->
    <div class="shrink-0 flex items-center justify-between px-5 py-3 border-b border-white/8 bg-black/20">
      <!-- Logo -->
      <div class="flex items-center gap-3">
        <img src="/only_icon.png" class="w-8 h-8 rounded-lg" alt="codx-junior" />
        <span class="text-white/90 font-semibold text-base tracking-tight">codx-junior</span>
      </div>

      <!-- Right side actions -->
      <div class="flex items-center gap-2">

        <!-- Bell / Recent Activity button -->
        <div class="relative" ref="bellWrapper">
          <button
            class="btn btn-ghost btn-sm btn-circle relative"
            :class="showActivityPanel ? 'text-primary' : 'text-white/50 hover:text-white'"
            title="Recent activity"
            @click="toggleActivityPanel"
          >
            <i class="fas fa-bell text-base"></i>
            <!-- Unread dot -->
            <span
              v-if="recentChatsCount > 0"
              class="absolute top-1 right-1 w-2 h-2 rounded-full bg-primary"
            ></span>
          </button>

          <!-- Floating recent chats panel -->
          <transition name="fade-drop">
            <div
              v-if="showActivityPanel"
              class="absolute right-0 top-full mt-2 w-80 bg-[#1a1a1a] border border-white/10 rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col"
              style="max-height: 480px;"
            >
              <!-- Panel header -->
              <div class="flex items-center justify-between px-4 py-3 border-b border-white/8 shrink-0">
                <span class="text-sm font-semibold text-white/80">Recent Chats</span>
                <button
                  class="btn btn-ghost btn-xs btn-circle text-white/40 hover:text-white"
                  @click="showActivityPanel = false"
                >
                  <i class="fas fa-xmark text-xs"></i>
                </button>
              </div>

              <!-- Chat list -->
              <div class="flex-1 overflow-hidden min-h-0">
                <RecentChatsQuickAccess
                  :collapsed="false"
                  @select="onRecentChatSelect"
                />
              </div>
            </div>
          </transition>
        </div>

        <!-- User avatar -->
        <UserInfo>
          <template #trigger="{ togglePanel, dailyLimitStatus }">
            <button
              class="btn btn-xs btn-ghost p-1 w-8 h-8 min-h-0"
              @click="togglePanel"
              :class="dailyLimitStatus === 'exceeded' ? 'text-error' : dailyLimitStatus === 'warning' ? 'text-warning' : 'text-info'"
            >
              <div class="avatar tooltip" :data-tip="$user?.username">
                <div class="w-8 rounded-full">
                  <img :src="$user?.avatar">
                </div>
              </div>
            </button>
          </template>
        </UserInfo>
      </div>
    </div>

    <!-- ── Main Content ── -->
    <div
      class="flex-1 overflow-y-auto flex flex-col items-center justify-center px-6 py-10 relative"
      @click="onPageClick"
    >
      <!-- Radial gradient glow -->
      <div
        class="absolute inset-0 pointer-events-none"
        style="background: radial-gradient(ellipse 60% 40% at 50% 45%, rgba(99,102,241,0.12) 0%, transparent 70%)"
      ></div>

      <!-- Greeting -->
      <div class="relative z-10 text-center mb-8">
        <h1
          class="font-semibold tracking-tight mb-2"
          :class="isMobile ? 'text-3xl' : 'text-5xl'"
        >
          What's next, <span class="text-codx-primary">{{ firstName }}</span> ?
        </h1>
        <p class="text-white/35 text-sm mt-2">What would you like to do today?</p>
      </div>

      <!-- ── Quick chat start input ── -->
      <div class="relative z-10 w-full mb-10" :class="isMobile ? 'max-w-full' : 'max-w-xl'">
        <div class="flex items-center gap-3 bg-white/6 border border-white/10 rounded-2xl px-4 py-3 focus-within:border-primary/50 transition-colors">
          <i class="fas fa-comment-lines text-white/30 shrink-0"></i>
          <input
            v-model="chatInput"
            type="text"
            placeholder="Start a new chat…"
            class="flex-1 bg-transparent text-sm text-white/80 placeholder:text-white/25 outline-none"
            @keydown.enter="startQuickChat"
          />
          <button
            class="btn btn-sm bg-codx-primary hover:bg-primary/80 text-white border-none rounded-xl px-4"
            :disabled="!chatInput.trim()"
            @click="startQuickChat"
          >
            <i class="fas fa-arrow-right text-xs"></i>
          </button>
        </div>
      </div>

      <!-- ── Bookmark grid ── -->
      <div
        class="relative z-10 grid gap-3 w-full"
        :class="isMobile ? 'grid-cols-2 max-w-sm' : 'grid-cols-3 max-w-2xl'"
      >
        <button
          v-for="item in bookmarks"
          :key="item.route"
          class="group flex flex-col items-center gap-3 p-5 rounded-2xl bg-white/4 border border-white/8 hover:bg-white/8 hover:border-white/18 transition-all duration-200 text-center"
          @click="navigate(item)"
        >
          <!-- Icon -->
          <div class="w-12 h-12 rounded-xl flex items-center justify-center text-xl transition-transform duration-200 group-hover:scale-110 bg-white/8">
            <i :class="[item.icon, 'text-white/60']"></i>
          </div>

          <!-- Label -->
          <div class="flex flex-col gap-0.5">
            <span class="text-white/85 font-medium text-sm leading-tight">{{ item.label }}</span>
            <span class="text-white/30 text-xs leading-relaxed">{{ item.description }}</span>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import RecentChatsQuickAccess from '@/components/chats/RecentChatsQuickAccess.vue'

export default {
  name: 'AppHomeView',
  components: {
    RecentChatsQuickAccess
  },
  data() {
    return {
      chatInput: '',
      showActivityPanel: false,
      recentChatsCount: 0
    }
  },
  computed: {
    isMobile() {
      return this.$ui.isMobile
    },
    firstName() {
      const name = this.$user?.username || 'there'
      return name.split(' ')[0]
    },
    bookmarks() {
      return [
        {
          route: '/quick-chat',
          label: 'Quick Chat',
          description: 'AI-powered chat',
          icon: 'fas fa-comment-lines'
        },
        {
          route: '/desktop',
          label: 'Desktop',
          description: 'Full workspace',
          icon: 'fas fa-table-columns'
        },
        {
          route: '/messenger',
          label: 'Messenger',
          description: 'Team channels',
          icon: 'fas fa-messages'
        },
        {
          route: '/desktop/files',
          label: 'File Explorer',
          description: 'Browse files',
          icon: 'fas fa-folder-open'
        },
        {
          route: '/desktop/wiki',
          label: 'Wiki',
          description: 'Knowledge base',
          icon: 'fas fa-graduation-cap'
        },
        {
          route: '/desktop/tasks',
          label: 'Task Manager',
          description: 'Manage tasks',
          icon: 'fas fa-list-check'
        }
      ]
    }
  },
  methods: {
    navigate(item) {
      this.$router.push(item.route)
    },
    toggleActivityPanel() {
      this.showActivityPanel = !this.showActivityPanel
    },
    onPageClick(e) {
      // Close activity panel when clicking outside the bell wrapper
      if (this.showActivityPanel && this.$refs.bellWrapper && !this.$refs.bellWrapper.contains(e.target)) {
        this.showActivityPanel = false
      }
    },
    onRecentChatSelect(chat) {
      this.showActivityPanel = false
      if (chat.mode === 'group') {
        this.$router.push({ path: '/messenger', query: { chatId: chat.id } })
      } else {
        this.$router.push({ path: '/quick-chat', query: { chatId: chat.id } })
      }
    },
    startQuickChat() {
      const text = this.chatInput.trim()
      if (!text) return
      // Navigate to quick-chat with the initial message as a query param
      this.$router.push({ path: '/quick-chat', query: { message: text } })
    }
  }
}
</script>

<style scoped>
.fade-drop-enter-active, .fade-drop-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.fade-drop-enter-from, .fade-drop-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>