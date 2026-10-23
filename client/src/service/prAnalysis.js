import Service from './service'
import { ENTITY_STATUS } from '../store/entityStatuses'
import { extractCodeBlocks } from '../utils/codeBlockExtractor'
import {
  createPrFileIndex,
  extractDiffPaths,
  isSameContent,
  matchPrFile,
  normalizePath,
  toRepoRelative
} from '../utils/prFileMatcher'

/**
 * Evidence tiers used to decide whether a chat "affects" a PR.
 *
 * `weight` is the score a single hit grants; a chat's score is its BEST tier
 * plus a small bonus for corroborating tiers, so forty vague mentions can never
 * outrank the chat that wrote the current content of a file.
 */
export const PR_CHAT_SIGNALS = {
  // chat is explicitly linked to a file of the PR (`chat.file_list`)
  fileList: { weight: 100, label: 'File linked to the chat' },
  // a code block in the chat IS the current content of the file at `to`
  content: { weight: 90, label: 'Wrote the current content' },
  // a code block holds an older version of the file
  staleContent: { weight: 45, label: 'Wrote an older version' },
  // a ```diff block quotes the file
  diffQuote: { weight: 45, label: 'Quoted the diff' },
  // child of the PR review chat (today's `prChats` signal)
  prSubtask: { weight: 40, label: 'PR review subtask' },
  // a line comment recorded in the message metadata targets the file
  commentMeta: { weight: 35, label: 'Line comment on the file' },
  // the chat is configured with the same branch pair
  branchConfig: { weight: 20, label: 'Same branch configuration' },
  // the file path is merely mentioned in the text
  mention: { weight: 15, label: 'Mentions the file' }
}

export const PR_CHAT_THRESHOLDS = {
  confirmed: 35,
  probable: 15
}

// Hard guards: the client-side scan must never turn into a request storm
const MAX_CHATS = 60
const CONCURRENCY = 4
const MAX_MATCHES_PER_CHAT = 5
const WINDOW_SLACK_MS = 7 * 24 * 60 * 60 * 1000
const CACHE_SIZE = 6
const MAX_MENTION_PATHS = 200

/**
 * PR ↔ chat correlation.
 *
 * Ordering (mirrors the design decision: content beats timestamps):
 *
 *   cheap signals (no request)  →  prioritise + cap  →  load history (capped,
 *   concurrency 4)  →  scan code blocks / diffs / comments  →  score.
 *
 * File ownership: several chats may match the same file, but only one of them
 * produced its current state. Each match is stamped with the DATE OF THE
 * MESSAGE that carried it and, per file, the chat holding the most recent
 * match owns the file (`resolveFileOwners`). Chat-level recency (`updated_at`,
 * which also moves on renames/status/column edits) is never used for that.
 *
 * Content is read once per file per run (`repo.readFromBranch`, or
 * `files.read` when comparing against the working tree) and memoised.
 */
export class PrAnalysisService extends Service {
  constructor($storex) {
    super($storex)
    // cacheKey → result (LRU, small)
    this._cache = new Map()
  }

  cacheKey({ project, fromBranch, toBranch }) {
    const projectId = project?.project_id || project?.codx_path || 'project'
    const revision = this.$chats?.activityRevision || 0
    return `${projectId}:${fromBranch || ''}:${toBranch || ''}:${revision}`
  }

  clearCache() {
    this._cache.clear()
  }

