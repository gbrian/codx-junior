<script setup>
import moment from 'moment'
import WallAvatar from '../wall/WallAvatar.vue'
import { buildAccounts, buildPosts, formatRelative } from '../wall/wallEvents'
import { kindConfig } from '../wall/wallKinds'
import { state as solopreneur } from './useSolopreneur'
import { translate } from './i18n'
</script>

<template>
  <!--
    Activity wall — Solopreneur summary card.

    SAME feed as src/components/wall/Wall.vue (same helpers, same stores, same
    avatars) but rendered as ONE card of the summary layout instead of the
    full-screen social shell: no left rail, no tabs, no composer, no right rail
    and no per-post action bar. The complete wall is still one click away from
    the header ("Open activity"), which opens the real `activity` app.

    This card replaced the inline "Quick messages" card of the summary. Quick
    messages was NOT removed: it keeps its own section
    (nav → Messages → SolopreneurMessages.vue).

    Why a dedicated component instead of a `compact` prop on Wall.vue:
    the wall is dark-first, social-shaped and driven by its own navigation,
    while every solopreneur component is a light, single-purpose card. Keeping
    the two renderings apart leaves the activity app untouched (it is used by
    the desktop panels) and lets this card reuse only the pure helpers
    (wallEvents / wallKinds) plus the shared avatar.
  -->
  <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h2 class="text-base font-semibold">{{ t('wl.title') }}</h2>
        <p class="text-sm text-base-content/50 mt-1.5 max-w-[46ch]">{{ t('wl.desc') }}</p>
      </div>
      <button
        v-if="canOpenWall"
        type="button"
        class="text-sm font-semibold text-codx-primary hover:underline whitespace-nowrap shrink-0"
        @click="openWall"
      >{{ t('wl.open') }}</button>
    </div>

    <!-- Loading -->
    <div v-if="status === 'loading'" class="mt-5 flex flex-col gap-4">
      <div v-for="n in 3" :key="n" class="flex gap-3.5 animate-pulse">
        <div class="w-8 h-8 rounded-full bg-base-content/10 shrink-0"></div>
        <div class="flex-1 flex flex-col gap-2 py-1">
          <div class="h-3 w-40 bg-base-content/10 rounded"></div>
          <div class="h-3 w-full bg-base-content/10 rounded"></div>
        </div>
      </div>
    </div>

    <!-- Error -->
    <div
      v-else-if="status === 'error'"
      class="mt-5 py-10 text-center bg-base-200 border border-dashed border-base-content/15 rounded-xl"
    >
      <p class="text-sm text-base-content/60">{{ t('wl.error') }}</p>
      <button
        type="button"
        class="mt-3 h-9 px-4 rounded-full border border-base-content/20 bg-base-100 text-sm font-semibold hover:bg-base-200 transition"
        @click="load"
      >{{ t('wl.retry') }}</button>
    </div>

    <!-- Feed -->
    <ul v-else-if="posts.length" class="mt-5 flex flex-col gap-1">
      <li v-for="post in posts" :key="post.id">
        <button
          type="button"
          class="w-full text-left flex gap-3.5 rounded-xl px-2 py-2.5 -mx-2 hover:bg-base-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-codx-primary/40"
          @click="openPost(post)"
        >
          <WallAvatar :account="authorOf(post)" :size="8" />

          <div class="min-w-0 flex-1">
            <div class="flex items-baseline gap-2">
              <span class="text-sm font-semibold truncate">{{ authorOf(post).name }}</span>
              <span class="text-[11px] text-base-content/40 shrink-0">{{ relative(post) }}</span>
              <span
                class="ml-auto inline-flex items-center gap-1 text-[11px] font-semibold shrink-0"
                :class="kindOf(post).color"
                :title="kindLabel(post)"
              >
                <i :class="kindOf(post).icon" aria-hidden="true"></i>
                <span class="hidden sm:inline">{{ kindLabel(post) }}</span>
              </span>
            </div>

            <p v-if="post.text" class="text-sm text-base-content/60 mt-1 leading-relaxed line-clamp-2">{{ post.text }}</p>

            <div class="flex items-center gap-2 mt-1.5 min-w-0">
              <span v-if="post.context" class="inline-flex items-center gap-1 text-[11px] text-base-content/40 min-w-0">
                <i :class="post.context.icon" class="shrink-0" aria-hidden="true"></i>
                <span class="truncate">{{ post.context.label }}</span>
              </span>
              <span
                v-if="unreadOf(post)"
                class="text-[11px] font-semibold px-2.5 py-0.5 rounded-full text-error bg-error/15 shrink-0"
              >{{ unreadOf(post) }} {{ t('wl.unread') }}</span>
            </div>
          </div>
        </button>
      </li>
    </ul>

    <!-- Empty -->
    <div
      v-else
      class="mt-5 py-10 text-center text-sm text-base-content/50 bg-base-200 border border-dashed border-base-content/15 rounded-xl"
    >{{ t('wl.empty') }}</div>
  </section>
</template>

<script>
// How much activity the card shows. The summary is a glance, not the feed.
const RECENT_PROJECTS = 3
const RECENT_MONTHS = 2
const MAX_POSTS = 6

