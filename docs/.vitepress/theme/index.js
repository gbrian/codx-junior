import DefaultTheme from 'vitepress/theme'
import './custom.css'
import RegisterForm from './RegisterForm.vue'

/** @type {import('vitepress').Theme} */
export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('RegisterForm', RegisterForm)
  }
}