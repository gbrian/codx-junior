import { defineConfig } from 'vitepress'
import tailwindcss from '@tailwindcss/vite'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "codx-junior",
  description: "The open-source workspace where AI agents and senior developers build software together.",
  vite: {
    base: "",
    server: {
      host: true,
      port: 19000,
      allowedHosts: true,
      watch: {
        ignored: ['.codx']
      }
    },
    plugins: [
      tailwindcss(),
    ],
  },
  head: [
    ['link', { rel: 'icon', href: '/only_icon.png' }],
  ],
  themeConfig: {
    search: {
      provider: 'local'
    },
    logo: 'public/only_icon.png',
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Guide', link: '/guide/introduction' },
      { text: 'Getting Started', link: '/getting-started' },
      { text: 'Features', link: '/features/chats-and-agents' },
      { text: 'Managed team', link: '/managed' },
      { text: 'Demo', link: '/demo' }
    ],
    sidebar: [
      {
        text: 'Introduction',
        items: [
          { text: 'What is codx-junior?', link: '/guide/introduction' },
          { text: 'Architecture', link: '/guide/architecture' },
          { text: 'Self-hosted or managed', link: '/managed' },
        ]
      },
      {
        text: 'Getting Started',
        items: [
          { text: 'Installation', link: '/getting-started' },
          { text: 'Initial setup', link: '/initial-setup' },
          { text: 'Configuration', link: '/configuration' },
        ]
      },
      {
        text: 'Features',
        items: [
          { text: 'Chats and agents', link: '/features/chats-and-agents' },
          { text: 'Kanban and tasks', link: '/features/kanban' },
          { text: 'Vibe coding', link: '/features/vibe-coding' },
          { text: 'Workspaces', link: '/features/workspaces' },
          { text: 'Teams and messenger', link: '/features/teams' },
          { text: 'Knowledge (RAG)', link: '/features/knowledge' },
          { text: 'Profiles', link: '/features/profiles' },
          { text: '@codx mentions', link: '/features/mentions' },
          { text: 'Git and code review', link: '/features/code-review' },
          { text: 'Wiki', link: '/features/wiki' },
          { text: 'Development tools', link: '/features/development-tools' },
        ]
      },
      {
        text: 'Administration',
        items: [
          { text: 'AI providers and models', link: '/features/ai-providers' },
          { text: 'Budget and analytics', link: '/features/budget-and-analytics' },
          { text: 'Users and security', link: '/features/users-and-security' },
          { text: 'Plugins', link: '/features/plugins' },
          { text: 'API', link: '/features/api' },
        ]
      },
      {
        text: 'Community',
        items: [
          { text: 'Demo', link: '/demo' },
          { text: 'Team', link: '/team' },
        ]
      }
    ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/gbrian/codx-junior' },
      { icon: 'linkedin', link: 'https://www.linkedin.com/company/meetnav' }
    ]
  }
})
