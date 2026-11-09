// ─────────────────────────────────────────────────────────────────────────────
// MOBILE INFORMATION ARCHITECTURE
//
// One place that describes what the mobile shell offers:
//
//   • MOBILE_TABS      — the persistent bottom tab bar.
//   • MOBILE_APP_GROUPS — the "Everything" launcher inside the More sheet.
//
// The tab bar is deliberately small: Home (management dashboard), Chats,
// Tasks, Activity and More. Everything else is one tap away from the More
// sheet, which is searchable and grouped the way people think about the
// product (work, people, build, insights, account).
//
// Route → tab mapping lives in the router metadata (`meta.mobile.tab`), not
// here, so a route owns how it highlights the bar (see router/index.ts).
// ─────────────────────────────────────────────────────────────────────────────

export const MOBILE_TABS = [
  {
    key: 'home',
    label: 'Home',
    icon: 'fa-solid fa-house',
    route: { name: 'home' }
  },
  {
    key: 'chats',
    label: 'Chats',
    icon: 'fa-regular fa-comments',
    route: { name: 'chats' }
  },
  {
    key: 'tasks',
    label: 'Tasks',
    icon: 'fa-solid fa-list-check',
    route: { name: 'kanban' }
  },
  {
    key: 'activity',
    label: 'Activity',
    icon: 'fa-solid fa-bolt',
    route: { name: 'activity' }
  },
  {
    key: 'more',
    label: 'More',
    icon: 'fa-solid fa-grip',
    action: 'menu'
  }
]

// Tone classes are written out in full so Tailwind's scanner can see them.
export const MOBILE_TONES = {
  primary: 'bg-primary/15 text-primary',
  secondary: 'bg-secondary/15 text-secondary',
  accent: 'bg-accent/15 text-accent',
  info: 'bg-info/15 text-info',
  success: 'bg-success/15 text-success',
  warning: 'bg-warning/15 text-warning',
  error: 'bg-error/15 text-error'
}

