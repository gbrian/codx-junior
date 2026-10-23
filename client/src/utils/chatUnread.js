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
// ─────────────────────────────────────────────────────────────────────────────

export function isUnreadMessage(message, username) {
  if (!username || !message) return false
  const isAssistantMsg = message.role === 'assistant'
  const isOtherUser = message.user !== username
  const isUnread = !message.read_by || !message.read_by.includes(username)
  const isDone = message.done !== false
  return isAssistantMsg && isOtherUser && isUnread && isDone && !message.hide
}

export function countUnreadMessages(messages, username) {
  if (!username) return 0
  return (messages || []).filter(message => isUnreadMessage(message, username)).length
}