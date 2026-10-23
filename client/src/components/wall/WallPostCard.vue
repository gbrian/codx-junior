<script setup>
import WallAvatar from './WallAvatar.vue'
import WallAttachment from './WallAttachment.vue'
import { avatarClass, formatCount, formatRelative, initials } from './wallEvents'
import { kindConfig } from './wallKinds'
</script>

<template>
  <article
    class="border-b border-base-content/10 px-4 py-3 transition-colors cursor-pointer"
    :class="hasUnread ? 'bg-error/[0.03] hover:bg-error/[0.06]' : 'hover:bg-base-content/[0.02]'"
    @click="$emit('action', 'open', post)"
  >
    <div class="flex gap-3">
      <WallAvatar :account="author" :size="10" />

      <div class="flex-1 min-w-0">
        <!-- Author line + unread badge + kind badge -->
        <div class="flex items-start gap-2">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-1 text-[15px] leading-5 flex-wrap">
              <span class="font-bold hover:underline truncate max-w-[160px]">{{ author.name }}</span>
              <i v-if="author.verified" class="fa-solid fa-circle-check text-info text-sm shrink-0" title="Verified"></i>
              <span class="text-base-content/50 truncate max-w-[140px]">@{{ author.handle }}</span>
              <span class="text-base-content/40">·</span>
              <span class="text-base-content/50 shrink-0">{{ relative }}</span>
            </div>

            <div v-if="post.context" class="flex items-center gap-1.5 mt-0.5 text-[13px] text-base-content/50">
              <i :class="post.context.icon" class="text-xs"></i>
              <span class="truncate">{{ post.context.label }}</span>
            </div>
          </div>

          <!-- Unread messages — only for chat / task events (see utils/chatUnread) -->
          <span
            v-if="hasUnread"
            class="badge badge-sm badge-error badge-outline gap-1 shrink-0 font-bold"
            :title="unreadTitle"
            :aria-label="unreadTitle"
          >
            <i class="fa-solid fa-check-double text-[9px]" aria-hidden="true"></i>
            {{ unreadLabel }}
          </span>

          <span
            class="inline-flex items-center gap-1 text-xs font-semibold shrink-0"
            :class="kind.color"
            :title="kind.label"
          >
            <i :class="kind.icon"></i>
            <span class="hidden sm:inline">{{ kind.label }}</span>
          </span>
        </div>

        <!-- Profiles selected for this event, as an avatar group led by the
             project (or author) icon. -->
        <div v-if="profiles.length" class="flex items-center gap-2 mt-1.5 min-w-0">
          <div class="avatar-group -space-x-2 rtl:space-x-reverse shrink-0">
            <!-- Project / user icon on the left -->
            <div class="avatar" :title="post.context?.label || author.name">
              <div class="w-6 h-6 rounded-full ring-2 ring-base-300 bg-base-200 grid place-items-center overflow-hidden">
                <img v-if="leadIcon" :src="leadIcon" alt="" class="w-full h-full object-cover" />
                <i v-else :class="leadFallbackIcon" class="text-[9px] text-base-content/60"></i>
              </div>
            </div>

            <!-- Profile avatars -->
            <div v-for="profile in visibleProfiles" :key="profile.id" class="avatar" :title="profile.name">
              <div
                class="w-6 h-6 rounded-full ring-2 ring-base-300 grid place-items-center overflow-hidden"
                :class="avatarClass(profile.id)"
              >
                <img v-if="profile.avatar" :src="profile.avatar" alt="" class="w-full h-full object-cover" />
                <span v-else class="text-[9px] font-bold text-white">{{ initials(profile.name) }}</span>
              </div>
            </div>

            <!-- Overflow -->
            <div v-if="extraProfiles" class="avatar avatar-placeholder">
              <div class="w-6 h-6 rounded-full ring-2 ring-base-300 bg-base-300 text-base-content/70">
                <span class="text-[9px] font-bold">+{{ extraProfiles }}</span>
              </div>
            </div>
          </div>

          <span class="text-[13px] text-base-content/50 truncate">{{ profilesLabel }}</span>
        </div>

        <!-- Body -->
        <p v-if="post.text" class="text-[15px] leading-relaxed mt-1 break-words whitespace-pre-line">{{ post.text }}</p>

        <WallAttachment v-if="post.attachment" :attachment="post.attachment" @action="$emit('action', $event, post)" />

        <!-- Action bar (reply / repost / like / views / bookmark / share) -->
        <div class="flex items-center justify-between max-w-[425px] mt-2 -ml-2 text-base-content/50 text-[13px]">
          <button
            class="group flex items-center gap-1 p-2 rounded-full transition-colors"
            :class="hasUnread ? 'text-error' : 'hover:bg-info/10 hover:text-info'"
            @click.stop="$emit('action', 'reply', post)"
            aria-label="Reply"
          >
            <i class="fa-regular fa-comment"></i>
            <span>{{ replies }}</span>
          </button>

          <button
            class="group flex items-center gap-1 p-2 rounded-full transition-colors"
            :class="viewer.reposted ? 'text-success' : 'hover:bg-success/10 hover:text-success'"
            @click.stop="$emit('action', 'repost', post)"
            aria-label="Repost"
          >
            <i class="fa-solid fa-retweet"></i>
            <span>{{ reposts }}</span>
          </button>

          <button
            class="group flex items-center gap-1 p-2 rounded-full transition-colors"
            :class="viewer.liked ? 'text-error' : 'hover:bg-error/10 hover:text-error'"
            @click.stop="$emit('action', 'like', post)"
            aria-label="Like"
          >
            <i :class="viewer.liked ? 'fa-solid fa-heart' : 'fa-regular fa-heart'"></i>
            <span>{{ likes }}</span>
          </button>

          <button
            class="group flex items-center gap-1 p-2 rounded-full hover:bg-info/10 hover:text-info transition-colors"
            @click.stop="$emit('action', 'open', post)"
            aria-label="Views"
          >
            <i class="fa-solid fa-chart-simple"></i>
            <span>{{ views }}</span>
          </button>

          <div class="flex items-center">
            <button
              class="group p-2 rounded-full transition-colors"
              :class="viewer.bookmarked ? 'text-info' : 'hover:bg-info/10 hover:text-info'"
              @click.stop="$emit('action', 'bookmark', post)"
              aria-label="Bookmark"
            >
              <i :class="viewer.bookmarked ? 'fa-solid fa-bookmark' : 'fa-regular fa-bookmark'"></i>
            </button>
            <button
              class="group p-2 rounded-full hover:bg-info/10 hover:text-info transition-colors"
              @click.stop="$emit('action', 'share', post)"
              aria-label="Share"
            >
              <i class="fa-solid fa-share-nodes"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
  </article>