  /**
   * @param {Object} options
   * @param {Object} options.project     project (with `$api`) the branches belong to
   * @param {string} options.fromBranch  source branch (left selector)
   * @param {string} options.toBranch    target branch (right selector, may be `local`)
   * @param {Object} options.repoChanges `repo.changes()` payload
   * @param {Object} [options.chat]      chat being reviewed (excluded from the scan)
   * @returns {Promise<{chats: Array, fileChats: Object, files: Array, stats: Object}>}
   */
  async findChatsForPR(options = {}) {
    const project = options.project || this.$project
    const { fromBranch, toBranch, repoChanges, chat = null, useCache = true } = options

    const empty = {
      chats: [],
      fileChats: {},
      files: [],
      stats: { candidates: 0, scanned: 0, truncated: false, windowStart: null, cached: false }
    }
    if (!project || !repoChanges?.branch_file_and_commits) return empty

    const cacheKey = this.cacheKey({ project, fromBranch, toBranch })
    if (useCache && this._cache.has(cacheKey)) {
      const cached = this._cache.get(cacheKey)
      return { ...cached, stats: { ...cached.stats, cached: true } }
    }

    const prFiles = this.buildPrFiles(repoChanges, project)
    if (!prFiles.length) return empty

    const repoPath = repoChanges.repo_path || project.abs_project_path || ''
    const index = createPrFileIndex(prFiles.map(file => file.path), repoPath, this.buildRenames(prFiles))
    if (!index.files.size) return empty

    const windowStart = this.windowStart(prFiles)
    const candidates = this.getCandidates({ project, chat })
    const context = {
      contentCache: new Map(),
      mentionRegex: this.buildMentionRegex(index)
    }

    // 1. Cheap pass — free signals only, no request
    const prepared = candidates.map(candidate => {
      const signals = {}
      const matched = new Set()
      const messageIds = []
      // file path → newest match (message date + evidence), one entry per file
      const fileMatches = new Map()
      const add = this.signalCollector(signals, matched, messageIds, fileMatches)
      this.collectFreeSignals({ chat: candidate, index, parentChatId: chat?.id, fromBranch, toBranch, add })
      return { chat: candidate, signals, matched, messageIds, fileMatches, add }
    })

    // 2. Prioritise (best free signal, then recency) and cap before any request
    prepared.sort((a, b) => this.priority(b) - this.priority(a) || this.chatTime(b.chat) - this.chatTime(a.chat))
    const selected = prepared.slice(0, MAX_CHATS)

    // 3. History + scan (bounded concurrency, one read per file)
    await this.runWithConcurrency(selected, CONCURRENCY, async item => {
      const loaded = await this.loadChatHistory(item.chat)
      if (!loaded) return
      await this.scanMessages({ chat: loaded, index, project, toBranch, context, add: item.add })
    })

    const chats = selected
      .map(item => this.buildResult(item))
      .filter(result => result.score >= PR_CHAT_THRESHOLDS.probable)
      .sort((a, b) => b.score - a.score || this.dateValue(b.updatedAt) - this.dateValue(a.updatedAt))

    // Which chat owns each file: the one whose matching message is the NEWEST.
    // `fileChats` is built before the per-chat file lists are narrowed, so it
    // keeps the full history of who touched a file and in which order.
    const fileChats = this.buildFileChats(chats)
    const owners = this.resolveFileOwners(chats)

    chats.forEach(chatResult => {
      chatResult.files = chatResult.files.filter(path => {
        const ownerId = owners.get(path)
        return !ownerId || ownerId === chatResult.id
      })
    })

    Object.entries(fileChats).forEach(([path, list]) => {
      const ownerId = owners.get(path) || null
      list.forEach(entry => { entry.owner = !!ownerId && entry.id === ownerId })
    })

    const result = {
      chats,
      fileChats,
      // Diffs are dropped: the viewer already owns them
      files: prFiles.map(({ diff, ...rest }) => rest),
      stats: {
        candidates: candidates.length,
        scanned: selected.length,
        truncated: prepared.length > MAX_CHATS,
        windowStart,
        cached: false
      }
    }

    this.remember(cacheKey, result)
    return result
  }

  // ── PR files ──────────────────────────────────────────────────────────────

  buildPrFiles(repoChanges, project) {
    const repoPath = String(repoChanges?.repo_path || project?.abs_project_path || '').replace(/\/+$/, '')
    const entries = repoChanges?.branch_file_and_commits || {}

    return Object.keys(entries).map(rawPath => {
      const entry = entries[rawPath] || {}
      const path = toRepoRelative(rawPath, repoPath) || normalizePath(rawPath)
      return {
        path,
        absPath: repoPath ? `${repoPath}/${path}` : path,
        diff: entry.diff || '',
        commits: Array.isArray(entry.commits) ? entry.commits : [],
        lastChangeDate: this.lastChangeDate(entry),
        isDeleted: /deleted file mode/.test(entry.diff || '')
      }
    })
  }

  /**
   * Authoring date of the file change: the newest commit date of the file.
   * `last_modification` is only a fallback — it is the checkout mtime, which a
   * fresh clone/worktree resets to "now".
   */
  lastChangeDate(entry) {
    const values = (entry?.commits || []).map(commit => commit?.date).filter(Boolean)
    if (entry?.last_modification) values.push(entry.last_modification)
    const times = values.map(value => new Date(value).getTime()).filter(time => !Number.isNaN(time))
    return times.length ? new Date(Math.max(...times)).toISOString() : null
  }

  /** Lower bound used to order candidates — never to conclude "affects" */
  windowStart(prFiles) {
    const times = prFiles
      .map(file => (file.lastChangeDate ? new Date(file.lastChangeDate).getTime() : NaN))
      .filter(time => !Number.isNaN(time))
    if (!times.length) return null
    return new Date(Math.min(...times) - WINDOW_SLACK_MS).toISOString()
  }

