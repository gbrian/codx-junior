<script setup>
import ChatIcon from '@/components/chat/ChatIcon.vue'
</script>

<template>
  <Collapsible
    :defaultOpen="defaultOpen"
    @update:modelValue="$emit('update:open', $event)"
    class="w-full"
  >
    <!-- Icon -->
    <template #icon>
      <i class="fa-solid fa-layer-group text-xs opacity-60"></i>
    </template>

    <!-- Title -->
    <template #title>
      <div class="flex flex-wrap gap-2 text-xs text-base-content/50 mt-0.5">
        <span v-if="showProjectName">
          <i class="fa-solid fa-house text-xs"></i> {{ ownerProject?.title }}
        </span>
        <span>[{{ formattedUpdatedDate }}]</span>
        <span 
          v-if="chat.history?.length"
          class="click text-xs flex items-center gap-1 transition-all"
          :class="showHistory ? 'text-warning' : 'hover:text-warning'"
          @click="$emit('toggle-history')"
          title="Toggle history wall view"
        >
          <i class="fa-solid fa-clock-rotate-left"></i>
          <span>History</span>
        </span>
        <span>Subtasks</span>
        <span class="text-xs font-normal text-base-content/50 ml-1">({{ totalDescendants }})</span>
      </div>
    </template>

    <!-- Actions -->
    <template #actions>
      <button
        class="btn btn-xs btn-ghost text-base-content/50 hover:text-primary"
        @click.stop="$emit('add-subtask')"
      >
        <i class="fa-solid fa-plus text-xs"></i>
      </button>
    </template>

    <!-- Body -->
    <div 
      class="flex gap-2 overflow-x-auto p-2 scrollbar-thin transition-colors"
      @dragover.prevent="onDragOver"
      @drop="onDrop"
      :class="isDraggingOver ? 'bg-primary/5 rounded-lg' : ''"
    >
      <!-- Parent card -->
      <div
        class="flex flex-col gap-1 p-2 rounded-lg border-2 cursor-pointer shrink-0 w-36 transition-all"
        :class="!selectedChatId
          ? 'border-primary bg-primary/10'
          : 'border-base-content/10 bg-base-200 hover:border-base-content/30'"
        @click="selectChat(null)"
        v-if="selectedChatId"
      >
        <div class="flex items-center gap-1">
          <img class="w-4 h-4 rounded-full" :src="projectIcon" />
          <span class="text-xs font-bold truncate flex-1">Parent</span>
          <i class="fa-solid fa-house text-xs text-base-content/30"></i>
        </div>
        <div class="text-xs truncate text-base-content/70 leading-tight">{{ chat.name }}</div>
        <div class="text-xs text-base-content/40">
          {{ (chat.messages || []).length }} msgs
        </div>
      </div>

      <!-- CHANGED: Use tree data from props instead of computing -->
      <ChatTreeNode
        v-for="(childChat, idx) in orderedChildren"
        :key="childChat.id"
        :chat="childChat"
        :index="idx"
        :isSelected="selectedChatId === childChat.id"
        :isDragged="draggedItem?.id === childChat.id"
        :isDragOver="dragOverIndex === idx"
        :depth="0"
        :totalChildren="orderedChildren.length"
        :allChats="allChats"
        :projectIcon="projectIcon"
        @select="selectChat(childChat)"
        @add-subtask="$emit('add-subtask', childChat)"
        @drag-start="onDragStart(childChat, idx, $event)"
        @drag-end="onDragEnd"
        @drag-over="onDragOver"
        @drag-enter="onDragEnter(idx)"
      />

      <!-- Add card -->
      <div
        class="flex flex-col items-center justify-center gap-1 p-2 rounded-lg border-2 border-dashed border-base-content/20 cursor-pointer shrink-0 w-20 hover:border-primary hover:text-primary transition-all text-base-content/40"
        @click="$emit('add-subtask')"
      >
        <i class="fa-solid fa-plus text-lg"></i>
        <span class="text-xs">Add</span>
      </div>
    </div>
  </Collapsible>
</template>

<script>
export default {
  components: { ChatIcon },
  props: {
    chat: {
      type: Object,
      required: true
    },
    allChats: {
      type: Array,
      required: true
    },
    ownerProject: {
      type: Object,
      required: true
    },
    projectIcon: {
      type: String,
      required: true
    },
    defaultOpen: {
      type: Boolean,
      default: false
    },
    showProjectName: {
      type: Boolean,
      default: false
    },
    showHistory: {
      type: Boolean,
      default: false
    },
    formattedUpdatedDate: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      selectedChatId: null,
      draggedItem: null,
      draggedItemIndex: null,
      dragOverIndex: null,
      isDraggingOver: false
    }
  },
  computed: {
    directChildren() {
      return this.allChats
        .filter(c => c.parent_id === this.chat.id)
        .sort((a, b) => a.name > b.name ? 1 : -1)
    },
    orderedChildren() {
      const order = this.chat.meta_data?.childOrder || []
      const ordered = [...this.directChildren].sort((a, b) => {
        const indexA = order.indexOf(a.id)
        const indexB = order.indexOf(b.id)
        if (indexA === -1 && indexB === -1) return 0
        if (indexA === -1) return 1
        if (indexB === -1) return -1
        return indexA - indexB
      })
      return ordered
    },
    totalDescendants() {
      const countDescendants = (parentId) => {
        const direct = this.allChats.filter(c => c.parent_id === parentId)
        return direct.length + direct.reduce((sum, child) => sum + countDescendants(child.id), 0)
      }
      return countDescendants(this.chat.id)
    }
  },
  methods: {
    selectChat(childChat) {
      this.selectedChatId = childChat?.id || null
      this.$emit('select', childChat)
    },
    onDragStart(childChat, index, event) {
      this.draggedItem = childChat
      this.draggedItemIndex = index
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('text/html', event.currentTarget)
    },
    onDragOver(event) {
      event.preventDefault()
      event.dataTransfer.dropEffect = 'move'
      this.isDraggingOver = true
    },
    onDragEnter(index) {
      if (!this.draggedItem || index === this.draggedItemIndex) return
      this.dragOverIndex = index
    },
    async onDrop(event) {
      event.preventDefault()
      this.isDraggingOver = false
      
      if (!this.draggedItem || this.draggedItemIndex === null || this.dragOverIndex === null) {
        this.resetDragState()
        return
      }
      
      if (this.dragOverIndex === this.draggedItemIndex) {
        this.resetDragState()
        return
      }
      
      this.$emit('reorder', { from: this.draggedItemIndex, to: this.dragOverIndex })
      this.resetDragState()
    },
    onDragEnd() {
      this.isDraggingOver = false
      this.resetDragState()
    },
    resetDragState() {
      this.draggedItem = null
      this.draggedItemIndex = null
      this.dragOverIndex = null
    }
  }
}
</script>