<template>
  <div class="flex flex-col gap-4 p-5 w-full">
    <!-- ─── Header ──────────────────────────────────────────────────────── -->
    <div class="flex items-start gap-3">
      <div class="w-9 h-9 rounded-lg bg-warning/15 text-warning flex items-center justify-center shrink-0">
        <i class="fa-solid fa-bug text-sm"></i>
      </div>
      <div class="flex-1 min-w-0">
        <h2 class="text-base font-semibold text-base-content leading-6">Dump chat</h2>
        <p class="text-xs text-base-content/60 leading-relaxed">
          Full JSON snapshot of
          <span class="font-medium text-base-content/80">{{ chat?.name || chat?.id }}</span>
          for a postmortem: every message (hidden included), metadata, files,
          child tasks, run and usage data.
        </p>
      </div>
      <button
        class="btn btn-ghost btn-sm btn-circle shrink-0 focus:ring-2 focus:ring-primary/50"
        @click="$emit('close')"
        aria-label="Close chat dump"
        title="Close"
      >
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>

    <!-- ─── Sensitivity notice ──────────────────────────────────────────── -->
    <div class="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/10 px-3 py-2">
      <i class="fa-solid fa-lock text-xs text-warning mt-0.5 shrink-0"></i>
      <p class="text-xs text-base-content/70 leading-relaxed">
        Admin only. The dump contains prompts, tool calls, token usage and
        internal file paths — treat it as sensitive data.
      </p>
    </div>

    <!-- ─── Snapshot stats ──────────────────────────────────────────────── -->
    <div class="flex flex-wrap items-center gap-1.5">
      <span class="badge badge-ghost badge-sm gap-1.5">
        <i class="fa-solid fa-message text-[10px]"></i>{{ stats.messages }} messages
      </span>
      <span v-if="stats.hidden" class="badge badge-ghost badge-sm gap-1.5 text-warning/80">
        <i class="fa-solid fa-eye-slash text-[10px]"></i>{{ stats.hidden }} hidden
      </span>
      <span v-if="includeChildren && stats.children" class="badge badge-ghost badge-sm gap-1.5">
        <i class="fa-solid fa-sitemap text-[10px]"></i>{{ stats.children }} child tasks
      </span>
      <span class="badge badge-ghost badge-sm gap-1.5">
        <i class="fa-solid fa-database text-[10px]"></i>{{ stats.size }}
      </span>
    </div>

    <!-- ─── Options ─────────────────────────────────────────────────────── -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-1">
      <label class="flex items-center gap-2.5 cursor-pointer rounded-lg px-2 py-2 text-xs text-base-content/70 hover:bg-base-content/5 transition-colors duration-150">
        <input type="checkbox" class="checkbox checkbox-xs checkbox-primary" v-model="includeHidden" />
        <span>Include hidden messages</span>
      </label>
      <label class="flex items-center gap-2.5 cursor-pointer rounded-lg px-2 py-2 text-xs text-base-content/70 hover:bg-base-content/5 transition-colors duration-150">
        <input type="checkbox" class="checkbox checkbox-xs checkbox-primary" v-model="includeChildren" />
        <span>Include child tasks</span>
      </label>
      <label class="flex items-center gap-2.5 cursor-pointer rounded-lg px-2 py-2 text-xs text-base-content/70 hover:bg-base-content/5 transition-colors duration-150">
        <input type="checkbox" class="checkbox checkbox-xs checkbox-primary" v-model="includeEnvironment" />
        <span>Include environment context</span>
      </label>
      <label class="flex items-center gap-2.5 cursor-pointer rounded-lg px-2 py-2 text-xs text-base-content/70 hover:bg-base-content/5 transition-colors duration-150">
        <input type="checkbox" class="checkbox checkbox-xs checkbox-primary" v-model="pretty" />
        <span>Pretty print (readable)</span>
      </label>
    </div>

    <!-- ─── Preview ─────────────────────────────────────────────────────── -->
    <div class="flex flex-col gap-1.5 min-h-0">
      <div class="flex items-center justify-between gap-2 text-xs text-base-content/50">
        <span>Preview</span>
        <span v-if="previewTruncated" class="text-warning/80">
          truncated · {{ stats.size }} total
        </span>
      </div>
      <pre
        class="bg-base-300/50 border border-base-content/10 rounded-lg p-3 text-[11px] leading-relaxed font-mono overflow-auto text-base-content/70 max-h-64 whitespace-pre"
        tabindex="0"
        aria-label="Chat dump preview"
      >{{ previewText }}</pre>
    </div>

    <!-- ─── Actions ─────────────────────────────────────────────────────── -->
    <div class="flex flex-wrap items-center gap-2 pt-3 border-t border-base-content/10">
      <button class="btn btn-ghost btn-sm mr-auto" @click="$emit('close')">Close</button>
      <button
        class="btn btn-sm gap-2 focus:ring-2 focus:ring-primary/50"
        :disabled="copying"
        @click="copyToClipboard"
      >
        <i :class="copied ? 'fa-solid fa-check text-success' : 'fa-solid fa-clipboard'"></i>
        {{ copied ? 'Copied' : 'Copy to clipboard' }}
      </button>
      <button
        class="btn btn-primary btn-sm gap-2 focus:ring-2 focus:ring-primary/50"
        @click="downloadJson"
      >
        <i class="fa-solid fa-file-arrow-down"></i>
        Download .json
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    chat: { type: Object, required: true },
    // Direct child tasks, supplied by the host so the dump does not need to
    // reach into the chats store. Falls back to the store when omitted.
    childrenChats: { type: Array, default: () => [] }
  },
  emits: ['close'],
  data() {
    return {
      includeHidden: true,
      includeChildren: true,
      includeEnvironment: true,
      pretty: true,
      copied: false,
      copying: false,
      // Frozen when the dialog opens, so toggling options while reading the
      // preview does not change the timestamp stamped into the dump.
      exportedAt: null
    }
  },
  created() {
    this.exportedAt = new Date().toISOString()
  },
  computed: {
    messages() {
      return this.chat?.messages || []
    },
    hiddenMessages() {
      return this.messages.filter(message => message?.hide).length
    },
    stats() {
      return {
        messages: this.messages.length,
        hidden: this.hiddenMessages,
        children: (this.childrenChats || []).length,
        size: this.formatBytes(this.json.length)
      }
    },
    dump() {
      return this.buildDump()
    },
    json() {
      try {
        return this.pretty ? JSON.stringify(this.dump, null, 2) : JSON.stringify(this.dump)
      } catch (error) {
        // A chat holding a non-serializable value must not break the dialog:
        // return a minimal, still useful manifest instead.
        return JSON.stringify({
          dump_version: 1,
          kind: 'chat',
          exported_at: this.exportedAt,
          serialization_error: String(error?.message || error),
          chat_id: this.chat?.id || null
        }, null, 2)
      }
    },
    previewLimit() {
      return 40000
    },
    previewTruncated() {
      return this.json.length > this.previewLimit
    },
    previewText() {
      if (!this.previewTruncated) return this.json
      return `${this.json.slice(0, this.previewLimit)}\n…`
    },
    fileName() {
      const slug = String(this.chat?.name || 'chat')
        .toLowerCase()
        .normalize('NFKD')
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/(^-|-$)/g, '')
        .slice(0, 40) || 'chat'
      const stamp = String(this.exportedAt || '')
        .replace(/[-:]/g, '')
        .replace(/\..+/, '')
        .replace('T', '-')
      return `chat-dump-${slug}-${stamp}.json`
    }
  },
  watch: {
    json() {
      this.copied = false
    }
  },
  methods: {
    // ─── Dump assembly ────────────────────────────────────────────────────
    buildDump() {
      const chat = this.chat || {}
      const allMessages = chat.messages || []
      const messages = this.includeHidden ? allMessages : allMessages.filter(message => !message?.hide)

      const dump = {
        dump_version: 1,
        kind: 'chat',
        exported_at: this.exportedAt,
        exporter: this.buildExporter(),
        summary: this.buildSummary(chat, allMessages, messages),
        chat: this.clone({ ...chat, messages }),
        notes: [
          'messages keep every stored field (role, content, meta, hide, tokens, timestamps)',
          'file contents are NOT included: file_list, profiles and attachments carry paths only',
          this.includeChildren ? 'child tasks are embedded with their own messages' : 'child tasks are omitted',
          `generated by codx-junior at ${this.exportedAt}`
        ]
      }

      if (this.includeChildren) dump.children = this.buildChildren(chat)
      if (this.includeEnvironment) dump.environment = this.buildEnvironment()
      dump.diagnostics = this.buildDiagnostics(chat, allMessages, messages)

      return dump
    },
    buildExporter() {
      const user = this.$storex?.user || null
      if (!user) return null
      return this.clone({
        id: user.id ?? user.user_id ?? null,
        email: user.email ?? user.username ?? null,
        admin: !!this.isAdminUser
      })
    },
    buildSummary(chat, allMessages, messages) {
      return {
        id: chat.id || null,
        name: chat.name || null,
        mode: chat.mode || null,
        status: chat.status || null,
        board: chat.board ?? null,
        column: chat.column ?? null,
        project_id: chat.project_id ?? null,
        owner_project_id: chat.owner_project_id ?? null,
        parent_id: chat.parent_id ?? null,
        message_id: chat.message_id ?? null,
        run_id: chat.run_id ?? null,
        run_status: chat.run_status ?? null,
        is_template: !!chat.is_template,
        created_at: chat.created_at ?? null,
        updated_at: chat.updated_at ?? null,
        messages: messages.length,
        hidden_messages: allMessages.filter(message => message?.hide).length,
        child_tasks: (this.childrenChats || []).length,
        profiles: chat.profiles || [],
        tags: chat.tags || [],
        files: (chat.file_list || []).length,
        cost: chat.cost ?? null,
        estimation_cost: chat.estimation_cost ?? null
      }
    },
    buildChildren(chat) {
      const children = (this.childrenChats || []).length
        ? this.childrenChats
        : (this.$chats?.chatChildren?.(chat.id) || [])
      return this.clone(children.filter(Boolean).map(child => ({
        id: child.id,
        name: child.name,
        mode: child.mode,
        status: child.status,
        child_index: child.child_index ?? null,
        message_id: child.message_id ?? null,
        run_id: child.run_id ?? null,
        created_at: child.created_at ?? null,
        updated_at: child.updated_at ?? null,
        cost: child.cost ?? null,
        messages: child.messages || []
      })))
    },
    buildEnvironment() {
      const location = typeof window !== 'undefined' ? window.location : null
      return {
        ui_mode: this.$ui?.isMobile ? 'mobile' : (this.$ui?.isDesktopMode ? 'desktop' : 'web'),
        is_mobile: !!this.$ui?.isMobile,
        route: location ? `${location.pathname}${location.search || ''}` : null,
        viewport: typeof window !== 'undefined' ? `${window.innerWidth}x${window.innerHeight}` : null,
        language: typeof navigator !== 'undefined' ? navigator.language : null,
        user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : null
      }
    },
    buildDiagnostics(chat, allMessages, messages) {
      const lastMessage = messages[messages.length - 1] || null
      return {
        role_counts: this.countBy(messages, message => message?.role || 'unknown'),
        hidden_messages: allMessages.filter(message => message?.hide).length,
        empty_messages: messages.filter(message => !String(message?.content || '').trim()).length,
        with_files: messages.filter(message => (message?.files || []).length).length,
        last_message_at: lastMessage?.created_at ?? lastMessage?.updated_at ?? null,
        has_run: !!chat.run_id,
        run: this.buildRun(chat)
      }
    },
    buildRun(chat) {
      if (!chat?.run_id) return null
      try {
        const run = this.$storex?.orchestration?.runById?.(chat.run_id)
        return run ? this.clone(run) : null
      } catch (error) {
        return null
      }
    },
    countBy(items, keyOf) {
      return items.reduce((acc, item) => {
        const key = keyOf(item)
        acc[key] = (acc[key] || 0) + 1
        return acc
      }, {})
    },
    // ─── Export actions ───────────────────────────────────────────────────
    downloadJson() {
      try {
        const blob = new Blob([this.json], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = this.fileName
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
        this.$ui?.addNotification?.({ text: `Chat dump saved as ${this.fileName}`, type: 'success' })
      } catch (error) {
        this.$ui?.addNotification?.({ text: `Could not save the dump: ${this.errorMessage(error)}`, type: 'error' })
      }
    },
    async copyToClipboard() {
      if (this.copying) return
      this.copying = true
      this.copied = false
      try {
        await this.writeClipboard(this.json)
        this.copied = true
        this.$ui?.addNotification?.({ text: 'Chat dump copied to clipboard', type: 'success' })
        setTimeout(() => { this.copied = false }, 2500)
      } catch (error) {
        this.$ui?.addNotification?.({ text: `Could not copy the dump: ${this.errorMessage(error)}`, type: 'error' })
      } finally {
        this.copying = false
      }
    },
    // Clipboard API first; the textarea path keeps copy working on insecure
    // contexts (plain http) and when the permission is denied.
    async writeClipboard(text) {
      if (navigator.clipboard?.writeText) {
        try {
          await navigator.clipboard.writeText(text)
          return
        } catch (error) {
          // fall through to the legacy path
        }
      }
      const area = document.createElement('textarea')
      area.value = text
      area.setAttribute('readonly', '')
      area.style.position = 'fixed'
      area.style.top = '-1000px'
      area.style.opacity = '0'
      document.body.appendChild(area)
      area.select()
      const copied = document.execCommand('copy')
      document.body.removeChild(area)
      if (!copied) throw new Error('clipboard unavailable in this browser')
    },
    // ─── Helpers ──────────────────────────────────────────────────────────
    clone(value) {
      try {
        return JSON.parse(JSON.stringify(value))
      } catch (error) {
        return value
      }
    },
    formatBytes(bytes) {
      if (!bytes) return '0 B'
      const units = ['B', 'KB', 'MB', 'GB']
      let value = bytes
      let index = 0
      while (value >= 1024 && index < units.length - 1) {
        value /= 1024
        index++
      }
      return `${index === 0 ? value : value.toFixed(1)} ${units[index]}`
    },
    errorMessage(error) {
      return error?.message || String(error)
    }
  }
}
</script>