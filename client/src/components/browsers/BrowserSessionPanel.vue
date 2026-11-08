<script>
import BrowserViewer from './BrowserViewer.vue'
import Chat from '@/components/chat/Chat.vue'
import ConfirmDialog from '../ConfirmDialog.vue'
import VerticalSplitter from '../layout/VerticalSplitter.vue'
import { broadcastBrowserCollab } from '@/utils/browserCollab'

export default {
  name: 'BrowserSessionPanel',
  components: { BrowserViewer, Chat, ConfirmDialog, VerticalSplitter },
  props: {
    // Present when the panel is rendered inside a meeting call. It enables
    // collaborative annotations and the "share with call" action.
    meetId: { type: String, default: null }
  },
  data() {
    return {
      editFormData: {},
      saving: false,
      showChat: false,
      chatLoading: false,
      browserChatId: null,
      showChatMenu: false,
      showChatPicker: false,
      pickerLoading: false,
      pickerChats: [],
      pickerSearch: '',
      pickerError: null,
      // Why the selector was opened instead of a chat (no linked chat, stale
      // link, backend error). Rendered inside the dialog so the user is never
      // left wondering why a click did not open a chat.
      pickerReason: null,
      showDeleteConfirm: false,
      deleting: false
    }
  },
  computed: {
    selectedSession() {
      return this.$storex.browsers.selectedSession
    },
    selectedSessionId() {
      return this.selectedSession?.id || null
    },
    editingSessionId() {
      return this.$storex.browsers.editingSessionId
    },
    isEditing() {
      return this.editingSessionId !== null
    },
    isMobile() {
      return this.$storex.ui.isMobile
    },
    chatLabel() {
      const chats = this.selectedSession?.chat_ids || []
      return chats.length ? `${chats.length} chat(s)` : 'No chat linked'
    },
    browserChat() {
      return this.browserChatId ? this.$storex.chats.chats[this.browserChatId] : null
    },
    browserChatHasTools() {
      return (this.browserChat?.profiles || []).includes('browser')
    },
    linkedChatIds() {
      return this.selectedSession?.chat_ids || []
    },
    linkedChats() {
      return this.linkedChatIds.map((id) => {
        const chat = this.pickerChats.find(item => item.id === id) ||
          this.$storex.chats.chats[id]
        return chat || { id, name: `Chat ${String(id).slice(0, 8)}` }
      })
    },
    // Chats of this session, most recent FIRST by last updated message. This is
    // both what the header switcher lists and where the chat opened by default
    // comes from: "latest" means the chat whose last message is the newest.
    linkedChatOptions() {
      return this.linkedChatIds
        .map((id, index) => {
          const chat = this.chatMetaById(id)
          const stamp = this.chatLastMessageAt(chat)
          return {
            id,
            index,
            name: chat?.name || `Chat ${String(id).slice(0, 8)}`,
            updatedLabel: this.formatChatDate(stamp),
            time: this.chatTimestamp(stamp)
          }
        })
        // Chats without a known message keep the session order: the backend
        // appends every chat it links, so the newest id comes last.
        .sort((a, b) => (b.time - a.time) || (b.index - a.index))
    },
    latestLinkedChatId() {
      return this.linkedChatOptions[0]?.id || null
    },
    activeChatLabel() {
      const chat = this.browserChat
      if (chat) return chat.name || 'Untitled chat'
      return this.chatLoading ? 'Opening chat…' : 'Chat with this browser'
    },
    filteredPickerChats() {
      const term = (this.pickerSearch || '').trim().toLowerCase()
      const matches = term
        ? this.pickerChats.filter(chat =>
            String(chat.name || '').toLowerCase().includes(term) ||
            String(chat.description || '').toLowerCase().includes(term)
          )
        : this.pickerChats
      // The list can contain thousands of chats; render a bounded slice.
      return matches.slice(0, 100)
    }
  },
  watch: {
    editingSessionId: {
      immediate: true,
      handler(newId) {
        if (newId) {
          const session = this.$storex.browsers.sessionById(newId)
          if (session) {
            this.editFormData = { id: session.id, name: session.name }
          }
        } else {
          this.editFormData = {}
        }
      }
    },
    selectedSessionId(newId, oldId) {
      if (newId === oldId) return
      this.showChat = false
      this.showChatMenu = false
      this.showChatPicker = false
      this.pickerReason = null
      // A pending confirmation belongs to the session that opened it
      this.showDeleteConfirm = false
      this.browserChatId = null
    }
  },
  methods: {
    async handleSaveSession() {
      if (!this.editFormData.name?.trim()) {
        this.$storex.ui.addNotification({
          text: 'Session name is required',
          type: 'warning'
        })
        return
      }

      this.saving = true
      try {
        await this.$storex.browsers.updateSession(this.editFormData)
      } catch (error) {
        console.error('Failed to save session:', error)
      } finally {
        this.saving = false
      }
    },
    handleCancelEdit() {
      this.$storex.browsers.stopEditingSession()
      this.editFormData = {}
    },
    startEditingSession() {
      if (this.selectedSession?.id) {
        this.$storex.browsers.startEditingSession(this.selectedSession.id)
      }
    },
    handleDeleteSession() {
      if (!this.selectedSession?.id) return
      // Destructive: never delete on a single click, ask in a modal first
      this.showDeleteConfirm = true
    },
    cancelDelete() {
      if (this.deleting) return
      this.showDeleteConfirm = false
    },
    async confirmDeleteSession() {
      const sessionId = this.selectedSession?.id
      if (!sessionId || this.deleting) return

      this.deleting = true
      try {
        await this.$storex.browsers.deleteSession(sessionId)
        this.showDeleteConfirm = false
      } catch (error) {
        console.error('Failed to delete session:', error)
      } finally {
        this.deleting = false
      }
    },
    async handleRestartSession() {
      if (!this.selectedSession?.id) return
      try {
        await this.$storex.browsers.restartSession(this.selectedSession.id)
      } catch (error) {
        console.error('Failed to restart session:', error)
      }
    },
    // ── Chat switching ─────────────────────────────────────────────────────

    /** Metadata of a chat: fetched index first, then the store cache. */
    chatMetaById(chatId) {
      if (!chatId) return null
      return this.pickerChats.find(chat => chat.id === chatId) ||
        this.$storex.chats.chats[chatId] ||
        null
    },
    /** Timestamp as a number, 0 when missing/unparseable (so sorting is stable). */
    chatTimestamp(stamp) {
      if (!stamp) return 0
      const time = new Date(stamp).getTime()
      return Number.isNaN(time) ? 0 : time
    },
    /**
     * Stamp of the chat's last UPDATED message — what "latest" is measured on.
     * A full chat carries every message, a list/search summary only carries the
     * last one, so the newest message wins in both cases. Edited messages are
     * taken into account through their `updated_at`.
     */
    chatLastMessageAt(chat) {
      if (!chat) return null
      const messages = Array.isArray(chat.messages) ? chat.messages : []
      let latestStamp = null
      let latestTime = 0
      messages.forEach((message) => {
        const stamp = message?.updated_at || message?.timestamp || message?.created_at
        const time = this.chatTimestamp(stamp)
        if (time > latestTime) {
          latestTime = time
          latestStamp = stamp
        }
      })
      if (latestStamp) return latestStamp
      // Chat without messages loaded: fall back to its own bookkeeping fields.
      return chat.lastMessageAt || chat.updated_at || chat.created_at || null
    },
    /**
     * Id of the chat with the last updated message. Null when the session has
     * no chat linked (or none of them could be resolved), so the caller opens
     * the chat selector instead of letting the backend invent a chat.
     */
    async resolveLatestChatId() {
      const ids = [...this.linkedChatIds]
      if (!ids.length) return null
      // Ranking (and the switcher labels) need the metadata of every linked
      // chat. The store only holds the chats already opened here, so the index
      // is fetched once when any of them is still unknown.
      if (ids.some(id => !this.chatMetaById(id))) {
        await this.loadPickerChats()
      }
      return this.latestLinkedChatId
    },
    /**
     * Footer "Chat": dock the pane with the chat holding the last updated
     * message (focusing it when already open). When no chat can be resolved the
     * selector opens, so the user picks one or creates it — never a silent one.
     */
    async openLatestChat() {
      if (!this.selectedSession?.id || this.chatLoading) return
      if (this.showChat && this.browserChatId && !this.isMobile) {
        this.focusChat()
        return
      }
      await this.openChatWith({ latest: true })
    },
    focusChat() {
      this.showChat = true
      this.$nextTick(() => {
        // The composer is the only textarea the docked chat renders.
        const input = this.$refs.chatPane?.querySelector('textarea')
        if (input) input.focus()
      })
    },
    toggleChatMenu() {
      if (this.showChatMenu) {
        this.showChatMenu = false
        return
      }
      this.showChatMenu = true
      // The menu lists the session chats with their last-activity label, so the
      // metadata must be there before it is rendered.
      if (this.linkedChatIds.some(id => !this.chatMetaById(id))) {
        this.loadPickerChats()
      }
    },
    closeChatMenu() {
      this.showChatMenu = false
    },
    switchChat(chatId) {
      this.showChatMenu = false
      if (!chatId || chatId === this.browserChatId) {
        if (chatId) this.focusChat()
        return
      }
      this.openChatWith({ chatId })
    },
    newChatFromMenu() {
      this.showChatMenu = false
      this.createNewBrowserChat()
    },
    browseChatsFromMenu() {
      this.showChatMenu = false
      this.openChatPicker()
    },
    handleDocumentMousedown(event) {
      if (!this.showChatMenu) return
      const menu = this.$refs.chatMenu
      const title = this.$refs.chatMenuTrigger
      const switcher = this.$refs.chatSwitchTrigger
      if (menu?.contains(event.target) ||
          title?.contains(event.target) ||
          switcher?.contains(event.target)) return
      this.showChatMenu = false
    },
    handleWindowKeydown(event) {
      if (event.key === 'Escape' && this.showChatMenu) {
        this.showChatMenu = false
      }
    },

    // ── Chat picker / opening ──────────────────────────────────────────────

    /**
     * Open the chat selector.
     *
     * This is the single fallback for every "no chat could be opened" path: the
     * selector is the only place where the user can link an existing chat or
     * create a new one, so a failed click must always end here.
     */
    promptChatSelection(reason = null) {
      if (!this.selectedSession?.id) return
      this.pickerReason = reason
      this.showChat = false
      this.showChatPicker = true
      this.loadPickerChats()
    },
    openChatPicker() {
      if (!this.selectedSession?.id) return
      this.showChatMenu = false
      this.promptChatSelection()
    },
    closeChatPicker() {
      this.showChatPicker = false
      this.pickerReason = null
    },
    async loadPickerChats() {
      if (this.pickerLoading) return
      this.pickerLoading = true
      this.pickerError = null
      try {
        const project = this.$storex.projects.activeProject
        const api = project?.$api
        if (api?.chats?.list) {
          const response = await api.chats.list()
          const chats = Array.isArray(response) ? response : (response?.chats || [])
          // Same ordering rule as the switcher: newest last updated message first
          this.pickerChats = [...chats].sort((a, b) =>
            this.chatTimestamp(this.chatLastMessageAt(b)) -
            this.chatTimestamp(this.chatLastMessageAt(a))
          )
        } else {
          this.pickerChats = this.$storex.chats.allChats || []
        }
      } catch (error) {
        console.error('Failed to load chats for the picker:', error)
        this.pickerError = error.message || 'Could not load chats'
        this.pickerChats = this.$storex.chats.allChats || []
      } finally {
        this.pickerLoading = false
      }
    },
    /**
     * Open a chat in the docked pane.
     *
     * `latest` resolves the chat with the last updated message. The selector
     * opens whenever no chat can be opened — no linked chat, a linked chat that
     * was deleted (404) or a backend that returned nothing — so the user always
     * decides between an existing chat and a new one, and the button never
     * appears to do nothing.
     */
    async onAskAiAboutPage(context = {}) {
      if (!this.selectedSession?.id) return
      try {
        if (!this.showChat || !this.browserChatId) {
          await this.openChatWith({ latest: true })
        }
        if (!this.browserChatId) {
          // openChatWith opened the picker because no chat was linked.
          return
        }
        await this.$nextTick()
        const chat = this.$refs.browserChat
        if (!chat?.setEditorText) {
          this.$storex.ui.addNotification({
            text: 'Open the browser chat to ask the AI about this page',
            type: 'info'
          })
          return
        }
        const lines = ['I am looking at this page in the shared browser:']
        if (context.url) lines.push(`URL: ${context.url}`)
        if (context.title) lines.push(`Title: ${context.title}`)
        if (context.selection) lines.push(`Selected text: "${String(context.selection).slice(0, 600)}"`)
        if (context.active?.name || context.active?.text) {
          lines.push(`I was editing: ${context.active.name || context.active.text}`)
        }
        lines.push('', 'Please help me with: ')
        chat.setEditorText(lines.join('\n'))
        this.focusChat()
      } catch (error) {
        console.error('[BrowserSessionPanel] Could not prepare the AI question:', error)
        this.$storex.ui.addNotification({
          text: error.message || 'Could not prepare the question',
          type: 'error'
        })
      }
    },
    /**
     * Add an annotated browser screenshot to the session chat.
     *
     * The image and the textual description of every mark are inserted into the
     * composer (not sent immediately), so the user can add context or edit the
     * request before the AI receives it.
     */
    async onSendAnnotations(payload = {}) {
      if (!payload?.dataUrl) return
      try {
        if (!this.showChat || !this.browserChatId) {
          const latestChatId = await this.resolveLatestChatId()
          if (latestChatId) {
            await this.openChatWith({ chatId: latestChatId })
          } else {
            await this.openChatWith({ createNew: true })
          }
        }
        await this.$nextTick()
        const chat = this.$refs.browserChat
        if (!chat?.addAttachmentFromDataUrl) {
          this.downloadAnnotations(payload)
          return
        }
        const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
        const fileName = `browser-annotations-${stamp}.png`
        const attachment = await chat.addAttachmentFromDataUrl(payload.dataUrl, fileName)
        if (!attachment) {
          this.downloadAnnotations(payload)
          return
        }
        const lines = [
          'I annotated the shared browser page to give you visual instructions.',
          'The annotated screenshot is attached to this message.'
        ]
        if (payload.pageUrl) lines.push(`URL: ${payload.pageUrl}`)
        if (payload.pageTitle) lines.push(`Title: ${payload.pageTitle}`)
        if (['none', 'error'].includes(payload.captureKind)) {
          lines.push('(The live page screenshot could not be captured; rely on the URL and the notes below.)')
        }
        if (payload.summary) {
          lines.push('', 'What the drawing shows:', payload.summary)
        }
        lines.push(
          '',
          'Use the attached image together with these notes as the instructions for what to do on the page.'
        )
        const existing = chat.getEditorText?.() || ''
        chat.setEditorText(existing ? `${existing}\n\n${lines.join('\n')}` : lines.join('\n'))
        this.focusChat()
        this.$storex.ui.addNotification({
          text: 'Annotated screenshot added to the chat — review it and send.',
          type: 'success'
        })
      } catch (error) {
        console.error('[BrowserSessionPanel] Could not send annotations:', error)
        this.downloadAnnotations(payload)
      }
    },
    downloadAnnotations(payload) {
      try {
        const link = document.createElement('a')
        const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
        link.href = payload.dataUrl
        link.download = `browser-annotations-${stamp}.png`
        document.body.appendChild(link)
        link.click()
        link.remove()
        this.$storex.ui.addNotification({
          text: 'The chat is unavailable, so the annotated image was downloaded.',
          type: 'warning'
        })
      } catch (error) {
        this.$storex.ui.addNotification({
          text: error.message || 'Could not prepare the annotated image',
          type: 'error'
        })
      }
    },
    /**
     * Announce the session in the meeting. Peers receive it over the WebRTC
     * data channel and can open the same VNC view, sharing the page and the
     * annotation layer.
     */
    onShareSession(session = {}) {
      if (!this.meetId || !session.sessionId) return
      const user = this.$storex.users?.user || {}
      broadcastBrowserCollab(this.meetId, {
        kind: 'browser-session',
        sessionId: session.sessionId,
        sessionName: session.name || 'Browser session',
        pageUrl: session.url || '',
        pageTitle: session.title || '',
        user: {
          username: user.username || 'guest',
          name: user.name || user.username || 'Guest',
          avatar: user.avatar || ''
        }
      })
      this.$storex.ui.addNotification({
        text: `Browser session "${session.name || 'session'}" shared with the call`,
        type: 'success'
      })
    },

    async openChatWith({ chatId = null, createNew = false, latest = false } = {}) {
      if (!this.selectedSession?.id || this.chatLoading) return
      this.chatLoading = true
      try {
        const targetChatId = latest ? await this.resolveLatestChatId() : chatId

        if (!targetChatId && !createNew) {
          // No chat found → let the user choose
          this.promptChatSelection(
            this.linkedChatIds.length
              ? 'The chat linked to this session is no longer available.'
              : null
          )
          return
        }

        this.showChatPicker = false
        this.pickerReason = null
        const chat = await this.$storex.browsers.ensureChat({
          sessionId: this.selectedSession.id,
          chatId: targetChatId,
          createNew
        })

        if (!chat?.id) {
          // The backend returned no chat: offer the selection instead of
          // docking an empty pane the user cannot use.
          this.promptChatSelection('No chat could be opened for this session.')
          return
        }

        this.browserChatId = chat.id
        this.showChat = true
      } catch (error) {
        console.error('Failed to open browser chat:', error)
        // A linked chat that no longer exists must not be a dead end: fall back
        // to the selector, which is where the chat can be linked or created.
        const status = error?.response?.status
        this.promptChatSelection(
          status === 404
            ? 'That chat no longer exists. Pick another one or create a new chat.'
            : 'The chat could not be opened. Pick another one or create a new chat.'
        )
        this.$storex.ui.addNotification({
          text: error.message || 'Failed to open the browser chat',
          type: 'error'
        })
      } finally {
        this.chatLoading = false
      }
    },
    selectPickerChat(chat) {
      if (!chat?.id) return
      this.openChatWith({ chatId: chat.id })
    },
    createNewBrowserChat() {
      this.openChatWith({ createNew: true })
    },
    closeChat() {
      this.showChat = false
      this.showChatMenu = false
    },
    formatChatDate(value) {
      if (!value) return ''
      try {
        return new Date(value).toLocaleString()
      } catch (e) {
        return value
      }
    },
    formatDate(value) {
      if (!value) return ''
      try {
        return new Date(value).toLocaleString()
      } catch (e) {
        return value
      }
    }
  },
  mounted() {
    document.addEventListener('mousedown', this.handleDocumentMousedown)
    window.addEventListener('keydown', this.handleWindowKeydown)
  },
  beforeUnmount() {
    document.removeEventListener('mousedown', this.handleDocumentMousedown)
    window.removeEventListener('keydown', this.handleWindowKeydown)
  },
  inject: ['$storex']
}
</script>