  /** `diff --git a/old b/new` where the names differ → rename map for the index */
  buildRenames(prFiles) {
    const renames = {}
    prFiles.forEach(file => {
      extractDiffPaths(file.diff).forEach(({ old, new: next }) => {
        if (old && next && old !== next) renames[old] = next
      })
    })
    return renames
  }

  // ── Candidates ────────────────────────────────────────────────────────────

  getCandidates({ project, chat }) {
    const projectId = project?.project_id
    const all = (this.$chats?.allChats || []).filter(item => item?.id && item.id !== chat?.id)
    if (!all.length) return []

    // The chats store is scoped to the active project: when the panel works on
    // another project, fall back to everything it holds instead of returning none.
    const owned = projectId
      ? all.filter(item => {
        const owner = item.owner_project_id || item.project_id
        return !owner || owner === projectId
      })
      : all

    return (owned.length ? owned : all).sort((a, b) => this.chatTime(b) - this.chatTime(a))
  }

  /** Free signals: available on the chat summary, no message history needed */
  collectFreeSignals({ chat, index, parentChatId, fromBranch, toBranch, add }) {
    // No message to date these hits: the chat's own recency is the best
    // available proxy, and a dated code-block match always outranks them.
    const at = this.chatDate(chat)

    ;(chat.file_list || []).forEach(filePath => {
      const match = matchPrFile(filePath, index)
      if (match) add('fileList', match.path, null, at)
    })

    if (parentChatId && chat.parent_id === parentChatId) add('prSubtask', null, null, at)

    const pullRequests = chat.pr_view?.pull_requests
    if (pullRequests) {
      const wanted = [fromBranch, toBranch].map(value => String(value || '').trim()).filter(Boolean)
      Object.values(pullRequests).forEach(config => {
        if (!config) return
        const configured = [config.fromBranch, config.toBranch].map(value => String(value || '').trim())
        if (configured.some(value => value && wanted.includes(value))) add('branchConfig', null, null, at)
      })
    }
  }

  /**
   * Collects the evidence of a chat.
   *
   * @param {string} name       signal key from PR_CHAT_SIGNALS
   * @param {string} [filePath] PR file the signal points at
   * @param {string} [messageId] message that produced the signal
   * @param {string} [at]       DATE OF THAT MESSAGE — decides file ownership
   */
  signalCollector(signals, matched, messageIds, fileMatches = new Map()) {
    return (name, filePath, messageId = null, at = null) => {
      const tier = PR_CHAT_SIGNALS[name]
      if (!tier) return
      if (!signals[name] || signals[name].weight < tier.weight) {
        signals[name] = { name, weight: tier.weight, label: tier.label }
      }
      if (filePath) matched.add(filePath)
      if (messageId && !messageIds.includes(messageId)) messageIds.push(messageId)
      if (filePath) {
        this.rememberFileMatch(fileMatches, {
          path: filePath,
          signal: name,
          weight: tier.weight,
          messageId,
          at
        })
      }
    }
  }

  /**
   * Keeps ONE match per file: the most recent one, because that is the message
   * that produced the current state of the file.
   *
   * Dated beats undated (a real message timestamp always wins over the chat
   * fallback); on the same date the stronger evidence wins.
   */
  rememberFileMatch(fileMatches, match) {
    const path = match?.path
    if (!path) return

    const candidate = { ...match, atTime: this.dateValue(match.at) }
    const previous = fileMatches.get(path)
    if (!previous || this.isNewerMatch(candidate, previous)) {
      fileMatches.set(path, candidate)
    }
  }

  isNewerMatch(candidate, previous) {
    if (candidate.atTime !== previous.atTime) return candidate.atTime > previous.atTime
    return candidate.weight > previous.weight
  }

  priority(item) {
    const weights = Object.values(item.signals).map(signal => signal.weight)
    return weights.length ? Math.max(...weights) : 0
  }

  // ── Message history ───────────────────────────────────────────────────────

  /**
   * Ensure the full message history is available. `loadChat` already coalesces
   * concurrent loads and skips chats whose full history is loaded and fresh.
   */
  async loadChatHistory(chat) {
    if (!chat?.id) return null
    try {
      const status = this.$chats.chatLoadingStatus(chat.id)
      if (status === ENTITY_STATUS.LOADED && !this.$chats.chatNeedsReload(chat.id)) {
        return this.$chats.allChats.find(item => item.id === chat.id) || chat
      }
      const loaded = await this.$chats.loadChat(chat)
      return loaded || chat
    } catch (error) {
      console.warn('[prAnalysis] Unable to load chat history', chat?.id, error)
      return null
    }
  }

