<script setup>
import ChatIcon from '@/components/chat/ChatIcon.vue'
import ProjectDetailt from '@/components/ProjectDetailt.vue'
import UserSelector from '@/components/chat/UserSelector.vue'
import ExportChat from '@/components/chat/ExportChat.vue'
import TaskSettings from '@/components/kanban/TaskSettings.vue'
import ChatSelector from '@/components/chat/ChatSelector.vue'
import Markdown from '@/components/Markdown.vue'
</script>

<template>
  <div class="flex flex-col shrink-0 bg-base-200 border-b border-base-content/10">

    <!-- ── ROW 1: Main toolbar ──────────────────────────────────────────── -->
    <div class="flex items-center gap-1 px-2 py-1 min-h-0">

      <!-- Branch / navigation breadcrumb -->
      <div class="flex items-center gap-1 text-xs shrink-0">
        <span
          class="hover:underline cursor-pointer font-bold text-primary truncate max-w-[100px]"
          :title="kanbanTitle"
          @click="$emit('navigate-to-board')"
        >
          <i class="fa-brands fa-trello"></i>
          {{ kanbanTitle }}
        </span>
        <template v-if="parentChat">
          <span class="text-base-content/30">/</span>
          <span
            class="hover:underline cursor-pointer text-secondary truncate max-w-[80px]"
            :title="parentChat.name"
            @click="$emit('navigate-to-parent', parentChat)"
          >{{ parentChat.name }}</span>
        </template>
      </div>

      <!-- Git: current branch -->
      <div class="flex items-center gap-1 shrink-0 ml-1">
        <i class="fa-solid fa-code-branch text-xs text-warning"></i>
        <select
          class="select select-xs select-ghost max-w-[110px] font-mono text-xs"
          :value="currentBranch"
          @change="onCurrentBranchChange($event.target.value)"
        >
          <option v-for="b in availableBranches" :key="b" :value="b">{{ b }}</option>
        </select>
        <span class="text-base-content/30 text-xs">vs</span>
        <select
          class="select select-xs select-ghost max-w-[110px] font-mono text-xs"
          :value="compareBranch"
          @change="onCompareBranchChange($event.target.value)"
        >
          <option value="local">local</option>
          <option v-for="b in availableBranches" :key="b" :value="b">{{ b }}</option>
        </select>
        <button class="btn btn-xs btn-ghost text-xs" @click="$emit('create-branch')" title="New branch">
          <i class="fa-solid fa-plus text-xs"></i>
        </button>
      </div>

      <div class="grow"></div>

      <!-- View toggles -->
      <div class="flex items-center gap-0.5 shrink-0">
        <button
          class="btn btn-xs"
          :class="showChat ? 'btn-primary' : 'btn-ghost opacity-50'"
          @click="$emit('toggle-view', 'chat')"
          title="Chat"
        ><i class="fa-solid fa-comments text-xs"></i></button>
        <button
          class="btn btn-xs"
          :class="showChanges ? 'btn-warning' : 'btn-ghost opacity-50'"
          @click="$emit('toggle-view', 'changes')"
          title="Changes"
        ><i class="fa-solid fa-code-compare text-xs"></i></button>
        <button
          class="btn btn-xs"
          :class="showPreview ? 'btn-success' : 'btn-ghost opacity-50'"
          @click="$emit('toggle-view', 'preview')"
          title="Preview"
        ><i class="fa-solid fa-display text-xs"></i></button>
      </div>

      <!-- Search toggle -->
      <button
        class="btn btn-xs btn-ghost shrink-0"
        :class="showSearch ? 'text-primary' : ''"
        @click="showSearch = !showSearch"
        title="Search messages"
      ><i class="fa-solid fa-magnifying-glass text-xs"></i></button>

      <!-- Message count / hidden toggle -->
      <button
        v-if="chat"
        class="btn btn-xs btn-ghost shrink-0 tooltip"
        :class="showHidden ? 'text-warning' : ''"
        :data-tip="`${visibleCount} msgs${hiddenCount ? ` / ${hiddenCount} hidden` : ''}`"
        @click="toggleHidden"
      >
        <i class="fa-regular fa-message text-xs"></i>
        <span class="text-xs ml-0.5">{{ visibleCount }}</span>
        <span v-if="hiddenCount" class="text-xs opacity-60">
          <i class="fa-regular fa-eye-slash"></i>{{ hiddenCount }}
        </span>
      </button>

      <!-- Chat mode selector -->
      <div class="dropdown dropdown-end shrink-0" v-if="chat">
        <div tabindex="0" role="button" class="btn btn-xs btn-ghost">
          <ChatIcon :mode="chat.mode" />
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

      <!-- Reload -->
      <button class="btn btn-xs btn-ghost shrink-0" @click="$emit('reload')" title="Reload">
        <i class="fa-solid fa-rotate-right text-xs"></i>
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
        </ul>
      </div>
    </div>

    <!-- ── ROW 2: Chat identity (name, project, pin, description) ───────── -->
    <div class="flex items-center gap-1 px-2 pb-1 min-w-0" v-if="chat">

      <!-- Project selector + user selector -->
      <ProjectDetailt
        v-model="targetProject"
        :iconify="true"
        :options="{ showFolders: false, showIcon: true, showSelector: true }"
        @select="$emit('set-project', $event)"
      />
      <UserSelector class="dropdown-bottom" :allUsers="true" @user-changed="$emit('add-profile', $event)" />

      <!-- Pin -->
      <span class="click cursor-pointer shrink-0" @click="togglePin" :title="chat.pinned ? 'Unpin' : 'Pin'">
        <i class="text-warning fa-solid fa-bookmark text-xs" v-if="chat.pinned"></i>
        <i class="fa-regular fa-bookmark text-xs opacity-40" v-else></i>
      </span>

      <!-- Editable name -->
      <div class="flex-1 min-w-0">
        <input
          v-if="editName"
          type="text"
          class="input input-xs input-bordered w-full"
          v-model="localChatName"
          @keydown.enter.stop="saveName"
          @keydown.esc="editName = false"
        />
        <span
          v-else
          class="font-bold text-sm truncate block cursor-pointer"
          :title="chat.name"
          @dblclick="startEditName"
        >{{ chat.name || 'Vibe session' }}</span>
      </div>

      <!-- Description toggle -->
      <span
        v-if="chat.description"
        class="cursor-pointer text-xs shrink-0"
        :class="showDescription ? 'text-error/70' : 'text-info'"
        @click="showDescription = !showDescription"
        title="Toggle description"
      >
        <i class="fa-solid fa-circle-info"></i>
      </span>

      <!-- Date -->
      <span class="text-xs text-base-content/30 shrink-0">{{ formattedDate }}</span>
    </div>

    <!-- ── ROW 3: Search bar (conditional) ──────────────────────────────── -->
    <div class="flex items-center gap-1 px-2 pb-1" v-if="showSearch">
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

    <!-- ── ROW 4: Tags (conditional) ────────────────────────────────────── -->
    <div class="flex gap-1 flex-wrap px-2 pb-1" v-if="chat?.tags?.length">
      <div
        class="badge badge-xs badge-outline text-xs"
        v-for="tag in chat.tags"
        :key="tag"
      >#{{ tag }}</div>
    </div>

    <!-- ── ROW 5: Description (conditional) ─────────────────────────────── -->
    <div class="px-2 pb-1 text-xs" v-if="showDescription && chat?.description">
      <Markdown class="prose-xs" :text="chat.description" />
    </div>

    <!-- ── ROW 6: Subtasks strip (conditional) ──────────────────────────── -->
    <div
      v-if="childrenChats.length"
      class="flex items-center gap-1 px-2 pb-1 border-t border-base-content/10 pt-1"
    >
      <i class="fa-solid fa-layer-group text-xs opacity-40 shrink-0"></i>
      <span class="text-xs text-base-content/40 shrink-0">Subtasks</span>
      <div class="flex gap-1 overflow-x-auto flex-1 scrollbar-none">
        <!-- Parent card pill -->
        <button
          v-if="activeChildChat"
          class="btn btn-xs btn-ghost gap-1 shrink-0"
          @click="$emit('select-child-chat', null)"
          title="Back to parent"
        >
          <i class="fa-solid fa-house text-xs"></i>
          <span class="text-xs truncate max-w-[60px]">Parent</span>
        </button>

        <!-- Subtask pills -->
        <button
          v-for="(child, idx) in childrenChats"
          :key="child.id"
          class="btn btn-xs shrink-0 gap-1 truncate max-w-[100px]"
          :class="activeChildChat?.id === child.id ? 'btn-warning' : 'btn-ghost opacity-60 hover:opacity-100'"
          @click="$emit('select-child-chat', child)"
          :title="child.name"
        >
          <span class="text-xs font-mono opacity-50">{{ idx + 1 }}</span>
          <ChatIcon :mode="child.mode" class="text-xs" />
          <span class="text-xs truncate">{{ child.name }}</span>
          <span
            class="badge badge-xs ml-0.5"
            :class="child.column === 'Done' ? 'badge-success' : child.column === 'In Progress' ? 'badge-warning' : 'badge-ghost'"
          >{{ (child.column || '?').slice(0, 3) }}</span>
        </button>
      </div>

      <!-- Add subtask -->
      <button
        class="btn btn-xs btn-ghost shrink-0 opacity-40 hover:opacity-100"
        @click="$emit('new-subtask')"
        title="Add subtask"
      ><i class="fa-solid fa-plus text-xs"></i></button>
    </div>

    <!-- ── MODALS ────────────────────────────────────────────────────────── -->
    <modal v-if="showTaskSettings" close="true" @close="showTaskSettings = false">
      <TaskSettings :taskData="chat" @close="showTaskSettings = false" />
    </modal>

    <modal close="true" @close="showExportChat = false" v-if="showExportChat">
      <ExportChat :chat="chat" @close="showExportChat = false" />
    </modal>

    <modal close="true" @close="showChatSelector = false" v-if="showChatSelector">
      <ChatSelector />
    </modal>
  </div>
