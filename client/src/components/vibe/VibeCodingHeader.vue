<script setup>
import ProjectDetailt from '@/components/ProjectDetailt.vue'
import UserSelector from '@/components/chat/UserSelector.vue'
import Markdown from '@/components/Markdown.vue'
import ChatIcon from '@/components/chat/ChatIcon.vue'
import ChatProjectIcon from '@/components/ChatProjectIcon.vue'
</script>

<template>
  <div class="flex flex-col shrink-0 bg-base-200 border-b border-base-content/10">

    <!-- ── ROW 1: Main toolbar ──────────────────────────────────────────── -->
    <div class="flex items-center gap-1 px-2 py-1 min-h-0">

      <!-- Navigation breadcrumb -->
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

      <!-- Reload -->
      <button class="btn btn-xs btn-ghost shrink-0" @click="$emit('reload')" title="Reload">
        <i class="fa-solid fa-rotate-right text-xs"></i>
      </button>
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

    <!-- ── ROW 3: Tags (conditional) ────────────────────────────────────── -->
    <div class="flex gap-1 flex-wrap px-2 pb-1" v-if="chat?.tags?.length">
      <div
        class="badge badge-xs badge-outline text-xs"
        v-for="tag in chat.tags"
        :key="tag"
      >#{{ tag }}</div>
    </div>

    <!-- ── ROW 4: Description (conditional) ─────────────────────────────── -->
    <div class="px-2 pb-1 text-xs" v-if="showDescription && chat?.description">
      <Markdown class="prose-xs" :text="chat.description" />
    </div>

    <!-- ── ROW 5: Subtasks strip (conditional) ──────────────────────────── -->
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
          class="btn btn-xs shrink-0 truncate max-w-60"
          :class="activeChildChat?.id === child.id ? 'btn-warning' : 'btn-ghost opacity-60 hover:opacity-100'"
          @click="$emit('select-child-chat', child)"
          :title="child.name"
        >
          <span class="text-xs font-mono opacity-50">{{ idx + 1 }}</span>
          <div class="flex items-center">
            <ChatProjectIcon class="-mt-1 -mr-3" 
              :chat="child" 
              :width="4"
              :icon-only="true"  
            />
          </div>
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
  </div>
</template>

<script>
import moment from 'moment'

export default {
  props: {
    chat: { type: Object, default: null },
    projectName: { type: String, default: '' },
    showChat: { type: Boolean, default: true },
    showChanges: { type: Boolean, default: false },
    showPreview: { type: Boolean, default: true },
    activeChildChat: { type: Object, default: null }
  },
  emits: [
    'toggle-view', 'reload',
    'update:chat',
    'navigate-to-board', 'navigate-to-parent',
    'new-subtask',
    'select-child-chat', 'set-project', 'add-profile', 'toggle-kanban'
  ],
  data() {
    return {
      editName: false,
      localChatName: '',
      showDescription: false,
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
    }
  },
  methods: {
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
    }
  }
}
</script>