  /**
   * Scan messages newest → oldest. Stops after MAX_MATCHES_PER_CHAT hits so a
   * long chat cannot monopolise the run.
   *
   * Every hit is stamped with the message date, so two chats matching the same
   * file can be ordered by WHEN they wrote it instead of by score.
   */
  async scanMessages({ chat, index, project, toBranch, context, add }) {
    const messages = Array.isArray(chat.messages) ? chat.messages : []
    let matches = 0

    for (let i = messages.length - 1; i >= 0 && matches < MAX_MATCHES_PER_CHAT; i--) {
      const message = messages[i] || {}
      const messageId = message.doc_id || message.id || null
      const at = this.messageDate(message)
      const content = message.content || ''

      // 1. line comments stored in the message metadata
      const commentFile = message.meta_data?.diff?.comment?.file || message.meta_data?.diff?.file
      if (commentFile) {
        const match = matchPrFile(commentFile, index)
        if (match) {
          add('commentMeta', match.path, messageId, at)
          matches++
        }
      }

      if (!content) continue

      // 2. fenced blocks carrying a file path (```py src/a.py / <file_change path="…">)
      for (const block of extractCodeBlocks(content)) {
        if (matches >= MAX_MATCHES_PER_CHAT) break

        if (block.language === 'diff' || block.language === 'patch') {
          const paths = extractDiffPaths(block.content)
          const hit = paths.map(entry => matchPrFile(entry.new || entry.old, index)).find(Boolean)
          if (hit) {
            add('diffQuote', hit.path, messageId, at)
            matches++
          }
          continue
        }

        const match = matchPrFile(block.filePath, index)
        if (!match) continue

        const current = await this.readFileAtBranch({ project, file: match, branch: toBranch, context })
        if (current === null) {
          // Content unavailable (deleted file, unreadable ref): the block still
          // proves the chat touched the file.
          add('staleContent', match.path, messageId, at)
        } else if (isSameContent(block.content, current)) {
          add('content', match.path, messageId, at)
        } else {
          add('staleContent', match.path, messageId, at)
        }
        matches++
      }

      // 3. bare path mentions — lowest tier, one regex pass per message
      if (matches < MAX_MATCHES_PER_CHAT && context.mentionRegex) {
        const found = content.match(context.mentionRegex) || []
        for (const mention of new Set(found)) {
          if (matches >= MAX_MATCHES_PER_CHAT) break
          const match = matchPrFile(mention, index)
          if (!match) continue
          add('mention', match.path, messageId, at)
          matches++
        }
      }
    }
  }

  /**
   * Date of the message that produced a signal. `updated_at` reflects a message
   * edit, so it wins over `created_at`; `timestamp` is the last fallback used
   * by the chats store.
   */
  messageDate(message) {
    if (!message) return null
    return message.updated_at || message.created_at || message.timestamp || message.date || null
  }

  /** Chat-level date used only when a signal has no message behind it */
  chatDate(chat) {
    return chat?.lastMessageAt || chat?.updated_at || chat?.last_message_at || null
  }

  /**
   * File content at `branch` (tracks the PR files' own repository/worktree).
   * Memoised per run: one request per file, not per chat.
   */
  async readFileAtBranch({ project, file, branch, context }) {
    const api = project?.$api
    if (!api || !file?.path) return null

    const key = `${project.project_id || ''}:${branch || ''}:${file.path}`
    if (context.contentCache.has(key)) return context.contentCache.get(key)

    const request = (async () => {
      try {
        if (!branch || branch === 'local') {
          const data = await api.files.read(file.absPath)
          return data?.content ?? data?.page_content ?? null
        }
        if (typeof api.repo?.readFromBranch !== 'function') return null
        const data = await api.repo.readFromBranch(file.absPath, branch)
        return data?.content ?? data?.page_content ?? null
      } catch (error) {
        return null
      }
    })()

    context.contentCache.set(key, request)
    return request
  }

  // ── Scoring / results ─────────────────────────────────────────────────────

