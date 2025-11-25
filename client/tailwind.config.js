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
    extend: {
      colors: {
        'codx-primary': '#cc0099',
        'codx-secondary': '#8f008f',
      }
    },
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