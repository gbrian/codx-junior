import { defineConfig } from 'vitepress'
import tailwindcss from '@tailwindcss/vite'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "codx-junior",
  description: "Your FullStackHero AI",
  vite: {
    server: {
      host: true,
      port: 19000,
      allowedHosts: true,
      watch: {
        ignored: ['.codx']
      }
    },
    plugins: [
      tailwindcss()
    ],
  },
  head: [['link', { rel: 'icon', href: '/only_icon.png' }]],
  themeConfig: {
    search: {
      provider: 'local'
    },
    logo: 'public/only_icon.png',
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Getting Started', link: '/getting-started' },
      { text: 'Team', link: '/team' },
      { text: 'Demo', link: '/demo' }
    ],
    sidebar: [
      {
        text: 'Introduction',
        items: [
          { text: 'Home', link: '/' },
        ]
      },
      {
        text: 'Getting Started',
        items: [
          { text: 'Quick start', link: '/getting-started' },
          { text: 'Initial setup', link: '/initial-setup' },
        ]
      },
      {
        text: 'Features',
        items: [
          { text: 'Project\'s Dashboard', link: '/features' },
          { text: 'Project Management', link: '/features' },
          { text: 'Tasks', link: '/features' },
          { text: 'Code Generation and Review', link: '/features' },
          { text: 'Deployment and Operations', link: '/features' },
          { text: 'Collaboration and Communication', link: '/collaboration' },
          { text: 'Knowledge Sharing', link: '/knowledge-sharing' },
          { text: 'Development Tools', link: '/development-tools' },
          { text: 'Settings', link: '/settings' }
        ]
      },
      {
        text: 'Demo',
        items: [
          { text: 'codx-junior Demo', link: '/demo' }
        ]
      }
    ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/gbrian/codx-junior' },
      { icon: 'linkedin', link: 'https://www.linkedin.com/company/meetnav' }
    ]
  }
})
