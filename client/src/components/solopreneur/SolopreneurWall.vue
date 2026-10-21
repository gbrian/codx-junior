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

    What this card does that the raw wall does not:
      • every row names the TICKET it refers to (a ticket is a chat, see
        useSolopreneurProjects.js) — the title lives on `chat.name`
      • it reloads itself when a ticket is created or updated; the trigger is
        the activity signal CACHED BY THE CHATS STORE
        (`$storex.chats.activityRevision`), not a local diff of the chat list
        nor a scan of the transient `session.events` log
      • it can be narrowed down: status badges (default "All") + free-text search
      • on mobile a row can be swiped to the right to mark its ticket as done

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

    <!-- Filters: status badges ("All" by default) + free-text search over the
         tickets shown below. Both operate on the rows the card already loaded,
         so narrowing the feed never triggers another request. -->
    <div class="mt-4 flex flex-wrap items-center gap-2">
      <button
        v-for="filter in statusFilters"
        :key="filter.value"
        type="button"
        class="h-7 px-3 rounded-full text-[11px] font-semibold border transition inline-flex items-center gap-1.5"
        :class="statusFilter === filter.value
          ? 'bg-base-content text-base-100 border-base-content'
          : 'bg-base-100 border-base-content/20 text-base-content/60 hover:bg-base-200'"
        @click="statusFilter = filter.value"
      >
        {{ filter.label }}
        <span class="opacity-60">{{ filter.count }}</span>
      </button>

      <label class="ml-auto relative flex items-center">
        <i class="fa-solid fa-magnifying-glass absolute left-2.5 text-[11px] text-base-content/40" aria-hidden="true"></i>
        <input
          v-model="query"
          type="search"
          :placeholder="t('wl.search')"
          class="h-7 pl-7 pr-2.5 w-36 sm:w-48 rounded-full bg-base-200 text-xs outline-none focus:ring-2 focus:ring-codx-primary/30"
        />
      </label>
    </div>

    <!-- Gesture hint: only where the gesture exists -->
    <p v-if="isMobile && posts.length" class="mt-2 text-[11px] text-base-content/40">{{ t('wl.swipe') }}</p>

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
        @click="load()"
      >{{ t('wl.retry') }}</button>
    </div>

    <!-- Feed -->
    <ul v-else-if="posts.length" class="mt-5 flex flex-col gap-1">
      <li
        v-for="post in posts"
        :key="post.id"
        class="relative overflow-hidden rounded-xl"
      >
        <!-- Revealed while the row is dragged to the right (mobile): the gesture
             it will complete when the finger is lifted. -->
        <div
          v-if="revealed(post)"
          class="absolute inset-y-0 left-0 flex items-center gap-2 pl-3 text-xs font-semibold text-success pointer-events-none"
          aria-hidden="true"
        >
          <i class="fa-solid fa-circle-check"></i>
          <span>{{ t('wl.markDone') }}</span>
        </div>

        <button
          type="button"
          class="relative w-full text-left flex gap-3.5 rounded-xl px-2 py-2.5 -mx-2 hover:bg-base-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-codx-primary/40"
          :class="markingDone === post.chatId ? 'opacity-50' : ''"
          :style="rowStyle(post)"
          @click="openPost(post)"
          @touchstart="onRowTouchStart(post, $event)"
          @touchmove="onRowTouchMove(post, $event)"
          @touchend="onRowTouchEnd(post)"
          @touchcancel="resetSwipe"
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

            <!-- WHICH ticket changed (a ticket IS a chat, `name` is its title).
                 Without this line the row only said who did it. -->
            <p
              v-if="nameOf(post)"
              class="text-sm font-semibold mt-1 truncate"
              :title="nameOf(post)"
            >{{ nameOf(post) }}</p>

            <!-- Message preview: skipped when it is just the ticket title again
                 (a ticket with no messages yet). -->
            <p
              v-if="post.text && post.text !== nameOf(post)"
              class="text-sm text-base-content/60 mt-1 leading-relaxed line-clamp-2"
            >{{ post.text }}</p>

            <div class="flex items-center gap-2 mt-1.5 min-w-0">
              <span v-if="post.context" class="inline-flex items-center gap-1 text-[11px] text-base-content/40 min-w-0">
                <i :class="post.context.icon" class="shrink-0" aria-hidden="true"></i>
                <span class="truncate">{{ post.context.label }}</span>
              </span>
              <!-- Ticket status: the same value the badges above filter by -->
              <span
                v-if="post.chatId"
                class="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-base-200 shrink-0"
                :class="statusOf(post).color"
              >
                <i :class="statusOf(post).icon" aria-hidden="true"></i>
                {{ statusOf(post).label }}
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
    >{{ hasActiveFilter ? t('wl.noMatch') : t('wl.empty') }}</div>
  </section>