export const MOBILE_APP_GROUPS = [
  {
    id: 'work',
    label: 'Work',
    hint: 'Plan, execute and ship',
    apps: [
      {
        key: 'home',
        title: 'Home',
        description: 'Your command center',
        icon: 'fa-solid fa-house',
        tone: 'primary'
      },
      {
        key: 'chats',
        action: 'chats',
        title: 'Chats',
        description: 'All conversations',
        icon: 'fa-solid fa-inbox',
        tone: 'info'
      },
      {
        key: 'new-chat',
        action: 'new-chat',
        title: 'New chat',
        description: 'Start a conversation',
        icon: 'fa-solid fa-pen-to-square',
        tone: 'primary'
      },
      {
        key: 'tasks',
        title: 'Task manager',
        description: 'Boards, columns and cards',
        icon: 'fa-brands fa-trello',
        tone: 'success'
      },
      {
        key: 'planning',
        title: 'Planning',
        description: 'Global plan and follow-up',
        icon: 'fa-solid fa-diagram-project',
        tone: 'info'
      },
      {
        key: 'company',
        title: 'Company',
        description: 'Teams, people and missions',
        icon: 'fa-solid fa-building-columns',
        tone: 'primary'
      },
      {
        key: 'management-dashboard',
        title: 'Management',
        description: 'Pulse, blockers, delivery',
        icon: 'fa-solid fa-table-columns',
        tone: 'secondary'
      },
      {
        key: 'projects',
        title: 'Projects',
        description: 'Browse every workspace',
        icon: 'fa-solid fa-cubes',
        tone: 'accent'
      },
      {
        key: 'activity',
        title: 'Activity wall',
        description: 'What happened across projects',
        icon: 'fa-solid fa-bolt',
        tone: 'warning'
      }
    ]
  },
  {
    id: 'people',
    label: 'People',
    hint: 'Talk and meet',
    apps: [
      {
        key: 'messenger',
        title: 'Messenger',
        description: 'Channels and direct messages',
        icon: 'fa-regular fa-comments',
        tone: 'info'
      },
      {
        key: 'meet',
        title: 'Meet',
        description: 'Calls and live sessions',
        icon: 'fa-solid fa-video',
        tone: 'error'
      },
      {
        key: 'team',
        title: 'Team',
        description: 'Your people and their work',
        icon: 'fa-solid fa-people-group',
        tone: 'primary'
      }
    ]
  },
  {
    id: 'build',
    label: 'Build',
    hint: 'Code, files and knowledge',
    apps: [
      {
        key: 'file-explorer',
        title: 'Files',
        description: 'Browse the project tree',
        icon: 'fa-solid fa-folder-open',
        tone: 'warning'
      },
      {
        key: 'git-view',
        title: 'Git',
        description: 'Branches, commits and changes',
        icon: 'fa-solid fa-code-branch',
        tone: 'error'
      },
      {
        key: 'workspaces',
        title: 'Workspaces',
        description: 'Project apps and environments',
        icon: 'fa-solid fa-server',
        tone: 'info'
      },
      {
        key: 'browser-sessions',
        title: 'Browsers',
        description: 'Live browser sessions',
        icon: 'fa-regular fa-compass',
        tone: 'accent'
      },
      {
        key: 'infra',
        title: 'Infrastructure',
        description: 'Containers and services',
        icon: 'fa-solid fa-boxes-stacked',
        tone: 'secondary'
      },
      {
        key: 'wiki',
        title: 'Wiki',
        description: 'Project handbook',
        icon: 'fa-solid fa-graduation-cap',
        tone: 'success'
      },
      {
        key: 'docs',
        title: 'Docs',
        description: 'Long-form documentation',
        icon: 'fa-solid fa-book',
        tone: 'primary'
      },
      {
        key: 'knowledge',
        title: 'Knowledge',
        description: 'Search the knowledge base',
        icon: 'fa-solid fa-magnifying-glass',
        tone: 'info'
      }
    ]
  },
  {
    id: 'insights',
    label: 'Insights',
    hint: 'Measure and debug',
    apps: [
      {
        key: 'analytics',
        title: 'Analytics',
        description: 'Delivery and cost trends',
        icon: 'fa-solid fa-chart-area',
        tone: 'success'
      },
      {
        key: 'metrics',
        title: 'Metrics',
        description: 'Project telemetry',
        icon: 'fa-solid fa-gauge-high',
        tone: 'info'
      },
      {
        key: 'api-monitoring',
        title: 'API monitoring',
        description: 'Latency, errors and throughput',
        icon: 'fa-solid fa-heart-pulse',
        tone: 'error'
      },
      {
        key: 'chat-logs',
        title: 'Chat logs',
        description: 'Analyze conversations',
        icon: 'fa-solid fa-magnifying-glass-chart',
        tone: 'warning'
      },
      {
        key: 'decision-model-logs',
        title: 'Decision logs',
        description: 'How the agent decided',
        icon: 'fa-solid fa-code-branch',
        tone: 'secondary'
      },
      {
        key: 'log-viewer',
        title: 'Logs',
        description: 'Raw application output',
        icon: 'fa-solid fa-file-lines',
        tone: 'accent'
      }
    ]
  },
  {
    id: 'account',
    label: 'Account',
    hint: 'Settings and extras',
    apps: [
      {
        key: 'settings',
        title: 'Project settings',
        description: 'This project’s configuration',
        icon: 'fa-solid fa-gear',
        tone: 'info'
      },
      {
        key: 'global-settings',
        title: 'Global settings',
        description: 'Instance-wide configuration',
        icon: 'fa-solid fa-sliders',
        tone: 'secondary'
      },
      {
        key: 'knowledge_settings',
        title: 'Knowledge settings',
        description: 'Indexes and sources',
        icon: 'fa-solid fa-sliders',
        tone: 'success'
      },
      {
        key: 'account',
        title: 'My account',
        description: 'Profile, security and wallet',
        icon: 'fa-solid fa-user',
        tone: 'primary'
      },
      {
        key: 'vibe-coding',
        title: 'Vibe coding',
        description: 'Build by describing it',
        icon: 'fa-solid fa-wand-magic-sparkles',
        tone: 'accent'
      },
      {
        key: 'solopreneur',
        title: 'Solopreneur',
        description: 'Run your venture solo',
        icon: 'fa-solid fa-rocket',
        tone: 'error'
      }
    ]
  }
]

// Flat lookup used by the launcher search and by tests/quick links.
export const MOBILE_APPS = MOBILE_APP_GROUPS.flatMap(group => group.apps)

// Route title fallbacks. The router sets `meta.mobile.title` for every route;
// this map only covers routes registered elsewhere (or added later) so the
// shell never renders a blank title.
export const MOBILE_ROUTE_TITLES = {
  root: 'codx-junior',
  home: 'Home',
  chats: 'Chats',
  chat: 'Chat',
  'chat-workspace': 'Chat',
  'new-chat': 'New chat',
  kanban: 'Task manager',
  activity: 'Activity',
  messenger: 'Messenger',
  meet: 'Meet',
  'meet-session': 'Meeting',
  team: 'Team',
  workspaces: 'Workspaces',
  workspace: 'Workspace',
  browsers: 'Browser sessions',
  'browser-session': 'Browser',
  'file-explorer': 'Files',
  'file-viewer': 'File',
  'git-view': 'Git',
  wiki: 'Wiki',
  docs: 'Docs',
  knowledge: 'Knowledge',
  'knowledge-settings': 'Knowledge settings',
  projects: 'Projects',
  settings: 'Project settings',
  'global-settings': 'Global settings',
  account: 'Account',
  logs: 'Logs',
  'log-viewer': 'Logs',
  'chat-logs': 'Chat logs',
  'decision-model-logs': 'Decision logs',
  metrics: 'Metrics',
  analytics: 'Analytics',
  'management-dashboard': 'Management',
  'api-monitoring': 'API monitoring',
  infra: 'Infrastructure',
  'team-channel': 'Channel',
  'team-dm': 'Direct message',
  'team-media-library': 'Media library',
  'vibe-coding': 'Vibe coding',
  solopreneur: 'Solopreneur',
  'codx-junior-split': 'Desktop'
}
