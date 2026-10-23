<script setup>
import { WALL_NAV } from './wallKinds'
</script>

<template>
  <!--
    Left rail of the Activity Wall — the navigation surface whenever the wall is
    at least `@xl` wide (see Wall.vue). Below that the bottom bar
    (WallBottomNav.vue) takes over, so exactly one navigation always exists.

    The rail is icon-only until `@5xl`; because of that every entry carries a
    `title` + `aria-label` so Messages / Notifications & co. stay identifiable
    when collapsed.
  -->
  <nav class="flex flex-col gap-1 pt-2" aria-label="Activity navigation">
    <!-- Brand: the codx-junior logo links back home -->
    <button
      class="flex items-center justify-center @5xl:justify-start p-3 rounded-full hover:bg-base-200 transition-colors"
      @click="$emit('action', 'nav', { key: 'home' })"
      title="codx-junior activity home"
      aria-label="codx-junior activity home"
    >
      <img src="/only_icon.png" alt="codx-junior" class="w-7 h-7 rounded-full" />
    </button>

    <button
      v-for="item in nav"
      :key="item.key"
      class="flex items-center gap-3 p-3 rounded-full hover:bg-base-200 transition-colors w-full"
      :class="route === item.key ? 'font-bold bg-base-200' : ''"
      :title="item.label"
      :aria-label="item.label"
      :aria-current="route === item.key ? 'page' : undefined"
      @click="$emit('action', 'nav', item)"
    >
      <i :class="item.icon" class="w-6 text-center"></i>
      <span class="hidden @5xl:inline text-lg">{{ item.label }}</span>
      <span v-if="badgeFor(item.key)" class="badge badge-primary badge-sm ml-auto">{{ badgeFor(item.key) }}</span>
    </button>

    <button
      class="btn btn-primary rounded-full mt-2 w-12 h-12 p-0 @5xl:w-full @5xl:h-auto @5xl:py-3"
      @click="$emit('action', 'compose')"
      title="New post"
      aria-label="New post"
    >
      <i class="fa-solid fa-pen @5xl:mr-2"></i>
      <span class="hidden @5xl:inline">Post</span>
    </button>
  </nav>
</template>

<script>
export default {
  props: {
    route: { type: String, default: 'home' },
    notifications: { type: Number, default: 0 },
    messages: { type: Number, default: 0 }
  },
  emits: ['action'],
  data() {
    return { nav: WALL_NAV }
  },
  methods: {
    badgeFor(key) {
      if (key === 'notifications') return this.notifications
      if (key === 'messages') return this.messages
      return 0
    }
  }
}
</script>