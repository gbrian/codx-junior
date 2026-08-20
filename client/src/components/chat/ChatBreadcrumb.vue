<script setup>
</script>

<template>
  <div class="flex items-center gap-1 min-w-0 flex-wrap text-sm">
    <!-- Root chat -->
    <span
      class="hover:underline cursor-pointer font-bold text-primary truncate min-w-0"
      :title="rootChat.name"
      @click="selectChat(rootChat)"
    >
      {{ rootChat.name }}
    </span>

    <!-- Ancestor path -->
    <template v-for="(ancestor, index) in breadcrumbPath" :key="ancestor.id">
      <span class="text-base-content/40 shrink-0">/</span>
      <span
        class="hover:underline cursor-pointer font-bold text-secondary truncate min-w-0"
        :class="index === breadcrumbPath.length - 1 ? 'text-warning' : ''"
        :title="ancestor.name"
        @click="selectChat(ancestor)"
      >
        {{ ancestor.name }}
      </span>
    </template>
  </div>
</template>

<script>
export default {
  props: {
    rootChat: {
      type: Object,
      required: true
    },
    selectedChat: {
      type: Object,
      default: null
    },
    allChats: {
      type: Array,
      required: true
    }
  },
  computed: {
    breadcrumbPath() {
      if (!this.selectedChat || this.selectedChat.id === this.rootChat.id) {
        return []
      }

      const path = []
      let current = this.selectedChat

      while (current && current.parent_id && current.parent_id !== this.rootChat.id) {
        const parent = this.allChats.find(c => c.id === current.parent_id)
        if (!parent) break
        path.unshift(parent)
        current = parent
      }

      return path
    }
  },
  methods: {
    selectChat(chat) {
      this.$emit('select', chat)
    }
  }
}
</script>