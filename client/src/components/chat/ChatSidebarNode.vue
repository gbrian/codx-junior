<script setup>
import ChatIcon from './ChatIcon.vue'
import ProjectIcon from '../ProjectIcon.vue'
</script>

<template>
  <div class="group/node w-full" :class="isCompact ? 'relative' : ''">
    <!-- Chat Node Card -->
    <div
      class="p-3 rounded-lg border-2 cursor-pointer transition-all"
      :class="[
        selectedChatId === chat.id
          ? 'border-warning bg-warning/10'
          : 'border-base-content/10 bg-base-100 hover:bg-base-200',
        isCompact ? 'flex justify-center' : ''
      ]"
      @click="selectChat"
    >
      <!-- Compact Mode: Icon Only -->
      <template v-if="isCompact">
        <div class="flex flex-col items-center gap-1">
          <ProjectIcon 
            :icon-only="true"
            :width="3"
            :project="$chats.getChatProject({ owner_project_id: chat.project_id || chat.owner_project_id })" />
          <div v-if="isUpdating" class="shrink-0">
            <span class="loading loading-bars loading-xs shrink-0 text-info"></span>
          </div>
          <ChatIcon v-else :mode="chat.mode" class="text-xs shrink-0" />
        </div>
      </template>

      <!-- Expanded Mode: Full Content -->
      <template v-else>
        <div class="flex items-center gap-2 w-full">
          <!-- Expand/Collapse Button -->
          <button
            v-if="hasChildren"
            class="btn btn-xs btn-ghost p-0 w-5 h-5 shrink-0"
            @click.stop="isExpanded = !isExpanded"
            :title="isExpanded ? 'Collapse' : 'Expand'"
          >
            <i :class="[
              'fa-solid text-xs',
              isExpanded ? 'fa-chevron-down' : 'fa-chevron-right'
            ]"></i>
          </button>
          <div v-else class="w-5 shrink-0"></div>

          <!-- Icon + Content -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <!-- Loading indicator or Chat Icon -->
              <ProjectIcon 
                :icon-only="true"
                :width="3"
                :project="$chats.getChatProject({ owner_project_id: chat.project_id || chat.owner_project_id })" />
              <div v-if="isUpdating" class="shrink-0">
                <span class="loading loading-bars loading-xs shrink-0 text-info"></span>
              </div>
              <ChatIcon v-else :mode="chat.mode" class="text-xs shrink-0" />
              <span class="font-bold text-sm truncate">{{ chat.name }}</span>
              <span class="text-xs text-base-content/40 shrink-0 tabular-nums">
                {{ chat.messages?.length || 0 }}
              </span>
            </div>
            <div v-if="chat.description" class="text-xs text-base-content/60 line-clamp-1 mt-0.5">
              {{ chat.description }}
            </div>
          </div>

          <!-- Action Buttons (visible on hover) -->
          <div class="flex items-center gap-1 shrink-0">
            <!-- Plus: Create subtask -->
            <button
              class="btn btn-xs btn-ghost p-0 w-5 h-5"
              title="Create subtask"
              @click.stop="$emit('add-subtask', chat)"
            >
              <i class="fa-solid fa-plus text-xs"></i>
            </button>
            <!-- Trash: Delete subtask -->
            <button
              class="btn btn-xs btn-ghost p-0 w-5 h-5 text-error hover:bg-error/10"
              title="Delete subtask"
              @click.stop="$emit('delete-chat', chat)"
            >
              <i class="fa-solid fa-trash text-xs"></i>
            </button>
          </div>
        </div>
      </template>
    </div>

    <!-- Floating Popup (Compact Mode Only) -->
    <div 
      v-if="isCompact && isHoveringCompact"
      class="fixed left-20 top-0 z-50 bg-base-100 border-2 border-base-content/10 rounded-lg shadow-lg p-3 w-56 max-h-96 overflow-y-auto"
      :style="floatingStyle"
      @mouseenter="hoverTimeout = null"
      @mouseleave="startHoverTimeout"
    >
      <div class="space-y-3">
        <!-- Header with Icons -->
        <div class="flex items-center gap-2">
          <!-- Expand/Collapse Button -->
          <button
            v-if="hasChildren"
            class="btn btn-xs btn-ghost p-0 w-5 h-5 shrink-0"
            @click.stop="isExpanded = !isExpanded"
            :title="isExpanded ? 'Collapse' : 'Expand'"
          >
            <i :class="[
              'fa-solid text-xs',
              isExpanded ? 'fa-chevron-down' : 'fa-chevron-right'
            ]"></i>
          </button>
          <div v-else class="w-5 shrink-0"></div>

          <ProjectIcon 
            :icon-only="true"
            :width="3"
            :project="$chats.getChatProject({ owner_project_id: chat.project_id || chat.owner_project_id })" />
          <ChatIcon :mode="chat.mode" class="text-xs shrink-0" />
        </div>

        <!-- Title and Description -->
        <div class="min-w-0">
          <div class="font-bold text-sm truncate">{{ chat.name }}</div>
          <div v-if="chat.description" class="text-xs text-base-content/60 line-clamp-2 mt-1">
            {{ chat.description }}
          </div>
          <div class="text-xs text-base-content/40 mt-1">
            {{ chat.messages?.length || 0 }} messages
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex gap-2 pt-2 border-t border-base-200">
          <button
            class="btn btn-xs btn-ghost flex-1 justify-center gap-1"
            title="Create subtask"
            @click.stop="$emit('add-subtask', chat)"
          >
            <i class="fa-solid fa-plus text-xs"></i>
            <span class="text-xs">Add</span>
          </button>
          <button
            class="btn btn-xs btn-ghost flex-1 justify-center gap-1 text-error hover:bg-error/10"
            title="Delete subtask"
            @click.stop="$emit('delete-chat', chat)"
          >
            <i class="fa-solid fa-trash text-xs"></i>
            <span class="text-xs">Delete</span>
          </button>
        </div>

        <!-- Children in Floating View -->
        <div v-if="isExpanded && hasChildren" class="mt-3 pt-3 border-t border-base-200 space-y-2">
          <ChatSidebarNode
            v-for="child in children"
            :key="child.id"
            :chat="child"
            :allChats="allChats"
            :selectedChatId="selectedChatId"
            :isCompact="false"
            @select="$emit('select', $event)"
            @add-subtask="$emit('add-subtask', $event)"
            @delete-chat="$emit('delete-chat', $event)"
          />
        </div>
      </div>
    </div>

    <!-- Children (Nested) - Expanded Mode Only -->
    <div v-if="!isCompact && isExpanded && hasChildren" class="ml-4 mt-2 space-y-2">
      <ChatSidebarNode
        v-for="child in children"
        :key="child.id"
        :chat="child"
        :allChats="allChats"
        :selectedChatId="selectedChatId"
        :isCompact="isCompact"
        @select="$emit('select', $event)"
        @add-subtask="$emit('add-subtask', $event)"
        @delete-chat="$emit('delete-chat', $event)"
      />
    </div>
  </div>