</template>

<script>
// How much activity the card shows. The summary is a glance, not the feed.
const RECENT_PROJECTS = 3
const RECENT_MONTHS = 2
const MAX_POSTS = 6

// Tickets are created, renamed and moved all the time. A change does not
// reload the card immediately: the signals are batched and the feed is
// re-read once, a moment after the last one (see the watcher).
const REFRESH_DEBOUNCE = 800

// ── swipe to mark done (mobile) ─────────────────────────────────────────────
// A rightwards drag over a row means "this ticket is done": SWIPE_START is the
// distance that turns the gesture into a horizontal one (below it the touch is
// still undecided), SWIPE_DONE the distance that completes it, SWIPE_MAX what
// the row can slide. SWIPE_CLICK_GUARD drops the click a drag would fire.
const SWIPE_START = 12
const SWIPE_DONE = 64
const SWIPE_MAX = 96
const SWIPE_CLICK_GUARD = 400

// Kinds a solopreneur cares about, translated (the wall keeps its English
// WALL_KINDS labels for the full-screen app; this card speaks the UI language).
const KIND_KEYS = {
  chat: 'wl.chat',
  kanban: 'wl.task',
  code: 'wl.changes',
  pr: 'wl.pr',
  meet: 'wl.meet'
}

// Everything a drag touches. A single object keeps the gesture state in one
// place, so every row can react to it (`swipe.id` = the row being dragged).
function idleSwipe() {
  return { id: null, startX: 0, startY: 0, dx: 0, horizontal: false, active: false }
}

