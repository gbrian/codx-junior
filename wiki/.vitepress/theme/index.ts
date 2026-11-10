import DefaultTheme from 'vitepress/theme'
import { h } from 'vue'
import Assistant from './Assistant.vue'
import './custom.css'

export default {
  extends: DefaultTheme,
  Layout() {
    return h(DefaultTheme.Layout, null, {
      'layout-bottom': () => h(Assistant)
    })
  }
}