<template>
  <div class="flex flex-col h-full bg-base-100 overflow-hidden">
    <!-- Empty State -->
    <div v-if="!selectedSession && !isEditing" class="flex items-center justify-center h-full text-base-content/50">
      <div class="text-center">
        <i class="fa-regular fa-compass text-4xl mb-3 block opacity-25"></i>
        <p class="text-sm">Select a session to co-browse</p>
        <p class="text-xs opacity-60 mt-1">The AI and you control the same browser.</p>
      </div>
    </div>

    <!-- Edit Mode -->
    <div v-else-if="isEditing" class="flex flex-col h-full">
      <div class="sticky top-0 bg-base-100 border-b border-base-content/10 p-4">
        <h3 class="text-lg font-bold">Rename Session</h3>
      </div>
      <div class="p-4 space-y-4 flex-1">
        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">Session Name *</span>
          </label>
          <input
            v-model="editFormData.name"
            type="text"
            placeholder="Session name"
            class="input input-bordered"
            @keyup.enter="handleSaveSession"
          />
        </div>
        <p class="text-xs opacity-60">
          The session id and browser state do not change when renaming.
        </p>
      </div>
      <div class="border-t border-base-content/10 p-4 flex gap-2">
        <button
          @click="handleSaveSession"
          class="btn btn-success flex-1"
          :disabled="saving"
        >
          <span v-if="saving" class="loading loading-spinner loading-sm"></span>
          <i v-else class="fa-solid fa-save"></i>
          Save
        </button>
        <button @click="handleCancelEdit" class="btn btn-ghost flex-1" :disabled="saving">
          Cancel
        </button>
      </div>
    </div>

    <!-- Co-browsing view + optional chat with the shared browser.
         ONE splitter owns the layout: left = live browser, right = the session
         chat. `show-right` removes the chat pane (and its drag handle) while no
         chat is open, so the live view takes the full width instead of leaving
         an empty column. On mobile there is no splitter: one pane at a time. -->
    <template v-else>
      <VerticalSplitter
        class="flex-1 min-h-0"
        :split="!isMobile"
        show-handle
        persist-key="browsers.session.chat"
        :show-left="!isMobile || !showChat"
        :show-right="showChat"
        :panels="{
          left: { minSize: 35, defaultSize: 68, class: 'h-full' },
          right: { minSize: 25, defaultSize: 32, class: 'h-full' }
        }"
      >
        <template #left>
          <div class="h-full min-w-0 min-h-0">
            <BrowserViewer
              :session="selectedSession"
              :meet-id="meetId"
              @ask-ai="onAskAiAboutPage"
              @send-annotations="onSendAnnotations"
              @share-session="onShareSession"
            />
          </div>
        </template>

        <template #right>
          <div ref="chatPane" class="h-full min-h-0 flex flex-col bg-base-100 border-base-content/10 md:border-l">
            <div class="flex items-center gap-2 px-3 py-2 border-b border-base-content/10 bg-base-200/70 flex-shrink-0">
              <button v-if="isMobile" class="btn btn-xs btn-ghost btn-circle" @click="closeChat" title="Back">
                <i class="fa-solid fa-arrow-left"></i>
              </button>
              <i class="fa-regular fa-comments text-primary"></i>

              <!-- Chat identity: the pane opens the session's latest chat, and
                   both this title and the switch icon below open the switcher. -->
              <div class="min-w-0 flex-1 relative">
                <button
                  ref="chatMenuTrigger"
                  class="flex items-center gap-1 min-w-0 max-w-full rounded px-1 -mx-1 py-0.5 text-left hover:bg-base-content/5 focus:outline-none focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary transition-colors duration-150"
                  :aria-expanded="showChatMenu ? 'true' : 'false'"
                  aria-haspopup="menu"
                  title="Change chat"
                  @click="toggleChatMenu"
                >
                  <span class="text-sm font-semibold leading-tight truncate">{{ activeChatLabel }}</span>
                  <i
                    class="fa-solid fa-chevron-down text-[9px] opacity-50 flex-shrink-0 transition-transform duration-150"
                    :class="showChatMenu && 'rotate-180'"
                    aria-hidden="true"
                  ></i>
                </button>
                <p class="text-[11px] opacity-60 truncate">{{ selectedSession.name }}</p>

                <!-- Menu: chats of this session, newest last-updated message first -->
                <div
                  v-if="showChatMenu"
                  ref="chatMenu"
                  class="absolute left-0 top-full z-40 mt-1 w-72 max-w-[calc(100vw-2rem)] rounded-lg border border-base-content/10 bg-base-200 shadow-xl p-1"
                  role="menu"
                  aria-label="Chats of this session"
                >
                  <p class="flex items-center justify-between gap-2 px-2 py-1 text-[10px] font-bold uppercase tracking-wide opacity-50">
                    <span>Chats of this session</span>
                    <span v-if="linkedChatOptions.length">{{ linkedChatOptions.length }}</span>
                  </p>

                  <div v-if="pickerLoading" class="flex items-center gap-2 px-2 py-1.5 text-xs opacity-70">
                    <span class="loading loading-spinner loading-xs"></span> Loading chats...
                  </div>

                  <div v-else class="max-h-64 overflow-y-auto">
                    <button
                      v-for="chat in linkedChatOptions"
                      :key="chat.id"
                      role="menuitem"
                      class="w-full flex items-center gap-2 px-2 py-1.5 rounded text-left hover:bg-base-300 focus:outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary transition-colors duration-150"
                      @click="switchChat(chat.id)"
                    >
                      <i
                        class="fa-regular fa-comments text-[10px] flex-shrink-0"
                        :class="chat.id === browserChatId ? 'text-primary' : 'opacity-40'"
                        aria-hidden="true"
                      ></i>
                      <span class="flex-1 min-w-0">
                        <span
                          class="block text-sm truncate"
                          :class="chat.id === browserChatId ? 'font-semibold text-primary' : 'text-base-content/80'"
                        >
                          {{ chat.name }}
                        </span>
                        <span class="block text-[10px] opacity-50 truncate">
                          {{ chat.updatedLabel || 'No activity yet' }}
                        </span>
                      </span>
                      <i
                        v-if="chat.id === browserChatId"
                        class="fa-solid fa-check text-[10px] text-primary flex-shrink-0"
                        aria-hidden="true"
                      ></i>
                    </button>

                    <p v-if="!linkedChatOptions.length" class="px-2 py-2 text-xs opacity-60">
                      No chat linked yet — pick one below.
                    </p>
                  </div>

                  <div class="my-1 border-t border-base-content/10"></div>
                  <button
                    role="menuitem"
                    class="w-full flex items-center gap-2 px-2 py-1.5 rounded text-sm text-left hover:bg-base-300 focus:outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary transition-colors duration-150"
                    @click="browseChatsFromMenu"
                  >
                    <i class="fa-solid fa-list text-[10px] opacity-60 w-3 text-center" aria-hidden="true"></i>
                    All chats…
                  </button>
                  <button
                    role="menuitem"
                    class="w-full flex items-center gap-2 px-2 py-1.5 rounded text-sm text-left hover:bg-base-300 focus:outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary transition-colors duration-150"
                    @click="newChatFromMenu"
                  >
                    <i class="fa-solid fa-plus text-[10px] opacity-60 w-3 text-center" aria-hidden="true"></i>
                    New chat
                  </button>
                </div>
              </div>

              <span
                class="badge badge-xs"
                :class="browserChatHasTools ? 'badge-success' : 'badge-ghost'"
                :title="browserChatHasTools ? 'Browser tools active' : 'Browser profile not active'"
              >
                {{ browserChatHasTools ? 'browser tools' : 'AI' }}
              </span>

              <!-- Switch chat: explicit affordance, icon first -->
              <button
                ref="chatSwitchTrigger"
                class="btn btn-xs btn-ghost btn-circle"
                :class="showChatMenu && 'btn-active'"
                title="Switch chat"
                aria-label="Switch chat"
                aria-haspopup="menu"
                :aria-expanded="showChatMenu ? 'true' : 'false'"
                :disabled="chatLoading"
                @click="toggleChatMenu"
              >
                <span v-if="chatLoading" class="loading loading-spinner loading-xs"></span>
                <i v-else class="fa-solid fa-arrow-right-arrow-left text-[11px]"></i>
              </button>
              <button class="btn btn-xs btn-ghost btn-circle" @click="closeChat" title="Close chat" aria-label="Close chat">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>
            <div class="flex-1 min-h-0">
              <Chat
                v-if="browserChat"
                ref="browserChat"
                :chat="browserChat"
                :hide-files-header="true"
              />
              <div v-else class="h-full flex items-center justify-center">
                <div class="text-center text-sm opacity-60">
                  <span v-if="chatLoading" class="loading loading-spinner loading-md block mx-auto mb-2"></span>
                  <span>{{ chatLoading ? 'Opening chat...' : 'Chat unavailable' }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>
      </VerticalSplitter>

      <div class="border-t border-base-content/10 px-3 py-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] opacity-70">
        <span><i class="fa-solid fa-comments mr-1"></i>{{ chatLabel }}</span>
        <span><i class="fa-regular fa-clock mr-1"></i>{{ formatDate(selectedSession.last_active) }}</span>
        <a
          v-if="selectedSession.vnc_url"
          :href="selectedSession.vnc_url"
          target="_blank"
          rel="noopener noreferrer"
          class="link link-hover"
        >
          <i class="fa-solid fa-up-right-from-square mr-1"></i>Live view
        </a>
        <span class="flex-1"></span>
        <button
          class="btn btn-xs btn-secondary"
          :disabled="chatLoading"
          :aria-busy="chatLoading ? 'true' : 'false'"
          :title="showChat
            ? 'Focus the chat input'
            : 'Open the chat with the last updated message, or pick one'"
          @click="openLatestChat"
        >
          <span v-if="chatLoading" class="loading loading-spinner loading-xs"></span>
          <i v-else class="fa-regular fa-comments"></i>
          <span>{{ showChat ? 'Focus chat' : 'Chat' }}</span>
        </button>
        <button class="btn btn-xs btn-ghost" @click="startEditingSession">
          <i class="fa-solid fa-pen"></i> Rename
        </button>
        <button class="btn btn-xs btn-ghost" @click="handleRestartSession">
          <i class="fa-solid fa-rotate"></i> Restart
        </button>
        <button class="btn btn-xs btn-ghost text-error" @click="handleDeleteSession">
          <i class="fa-solid fa-trash"></i> Delete
        </button>
      </div>
    </template>

    <!-- Chat selector: open an existing chat or create a new one.
         Rendered with the global <modal>, which re-parents itself to the app
         root on mount. A plain `div.modal` stays inside this panel, whose
         `overflow-hidden`/transformed ancestors (dockview panels) clipped or
         stacked it behind the panel — the dialog opened but could not be seen,
         which looked exactly like "clicking Chat does nothing". -->
    <modal
      v-if="showChatPicker"
      close
      title="Chat with this browser"
      @close="closeChatPicker"
    >
      <div class="flex flex-col gap-3 md:w-[34rem]">
        <p class="flex items-center gap-1.5 text-xs text-base-content/60 min-w-0">
          <i class="fa-solid fa-window-restore flex-shrink-0" aria-hidden="true"></i>
          <span class="truncate">{{ selectedSession?.name }}</span>
        </p>

        <!-- Why the selector opened instead of a chat -->
        <p
          v-if="pickerReason"
          role="status"
          class="flex items-start gap-1.5 rounded-lg bg-info/10 px-2.5 py-2 text-[11px] text-info"
        >
          <i class="fa-solid fa-circle-info mt-0.5 flex-shrink-0" aria-hidden="true"></i>
          <span class="min-w-0">{{ pickerReason }}</span>
        </p>

        <!-- Chats already linked to this session -->
        <div v-if="linkedChats.length" class="flex flex-col gap-1">
          <p class="text-[10px] font-bold uppercase tracking-wide opacity-50">Linked to this session</p>
          <div class="flex flex-wrap gap-1">
            <button
              v-for="chat in linkedChats"
              :key="chat.id"
              class="btn btn-xs btn-success"
              @click="selectPickerChat(chat)"
            >
              <i class="fa-regular fa-comments" aria-hidden="true"></i>
              {{ chat.name }}
            </button>
          </div>
        </div>

        <label class="flex flex-col gap-1">
          <span class="sr-only">Search existing chats</span>
          <input
            v-model="pickerSearch"
            type="search"
            class="input input-sm input-bordered w-full"
            placeholder="Search existing chats..."
          />
        </label>

        <div class="max-h-64 overflow-y-auto border border-base-content/10 rounded-lg divide-y divide-base-content/10">
          <div v-if="pickerLoading" class="p-6 flex items-center justify-center gap-2 text-sm opacity-70">
            <span class="loading loading-spinner loading-sm"></span> Loading chats...
          </div>
          <div v-else-if="filteredPickerChats.length === 0" class="p-6 text-center text-sm opacity-60">
            {{ pickerError || 'No chats found. Create a new one below.' }}
          </div>
          <button
            v-for="chat in filteredPickerChats"
            :key="chat.id"
            class="w-full text-left px-3 py-2 hover:bg-base-200 transition-colors duration-150"
            @click="selectPickerChat(chat)"
          >
            <div class="flex items-center gap-2">
              <i class="fa-regular fa-comments text-base-content/40" aria-hidden="true"></i>
              <span class="font-medium truncate flex-1">{{ chat.name || 'Untitled chat' }}</span>
              <span
                v-if="linkedChatIds.includes(chat.id)"
                class="badge badge-xs badge-success"
              >linked</span>
            </div>
            <div class="text-[11px] opacity-50 truncate mt-0.5">
              {{ chat.description || chat.board || '' }}
              <span v-if="chatLastMessageAt(chat)"> · {{ formatChatDate(chatLastMessageAt(chat)) }}</span>
            </div>
          </button>
        </div>
      </div>

      <template #footer>
        <button class="btn btn-sm btn-ghost" @click="closeChatPicker">Cancel</button>
        <button class="btn btn-sm btn-primary gap-1" :disabled="chatLoading" @click="createNewBrowserChat">
          <span v-if="chatLoading" class="loading loading-spinner loading-xs"></span>
          <i v-else class="fa-solid fa-plus" aria-hidden="true"></i>
          New chat
        </button>
      </template>
    </modal>

    <!-- Delete confirmation: a <modal> instead of window.confirm(), so the
         dialog is styled, focus-trapped, ESC/backdrop-closable and consistent
         with the confirmation used by the session list. -->
    <ConfirmDialog
      v-if="showDeleteConfirm && selectedSession"
      title="Delete session"
      :message="`Delete browser session '${selectedSession.name}'?`"
      :details="selectedSession.url ? [selectedSession.url] : []"
      hint="The session, its container and the live browser state will be removed. This cannot be undone."
      icon="fa-trash"
      icon-class="text-error"
      confirm-label="Delete"
      confirm-icon="fa-trash"
      confirm-class="btn-error"
      :busy="deleting"
      @confirm="confirmDeleteSession"
      @cancel="cancelDelete"
    />
  </div>
</template>