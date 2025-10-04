import daisyui from 'daisyui'
import typography from '@tailwindcss/typography'
import queries from '@tailwindcss/container-queries'

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx,vue}",
  ],
  theme: {
    extend: {},
  },
  plugins: [
    daisyui, 
    typography,
    queries,
  ],
  daisyui: {
    themes: true,
  },
}