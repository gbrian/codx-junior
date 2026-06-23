<script setup>
import ChatIcon from '@/components/chat/ChatIcon.vue'
import ExportChat from '@/components/chat/ExportChat.vue'
import TaskSettings from '@/components/kanban/TaskSettings.vue'
import ChatSelector from '@/components/chat/ChatSelector.vue'
import ProjectDetailt from '@/components/ProjectDetailt.vue'
</script>

<template>
  <div class="flex flex-col shrink-0 bg-base-200/60 border-b border-base-content/10">
    <!-- Header row with icon, name, and action buttons -->
    <div class="flex items-center gap-1 px-2 py-1.5 min-h-0">
      
      <div class="flex gap-2 items-center">
        <div class="badge badge-outline">
        <ProjectDetailt 
          v-model="targetProject" 
          :iconify="false"
          :iconSize="4"
          :options="{ showFolders: false, showIcon: true, showSelector: true }"
          @select="setChatProject"
        />
        </div>
        <span class="text-sm font-bold truncate grow">{{ chat?.name || 'Vibe session' }}</span>
      </div>

      <div class="grow"></div>

      <!-- Chat mode selector dropdown -->
      <div class="dropdown dropdown-end shrink-0" v-if="chat">
        <div tabindex="0" role="button" class="btn btn-xs btn-ghost" title="Chat mode">
          <ChatIcon :mode="chat.mode" class="text-xs" />
        </div>
        <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-20 w-44 p-1 shadow text-xs">
          <li @click="setChatMode('chat')"><a><ChatIcon mode="chat" /> Conversation</a></li>
          <li @click="setChatMode('task')"><a><ChatIcon mode="task" /> Document</a></li>
          <li @click="setChatMode('topic')"><a><ChatIcon mode="topic" /> Group chat</a></li>
          <li @click="setChatMode('vibe')"><a><ChatIcon mode="vibe" /> Vibe</a></li>
          <li @click="setChatMode('prview')"><a><ChatIcon mode="prview" /> Changes review</a></li>
          <li @click="setChatMode('browser')"><a><ChatIcon mode="browser" /> Browser</a></li>
        </ul>
      </div>

      <!-- Message count / hidden toggle -->
      <button
        v-if="chat"
        class="btn btn-xs btn-ghost shrink-0 tooltip"
        :class="showHiddenMessages ? 'text-warning' : ''"
        :data-tip="`${visibleCount} msgs${hiddenCount ? ` / ${hiddenCount} hidden` : ''}`"
        @click="toggleHidden"
        title="Toggle hidden messages"
      >
        <i class="fa-regular fa-message text-xs"></i>
        <span class="text-xs ml-0.5">{{ visibleCount }}</span>
        <span v-if="hiddenCount" class="text-xs opacity-60">
          <i class="fa-regular fa-eye-slash"></i>{{ hiddenCount }}
        </span>
      </button>

      <!-- Search toggle -->
      <button
        class="btn btn-xs btn-ghost shrink-0"
        :class="showSearch ? 'text-primary' : ''"
        @click="showSearch = !showSearch"
        title="Search messages"
      >
        <i class="fa-solid fa-magnifying-glass text-xs"></i>
      </button>

      <!-- ⋮ More menu -->
      <div class="dropdown dropdown-end shrink-0" v-if="chat">
        <div tabindex="0" role="button" class="btn btn-xs btn-ghost">
          <i class="fa-solid fa-ellipsis-vertical text-xs"></i>
        </div>
        <ul tabindex="0" class="dropdown-content menu bg-base-300 border rounded-box z-20 w-52 p-1 shadow text-xs">
          <li @click="$emit('new-subtask')"><a><i class="fa-solid fa-plus"></i> New subtask</a></li>
          <li @click="$emit('create-subtasks')"><a><i class="fa-solid fa-wand-magic-sparkles"></i> Create subtasks</a></li>
          <li @click="showExportChat = true"><a><i class="fa-solid fa-file-arrow-down"></i> Export</a></li>
          <li @click="showChatSelector = true"><a><i class="fa-solid fa-link"></i> Link chats</a></li>
          <li @click="$emit('new-tag')"><a><i class="fa-solid fa-tag"></i> Add tag</a></li>
          <hr class="my-1"/>
          <li @click="$emit('reload')"><a><i class="fa-solid fa-recycle"></i> Reload</a></li>
          <li @click="saveChat"><a><i class="fa-solid fa-floppy-disk"></i> Save</a></li>
          <hr class="my-1"/>
          <li @click="showTaskSettings = true"><a><i class="fa-solid fa-gear"></i> Settings</a></li>
          <li @click="showDeleteConfirm = true"><a class="text-error"><i class="fa-solid fa-trash"></i> Delete</a></li>
        </ul>
      </div>
    </div>

    <!-- Search bar (conditional) -->
    <div class="flex items-center gap-1 px-2 pb-1 bg-base-200/30" v-if="showSearch">
      <div class="flex input input-xs input-bordered items-center gap-1 flex-1">
        <input
          v-model="chatSearch"
          class="bg-transparent w-full min-w-0 text-xs"
          placeholder="Search messages..."
          @input="$emit('update:search', chatSearch)"
        />
        <span class="text-error cursor-pointer text-xs" @click="clearSearch" v-if="chatSearch">
          <i class="fa-regular fa-circle-xmark"></i>
        </span>
      </div>
    </div>

    <!-- Modals -->
    <modal v-if="showTaskSettings" close="true" @close="showTaskSettings = false">
      <TaskSettings :taskData="chat" @close="showTaskSettings = false" />
    </modal>

    <modal close="true" @close="showExportChat = false" v-if="showExportChat">
      <ExportChat :chat="chat" @close="showExportChat = false" />
    </modal>

    <modal close="true" @close="showChatSelector = false" v-if="showChatSelector">
      <ChatSelector />
    </modal>

    <!-- Delete confirmation modal -->
    <modal close="true" @close="showDeleteConfirm = false" v-if="showDeleteConfirm">
      <div class="card bg-base-100 w-96 shadow-xl">
        <div class="card-body">
          <h2 class="card-title text-error flex items-center gap-2">
            <i class="fa-solid fa-exclamation-triangle"></i>
            Delete Chat
          </h2>
          <p class="text-sm">Are you sure you want to delete <strong>{{ chat?.name }}</strong>?</p>
          <p class="text-xs text-base-content/60">This action cannot be undone.</p>
          <div class="card-actions justify-end gap-2 mt-4">
            <button class="btn btn-sm btn-ghost" @click="showDeleteConfirm = false">
              Cancel
            </button>
            <button class="btn btn-sm btn-error" @click="confirmDelete">
              <i class="fa-solid fa-trash"></i> Delete
            </button>
          </div>
        </div>
      </div>
    </modal>
  </div>
