<script setup>
import ChatSidebarNode from './ChatSidebarNode.vue'
import ChatListRenderer from './ChatListRenderer.vue'
import ProfileAvatar from '../profile/ProfileAvatar.vue'
import ProfileCard from '../ProfileCard.vue'
import ChatAttachmentPreview from './ChatAttachmentPreview.vue'
</script>

<template>
  <!-- ── Chat rail ──
       Two widths driven by `isCompact`: a 16rem panel with labelled sections and
       a 4rem icon rail exposing the same actions. Every block is a real
       <section> with a heading, so the rail reads as a document outline instead
       of a pile of floating widgets, and each heading carries the count of what
       it lists (Progressive disclosure: the number is the reason to scroll). -->
  <aside
    class="flex flex-col h-full overflow-hidden relative border-r-2 border-l-2 border-base-300 transition-all duration-200"
    :class="[
      isCompact ? 'w-16' : 'w-64',
      $ui?.isMobile && !isCompact ? 'shadow-lg z-40' : ''
    ]"
    aria-label="Chat and subtasks"
  >

    <!-- ─────────────────────────── HEADER: root chat ─────────────────────────── -->
    <div class="shrink-0 border-b border-base-100">
      <!-- Expanded: the full node card (identity + hover actions) -->
      <div v-if="!isCompact" class="px-2 py-2">
        <ChatSidebarNode
          :chat="rootChat"
          :allChats="[]"
          :selectedChatId="selectedChatId"
          :isCompact="false"
          :channelMode="channelMode"
          @select="selectChat"
          @add-subtask="$emit('add-subtask', $event)"
          @delete-chat="$emit('delete-chat', $event)"
        />
      </div>

      <!-- Compact: one square avatar. The project icon is an <img> layered over
           the initials' fallback — never a CSS background behind the text. -->
      <div v-else class="flex flex-col items-center gap-2 p-2">
        <button
          type="button"
          class="tooltip tooltip-right shrink-0 rounded-lg"
          :data-tip="rootChat?.name"
          :aria-label="`Open ${rootChat?.name || 'chat'}`"
          :aria-current="isRootSelected ? 'page' : undefined"
          @click="selectChat(rootChat)"
        >
          <span
            class="w-10 h-10 rounded-lg flex items-center justify-center overflow-hidden text-xs font-bold border transition-all duration-200"
            :class="isRootSelected
              ? 'border-primary/60 shadow-md ring-2 ring-primary/20'
              : 'border-base-content/20 hover:border-base-content/30 hover:bg-base-content/10'"
          >
            <img
              v-if="rootProject?.project_icon"
              :src="rootProject.project_icon"
              :alt="rootChat?.name || ''"
              class="w-full h-full object-cover"
            />
            <span v-else>{{ getInitials(rootChat?.name) }}</span>
          </span>
        </button>
      </div>
    </div>

    <!-- ─────────────────────── CENTER: scrollable sections ─────────────────────── -->
    <div class="flex-1 overflow-y-auto min-h-0 flex flex-col">

      <!-- Attachments — the card already prints its own header/count -->
      <section v-if="workingChat.attachments?.length" class="shrink-0 border-b border-base-100 p-2">
        <ChatAttachmentPreview
          :attachments="workingChat.attachments"
          @remove-attachment="$emit('remove-attachment', $event)"
        />
      </section>

      <!-- Profiles (channel members live in the host's members panel, so the
           block is hidden — not removed — in channel mode) -->
      <section
        v-if="chatProfiles.length"
        class="shrink-0 border-b border-base-100"
        :class="{ hidden: channelMode }"
      >
        <div v-if="!isCompact" class="px-2 py-2">
          <div class="flex items-center gap-2 px-1 mb-2">
            <h3 class="text-[10px] font-semibold uppercase tracking-[0.08em] text-base-content/45">Profiles</h3>
            <span class="ml-auto text-[10px] text-base-content/40 tabular-nums">{{ chatProfiles.length }}</span>
          </div>
          <div class="space-y-2">
            <ProfileCard
              v-for="profile in chatProfiles"
              :key="profile.name"
              :profile="profile"
              :mini="true"
            />
          </div>
        </div>

        <!-- Compact: avatars only, each with a readable tooltip -->
        <div v-else class="p-2 flex flex-col items-center gap-2">
          <i class="fa-solid fa-circle-user text-[11px] text-base-content/40" aria-hidden="true"></i>
          <div class="flex flex-col items-center gap-1.5">
            <span
              v-for="profile in chatProfiles"
              :key="profile.name"
              class="tooltip tooltip-right"
              :data-tip="profile.name"
            >
              <ProfileAvatar :profile="profile" :width="10" />
            </span>
          </div>
        </div>
      </section>

      <!-- Subtasks — groups / channels have no task hierarchy -->
      <section
        v-if="allNestedChats.length > 0"
        class="flex-1 min-h-0 flex flex-col px-2 py-2"
        :class="{ hidden: channelMode }"
      >
        <!-- Header: count + status filter -->
        <div v-if="!isCompact" class="flex items-center gap-2 px-1 mb-2 shrink-0">
          <h3 class="text-[10px] font-semibold uppercase tracking-[0.08em] text-base-content/45">Subtasks</h3>
          <span class="text-[10px] text-base-content/40 tabular-nums">
            {{ filteredNestedChats.length }}<template v-if="statusFilter">/{{ allNestedChats.length }}</template>
          </span>

          <div class="grow"></div>

          <!-- Status filter dropdown -->
          <div class="dropdown dropdown-end" @click.stop>
            <button
              tabindex="0"
              type="button"
              class="btn btn-xs btn-ghost gap-1 normal-case h-6 min-h-0 px-1.5"
              :class="statusFilter && $chats.statusTextColor(statusFilter)"
              :title="statusFilter ? `Filtered by: ${$chats.statusLabel(statusFilter)}` : 'Filter subtasks by status'"
            >
              <i :class="statusFilter ? $chats.statusIcon(statusFilter) : 'fa-solid fa-filter'"></i>
              <span class="text-[10px] font-medium">{{ statusFilter ? $chats.statusLabel(statusFilter) : 'All' }}</span>
              <i class="fa-solid fa-chevron-down text-[8px] opacity-60"></i>
            </button>
            <ul
              tabindex="0"
              class="dropdown-content menu menu-sm bg-base-100 rounded-box z-50 w-44 p-1 shadow-lg border border-base-300"
            >
              <li>
                <a
                  @click.stop="setStatusFilter(null)"
                  :class="[!statusFilter && 'active', 'flex items-center gap-2']"
                >
                  <i class="fa-solid fa-layer-group opacity-60"></i>
                  <span>All statuses</span>
                  <span class="ml-auto opacity-50 text-[10px]">{{ allNestedChats.length }}</span>
                </a>
              </li>
              <li v-for="option in $chats.statusList" :key="option.value">
                <a
                  @click.stop="setStatusFilter(option.value)"
                  :class="[statusFilter === option.value && 'active', 'flex items-center gap-2']"
                >
                  <i :class="[option.icon, option.textColor]"></i>
                  <span>{{ option.label }}</span>
                  <span class="ml-auto opacity-50 text-[10px]">{{ statusCounts[option.value] || 0 }}</span>
                </a>
              </li>
            </ul>
          </div>
        </div>

        <!-- Compact: the active filter is an icon, the count stays visible -->
        <div
          v-else-if="statusFilter"
          class="flex justify-center mb-1 shrink-0"
          :title="`Filtered by: ${$chats.statusLabel(statusFilter)}`"
        >
          <i class="text-xs" :class="[$chats.statusIcon(statusFilter), $chats.statusTextColor(statusFilter)]"></i>
        </div>

        <ChatListRenderer
          :class="!isCompact && 'p-1'"
          :chatList="filteredNestedChats"
          :selectedChatId="selectedChatId"
          :isCompact="isCompact"
          :allChats="allChats"
          :useExtended="false"
          :emptyText="statusFilter ? 'No subtasks with this status' : 'No subtasks yet'"
          @select="selectChat"
          @add-subtask="$emit('add-subtask', $event)"
          @delete-chat="$emit('delete-chat', $event)"
        />
      </section>

      <!-- Empty state — a placeholder, not a list -->
      <div v-else class="px-3 py-8 text-center" :class="{ hidden: channelMode }">
        <i class="fa-solid fa-list-check text-base-content/20 text-lg mb-2 block" aria-hidden="true"></i>
        <p class="text-xs text-base-content/40">No subtasks yet</p>
      </div>
    </div>

    <!-- ─────────────────────────── FOOTER: action toolbar ─────────────────────────── -->
    <div class="shrink-0 border-t border-base-100 px-2 py-2">
      <div class="flex items-center gap-1" :class="isCompact && 'flex-col gap-2'">

        <!-- Browser session (channels have no codebase to browse; hidden, still
             available for task chats) -->
        <button
          type="button"
          class="flex-1 flex items-center justify-center h-9 rounded-lg text-base-content/60 hover:text-base-content/90 hover:bg-base-200 focus-visible:ring-2 focus-visible:ring-primary/50 transition-colors duration-150"
          :class="{ hidden: channelMode }"
          title="Create browser session"
          aria-label="Create browser session"
          @click.stop="openBrowserSessionDialog"
        >
          <i class="fa-solid fa-globe text-sm" aria-hidden="true"></i>
        </button>

        <!-- More actions — grouped menu, opens upwards -->
        <div class="dropdown dropdown-top dropdown-start flex-1">
          <button
            ref="actionsTrigger"
            type="button"
            class="w-full flex items-center justify-center h-9 rounded-lg text-base-content/60 hover:text-base-content/90 hover:bg-base-200 focus-visible:ring-2 focus-visible:ring-primary/50 transition-colors duration-150"
            title="More actions"
            aria-label="More actions"
            aria-haspopup="menu"
          >
            <i class="fa-solid fa-ellipsis-vertical text-sm" aria-hidden="true"></i>
          </button>
          <ul
            tabindex="0"
            class="dropdown-content menu menu-sm bg-base-100 rounded-box z-50 w-48 p-1 shadow-lg border border-base-300 mb-1"
          >
            <!-- Group headers replace the previous empty <li> spacers: a menu
                 that is scannable in three blocks, not seven loose rows. -->
            <li class="menu-title" :class="{ hidden: channelMode }">Task</li>
            <li :class="{ hidden: channelMode }">
              <a @click.stop="handleFooterAction({ type: 'timeline' })">
                <i class="fa-solid fa-timeline text-sm opacity-70" aria-hidden="true"></i>
                View timeline
              </a>
            </li>
            <li :class="{ hidden: channelMode }">
              <a @click.stop="handleFooterAction({ type: 'logs' })">
                <i class="fa-solid fa-file-lines text-sm opacity-70" aria-hidden="true"></i>
                View AI logs
              </a>
            </li>

            <li class="menu-title">Chat</li>
            <li>
              <a
                @click.stop="handleReload"
                :class="isReloading && 'is-disabled pointer-events-none opacity-50'"
              >
                <i class="fa-solid fa-arrows-rotate text-sm opacity-70" :class="isReloading && 'fa-spin'" aria-hidden="true"></i>
                Reload chat
              </a>
            </li>
            <li>
              <a @click.stop="handleFooterAction({ type: 'export' })">
                <i class="fa-solid fa-download text-sm opacity-70" aria-hidden="true"></i>
                Export chat
              </a>
            </li>
            <!-- Admin only: raw JSON snapshot for a postmortem. Deliberately NOT
                 hidden in channel mode — a group conversation may need one too.
                 `canDump` is resolved by the host (ChatView). -->
            <li v-if="canDump">
              <a
                @click.stop="handleFooterAction({ type: 'dump' })"
                title="Admin only: full chat dump (JSON, postmortem)"
              >
                <i class="fa-solid fa-bug text-sm opacity-70 text-warning" aria-hidden="true"></i>
                Dump chat
              </a>
            </li>

            <li class="menu-title" :class="{ hidden: channelMode }">Configuration</li>
            <li :class="{ hidden: channelMode }">
              <a @click.stop="handleFooterAction({ type: 'settings' })">
                <i class="fa-solid fa-gear text-sm opacity-70" aria-hidden="true"></i>
                Properties
              </a>
            </li>
          </ul>
        </div>

        <!-- ── Host-provided actions ──
             Views embedding the sidebar inject their own toolbar buttons here
             (e.g. MessengerView's channel members toggle), so host features sit
             next to the built-in chat actions instead of floating over the chat
             header. Render ONE button per action and reuse the toolbar classes
             of the buttons above so it matches at every sidebar width:
               class="flex-1 flex items-center justify-center h-9 rounded-lg
                      text-base-content/60 hover:text-base-content/90
                      hover:bg-base-200 focus-visible:ring-2
                      focus-visible:ring-primary/50 transition-colors duration-150"
             The container is a row when expanded and a column when compact, so
             `flex-1` is all a button needs to align. -->
        <slot name="actions" />

        <!-- Compact toggle -->
        <button
          type="button"
          class="flex-1 flex items-center justify-center h-9 rounded-lg text-base-content/60 hover:text-base-content/90 hover:bg-base-200 focus-visible:ring-2 focus-visible:ring-primary/50 transition-colors duration-150"
          :title="isCompact ? 'Expand sidebar' : 'Collapse sidebar'"
          :aria-label="isCompact ? 'Expand sidebar' : 'Collapse sidebar'"
          :aria-expanded="!isCompact"
          @click.stop="$emit('toggle-compact')"
        >
          <i :class="isCompact ? 'fa-solid fa-angle-right' : 'fa-solid fa-angle-left'" aria-hidden="true"></i>
        </button>
      </div>
    </div>

    <!-- ── Browser session dialog ──
         Rendered through the app <modal>, which mounts itself on the app root:
         a dialog nested inside this `overflow-hidden` rail was clipped and could
         not be escaped with the keyboard. -->
    <modal
      v-if="showBrowserDialog"
      title="Create browser session"
      close
      @close="closeBrowserSessionDialog"
    >
      <div class="flex flex-col gap-4 w-full md:w-96">
        <label class="block">
          <span class="block text-[11px] font-medium uppercase tracking-[0.06em] text-base-content/45 mb-1">
            Session name
          </span>
          <input
            v-model="browserSessionForm.name"
            type="text"
            placeholder="e.g., Testing Session"
            class="input input-sm input-bordered w-full bg-base-100 focus:border-primary/50 focus:ring-2 focus:ring-primary/40"
          />
        </label>

        <label class="block">
          <span class="block text-[11px] font-medium uppercase tracking-[0.06em] text-base-content/45 mb-1">
            Chat
          </span>
          <input
            :value="workingChat.name"
            type="text"
            disabled
            class="input input-sm input-bordered w-full bg-base-200/60 text-base-content/50"
          />
        </label>

        <label class="block">
          <span class="block text-[11px] font-medium uppercase tracking-[0.06em] text-base-content/45 mb-1">
            Description <span class="normal-case font-normal text-base-content/35">(optional)</span>
          </span>
          <textarea
            v-model="browserSessionForm.description"
            placeholder="Add notes about this session..."
            class="textarea textarea-bordered textarea-sm w-full resize-none bg-base-100 focus:border-primary/50 focus:ring-2 focus:ring-primary/40"
            rows="3"
          ></textarea>
        </label>

        <div class="flex items-center justify-end gap-2 pt-1">
          <button type="button" class="btn btn-ghost btn-sm" @click="closeBrowserSessionDialog">
            Cancel
          </button>
          <button
            type="button"
            class="btn btn-primary btn-sm gap-1"
            :disabled="!browserSessionForm.name.trim() || isCreatingSession"
            @click="createBrowserSession"
          >
            <span v-if="isCreatingSession" class="loading loading-spinner loading-xs"></span>
            <i v-else class="fa-solid fa-globe" aria-hidden="true"></i>
            Create session
          </button>
        </div>
      </div>
    </modal>
  </aside>
</template>

<script>
export default {
  props: {
    workingChat: { type: Object, required: true },
    rootChat: { type: Object, required: true },
    allChats: { type: Array, default: () => [] },
    selectedChatId: { type: String, default: null },
    workingChatMode: { type: String, default: 'chat' },
    chatSearch: { type: String, default: null },
    isCompact: { type: Boolean, default: false },
    chatProfiles: { type: Array, default: () => [] },
    // Messenger / channel view: the sidebar stops listing task data (subtasks
    // tree, members, browser sessions, task actions). Everything is hidden with
    // CSS instead of removed so the sidebar keeps working for task chats.
    // Defaults to false: existing usages are untouched.
    channelMode: { type: Boolean, default: false },
    // Admin-only "dump chat" action (raw JSON snapshot for a postmortem).
    // The permission is resolved by the host (ChatView), the sidebar only
    // renders the entry point. Defaults to false so no existing usage gains
    // a new menu item.
    canDump: { type: Boolean, default: false }
  },
  emits: ['select', 'add-subtask', 'action', 'update-search', 'mode-changed', 'toggle-compact', 'delete-chat', 'remove-attachment'],
  data() {
    return {
      showBrowserDialog: false,
      isCreatingSession: false,
      isReloading: false,
      statusFilter: null,
      browserSessionForm: {
        name: '',
        description: ''
      }
    }
  },
  computed: {
    isRootSelected() {
      return !!this.rootChat?.id && this.selectedChatId === this.rootChat.id
    },
    // Working project of the root chat (its icon replaces the initials in the
    // compact rail). Read straight from the chat instead of pre-building a map
    // keyed by id — the previous lookup used the chat OBJECT as key and always
    // missed, so the project icon never showed.
    rootProject() {
      if (!this.rootChat) return null
      try {
        return this.$chats.getChatWorkingProject(this.rootChat) || null
      } catch {
        return null
      }
    },
    allNestedChats() {
      // Groups / channels have no task hierarchy: nothing to list
      if (this.channelMode) return []
      return this.$storex.chats.chatDescendants(this.rootChat.id).filter(chat => chat.id !== this.rootChat.id)
    },
    sortedAllNestedChats() {
      return [...this.allNestedChats].sort((a, b) => {
        const timeA = new Date(a.updated_at || a.created_at || 0).getTime()
        const timeB = new Date(b.updated_at || b.created_at || 0).getTime()
        return timeB - timeA
      })
    },
    filteredNestedChats() {
      if (!this.statusFilter) return this.sortedAllNestedChats
      // Chats without an explicit status default to 'todo' (store DEFAULT_STATUS)
      return this.sortedAllNestedChats.filter(chat => (chat.status || 'todo') === this.statusFilter)
    },
    statusCounts() {
      return this.allNestedChats.reduce((counts, chat) => {
        const status = chat.status || 'todo'
        counts[status] = (counts[status] || 0) + 1
        return counts
      }, {})
    },
    selectedChat() {
      return this.allChats.find(c => c.id === this.selectedChatId) || this.rootChat
    }
  },
  methods: {
    selectChat(chat) {
      this.$emit('select', chat)
    },
    setStatusFilter(status) {
      // Toggle: clicking the active status clears the filter
      this.statusFilter = this.statusFilter === status ? null : status
      document.activeElement?.blur()
    },
    getInitials(name) {
      if (!name) return 'CH'
      const cleanName = name.replace(/[^\w\s-]/g, '').trim()
      const words = cleanName.split(/\s+/)
      if (words.length >= 2) {
        return (words[0][0] + words[1][0]).toUpperCase()
      }
      return name.substring(0, 2).toUpperCase()
    },
    handleFooterAction(action) {
      this.$emit('action', action)
      // Close the dropdown after selecting an item
      this.$refs.actionsTrigger?.blur()
    },
    handleReload() {
      // Close the dropdown, then trigger reload
      this.$refs.actionsTrigger?.blur()
      this.reloadActiveChat()
    },
    async reloadActiveChat() {
      const chat = this.workingChat
      if (!chat?.id || this.isReloading) return

      this.isReloading = true
      try {
        await this.$storex.chats.reloadChat({
          id: chat.id,
          project_id: chat.project_id,
          owner_project_id: chat.owner_project_id
        })
      } catch (error) {
        console.error('[ChatSidebar] Error reloading chat:', error)
      } finally {
        this.isReloading = false
      }
    },
    openBrowserSessionDialog() {
      this.browserSessionForm = {
        name: `${this.workingChat.name} - Browser Session`,
        description: ''
      }
      this.showBrowserDialog = true
    },
    closeBrowserSessionDialog() {
      this.showBrowserDialog = false
      this.browserSessionForm = {
        name: '',
        description: ''
      }
      this.isCreatingSession = false
    },
    async createBrowserSession() {
      if (!this.browserSessionForm.name.trim()) return

      this.isCreatingSession = true
      try {
        const sessionData = {
          name: this.browserSessionForm.name,
          description: this.browserSessionForm.description,
          chat_id: this.workingChat.id
        }

        const session = await this.$storex.browsers.createSession(sessionData)
        this.closeBrowserSessionDialog()
        if (session?.id) {
          await this.$storex.browsers.runSession(session.id)
        }
      } catch (error) {
        console.error('[ChatSidebar] Error creating browser session:', error)
      } finally {
        this.isCreatingSession = false
      }
    }
  }
}
</script>