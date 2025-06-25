import config from './config.json' with {type: 'json'};
import { defineConfig } from 'vitepress'

const {
  project: {
    name: title,
    description,
    icon,
    repository
  },
  sidebar
} = config as any
const socialLinks = []
if (repository) {
  socialLinks.push({ icon: 'github', link: repository })
}
// https://vitepress.dev/reference/site-config
export default defineConfig({
  title,
  description,
  base:'/api/wiki/' + title,
  ignoreDeadLinks: true,
  themeConfig: {
    search: {
      provider: 'local'
    },
    logo: icon,
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: 'Home', link: '/' },
    ],
    sidebar,
    socialLinks
  },
})