</template>

<script>
export default {
  props: {
    chat: { type: Object, default: null },
    showHiddenMessages: { type: Boolean, default: false },
    filter: { type: String, default: '' }
  },
  emits: [
    'reload', 'new-subtask', 'create-subtasks', 'new-tag',
    'update:chat', 'update:search', 'update:showHidden', 'delete-chat'
  ],
  data() {
    return {
      showSearch: false,
      chatSearch: '',
      showTaskSettings: false,
      showExportChat: false,
      showChatSelector: false,
      showDeleteConfirm: false,
      targetProject: null
    }
  },
  computed: {
    visibleCount() {
      return (this.chat?.messages || []).filter(m => !m.hide).length
    },
    hiddenCount() {
      return (this.chat?.messages || []).filter(m => m.hide).length
    },
  },
  watch: {
    chat(newChat, oldChat) {
      if (newChat?.id !== oldChat?.id) {
        this.showSearch = false
        this.chatSearch = ''
        this.showDeleteConfirm = false
        this.setTargetProject()
      }
    },
    filter(val) {
      this.chatSearch = val
    }
  },
  mounted() {
    this.setTargetProject()
  },
  methods: {
    setTargetProject() {
      if (this.chat?.project_id) {
        this.targetProject = this.$storex.projects.allProjectsById[this.chat.project_id] || this.$project
      }
    },

    setChatMode(mode) {
      if (!this.chat) return
      this.$emit('update:chat', { ...this.chat, mode })
    },

    setChatProject(project) {
      if (!this.chat || !project) return
      this.$emit('update:chat', { ...this.chat, project_id: project.project_id })
    },

    toggleHidden() {
      this.$emit('update:showHidden', !this.showHiddenMessages)
    },

    saveChat() {
      if (!this.chat) return
      this.$storex.chats.saveChat(this.chat)
    },

    clearSearch() {
      this.chatSearch = ''
      this.$emit('update:search', '')
    },

    confirmDelete() {
      if (!this.chat) return
      this.showDeleteConfirm = false
      this.$emit('delete-chat', this.chat)
    }
  }
}
</script>