  buildResult(item) {
    const weights = Object.values(item.signals).map(signal => signal.weight)
    const base = weights.length ? Math.max(...weights) : 0
    const bonus = Math.min(9, Math.max(0, weights.length - 1) * 3)
    const score = Math.min(100, base + bonus + this.recencyBonus(item.chat))

    // Newest match first: `fileMatches[0]` is the message that produced the
    // current state of the file this chat matched most recently.
    const fileMatches = Array.from(item.fileMatches.values())
      .map(({ path, signal, weight, messageId, at, atTime }) => ({ path, signal, weight, messageId, at, atTime }))
      .sort((a, b) => b.atTime - a.atTime || b.weight - a.weight)

    return {
      id: item.chat.id,
      name: item.chat.name || 'Untitled chat',
      mode: item.chat.mode || 'chat',
      parentId: item.chat.parent_id || null,
      updatedAt: item.chat.updated_at || item.chat.lastMessageAt || null,
      score,
      confirmed: score >= PR_CHAT_THRESHOLDS.confirmed,
      signals: Object.values(item.signals).sort((a, b) => b.weight - a.weight),
      files: Array.from(item.matched),
      fileMatches,
      // Newest matched message (null when the chat only matched by summary)
      latestMatchAt: fileMatches[0]?.at || null,
      messageId: item.messageIds[0] || fileMatches[0]?.messageId || null,
      messageIds: item.messageIds
    }
  }

  /**
   * file → chats that touched it. Each entry carries the date of the message
   * that matched it and is sorted newest first, so `list[0]` is the chat that
   * wrote the current state of the file.
   */
  buildFileChats(chats) {
    const result = {}

    chats.forEach(chat => {
      const matches = new Map((chat.fileMatches || []).map(match => [match.path, match]))
      const paths = new Set([...(chat.files || []), ...matches.keys()])

      paths.forEach(path => {
        if (!result[path]) result[path] = []
        if (result[path].some(item => item.id === chat.id)) return

        const match = matches.get(path) || null
        result[path].push({
          id: chat.id,
          name: chat.name,
          score: chat.score,
          confirmed: chat.confirmed,
          signals: chat.signals.map(signal => signal.name),
          signal: match?.signal || null,
          messageId: match?.messageId || chat.messageId || null,
          at: match?.at || null,
          atTime: match?.atTime || 0,
          owner: false
        })
      })
    })

    Object.values(result).forEach(list => {
      list.sort((a, b) => b.atTime - a.atTime || b.score - a.score)
    })

    return result
  }

  /**
   * path → id of the chat that owns it, i.e. the chat whose matching message is
   * the most recent one. Ties (same date) are broken by score, then chat date.
   */
  resolveFileOwners(chats) {
    const ranked = new Map()

    chats.forEach(chat => {
      const updatedAt = this.dateValue(chat.updatedAt)
      ;(chat.fileMatches || []).forEach(match => {
        const candidate = {
          chatId: chat.id,
          atTime: match.atTime || 0,
          score: chat.score,
          updatedAt
        }
        const current = ranked.get(match.path)
        if (!current || this.isBetterOwner(candidate, current)) {
          ranked.set(match.path, candidate)
        }
      })
    })

    const owners = new Map()
    ranked.forEach((value, path) => owners.set(path, value.chatId))
    return owners
  }

  isBetterOwner(candidate, current) {
    if (candidate.atTime !== current.atTime) return candidate.atTime > current.atTime
    if (candidate.score !== current.score) return candidate.score > current.score
    return candidate.updatedAt > current.updatedAt
  }

  recencyBonus(chat) {
    const time = this.chatTime(chat)
    if (!time) return 0
    const days = (Date.now() - time) / 86400000
    if (days <= 1) return 10
    if (days <= 7) return 6
    if (days <= 30) return 3
    return 0
  }

  chatTime(chat) {
    return this.dateValue(chat?.updated_at || chat?.lastMessageAt || chat?.last_message_at)
  }

  dateValue(value) {
    if (!value) return 0
    const time = new Date(value).getTime()
    return Number.isNaN(time) ? 0 : time
  }

  /** Regex matching any PR path inside a message (skipped for huge PRs) */
  buildMentionRegex(index) {
    const paths = Array.from(index.files.keys())
    if (!paths.length || paths.length > MAX_MENTION_PATHS) return null
    const escaped = paths
      .slice()
      .sort((a, b) => b.length - a.length)
      .map(path => path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    return new RegExp(escaped.join('|'), 'g')
  }

  // ── Utilities ─────────────────────────────────────────────────────────────

  async runWithConcurrency(items, limit, worker) {
    const queue = [...items]
    const runners = new Array(Math.min(limit, queue.length)).fill(null).map(async () => {
      while (queue.length) {
        const item = queue.shift()
        try {
          await worker(item)
        } catch (error) {
          console.warn('[prAnalysis] candidate failed', error)
        }
      }
    })
    await Promise.all(runners)
  }

  remember(key, result) {
    this._cache.set(key, result)
    while (this._cache.size > CACHE_SIZE) {
      const oldest = this._cache.keys().next().value
      this._cache.delete(oldest)
    }
  }
}