</template>

<script>
export default {
  props: {
    post: { type: Object, required: true },
    author: { type: Object, required: true },
    viewer: { type: Object, default: () => ({}) }
  },
  emits: ['action'],
  computed: {
    kind() {
      return kindConfig(this.post.kind)
    },
    relative() {
      return formatRelative(this.post.createdAt)
    },
    replies() {
      return formatCount(this.post.counts?.replies || 0)
    },
    reposts() {
      return formatCount((this.post.counts?.reposts || 0) + (this.viewer.reposted ? 1 : 0))
    },
    likes() {
      // Chat-backed posts already include the viewer's like in `counts.likes`
      // (synced from the chat metadata); local-only posts add it optimistically.
      const extra = this.post.chatId ? 0 : (this.viewer.liked ? 1 : 0)
      return formatCount((this.post.counts?.likes || 0) + extra)
    },
    views() {
      return formatCount(this.post.counts?.views || 0)
    },

    // ── Unread messages (chat / task events only) ────────────────────────────
    // Only chat and task events surface the unread badge. The count is computed
    // for the current user in `wallEvents.chatToPost` (see utils/chatUnread) and
    // reaches the card as `post.unreadCount`.
    chatOrTask() {
      return ['chat', 'kanban'].includes(this.post.kind)
    },
    unreadCount() {
      return this.chatOrTask ? (this.post.unreadCount || 0) : 0
    },
    hasUnread() {
      return this.unreadCount > 0
    },
    unreadTitle() {
      const count = this.unreadCount
      return `${count} unread message${count === 1 ? '' : 's'}`
    },
    unreadLabel() {
      return String(Math.min(this.unreadCount, 99)) + (this.unreadCount > 99 ? '+' : '')
    },

    // ── Profiles (avatar group) ──────────────────────────────────────────────
    // `wallEvents.chatToPost` already resolves the names into accounts, but we
    // tolerate a bare string too so a hand-built post never crashes the card.
    profiles() {
      return (this.post.profiles || [])
        .map(p => (typeof p === 'string' ? { id: p, name: p, avatar: null } : p))
        .filter(p => p?.name)
    },
    visibleProfiles() {
      return this.profiles.slice(0, 3)
    },
    extraProfiles() {
      return Math.max(0, this.profiles.length - this.visibleProfiles.length)
    },
    // The group is led by the project icon; when the event has no project we
    // fall back to the author's avatar (user / bot).
    leadIcon() {
      return this.post.projectIcon || this.author?.avatar || null
    },
    leadFallbackIcon() {
      return ['project', 'bot'].includes(this.author?.type)
        ? 'fa-solid fa-cube'
        : 'fa-solid fa-user'
    },
    profilesLabel() {
      return this.profiles.map(p => '@' + p.name).join(' ')
    }
  }
}
</script>