import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "codx-junior",
  description: "codx-junior wiki",
  base:'/api/wiki/codx-junior',
  themeConfig: {
    search: {
      provider: 'local'
    },
    logo: "https://codx-dev.meetnav.com/only_icon.png",
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: 'Home', link: '/' },
    ],

    sidebar: [
    ],

  }
})
