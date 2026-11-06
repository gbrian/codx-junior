import { onBeforeUnmount, onMounted, ref } from 'vue'

// ─────────────────────────────────────────────────────────────────────────────
// MOBILE VIEWPORT
//
// The layout is a fixed app shell (top bar + content + bottom bar) instead of a
// document that scrolls. On phones the browser chrome and the on-screen
// keyboard change the *visual* viewport without resizing the layout viewport,
// which is what used to push the composer and the tab bar off screen.
//
// This composable follows `window.visualViewport` and exposes:
//
//   height        — the usable height, in CSS pixels, for the app shell.
//   keyboardOpen  — true while the on-screen keyboard covers a meaningful part
//                   of the screen (the tab bar hides itself then).
//   keyboardInset — how many pixels the keyboard occupies.
//
// It is intentionally dependency-free and safe on desktop (visualViewport is
// either absent or equal to the window size).
// ─────────────────────────────────────────────────────────────────────────────
export function useMobileViewport() {
  const height = ref(readHeight())
  const keyboardOpen = ref(false)
  const keyboardInset = ref(0)

  let viewport = null
  let raf = null

  function readHeight() {
    if (typeof window === 'undefined') return 0
    return Math.round(window.visualViewport?.height || window.innerHeight || 0)
  }

  function update() {
    if (raf) return
    raf = window.requestAnimationFrame(() => {
      raf = null
      const next = readHeight()
      const inset = Math.max(0, Math.round((window.innerHeight || next) - next))
      // A small difference is just the URL bar collapsing/expanding. Only a
      // sizable inset means the on-screen keyboard is open.
      const nextKeyboard = inset > 140
      height.value = next
      keyboardInset.value = inset
      keyboardOpen.value = nextKeyboard
      // Keep the CSS variable in sync for children that cannot read the ref
      // (for example the chat composer's max-height calculation).
      document.documentElement.style.setProperty('--mobile-vh', `${next}px`)
      document.documentElement.style.setProperty('--mobile-keyboard', `${inset}px`)
      document.documentElement.classList.toggle('mobile-keyboard-open', nextKeyboard)
    })
  }

  onMounted(() => {
    viewport = window.visualViewport || null
    update()
    window.addEventListener('resize', update)
    window.addEventListener('orientationchange', update)
    viewport?.addEventListener('resize', update)
    viewport?.addEventListener('scroll', update)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('resize', update)
    window.removeEventListener('orientationchange', update)
    viewport?.removeEventListener('resize', update)
    viewport?.removeEventListener('scroll', update)
    if (raf) window.cancelAnimationFrame(raf)
    document.documentElement.classList.remove('mobile-keyboard-open')
    document.documentElement.style.removeProperty('--mobile-vh')
    document.documentElement.style.removeProperty('--mobile-keyboard')
  })

  return { height, keyboardOpen, keyboardInset }
}
