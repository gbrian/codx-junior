import moment from 'moment'
import { countUnreadMessages } from '@/utils/chatUnread'

// ─────────────────────────────────────────────────────────────────────────────
// Wall — pure helpers that turn codx-junior store data into feed posts.
//
// Everything here is a side-effect-free function so the mapping stays easy to
// reason about (and to unit-test) independently from the components.
// ─────────────────────────────────────────────────────────────────────────────

// Deterministic 0..n hash — used to pick a stable avatar colour per account
export function seedIndex(str) {
  let h = 0
  const s = String(str || '')
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return h
}

// daisyUI background classes used as deterministic avatar fallbacks.
// These are all dark enough for white text (warning/light neutrals are excluded
// on purpose so initials stay legible).
const AVATAR_CLASSES = ['bg-primary', 'bg-secondary', 'bg-accent', 'bg-info', 'bg-success', 'bg-neutral']

export function avatarClass(seed) {
  return AVATAR_CLASSES[seedIndex(seed) % AVATAR_CLASSES.length]
}

export function initials(name) {
  const words = String(name || '').trim().split(/\s+/).filter(Boolean)
  if (!words.length) return '?'
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase()
  return (words[0][0] + words[1][0]).toUpperCase()
}

export function formatRelative(iso) {
  const d = moment(iso)
  return d.isValid() ? d.fromNow() : ''
}

export function formatTime(iso) {
  const d = moment(iso)
  return d.isValid() ? d.format('MMM D, YYYY · HH:mm') : ''
}

export function formatCount(n) {
  n = Number(n) || 0
  if (n < 1000) return String(n)
  if (n < 1000000) return (n / 1000).toFixed(n < 10000 ? 1 : 0).replace(/\.0$/, '') + 'K'
  return (n / 1000000).toFixed(1) + 'M'
}

// The account used for every codx-junior generated event. It renders the project
// logo (the wall must never use any third-party brand icon/name).
export function botAccount() {
  return {
    id: 'codx-junior',
    name: 'codx-junior',
    handle: 'codx-junior',
    avatar: '/only_icon.png',
    verified: true,
    type: 'bot'
  }
}

export function meAccount(currentUser) {
  return {
    id: '__me',
    name: currentUser?.name || currentUser?.username || 'You',
    handle: currentUser?.username || 'you',
    avatar: currentUser?.avatar || null,
    verified: false,
    type: 'me'
  }
}

// Build the accounts referenced by the feed (current user + bot + users + projects).
//
// Accounts are indexed by EVERY identifier the stores expose (id, username,
// userName, project_id, project_name). A post stores its author as a bare id or
// username, so without these aliases a "username" author would silently fall
// back to the bot avatar — which is exactly the "user icon fails" symptom.
export function buildAccounts({ currentUser = null, users = [], projects = [] } = {}) {
  const accounts = { __me: meAccount(currentUser), 'codx-junior': botAccount() }

  const register = (id, account) => {
    if (!id) return
    const key = String(id)
    if (!accounts[key]) accounts[key] = account
  }

  ;(users || []).forEach(u => {
    const primaryId = u?.id || u?.username || u?.userName
    if (!primaryId) return
    const account = {
      id: primaryId,
      name: u.name || u.username || u.userName || 'User',
      handle: u.username || u.userName || primaryId,
      avatar: u.avatar || null,
      verified: false,
      type: 'user'
    }
    register(u.id, account)
    register(u.username, account)
    register(u.userName, account)
  })

  ;(projects || []).forEach(p => {
    if (!p?.project_id) return
    const account = {
      id: p.project_id,
      name: p.project_name,
      handle: p.project_name,
      avatar: p.project_icon || '/only_icon.png',
      verified: true,
      type: 'project'
    }
    register(p.project_id, account)
    register(p.project_name, account)
  })

  return accounts
}

// Resolve the profiles selected for a chat into displayable accounts.
//
// A chat only stores the profile NAMES (`Chat.vue` → onProfilesChanged maps the
// selection to `p.name || p`), so there is no avatar to render straight from the
// chat. We look the names up in the project's loaded profiles to pick up their
// avatar when there is one, and fall back to an initials-based account (see
// `avatarClass`/`initials`) so the card always renders something meaningful.
export function resolveProfiles(chat, project) {
  const names = Array.isArray(chat?.profiles) ? chat.profiles : []
  const projectProfiles = project?.$state?.profiles || []

  return names
    .map(name => {
      const key = typeof name === 'string' ? name : (name?.name || name?.id)
      if (!key) return null
      const found = projectProfiles.find(p => (p?.name || p?.id) === key)
      return {
        id: key,
        name: key,
        avatar: found?.avatar || found?.profile_icon || found?.icon || null,
        type: 'profile'
      }
    })
    .filter(Boolean)
}

