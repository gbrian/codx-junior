// ─────────────────────────────────────────────────────────────────────────────
// Team View – shared metadata & presentation helpers
//
// The Team screen re-frames each *profile* as an AI "team member". It speaks
// manager language (roles, skills) instead of raw technical concepts
// (category, file_match, api_settings).
//
// Teams are persisted per project through the teams API (see
// `src/api/modules/teams.js` → `$project.$api.teams`) and are the SINGLE source
// of truth for teams AND membership. There is no client-side fallback: an empty
// list simply means the project has no teams yet and the UI prompts to create
// one.
//
// Membership is many-to-many: a member (profile name) may appear in the
// `profiles` list of several teams. See `src/views/TeamView.vue`
// (`memberTeamIds`) for the consumer side.
// ─────────────────────────────────────────────────────────────────────────────

// ── Business roles ───────────────────────────────────────────────────────────
// Maps the profile `category` to a friendly label, an icon, a hint and a
// DaisyUI badge class. Class names are full literals so Tailwind detects them.
export const ROLE_META = {
  project: {
    label: 'Team Lead',
    hint: 'Leads and coordinates the team',
    icon: 'fa-solid fa-crown',
    badge: 'badge-primary'
  },
  assistant: {
    label: 'Assistant',
    hint: 'General-purpose helper for everyday work',
    icon: 'fa-solid fa-wand-magic-sparkles',
    badge: 'badge-secondary'
  },
  chat: {
    label: 'Chat Assistant',
    hint: 'Conversational responder for people-facing chats',
    icon: 'fa-regular fa-comments',
    badge: 'badge-info'
  },
  agent: {
    label: 'Agent',
    hint: 'Works autonomously on multi-step tasks',
    icon: 'fa-solid fa-robot',
    badge: 'badge-accent'
  },
  'agent-validator': {
    label: 'Reviewer',
    hint: "Checks and validates other members' work",
    icon: 'fa-solid fa-shield-halved',
    badge: 'badge-success'
  },
  file: {
    label: 'File Specialist',
    hint: 'Expert on a specific set of files',
    icon: 'fa-regular fa-file-code',
    badge: 'badge-warning'
  }
}

export function roleMeta(category) {
  return ROLE_META[category] || ROLE_META.assistant
}

// Default guardrails applied to a member that has none yet. Kept in sync with
// the shape used by EditProfile.vue / the profiles API.
export const EMPTY_GUARDRAILS = {
  enabled: false,
  scope: '',
  scope_keywords: [],
  scope_similarity_threshold: 0.35,
  allowed_tools: [],
  refusal_message: 'I can only answer questions within my configured scope.',
  risk_threshold: 10.0,
  use_llm_classifier: false
}

// ── API <-> local team mapping ───────────────────────────────────────────────
// The backend `Team` model (codx/junior/teams/model.py) matches the local team
// object closely, so the mapping is a thin normalisation.

/** Build a local UI team from an API team. */
export function toLocalTeam(apiTeam) {
  return {
    id: apiTeam.id,
    name: apiTeam.name || 'Team',
    description: apiTeam.description || '',
    color: apiTeam.color || '#6366f1',
    icon: apiTeam.icon || 'fa-solid fa-people-group',
    logo: apiTeam.logo || '',
    profiles: apiTeam.profiles || []
  }
}

/** Serialise a local UI team into the payload accepted by the teams API. */
export function toApiTeam(team) {
  return {
    id: team.id,
    name: team.name,
    description: team.description || '',
    color: team.color || '#6366f1',
    icon: team.icon || '',
    logo: team.logo || '',
    profiles: team.profiles || []
  }
}

// ── Presentation helpers ─────────────────────────────────────────────────────
// Same robohash/gravatar fallback used by ProfileCard / EditProfile.
export function avatarUrl(member) {
  if (member?.avatar) return member.avatar
  const seed = encodeURIComponent(member?.name || 'member')
  return `https://gravatar.com/avatar/baa8db8ab2afb7ababc235269e762662?s=200&d=robohash&r=${seed}`
}

// Made with ❤️ by codx-junior