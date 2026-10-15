<script setup>
import moment from 'moment'
import { WALL_FILTERS } from './wallKinds'
import { buildAccounts, buildPosts, filterPosts, formatTime } from './wallEvents'
import WallNav from './WallNav.vue'
import WallBottomNav from './WallBottomNav.vue'
import WallRightRail from './WallRightRail.vue'
import WallTimeline from './WallTimeline.vue'
import WallComposer from './WallComposer.vue'
import WallAvatar from './WallAvatar.vue'
</script>

<template>
  <div class="w-full h-full bg-base-300 text-base-content">
    <!-- Three-column grid, centered on wide screens (mirrors the mockup shell) -->
    <div class="mx-auto flex w-full max-w-[1265px] h-full">
      <!-- Left rail (desktop) -->
      <header class="hidden md:flex flex-col shrink-0 border-r border-base-content/10 px-1 md:w-16 xl:w-64">
        <WallNav :route="route" :notifications="notificationCount" :messages="messageCount" @action="onAction" />
        <div class="mt-auto p-3 text-xs text-base-content/40 hidden xl:block">codx-junior · Activity</div>
      </header>

      <!-- Main column -->
      <main class="flex-1 min-w-0 max-w-[600px] flex flex-col md:border-r border-base-content/10 overflow-y-auto pb-16 md:pb-0">
        <!-- Single sticky header: title + tabs + kind filters. Keeping them in ONE
             sticky block fixes the bug where the filter chips slid under the
             header and became invisible (they used to be a separate sticky row
             that also pinned to top-0). -->
        <div class="sticky top-0 z-20 bg-base-300/95 backdrop-blur border-b border-base-content/10">
          <!-- Title row -->
          <div class="flex items-center gap-3 px-4 h-14">
            <img src="/only_icon.png" alt="codx-junior" class="w-7 h-7 rounded-full md:hidden" />
            <h1 class="text-lg font-bold flex-1 truncate">{{ title }}</h1>
            <button v-if="showFilters" class="btn btn-ghost btn-sm btn-circle" @click="reload" aria-label="Refresh activity">
              <i class="fa-solid fa-rotate"></i>
            </button>
          </div>

          <!-- Tabs (home only) -->
          <div v-if="route === 'home'" class="flex" role="tablist">
            <button
              v-for="t in tabs"
              :key="t.key"
              role="tab"
              :aria-selected="tab === t.key"
              class="flex-1 py-3 text-sm hover:bg-base-content/5 transition-colors relative"
              :class="tab === t.key ? 'font-bold' : 'text-base-content/50'"
              @click="tab = t.key"
            >
              {{ t.label }}
              <span v-if="tab === t.key" class="absolute bottom-0 left-1/2 -translate-x-1/2 h-1 w-12 rounded-full bg-primary"></span>
            </button>
          </div>

          <!-- Kind filters + unread selector -->
          <div v-if="showFilters" class="flex gap-2 px-3 py-2 overflow-x-auto border-t border-base-content/5">
            <!-- Unread selector: keep only events that still have unread replies -->
            <button
              class="btn btn-sm rounded-full shrink-0 gap-1.5"
              :class="unreadOnly ? 'btn-primary' : 'btn-ghost text-base-content/70'"
              :aria-pressed="unreadOnly"
              title="Show only events with unread messages"
              @click="unreadOnly = !unreadOnly"
            >
              <i class="fa-solid fa-envelope-open-text text-xs" aria-hidden="true"></i>
              Unread
              <span
                v-if="unreadCount"
                class="badge badge-xs"
                :class="unreadOnly ? 'badge-primary-content' : 'badge-error'"
              >{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
            </button>

            <span class="self-center w-px h-5 bg-base-content/10 shrink-0" aria-hidden="true"></span>

            <button
              v-for="f in filters"
              :key="f.key"
              class="btn btn-sm rounded-full shrink-0"
              :class="kind === f.key ? 'btn-primary' : 'btn-ghost text-base-content/70'"
              @click="kind = f.key"
            >
              {{ f.label }}
            </button>
          </div>
        </div>

        <!-- Composer -->
        <div v-if="route === 'home' || route === 'profile'" class="border-b border-base-content/10">
          <WallComposer
            :me="meAccount"
            :project="activeProject"
            :reply-to="replyTo"
            :reply-author="replyAuthor"
            :submitting="submitting"
            @submit="onComposerSubmit"
            @cancel-reply="replyTo = null"
          />
        </div>

        <!-- Notifications view -->
        <div v-if="route === 'notifications'" class="flex flex-col">
          <div
            v-for="n in notifications"
            :key="n.ts + (n.text || '')"
            class="flex items-start gap-3 px-4 py-3 border-b border-base-content/10"
          >
            <span class="mt-0.5" :class="notifColor(n.type)"><i :class="notifIcon(n.type)"></i></span>
            <div class="flex-1 min-w-0">
              <div class="text-sm font-semibold break-words">{{ n.text }}</div>
              <div class="text-xs text-base-content/50 mt-0.5">{{ n.ts }}</div>
            </div>
          </div>
          <div v-if="!notifications.length" class="p-10 text-center text-base-content/50">
            <i class="fa-solid fa-bell-slash text-3xl"></i>
            <p class="mt-2">No notifications</p>
          </div>
        </div>

        <!-- Messages view -->
        <div v-else-if="route === 'messages'" class="flex flex-col">
          <div
            v-for="conv in conversations"
            :key="conv.id"
            class="flex items-center gap-3 px-4 py-3 border-b border-base-content/10 hover:bg-base-content/5"
          >
            <span class="w-10 h-10 rounded-full bg-primary/20 text-primary grid place-items-center">
              <i class="fa-solid fa-hashtag"></i>
            </span>
            <div class="flex-1 min-w-0">
              <div class="font-bold text-sm truncate">{{ conv.name }}</div>
              <div class="text-xs text-base-content/50 truncate">{{ conv.team }}</div>
            </div>
          </div>
          <div v-if="!conversations.length" class="p-10 text-center text-base-content/50">
            <i class="fa-solid fa-envelope-open text-3xl"></i>
            <p class="mt-2">No conversations</p>
          </div>
        </div>

        <!-- Profile view -->
        <div v-else-if="route === 'profile'">
          <div class="p-4 border-b border-base-content/10 flex items-center gap-4">
            <WallAvatar :account="meAccount" :size="12" />
            <div class="min-w-0">
              <div class="text-lg font-bold truncate">{{ meAccount.name }}</div>
              <div class="text-sm text-base-content/50 truncate">@{{ meAccount.handle }}</div>
            </div>
          </div>
          <WallTimeline :posts="posts" :status="status" :accounts="accounts" :viewers="viewerMap" @action="onAction" @retry="reload" />
        </div>

        <!-- Feed (home / explore / bookmarks) -->
        <WallTimeline v-else :posts="posts" :status="status" :accounts="accounts" :viewers="viewerMap" @action="onAction" @retry="reload" />
      </main>

      <!-- Right rail (desktop) -->
      <aside class="hidden lg:block w-80 shrink-0 px-4 py-4 overflow-y-auto">
        <WallRightRail
          :query="query"
          :trends="trends"
          :suggestions="suggestions"
          :following="following"
          @search="setQuery"
          @follow="toggleFollow"
        />
      </aside>
    </div>

    <!-- Mobile bottom bar (the wall's own navigation) -->
    <WallBottomNav
      :route="route"
      :notifications="notificationCount"
      :messages="messageCount"
      @action="onAction"
    />

    <!-- Thread modal -->
    <modal v-if="threadPost" close="true" @close="threadPost = null">
      <template #header>Thread</template>
      <div class="flex flex-col gap-3">
        <div class="flex gap-3">
          <WallAvatar :account="accounts[threadPost.authorId]" :size="10" />
          <div class="flex-1 min-w-0">
            <div class="text-sm font-bold truncate">{{ accounts[threadPost.authorId]?.name }}</div>
            <div class="text-xs text-base-content/50">@{{ accounts[threadPost.authorId]?.handle }} · {{ formatTime(threadPost.createdAt) }}</div>
            <p class="text-sm mt-1 whitespace-pre-line break-words">{{ threadPost.text }}</p>
          </div>
        </div>
        <div class="text-xs text-base-content/50">{{ threadPost.counts.views }} view(s)</div>
        <div class="border-t border-base-content/10 pt-2">
          <WallComposer
            :me="meAccount"
            :project="activeProject"
            :reply-to="threadPost"
            :reply-author="threadAuthor"
            :submitting="submitting"
            @submit="onComposerSubmit"
          />
        </div>
      </div>
    </modal>
  </div>
</template>

<script>
// Persisted viewer state (likes are stored on the chat, these remain local)
const WALL_STORAGE_KEY = 'codx.wall.state.v1'

// ── Multi-project feed (temporary) ───────────────────────────────────────────
// The wall aggregates activity from EVERY project, newest first. That needs a
// backend endpoint returning cross-project activity in a single call; until it
// exists we read the first `WALL_PROJECT_LIMIT` (most recently active) projects
// to exercise the multi-project path.
const WALL_PROJECT_LIMIT = 3

export default {
  props: {
    project: { type: Object, default: null },
    board: { type: String, default: null }
  },
  data() {
    return {
      route: 'home',
      tab: 'for-you',
      kind: 'all',
      // "Unread" selector: when true only events with unread replies are shown.
      unreadOnly: false,
      query: '',
      status: 'ready',
      submitting: false,
      replyTo: null,
      threadPost: null,
      viewers: {},
      localPosts: [],
      following: [],
      // Activity loaded across projects ([{ chat, project }]) for the feed.
      projectChats: [],
      tabs: [
        { key: 'for-you', label: 'For you' },
        { key: 'following', label: 'Following' }
      ],
      filters: WALL_FILTERS
    }
  },
  computed: {
    activeProject() {
      return this.project || this.$projects.activeProject || null
    },
    allProjects() {
      return this.$projects.allProjects || []
    },
    me() {
      return this.$storex.users.user || this.$user || {}
    },
    meAccount() {
      return buildAccounts({ currentUser: this.me }).__me
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
    // The account behind the post being replied to (for the composer banner).
    replyAuthor() {
      return this.replyTo ? this.accounts[this.replyTo.authorId] : null
    },
    threadAuthor() {
      return this.threadPost ? this.accounts[this.threadPost.authorId] : null
    },
    // Recent activity assembled from the real project and chat data.
    wallChats() {
      const list = []
      const seen = new Set()
      const push = (chat, project) => {
        const id = chat?.id ?? chat?.doc_id
        if (!id || seen.has(id)) return
        seen.add(id)
        list.push({ chat, project })
      }

      // 1) Activity loaded across projects (multi-project feed). Each entry
      //    already carries its project so the post renders the right icon and
      //    context; `buildPosts` merges everything newest-first.
      this.projectChats.forEach(({ chat, project }) => push(chat, project))

      // 2) Active project sources (metrics + store) as the baseline.
      const projects = this.project ? [this.project] : (this.$projects.allProjects || [])
      projects.forEach(project => {
        (project.metrics?.wall || []).forEach(chat => push(chat, project))
      })

      const fallbackProject = this.project || this.activeProject
      const projectOf = chat =>
        this.$projects.allProjectsById?.[chat?.project_id || chat?.owner_project_id] || fallbackProject

      ;(this.$chats.allChats || []).forEach(chat => push(chat, projectOf(chat)))
      ;(this.$chats.recentChats || []).forEach(chat => push(chat, projectOf(chat)))

      return list.filter(({ chat }) => !chat.is_template && chat.mode !== 'channel')
    },
    notifications() {
      return this.$ui.notifications || []
    },
    basePosts() {
      // Feed from every source: chats, live meets and — the fix — the meets that
      // already ended. `allActiveMeets` only holds in-progress meets (an ended
      // meet is removed from it and pushed to `meetHistory`), so feeding the wall
      // with active meets alone is exactly why past meetings never showed up.
      const meetsStore = this.$storex.meets || {}
      const meets = [
        ...(meetsStore.allActiveMeets || []),
        ...(meetsStore.meetHistory || [])
      ]
      const posts = buildPosts({
        chats: this.wallChats,
        meets,
        // Used to compute the unread-reply badge on chat / task events.
        currentUser: this.me?.username
      })
      return [...this.localPosts, ...posts].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
    },
    posts() {
      if (this.route === 'bookmarks') {
        return this.basePosts.filter(p => this.viewers[p.id]?.bookmarked)
      }
      if (this.route === 'profile') {
        const me = this.me?.username
        return this.basePosts.filter(p => p.authorId === '__me' || (me && p.authorId === me))
      }
      return filterPosts(this.basePosts, {
        tab: this.tab,
        kind: this.kind,
        query: this.query,
        following: this.following,
        unreadOnly: this.unreadOnly
      })
    },
    // Number of events that still have unread replies — drives the selector badge.
    unreadCount() {
      return this.basePosts.filter(p => (p.unreadCount || 0) > 0).length
    },
    // Viewer state per post. Bookmarks/reposts stay local; likes for chat-backed
    // posts are resolved from the chat metadata (`likedBy`).
    viewerMap() {
      const me = this.me?.username
      const map = {}
      this.basePosts.forEach(p => {
        const local = this.viewers[p.id] || {}
        const liked = p.chatId ? (p.likedBy || []).includes(me) : !!local.liked
        map[p.id] = { ...local, liked }
      })
      return map
    },
    // The home header greets the current user instead of a generic "Activity".
    title() {
      const welcome = `Welcome ${this.meAccount.name}`
      return {
        home: welcome,
        explore: 'Explore',
        notifications: 'Notifications',
        messages: 'Messages',
        bookmarks: 'Bookmarks',
        profile: this.meAccount.name
      }[this.route] || welcome
    },
    showFilters() {
      return ['home', 'explore'].includes(this.route)
    },
    notificationCount() {
      return this.notifications.length
    },
    messageCount() {
      return this.conversations.length
    },
    conversations() {
      const teams = this.$teams.teams || []
      const list = []
      teams.forEach(team => {
        (team.categories || []).forEach(cat => {
          (cat.channels || []).forEach(ch => {
            list.push({ id: `${team.id}-${ch.id}`, name: `# ${ch.name}`, team: team.name })
          })
        })
      })
      return list
    },
    trends() {
      return (this.$storex.kanban.allBoards || [])
        .filter(b => !b.virtual)
        .slice(0, 5)
        .map(b => ({
          query: b.title,
          label: b.type === 'sprint' ? 'Sprint' : 'Board',
          count: (this.$storex.kanban.boardChats(b.id) || []).length
        }))
    },
    suggestions() {
      const accounts = this.accounts
      const users = (this.$storex.api.userNetwork || [])
        .map(u => accounts[u.id || u.username || u.userName])
        .filter(Boolean)
      const bot = accounts['codx-junior']
      return [bot, ...users].filter(a => a && a.id !== '__me').slice(0, 5)
    }
  },
  watch: {
    // Projects load asynchronously; build the multi-project feed once available.
    allProjects(list) {
      if (list?.length && !this.projectChats.length) {
        this.loadRecentProjectChats()
      }
    }
  },
  created() {
    this.restore()
    this.loadActivity()
  },
  methods: {
    async loadActivity() {
      await this.loadActiveProjectChats()
      await this.loadRecentProjectChats()
    },
    async loadActiveProjectChats() {
      try {
        if (!(this.$chats.allChats || []).length) {
          await this.$storex.chats.loadChats()
        }
      } catch (error) {
        console.warn('[Wall] Failed to load activity', error)
      }
    },
    // Multi-project activity (temporary test feed). Reads the most recently
    // active projects and pins each chat to its project so `chatToPost` can
    // render the right icon/context; `buildPosts` merges everything newest-first.
    async loadRecentProjectChats() {
      const projects = (this.$projects.allProjects || []).filter(p => p.$api)
      const targets = projects.slice(0, WALL_PROJECT_LIMIT)
      if (!targets.length) return
      const filters = { from_date: moment().add(-2, 'months').format('YYYY-MM-DD') }
      const batches = await Promise.all(targets.map(async project => {
        try {
          const chats = await project.$api.chats.list(filters)
          return (chats || []).map(chat => ({ chat, project }))
        } catch (error) {
          console.warn(`[Wall] Failed to load activity for ${project.project_name}`, error)
          return []
        }
      }))
      this.projectChats = batches.reduce((all, batch) => all.concat(batch), [])
    },
    onAction(type, payload) {
      switch (type) {
        case 'nav':
          this.route = payload.key
          this.query = ''
          this.unreadOnly = false
          break
        case 'compose':
          this.route = 'home'
          this.replyTo = null
          break
        case 'open':
          // A chat card navigates to (opens) the chat it points at. Events that
          // are not backed by a chat (e.g. meets) keep opening the thread modal.
          if (payload?.chatId) {
            this.openChat(payload)
          } else {
            this.threadPost = payload
          }
          break
        case 'reply':
          this.replyTo = payload
          this.route = 'home'
          break
        case 'cancel-reply':
          this.replyTo = null
          break
        case 'like':
          this.toggleLike(payload)
          break
        case 'repost':
          this.toggleViewer(payload.id, 'reposted')
          break
        case 'bookmark':
          this.toggleViewer(payload.id, 'bookmarked')
          break
        case 'share':
          this.share(payload)
          break
        case 'join-meet':
          if (payload?.meetId && this.$storex.ui.openMeet) this.$storex.ui.openMeet(payload.meetId)
          break
        default:
          break
      }
    },
    // Navigate to the chat behind a feed card. The post only carries the chat id
    // and its project, so switch to that project first when the chat belongs to
    // another (sub)project, then let the chats store load and activate it.
    async openChat(post) {
      if (!post?.chatId) return
      const projectId = post.projectId
      const project = projectId ? this.$projects.allProjectsById?.[projectId] : null
      if (project && project.project_id !== this.$projects.activeProject?.project_id) {
        await this.$projects.setActiveProject(project)
      }
      await this.$storex.chats.setActiveChat({
        id: post.chatId,
        project_id: projectId,
        owner_project_id: projectId
      })
    },

    // ── Composer wiring ─────────────────────────────────────────────────────
    // A post creates a chat; a reply appends a comment to the target chat.
    onComposerSubmit(payload) {
      if (this.replyTo) {
        if (this.replyTo.chatId) return this.addComment(this.replyTo, payload)
        return this.addLocalReply(this.replyTo, payload)
      }
      return this.createPost(payload)
    },
    buildMessage({ text, profiles = [], files = [], attachments = [] }) {
      return {
        role: 'user',
        content: text,
        files,
        profiles,
        attachments,
        user: this.me?.username || 'you',
        meta_data: {},
        done: true
      }
    },
    deriveTitle(text) {
      const clean = String(text || '').replace(/\s+/g, ' ').trim()
      if (!clean) return 'Wall post'
      return clean.length > 60 ? clean.slice(0, 60) + '…' : clean
    },
    async createPost({ text, profiles, files, attachments, project }) {
      // The composer lets the author pick the target project; fall back to the
      // active one when none is set.
      const targetProject = project || this.activeProject
      if (!targetProject) {
        this.$toast.error('Select a project first')
        return
      }
      this.submitting = true
      try {
        const chat = await this.$storex.chats.createNewChat({
          name: this.deriveTitle(text),
          mode: 'chat',
          profiles: profiles || [],
          file_list: files || [],
          owner_project_id: targetProject.project_id,
          project_id: targetProject.project_id,
          // Flag the chat as a wall post + reserve the likes slot in meta_data.
          meta_data: { wall: { post: true, likes: [] } },
          messages: [this.buildMessage({ text, profiles, files, attachments })]
        })
        // Run the project chat only when profiles were selected.
        if (chat && profiles?.length) {
          await this.$storex.projects.chatWihProject(chat)
        }
        await this.loadActivity()
        this.$toast.success('Posted')
      } catch (error) {
        console.error('[Wall] Failed to create post', error)
        this.$toast.error('Could not create the post')
      } finally {
        this.submitting = false
      }
    },
    async addComment(post, payload) {
      this.submitting = true
      try {
        let chat = this.$chats.chats?.[post.chatId]
        if (!chat) {
          chat = await this.$storex.chats.loadChat({ id: post.chatId, owner_project_id: post.projectId })
        }
        if (!chat) {
          this.$toast.error('Chat not found')
          return
        }
        await this.$storex.chats.addMessage({ chat, message: this.buildMessage(payload) })
        // A comment that mentions profiles also runs the project chat.
        if (payload.profiles?.length) {
          await this.$storex.projects.chatWihProject(chat)
        }
        this.replyTo = null
        this.$toast.success('Reply sent')
      } catch (error) {
        console.error('[Wall] Failed to add comment', error)
        this.$toast.error('Could not send the reply')
      } finally {
        this.submitting = false
      }
    },
    // Fallback for replies to events that are not backed by a chat (e.g. meets).
    addLocalReply(post, { text }) {
      const newPost = {
        id: `local-${Date.now()}`,
        kind: 'chat',
        authorId: '__me',
        createdAt: new Date().toISOString(),
        text,
        context: this.activeProject
          ? { label: this.activeProject.project_name, icon: 'fa-solid fa-cube' }
          : null,
        attachment: null,
        replyTo: post.id,
        counts: { replies: 0, reposts: 0, likes: 0, views: 1 }
      }
      this.localPosts = [newPost, ...this.localPosts]
      this.replyTo = null
      this.persist()
      this.$toast.success('Reply sent')
    },

    // ── Likes (stored on the chat metadata) ─────────────────────────────────
    async toggleLike(post) {
      if (!post?.chatId) {
        this.toggleViewer(post.id, 'liked')
        return
      }
      try {
        let chat = this.$chats.chats?.[post.chatId]
        if (!chat || !chat.meta_data) {
          chat = await this.$storex.chats.loadChat({ id: post.chatId, owner_project_id: post.projectId })
        }
        if (!chat) return
        const meta = { ...(chat.meta_data || {}) }
        const wall = { ...(meta.wall || {}) }
        const likes = Array.isArray(wall.likes) ? [...wall.likes] : []
        const me = this.me?.username
        const ix = likes.indexOf(me)
        if (ix >= 0) likes.splice(ix, 1)
        else if (me) likes.push(me)
        wall.likes = likes
        meta.wall = wall
        await this.$storex.chats.updateChatInfo({ chat, updates: { meta_data: meta } })
      } catch (error) {
        console.error('[Wall] Failed to toggle like', error)
      }
    },

    toggleViewer(id, key) {
      const current = this.viewers[id] || {}
      this.viewers = { ...this.viewers, [id]: { ...current, [key]: !current[key] } }
      this.persist()
    },
    toggleFollow(id) {
      this.following = this.following.includes(id)
        ? this.following.filter(f => f !== id)
        : [...this.following, id]
      this.persist()
    },
    setQuery(value) {
      this.query = value
      if (this.route !== 'home' && this.route !== 'explore') this.route = 'explore'
    },
    async share(post) {
      const url = `${window.location.origin}${window.location.pathname}#wall-${post.id}`
      try {
        await navigator.clipboard.writeText(url)
        this.$toast.success('Link copied')
      } catch (e) {
        this.$toast.info(url)
      }
    },
    reload() {
      this.status = 'loading'
      this.$nextTick(() => { this.status = 'ready' })
    },
    persist() {
      try {
        localStorage.setItem(WALL_STORAGE_KEY, JSON.stringify({
          viewers: this.viewers,
          localPosts: this.localPosts,
          following: this.following
        }))
      } catch (e) {
        // Storage may be unavailable (private mode / quota) — ignore
      }
    },
    restore() {
      try {
        const saved = JSON.parse(localStorage.getItem(WALL_STORAGE_KEY) || '{}')
        if (saved.viewers) this.viewers = saved.viewers
        if (Array.isArray(saved.localPosts)) this.localPosts = saved.localPosts
        if (Array.isArray(saved.following)) this.following = saved.following
      } catch (e) {
        // Corrupted state — start fresh
      }
    },
    notifIcon(type) {
      return {
        error: 'fa-solid fa-circle-xmark',
        warning: 'fa-solid fa-triangle-exclamation',
        success: 'fa-solid fa-circle-check'
      }[type] || 'fa-solid fa-circle-info'
    },
    notifColor(type) {
      return {
        error: 'text-error',
        warning: 'text-warning',
        success: 'text-success'
      }[type] || 'text-info'
    }
  }
}
</script>