const EMPTY_COUNTS = { replies: 0, reposts: 0, likes: 0, views: 0 }

// ─── Wall posts (chat-backed) ────────────────────────────────────────────────
// A chat created from the wall composer is flagged in its metadata so the feed
// can render it as a social post: the ORIGINAL message is the post body, every
// following message is a reply and the likes live in the chat metadata.
export const WALL_META_KEY = 'wall'

export function isWallPost(chat) {
  return !!chat?.meta_data?.[WALL_META_KEY]?.post
}

export function wallLikes(chat) {
  const likes = chat?.meta_data?.[WALL_META_KEY]?.likes
  return Array.isArray(likes) ? likes : []
}

function postContext(chat, project) {
  if (chat?.board) return { label: chat.board, icon: 'fa-brands fa-trello' }
  if (project?.project_name) return { label: project.project_name, icon: 'fa-solid fa-cube' }
  return null
}

function postAttachment(chat) {
  if (!chat) return null
  if (chat.pr_view?.from_branch) {
    return {
      type: 'pr',
      title: chat.pr_view.title || chat.name,
      from: chat.pr_view.from_branch,
      to: chat.pr_view.to_branch
    }
  }
  if (chat.file_list?.length) {
    return { type: 'code', files: chat.file_list.map(path => ({ path })) }
  }
  if (chat.board || chat.column) {
    return { type: 'board', board: chat.board, to: chat.column || chat.status, task: chat.name }
  }
  return null
}

// Map the attachments carried by a message (ChatAttachment JSON, base64) into a
// renderable attachment. Images and audio get their own types so pasted photos
// and recorded voice notes render as real media (players / thumbnails).
function messageAttachment(message) {
  const attachments = message?.attachments || []
  if (!attachments.length) return null

  const dataUrl = a => `data:${a.file_type};base64,${a.base64_data}`

  const images = attachments
    .filter(a => String(a.file_type || '').startsWith('image/') && a.base64_data)
    .map(a => ({ src: dataUrl(a), name: a.file_name || 'image' }))
  if (images.length) return { type: 'images', images }

  // Audio notes (recorded voice messages / uploaded audio) render as players.
  const audios = attachments
    .filter(a => String(a.file_type || '').startsWith('audio/') && a.base64_data)
    .map(a => ({ src: dataUrl(a), name: a.file_name || 'audio note', fileType: a.file_type }))
  if (audios.length) return { type: 'audio', audios }

  return { type: 'files', files: attachments.map(a => ({ path: a.file_name || 'file' })) }
}

function postKind(chat) {
  if (chat?.pr_view?.from_branch) return 'pr'
  if (chat?.file_list?.length) return 'code'
  if (chat?.board || chat?.column) return 'kanban'
  return 'chat'
}

// Turn a chat (a project activity item) into a feed post.
//
// `currentUser` (a username) is optional: when provided the post carries the
// unread-reply count for that user (see utils/chatUnread) so the card can show
// the same "unread messages" notification the sprint task card does.
export function chatToPost(chat, project, currentUser = null) {
  if (!chat) return null
  const messages = chat.messages || []
  const wall = isWallPost(chat)
  // Wall posts show their ORIGINAL message (the post) and count the replies;
  // every other chat keeps the "latest activity" preview.
  const head = wall
    ? (messages.find(m => m.role !== 'assistant') || messages[0] || {})
    : (messages[messages.length - 1] || {})
  const isBot = head.role === 'assistant'
  const text = String(head.content || chat.name || 'Activity').replace(/\s+/g, ' ').trim()
  const likes = wallLikes(chat)
  return {
    id: `chat-${project?.project_id || 'na'}-${chat.id || chat.doc_id || text.slice(0, 16)}`,
    kind: postKind(chat),
    authorId: isBot ? 'codx-junior' : (head.user || '__me'),
    createdAt: head.timestamp || head.created_at || chat.updated_at || chat.lastMessageAt || new Date().toISOString(),
    text: text.slice(0, 500),
    context: postContext(chat, project),
    attachment: messageAttachment(head) || postAttachment(chat),
    counts: {
      ...EMPTY_COUNTS,
      likes: likes.length,
      replies: wall ? Math.max(0, messages.length - 1) : 0,
      views: messages.length
    },
    chatId: chat.id,
    projectId: project?.project_id || null,
    // The icon leading the profile avatar group: the project it belongs to.
    projectIcon: project?.project_icon || null,
    profiles: resolveProfiles(chat, project),
    // Unread assistant replies addressed to the current user (0 for other users).
    unreadCount: countUnreadMessages(messages, currentUser),
    wallPost: wall,
    likedBy: likes
  }
}