</template>

<script>
export default {
  props: {
    chat: { type: Object, required: true },
    allChats: { type: Array, default: () => [] },
    selectedChatId: { type: String, default: null },
    isCompact: { type: Boolean, default: false }
  },
  emits: ['select', 'add-subtask', 'delete-chat'],
  data() {
    return {
      isExpanded: true,
      isHoveringCompact: false,
      hoverTimeout: null,
      floatingTop: 0
    }
  },
  computed: {
    children() {
      return this.allChats.filter(c => c.parent_id === this.chat.id)
    },
    hasChildren() {
      return this.children.length > 0
    },
    isUpdating() {
      return this.$storex.chats.isChatUpdating(this.chat.id)
    },
    floatingStyle() {
      return {
        top: `${this.floatingTop}px`
      }
    }
  },
  methods: {
    selectChat() {
      this.$emit('select', this.chat)
    },
    handleMouseEnter(event) {
      if (!this.isCompact) return
      this.hoverTimeout = null
      const rect = event.currentTarget.getBoundingClientRect()
      this.floatingTop = Math.max(0, rect.top)
      this.isHoveringCompact = true
    },
    handleMouseLeave() {
      this.startHoverTimeout()
    },
    startHoverTimeout() {
      this.hoverTimeout = setTimeout(() => {
        this.isHoveringCompact = false
      }, 200)
    }
  },
  mounted() {
    if (this.isCompact) {
      this.$el.addEventListener('mouseenter', this.handleMouseEnter)
      this.$el.addEventListener('mouseleave', this.handleMouseLeave)
    }
  },
  beforeUnmount() {
    if (this.hoverTimeout) {
      clearTimeout(this.hoverTimeout)
    }
    if (this.isCompact) {
      this.$el.removeEventListener('mouseenter', this.handleMouseEnter)
      this.$el.removeEventListener('mouseleave', this.handleMouseLeave)
    }
  }
}
</script>