import config from './config.json' with {type: 'json'};
import { defineConfig } from 'vitepress'

const {
  project: {
    name: title,
    description,
    icon,
    repository
  },
  sidebar,
  base
} = config as any

const socialLinks = []
if (repository) {
  socialLinks.push({ icon: 'github', link: repository })
}

// The generated wiki is deployable as its own website. `base` is written by
// the site builder (`/` for standalone deployments, a sub-path when hosted
// under codx-junior).
export default defineConfig({
  title,
  description,
  base: base || '/',
  ignoreDeadLinks: true,
  head: [
    ['meta', { name: 'theme-color', content: '#550e57' }]
  ],
  themeConfig: {
    search: { provider: 'local' },
    logo: icon,
    nav: [{ text: 'Home', link: '/' }],
    sidebar,
    socialLinks
  }
})