// Kinds a solopreneur cares about, translated (the wall keeps its English
// WALL_KINDS labels for the full-screen app; this card speaks the UI language).
const KIND_KEYS = {
  chat: 'wl.chat',
  kanban: 'wl.task',
  code: 'wl.changes',
  pr: 'wl.pr',
  meet: 'wl.meet'
}

export default {
  name: 'SolopreneurWall',
  data() {
    return {
      status: 'loading',
      // [{ chat, project }] — the same shape buildPosts() expects (see wallEvents)
      chats: []
    }
  },
  computed: {
    me() {
      return this.$storex.users.user || this.$user || {}
    },
    accounts() {
      const users = [
        ...(this.$users.allUsers || []),
        ...(this.$storex.api.userNetwork || [])
      ]
      return buildAccounts({
        currentUser: this.me,
        users,
        projects: this.$projects.allProjects || []
      })
    },
    activeProject() {
      return this.$projects.activeProject || null
    },
    // The full wall is an app ("activity" → Wall.vue); opening an app only
    // makes sense in desktop/panel mode, so the link is hidden when there is
    // no panel host to render it.
    canOpenWall() {
      return !!this.$storex.ui?.isDesktopMode
    },
    posts() {
      const meets = (this.$storex.meets || {}).allActiveMeets || []
      const chats = this.chats.filter(({ chat }) => chat && !chat.is_template && chat.mode !== 'channel')
      return buildPosts({ chats, meets, currentUser: this.me?.username }).slice(0, MAX_POSTS)
    }
  },
  created() {
    this.load()
  },
  methods: {
    t(key) {
      return translate(solopreneur.lang, key)
    },

    // ── Data ────────────────────────────────────────────────────────────────
    async load() {
      this.status = 'loading'
      try {
        await this.loadChats()
        this.status = 'ready'
      } catch (error) {
        console.error('[SolopreneurWall] Failed to load activity', error)
        this.status = 'error'
      }
    },
    async loadChats() {
      const fallbackProject = this.activeProject

      // Baseline: whatever the chats store already holds (active project).
      if (!(this.$chats?.allChats || []).length) {
        try {
          await this.$storex.chats.loadChats()
        } catch (error) {
          console.warn('[SolopreneurWall] Failed to load project chats', error)
        }
      }

      // Multi-project activity: the most recently used projects, newest first.
      const targets = (this.$projects.allProjects || []).filter(p => p.$api).slice(0, RECENT_PROJECTS)
      const filters = { from_date: moment().add(-RECENT_MONTHS, 'months').format('YYYY-MM-DD') }
      const batches = await Promise.all(targets.map(async project => {
        try {
          const chats = await project.$api.chats.list(filters)
          return (chats || []).map(chat => ({ chat, project }))
        } catch (error) {
          console.warn(`[SolopreneurWall] Failed to load activity for ${project.project_name}`, error)
          return []
        }
      }))

      const entries = batches.reduce((all, batch) => all.concat(batch), [])
      const projectOf = chat =>
        this.$projects.allProjectsById?.[chat?.project_id || chat?.owner_project_id] || fallbackProject

      this.chats = entries.length
        ? entries
        : (this.$chats?.allChats || []).map(chat => ({ chat, project: projectOf(chat) }))
    },

    // ── Presentation ────────────────────────────────────────────────────────
    // Same resolution order as WallTimeline: exact id, lowercase id, handle/name
    // match, then the bot — a post authored by a username still gets its avatar.
    authorOf(post) {
      const accounts = this.accounts || {}
      const id = post?.authorId
      return accounts[id]
        || accounts[String(id || '').toLowerCase?.()]
        || Object.values(accounts).find(a => a.handle === id || a.name === id)
        || accounts['codx-junior']
        || {}
    },
    kindOf(post) {
      return kindConfig(post?.kind)
    },
    kindLabel(post) {
      const key = KIND_KEYS[post?.kind]
      return key ? this.t(key) : kindConfig(post?.kind).label
    },
    relative(post) {
      return formatRelative(post?.createdAt)
    },
    unreadOf(post) {
      return ['chat', 'kanban'].includes(post?.kind) ? (post?.unreadCount || 0) : 0
    },

    // ── Actions ─────────────────────────────────────────────────────────────
    // A row opens what it points at, exactly like the wall does: the chat (and
    // its project) or the running meet.
    async openPost(post) {
      try {
        if (post?.meetId) {
          if (this.$storex.ui.openMeet) this.$storex.ui.openMeet(post.meetId)
          return
        }
        if (!post?.chatId) return
        const project = post.projectId ? this.$projects.allProjectsById?.[post.projectId] : null
        if (project && project.project_id !== this.$projects.activeProject?.project_id) {
          await this.$projects.setActiveProject(project)
        }
        await this.$storex.chats.setActiveChat({
          id: post.chatId,
          project_id: post.projectId,
          owner_project_id: post.projectId
        })
      } catch (error) {
        console.error('[SolopreneurWall] Could not open the activity', error)
        this.$ui?.addNotification?.({ text: this.t('wl.error'), type: 'error' })
      }
    },
    openWall() {
      this.$storex.ui.showApp({
        key: 'activity',
        name: 'Activity',
        component: 'activity',
        params: this.activeProject ? { project: this.activeProject } : {}
      })
    }
  }
}
</script>