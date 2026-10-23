<script setup>
import WallPostCard from './WallPostCard.vue'
</script>

<template>
  <div>
    <!-- Loading -->
    <div v-if="status === 'loading'" class="p-4 flex flex-col gap-4">
      <div v-for="n in 5" :key="n" class="flex gap-3 animate-pulse">
        <div class="w-10 h-10 rounded-full bg-base-content/10"></div>
        <div class="flex-1 flex flex-col gap-2 py-1">
          <div class="h-3 w-40 bg-base-content/10 rounded"></div>
          <div class="h-3 w-full bg-base-content/10 rounded"></div>
          <div class="h-3 w-2/3 bg-base-content/10 rounded"></div>
        </div>
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="status === 'error'" class="p-8 text-center">
      <i class="fa-solid fa-triangle-exclamation text-3xl text-error"></i>
      <h3 class="font-bold mt-2">Something went wrong</h3>
      <p class="text-sm text-base-content/50">The activity feed could not be loaded.</p>
      <button class="btn btn-primary btn-sm mt-3" @click="$emit('retry')">Retry</button>
    </div>

    <!-- Empty -->
    <div v-else-if="!posts.length" class="p-10 text-center">
      <i class="fa-solid fa-inbox text-3xl text-base-content/40"></i>
      <h3 class="font-bold mt-2">Nothing here yet</h3>
      <p class="text-sm text-base-content/50 max-w-xs mx-auto">
        When your team chats, moves tasks or opens a meet, it shows up here.
      </p>
      <button class="btn btn-ghost btn-sm mt-3" @click="$emit('action', 'nav', { key: 'home' })">Back home</button>
    </div>

    <!-- Feed -->
    <template v-else>
      <WallPostCard
        v-for="post in posts"
        :key="post.id"
        :post="post"
        :author="authorOf(post)"
        :viewer="viewerOf(post)"
        @action="onAction"
      />
    </template>
  </div>
</template>

<script>
export default {
  props: {
    posts: { type: Array, default: () => [] },
    status: { type: String, default: 'ready' },
    accounts: { type: Object, default: () => ({}) },
    viewers: { type: Object, default: () => ({}) }
  },
  emits: ['action', 'retry'],
  methods: {
    // Resolve the author as robustly as possible: by exact id, lowercase id,
    // handle/name match, then finally the bot account. This guarantees a post
    // authored by a username still shows the right avatar instead of "AI".
    authorOf(post) {
      const accounts = this.accounts || {}
      const id = post?.authorId
      return accounts[id]
        || accounts[String(id || '').toLowerCase?.()]
        || Object.values(accounts).find(a => a.handle === id || a.name === id)
        || accounts['codx-junior']
        || {}
    },
    viewerOf(post) {
      return this.viewers[post.id] || {}
    },
    onAction(type, post) {
      this.$emit('action', type, post)
    }
  }
}
</script>
