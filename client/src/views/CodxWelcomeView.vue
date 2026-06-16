<script setup>
import Wall from '../components/wall/Wall.vue'
</script>

<template>
  <div class="h-full flex flex-col bg-base-100 overflow-hidden">
    <!-- Top Bar -->
    <div class="flex items-center gap-4 px-6 py-3 border-b border-base-300 bg-base-100">
      <img src="/only_icon.png" class="w-6 h-6" />
      <span class="font-bold text-lg tracking-tight">codx<span class="text-primary">-junior</span></span>
      <div class="flex-1"></div>
      <!-- Search / Command Palette trigger -->
      <div class="flex items-center gap-2 bg-base-200 rounded-lg px-3 py-1.5 cursor-pointer hover:bg-base-300 transition-colors min-w-48"
        @click="showSearch = true">
        <i class="fa-solid fa-magnifying-glass text-base-content/40 text-sm"></i>
        <span class="text-sm text-base-content/40">Search or jump to...</span>
        <kbd class="kbd kbd-sm ml-auto">⌘K</kbd>
      </div>
      <div class="flex gap-1">
        <button class="btn btn-ghost btn-sm btn-circle" @click="$ui.setActiveTab('analytics')">
          <i class="fa-solid fa-chart-area"></i>
        </button>
        <button class="btn btn-ghost btn-sm btn-circle" @click="$ui.setActiveTab('wiki')">
          <i class="fa-solid fa-graduation-cap"></i>
        </button>
        <button class="btn btn-primary btn-sm gap-1" @click="onNewQuickChat">
          <i class="fa-solid fa-plus text-xs"></i> Chat
        </button>
      </div>
    </div>

    <!-- Search Modal -->
    <div v-if="showSearch" class="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/50"
      @click.self="showSearch = false">
      <div class="card bg-base-100 shadow-2xl w-full max-w-lg border border-base-300">
        <div class="card-body p-3">
          <input
            ref="searchInput"
            v-model="searchQuery"
            type="text"
            placeholder="Search projects, chats, commands..."
            class="input input-bordered w-full"
            @keydown.escape="showSearch = false"
          />
          <ul class="menu p-0 mt-1 gap-0.5 max-h-64 overflow-y-auto">
            <li v-for="result in searchResults" :key="result.key">
              <a class="flex gap-3" @click="result.fn(); showSearch = false">
                <i :class="result.icon" class="text-primary w-4 text-center"></i>
                <span>{{ result.label }}</span>
                <span class="text-xs text-base-content/40 ml-auto">{{ result.type }}</span>
              </a>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Main 3-pane layout -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Pane 1: Navigation Rail -->
      <div class="w-14 flex flex-col items-center py-4 gap-3 border-r border-base-300 bg-base-200">
        <button v-for="nav in navRail" :key="nav.tab"
          class="btn btn-ghost btn-square btn-sm tooltip tooltip-right"
          :data-tip="nav.label"
          :class="activePane === nav.tab ? 'bg-primary text-primary-content hover:bg-primary' : ''"
          @click="activePane = nav.tab">
          <i :class="nav.icon"></i>
        </button>
      </div>

      <!-- Pane 2: Content Panel -->
      <div class="w-72 flex-shrink-0 border-r border-base-300 flex flex-col overflow-hidden">
        <!-- Pane header -->
        <div class="px-3 py-2 border-b border-base-300 text-sm font-semibold text-base-content/70 flex items-center gap-2">
          <i :class="activeNavItem?.icon" class="text-primary"></i>
          {{ activeNavItem?.label }}
        </div>

        <!-- Projects pane -->
        <div v-if="activePane === 'projects'" class="flex-1 overflow-y-auto p-2 flex flex-col gap-1">
          <div v-for="project in $projects.allProjects" :key="project.project_id"
            class="flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer hover:bg-base-200 transition-colors"
            :class="$projects.activeProject?.project_id === project.project_id ? 'bg-primary/10 text-primary' : ''"
            @click="gotoProject(project)">
            <span v-if="project.project_icon" v-html="project.project_icon" class="w-4 text-center text-sm"></span>
            <i v-else class="fa-solid fa-folder text-sm w-4 text-center"></i>
            <span class="text-sm truncate flex-1">{{ project.project_name }}</span>
          </div>
        </div>

        <!-- Chats pane -->
        <div v-if="activePane === 'chats'" class="flex-1 overflow-y-auto p-2 flex flex-col gap-1">
          <div v-for="chat in sortedChats" :key="chat.id"
            class="flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer hover:bg-base-200 transition-colors"
            @click="openChat(chat)">
            <i class="fa-solid fa-message text-xs text-accent w-4 text-center"></i>
            <div class="flex-1 min-w-0">
              <div class="text-sm truncate">{{ chat.name || 'Untitled' }}</div>
              <div class="text-xs text-base-content/40 truncate">{{ chat.updated_at }}</div>
            </div>
          </div>
        </div>

        <!-- Tasks pane -->
        <div v-if="activePane === 'tasks'" class="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
          <button class="btn btn-primary btn-sm w-full gap-2" @click="$ui.setActiveTab('tasks')">
            <i class="fa-brands fa-trello"></i> Open Task Manager
          </button>
          <div class="text-xs text-base-content/40 text-center mt-2">View boards and manage tasks</div>
        </div>
      </div>

      <!-- Pane 3: Activity Feed -->
      <div class="flex-1 overflow-hidden flex flex-col">
        <div class="px-4 py-2 border-b border-base-300 flex items-center gap-2">
          <i class="fa-solid fa-wave-square text-primary"></i>
          <span class="text-sm font-semibold">Activity Feed</span>
          <div class="badge badge-primary badge-sm ml-auto">Live</div>
        </div>
        <div class="flex-1 overflow-auto p-4">
          <Wall />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      activePane: 'projects',
      showSearch: false,
      searchQuery: '',
      navRail: [
        { tab: 'projects', label: 'Projects', icon: 'fa-solid fa-folder' },
        { tab: 'chats', label: 'Chats', icon: 'fa-solid fa-comments' },
        { tab: 'tasks', label: 'Tasks', icon: 'fa-brands fa-trello' },
      ]
    }
  },
  computed: {
    activeNavItem() {
      return this.navRail.find(n => n.tab === this.activePane)
    },
    sortedChats() {
      return $storex.chats.allChats
        .sort((a, b) => a.updated_at > b.updated_at ? -1 : 1)
        .slice(0, 20)
    },
    // Search across projects and chats
    searchResults() {
      if (!this.searchQuery) return []
      const q = this.searchQuery.toLowerCase()
      const projectResults = $storex.projects.allProjects
        .filter(p => p.project_name.toLowerCase().includes(q))
        .slice(0, 4)
        .map(p => ({
          key: `project-${p.project_id}`,
          label: p.project_name,
          type: 'Project',
          icon: 'fa-solid fa-folder',
          fn: () => this.gotoProject(p)
        }))
      const chatResults = $storex.chats.allChats
        .filter(c => (c.name || '').toLowerCase().includes(q))
        .slice(0, 4)
        .map(c => ({
          key: `chat-${c.id}`,
          label: c.name || 'Untitled',
          type: 'Chat',
          icon: 'fa-solid fa-message',
          fn: () => this.openChat(c)
        }))
      return [...projectResults, ...chatResults]
    }
  },
  methods: {
    async onNewQuickChat() {
      const chat = await this.$service.chat.newQuickChat()
      this.$ui.openChat(chat)
    },
    gotoProject(project) {
      this.$projects.setActiveProject(project)
      this.$ui.setActiveTab('tasks')
    },
    openChat(chat) {
      this.$chats.setActiveChat(chat)
      this.$ui.setActiveTab('tasks')
    }
  }
}
</script>