export default {
  name: 'SolopreneurWall',
  data() {
    return {
      status: 'loading',
      // [{ chat, project }] — the same shape buildPosts() expects (see wallEvents)
      chats: [],
      // A request is in flight: the live-update watchers must not stack loads.
      loading: false,
      // Pending debounced reload (silent: the feed stays on screen).
      refreshTimer: null,
      // ── filters ───────────────────────────────────────────────────────────
      // 'all' | a chat status value (todo / doing / onhold / done / rejected)
      statusFilter: 'all',
      query: '',
      // ── gestures ──────────────────────────────────────────────────────────
      swipe: idleSwipe(),
      // Timestamp of the last drag, so its click does not open the ticket.
      suppressOpenAt: 0,
      // Ticket currently being marked done (row dims while the request runs).
      markingDone: null
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
    // The swipe gesture is touch-only: it is offered on the mobile layout.
    isMobile() {
      return !!this.$storex.ui?.isMobile
    },
    // Ticket titles by chat id. The card reads the chat list itself, so the
    // title is always available once the data is in — no extra lookup.
    chatNames() {
      return this.chats.reduce((acc, { chat }) => {
        if (chat?.id) acc[chat.id] = String(chat.name || '').trim()
        return acc
      }, {})
    },
    // Ticket statuses by chat id (`status` is the sprint column of a ticket;
    // a ticket IS a chat — see useSolopreneurProjects.js).
    chatStatuses() {
      return this.chats.reduce((acc, { chat }) => {
        if (chat?.id) acc[chat.id] = chat.status || 'todo'
        return acc
      }, {})
    },
    // The whole feed before filtering/truncating: filters must see every row,
    // otherwise the search would only look at the rows already displayed.
    allPosts() {
      const meets = (this.$storex.meets || {}).allActiveMeets || []
      const chats = this.chats.filter(({ chat }) => chat && !chat.is_template && chat.mode !== 'channel')
      return buildPosts({ chats, meets, currentUser: this.me?.username })
    },
    filteredPosts() {
      const q = this.query.trim().toLowerCase()
      return this.allPosts.filter(post => {
        // Status badge. Rows without a ticket (meets) have no status, so they
        // only survive the "All" filter.
        if (this.statusFilter !== 'all') {
          if (!post.chatId) return false
          if ((this.chatStatuses[post.chatId] || 'todo') !== this.statusFilter) return false
        }
        if (!q) return true
        // Free text: the ticket name is the main thing users search for, but
        // the message preview and the board/project chip help too.
        return [this.nameOf(post), post.text, post.context?.label]
          .filter(Boolean)
          .some(value => String(value).toLowerCase().includes(q))
      })
    },
    posts() {
      return this.filteredPosts.slice(0, MAX_POSTS)
    },
    hasActiveFilter() {
      return this.statusFilter !== 'all' || !!this.query.trim()
    },
    // Badge row: "All" + the statuses actually present in the feed (the
    // selected one always stays visible, even when it empties out).
    statusFilters() {
      const counts = this.allPosts.reduce((acc, post) => {
        if (!post.chatId) return acc
        const value = this.chatStatuses[post.chatId] || 'todo'
        acc[value] = (acc[value] || 0) + 1
        return acc
      }, {})
      const filters = [{ value: 'all', label: this.t('wl.all'), count: this.allPosts.length }]
      this.$storex.chats.statusList.forEach(entry => {
        const count = counts[entry.value] || 0
        if (!count && this.statusFilter !== entry.value) return
        filters.push({ value: entry.value, label: this.statusLabel(entry.value), count })
      })
      return filters
    },

    // ── live update signal ─────────────────────────────────────────────────
    // The chats store caches the last activity: `setChatActivity` bumps
    // `chatActivity.revision` on every socket "changed"/"done" event (of ANY
    // project) and on every local chat write (create, rename, status, delete).
    // Watching that number keeps the trigger cheap and immune to the expiry of
    // `session.events`; the store never signals on READ paths, so a refresh
    // cannot re-arm itself.
    activityRevision() {
      return this.$storex.chats.activityRevision
    }
  },
  watch: {
    activityRevision() {
      this.scheduleRefresh()
    }
  },
  created() {
    this.load()
  },
  beforeUnmount() {
    clearTimeout(this.refreshTimer)
  },
  methods: {
    t(key) {
      return translate(solopreneur.lang, key)
    },

    // ── Data ────────────────────────────────────────────────────────────────
    // `silent` is the live-update mode: the data is replaced in place, without
    // the skeleton and without dropping the feed when the request fails.
    async load({ silent = false } = {}) {
      // Never stack requests; a pending silent reload is retried afterwards.
      if (this.loading) {
        if (silent) this.scheduleRefresh()
        return
      }
      this.loading = true
      if (!silent) this.status = 'loading'
      try {
        await this.loadChats()
        this.status = 'ready'
      } catch (error) {
        console.error('[SolopreneurWall] Failed to load activity', error)
        if (!silent || !this.chats.length) this.status = 'error'
      } finally {
        this.loading = false
      }
    },
    scheduleRefresh() {
      clearTimeout(this.refreshTimer)
      this.refreshTimer = setTimeout(() => this.load({ silent: true }), REFRESH_DEBOUNCE)
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
    // Ticket title of the row (empty for non-chat events, e.g. meets).
    nameOf(post) {
      return post?.chatId ? (this.chatNames[post.chatId] || '') : ''
    },
    // Status of the row's ticket, ready to render (label + icon + colour).
    statusOf(post) {
      const value = post?.chatId ? (this.chatStatuses[post.chatId] || 'todo') : null
      const config = value ? this.$storex.chats.statusConfig(value) : null
      return {
        value,
        label: value ? this.statusLabel(value) : '',
        icon: config?.icon || '',
        color: config?.textColor || 'text-base-content/60'
      }
    },
    // Status copy in the UI language, falling back to the store label.
    statusLabel(value) {
      const key = 'sp.' + value
      const translated = this.t(key)
      return translated === key ? this.$storex.chats.statusLabel(value) : translated
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

    // ── Swipe to mark done (mobile only) ────────────────────────────────────
    // Only tickets that are not done yet can be swiped; meets and done rows
    // stay plain buttons.
    canSwipe(post) {
      if (!this.isMobile || !post?.chatId || post.meetId) return false
      if (this.markingDone === post.chatId) return false
      return this.statusOf(post).value !== 'done'
    },
    // Row offset while it is being dragged. `touch-action: pan-y` hands the
    // horizontal axis to the gesture and keeps the vertical page scroll native,
    // so nothing has to call preventDefault.
    rowStyle(post) {
      const dragging = this.swipe.active && this.swipe.id === post.id
      const dx = this.swipe.id === post.id ? this.swipe.dx : 0
      return {
        transform: dx ? `translateX(${dx}px)` : undefined,
        transition: dragging ? 'none' : 'transform 180ms ease',
        touchAction: 'pan-y'
      }
    },
    // The "Done" label behind the row is only painted while it is revealed,
    // because the row itself has no background to cover it.
    revealed(post) {
      return this.swipe.id === post.id && this.swipe.dx > 0
    },
    onRowTouchStart(post, event) {
      if (!this.canSwipe(post)) return
      const touch = event.touches?.[0]
      if (!touch) return
      this.swipe = {
        id: post.id,
        startX: touch.clientX,
        startY: touch.clientY,
        dx: 0,
        horizontal: false,
        active: true
      }
    },
    onRowTouchMove(post, event) {
      if (!this.swipe.active || this.swipe.id !== post.id) return
      const touch = event.touches?.[0]
      if (!touch) return
      const dx = touch.clientX - this.swipe.startX
      const dy = touch.clientY - this.swipe.startY
      if (!this.swipe.horizontal) {
        // Undecided yet: a small movement keeps the axis open.
        if (Math.abs(dx) < SWIPE_START) return
        // A vertical drag belongs to the page: abandon the gesture.
        if (Math.abs(dy) > Math.abs(dx)) {
          this.swipe.active = false
          return
        }
        this.swipe.horizontal = true
      }
      // Rightwards only — the gesture means "mark done".
      this.swipe.dx = Math.max(0, Math.min(dx, SWIPE_MAX))
    },
    async onRowTouchEnd(post) {
      if (!this.swipe.active || this.swipe.id !== post.id) return
      const dx = this.swipe.dx
      const dragged = dx >= SWIPE_START
      const complete = dx >= SWIPE_DONE
      this.resetSwipe()
      // A drag must never also open the ticket when the finger is lifted.
      if (dragged) this.suppressOpenAt = Date.now()
      if (complete) await this.markDone(post)
    },
    resetSwipe() {
      this.swipe = idleSwipe()
    },

    // Persist the "done" status of a ticket. A ticket is a chat, so its status
    // goes through `updateChatInfo` (PUT metadata) — the same path the sprints
    // board uses. It works for chats of other projects too, since the project
    // is resolved from the chat itself.
    async markDone(post) {
      const chatId = post?.chatId
      if (!chatId) return
      const entry = this.chats.find(({ chat }) => chat?.id === chatId)
      const chat = entry?.chat || this.$storex.chats.chats?.[chatId]
      if (!chat?.id) return
      if ((chat.status || 'todo') === 'done') return

      this.markingDone = chatId
      try {
        await this.$storex.chats.updateChatInfo({ chat, updates: { status: 'done' } })
        // Optimistic: the row and the status badges follow immediately, even
        // when the chat is not cached in the store (other project).
        chat.status = 'done'
        this.$storex.ui?.addNotification?.({ text: this.t('wl.done'), type: 'success' })
        // The store already bumped `activityRevision` (debounced refresh is on
        // its way); this call just avoids waiting for that debounce when the
        // write failed silently and no signal was emitted.
        this.scheduleRefresh()
      } catch (error) {
        console.error('[SolopreneurWall] Could not mark the ticket as done', error)
        this.$storex.ui?.addNotification?.({ text: this.t('wl.doneError'), type: 'error' })
      } finally {
        this.markingDone = null
      }
    },

    // ── Actions ─────────────────────────────────────────────────────────────
    // A row opens what it points at, exactly like the wall does: the chat (and
    // its project) or the running meet.
    async openPost(post) {
      // Ignore the click that closes a swipe gesture.
      if (Date.now() - this.suppressOpenAt < SWIPE_CLICK_GUARD) return
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