</template>

<script>
import moment from 'moment'

export default {
  props: {
    chat: { type: Object, default: null },
    projectName: { type: String, default: '' },
    availableBranches: { type: Array, default: () => [] },
    showChat: { type: Boolean, default: true },
    showChanges: { type: Boolean, default: false },
    showPreview: { type: Boolean, default: true },
    activeChildChat: { type: Object, default: null },
    showHiddenMessages: { type: Boolean, default: false }
  },
  emits: [
    'toggle-view', 'reload', 'create-branch',
    'branch-changed', 'compare-branch-changed',
    'update:chat', 'update:search', 'update:showHidden',
    'navigate-to-board', 'navigate-to-parent',
    'new-subtask', 'create-subtasks', 'new-tag',
    'select-child-chat', 'set-project', 'add-profile'
  ],
  data() {
    return {
      showSearch: false,
      chatSearch: '',
      editName: false,
      localChatName: '',
      showDescription: false,
      showTaskSettings: false,
      showExportChat: false,
      showChatSelector: false,
      showHidden: false,
      targetProject: null
    }
  },
  computed: {
    kanbanTitle() {
      return this.chat?.board || this.$project?.project_name || 'Board'
    },
    parentChat() {
      if (!this.chat?.parent_id) return null
      return this.$storex.chats.chats[this.chat.parent_id] || null
    },
    childrenChats() {
      if (!this.chat?.id) return []
      return this.$storex.chats.allChats
        .filter(c => c.parent_id === this.chat.id)
        .sort((a, b) => a.name > b.name ? 1 : -1)
    },
    currentBranch() {
      return this.chat?.meta_data?.current_branch || (this.availableBranches[0] || 'main')
    },
    compareBranch() {
      return this.chat?.meta_data?.compare_branch || 'local'
    },
    visibleCount() {
      return (this.chat?.messages || []).filter(m => !m.hide).length
    },
    hiddenCount() {
      return (this.chat?.messages || []).filter(m => m.hide).length
    },
    formattedDate() {
      if (!this.chat?.updated_at) return ''
      const d = moment(this.chat.updated_at)
      return d.isAfter(moment().subtract(7, 'days')) ? d.fromNow() : d.format('MM-DD')
    }
  },
  watch: {
    chat(newVal) {
      if (newVal) {
        this.localChatName = newVal.name || ''
        this.targetProject = this.$storex.projects.allProjectsById[newVal.project_id] || this.$project
      }
    },
    showHidden(val) {
      this.$emit('update:showHidden', val)
    }
  },
  methods: {
    onCurrentBranchChange(branch) {
      this.updateChatMeta({ current_branch: branch })
      this.$emit('branch-changed', branch)
    },

    onCompareBranchChange(branch) {
      this.updateChatMeta({ compare_branch: branch })
      this.$emit('compare-branch-changed', branch)
    },

    /** Merge meta_data patch and emit update:chat */
    updateChatMeta(patch) {
      if (!this.chat) return
      const updated = {
        ...this.chat,
        meta_data: { ...(this.chat.meta_data || {}), ...patch }
      }
      this.$emit('update:chat', updated)
    },

    toggleHidden() {
      this.showHidden = !this.showHidden
    },

    setChatMode(mode) {
      if (!this.chat) return
      this.$emit('update:chat', { ...this.chat, mode })
    },

    startEditName() {
      this.localChatName = this.chat?.name || ''
      this.editName = true
    },

    saveName() {
      this.editName = false
      if (!this.chat || !this.localChatName.trim()) return
      this.$emit('update:chat', { ...this.chat, name: this.localChatName.trim() })
    },

    togglePin() {
      if (!this.chat) return
      this.$emit('update:chat', { ...this.chat, pinned: !this.chat.pinned })
    },

    saveChat() {
      if (!this.chat) return
      this.$storex.chats.saveChat(this.chat)
    },

    clearSearch() {
      this.chatSearch = ''
      this.$emit('update:search', '')
    },

    /** Called by parent after branch creation */
    onBranchCreated(branch) {
      this.onCurrentBranchChange(branch)
    }
  }
}
</script>