// Turn a live OR ended meet into a feed post.
//
// An ended meet is moved from `activeMeets` to `meetHistory` (carrying
// `status: 'ended'` and `endedAt`). We honour that here so past meetings render
// as "Meeting ended" with a neutral, non-joinable attachment, while live meets
// keep their "started"/LIVE treatment.
export function meetToPost(meet) {
  if (!meet?.meetId) return null
  const ended = meet.status === 'ended'
  const startedAt = meet.startedAt || meet.endedAt || Date.now()
  const endedAt = meet.endedAt || null
  return {
    id: `meet-${meet.meetId}`,
    kind: 'meet',
    authorId: meet.initiator || 'codx-junior',
    // Ended meets are ordered by when they finished; live ones by their start.
    createdAt: new Date(ended ? (endedAt || startedAt) : startedAt).toISOString(),
    text: `${ended ? 'Meeting ended' : 'Meeting started'} — ${meet.name || 'Meet'}`,
    context: { label: ended ? 'Past meet' : 'Meet', icon: 'fa-solid fa-video' },
    attachment: {
      type: 'meet',
      title: meet.name,
      status: ended ? 'ended' : 'live',
      participants: meet.participants || [],
      startedAt,
      endedAt
    },
    counts: { ...EMPTY_COUNTS, views: (meet.participants || []).length },
    meetId: meet.meetId
  }
}

// Turn a UI notification into a feed post (used by the Notifications view)
export function notificationToPost(notification, index) {
  return {
    id: `notif-${index}-${notification?.ts || ''}`,
    kind: 'system',
    authorId: 'codx-junior',
    createdAt: new Date().toISOString(),
    text: notification?.text || '',
    context: null,
    attachment: null,
    type: notification?.type || 'info',
    counts: { ...EMPTY_COUNTS }
  }
}

// Assemble the feed from every source, newest first.
// `currentUser` (username) is forwarded so chat posts compute their unread count.
export function buildPosts({ chats = [], meets = [], notifications = [], withNotifications = false, currentUser = null } = {}) {
  const posts = []

  chats.forEach(({ chat, project }) => {
    const post = chatToPost(chat, project, currentUser)
    if (post) posts.push(post)
  })

  meets.forEach(meet => {
    const post = meetToPost(meet)
    if (post) posts.push(post)
  })

  if (withNotifications) {
    notifications.forEach((n, ix) => posts.push(notificationToPost(n, ix)))
  }

  return posts.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
}

// Tab / kind / free-text / unread filtering
//
// `unreadOnly` powers the "Unread" selector on the wall: when set, only events
// that still have unread replies for the current user are kept. The count is
// computed once in `chatToPost` (see utils/chatUnread) and travels with the post
// as `post.unreadCount`, so filtering here stays a pure, cheap operation.
export function filterPosts(posts, { tab = 'for-you', kind = 'all', query = '', following = [], unreadOnly = false } = {}) {
  let out = posts

  if (unreadOnly) {
    out = out.filter(p => (p.unreadCount || 0) > 0)
  }

  if (tab === 'following') {
    const set = new Set(following)
    out = out.filter(p => p.authorId === '__me' || p.authorId === 'codx-junior' || set.has(p.authorId))
  }

  if (kind && kind !== 'all') out = out.filter(p => p.kind === kind)

  const q = String(query || '').trim().toLowerCase()
  if (q) {
    out = out.filter(p =>
      String(p.text || '').toLowerCase().includes(q) ||
      String(p.context?.label || '').toLowerCase().includes(q))
  }

  return out
}