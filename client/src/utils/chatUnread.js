// ─────────────────────────────────────────────────────────────────────────────
// Unread messages — shared rule
//
// Used by the sprint/kanban task cards (SprintTaskCard.vue) and by the activity
// wall (src/components/wall/*) so both surfaces agree on what "unread" means.
//
// A message counts as UNREAD for the current user when ALL of these hold:
//   • it is an assistant reply (not a user prompt),
//   • it was not authored by the current user,
//   • the current user is not in its `read_by` list,
//   • it has finished processing (`done !== false`) — a still-streaming reply
//     must never light up the badge, and
//   • it is not hidden.
//
// Channels (team chat) also count messages written by OTHER PEOPLE, so the same
// rule is exposed with `includeUserMessages`. The default keeps the historical
// assistant-only behaviour so kanban cards and the activity wall do not change.
// ─────────────────────────────────────────────────────────────────────────────

export function isUnreadForUser(message, username, options = {}) {
  if (!username || !message) return false
  const includeUserMessages = options.includeUserMessages === true
  const isCountedRole = message.role === 'assistant' || (includeUserMessages && message.role === 'user')
  const isOtherUser = message.user !== username
  const isUnread = !message.read_by || !message.read_by.includes(username)
  const isDone = message.done !== false
  return isCountedRole && isOtherUser && isUnread && isDone && !message.hide
}

export function isUnreadMessage(message, username) {
  return isUnreadForUser(message, username)
}

export function countUnreadMessages(messages, username) {
  if (!username) return 0
  return (messages || []).filter(message => isUnreadMessage(message, username)).length
}

// Channel rule: colleagues' messages AND profile replies both count.
export function countChannelUnread(messages, username) {
  if (!username) return 0
  return (messages || []).filter(message => isUnreadForUser(message, username, { includeUserMessages: true })).length
}
