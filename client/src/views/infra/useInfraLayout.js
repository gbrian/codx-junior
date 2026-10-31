/**
 * ============================================================================
 * Infrastructure — panel layout detection.
 * ----------------------------------------------------------------------------
 * InfraView is rendered inside a RESIZABLE dockview panel, so "mobile" has to
 * mean "THIS PANEL is narrow" — not "the browser window is narrow".
 *
 * Container-query utilities (`@2xl:`, `@3xl:`…) did not resolve inside the
 * dockview panel in this build, which left the tables permanently `hidden`
 * and only the card markup visible. The width is therefore measured directly
 * with a ResizeObserver and exposed as reactive flags.
 *
 * The panels then MOUNT one markup or the other (`v-if`) instead of rendering
 * both and hiding one with CSS:
 *   • deterministic — no dependency on container-query support;
 *   • no `display` conflict with daisyUI's `.card` (which sets its own
 *     `display`, the reason `class="hidden md:block card"` never worked).
 *
 * VISIBILITY
 * ----------
 * The same root element is also observed for VISIBILITY (`observePanelVisibility`)
 * because a dockview panel added with `renderer: 'always'` stays MOUNTED while
 * its tab is inactive. `onBeforeUnmount` therefore cannot be used to decide when
 * the view stopped being on screen — which is exactly what the Infrastructure
 * polling loop needs to know.
 * ============================================================================
 */
import { reactive } from 'vue'

/** Widths (px) at which the layout switches. Mirrors the Tailwind container scale. */
export const LAYOUT_BREAKPOINTS = {
  xl: 576, // events: single-line rows
  '2xl': 672, // header / KPI strip / filters stack; simple lists become cards
  '3xl': 768, // containers: cards instead of the 6-column table
  '4xl': 896 // stacks: two columns
}

/**
 * Reactive layout flags read by the infra components.
 *
 *  inline  – panel is wide enough for one-line event rows
 *  compact – panel is narrow: stack header / KPIs / filters, lists become cards
 *  cards   – panel is narrow: container list uses cards (needs more room than
 *            the simple lists because its table has 6 dense columns)
 *  twoCol  – panel is wide enough for two stack cards side by side
 *  width   – last measured width (debug aid; nothing renders from it)
 */
export const layout = reactive({
  width: 0,
  inline: false,
  compact: true,
  cards: true,
  twoCol: false
})

let observer = null

/** Recomputes the flags. Same-value assignments do not trigger re-renders. */
function apply(width) {
  const w = Math.max(0, Math.round(width || 0))
  layout.width = w
  layout.inline = w >= LAYOUT_BREAKPOINTS.xl
  layout.compact = w < LAYOUT_BREAKPOINTS['2xl']
  layout.cards = w < LAYOUT_BREAKPOINTS['3xl']
  layout.twoCol = w >= LAYOUT_BREAKPOINTS['4xl']
}

/** Stops observing (safe to call repeatedly). */
export function disposePanelWidth() {
  if (observer) {
    observer.disconnect()
    observer = null
  }
}

/**
 * Starts tracking the width of `el`.
 * Returns a disposer — call it from `onBeforeUnmount`.
 */
export function observePanelWidth(el) {
  disposePanelWidth()
  if (!el) return disposePanelWidth

  apply(el.clientWidth)

  // Fallback for environments without ResizeObserver.
  if (typeof ResizeObserver === 'undefined') {
    const onResize = () => apply(el.clientWidth)
    window.addEventListener('resize', onResize)
    observer = { disconnect: () => window.removeEventListener('resize', onResize) }
    return disposePanelWidth
  }

  observer = new ResizeObserver(() => apply(el.clientWidth))
  observer.observe(el)
  return disposePanelWidth
}

/* ── Visibility ───────────────────────────────────────────────────────────── */
let visibilityObserver = null

/** Stops tracking visibility (safe to call repeatedly). */
export function disposePanelVisibility() {
  if (visibilityObserver) {
    visibilityObserver.disconnect()
    visibilityObserver = null
  }
}

/**
 * Tracks whether `el` is actually on screen.
 *
 * Two things hide this view WITHOUT unmounting it, so `onBeforeUnmount` alone
 * is not enough to know when to stop polling:
 *   • its dockview tab is not the active one — panels are added with
 *     `renderer: 'always'`, so the component stays mounted out of sight;
 *   • the browser tab/window is in the background.
 *
 * `IntersectionObserver` covers the first case (a hidden panel has no
 * intersection rect) and `visibilitychange` the second one. `onChange` fires
 * only when the COMBINED result flips, so the caller can pause/resume a timer
 * without reacting to every observer callback.
 *
 * Returns a disposer — call it from `onBeforeUnmount`.
 */
export function observePanelVisibility(el, onChange) {
  disposePanelVisibility()
  if (!el) return disposePanelVisibility

  let onScreen = true
  let pageVisible = document.visibilityState !== 'hidden'
  let last = null

  const notify = () => {
    const visible = onScreen && pageVisible
    if (visible === last) return
    last = visible
    if (typeof onChange === 'function') onChange(visible)
  }

  const onPageVisibility = () => {
    pageVisible = document.visibilityState !== 'hidden'
    notify()
  }
  document.addEventListener('visibilitychange', onPageVisibility)

  let intersection = null
  if (typeof IntersectionObserver !== 'undefined') {
    intersection = new IntersectionObserver((entries) => {
      const entry = entries[entries.length - 1]
      onScreen = !!entry?.isIntersecting
      notify()
    }, { threshold: 0 })
    intersection.observe(el)
  }

  visibilityObserver = {
    disconnect() {
      if (intersection) intersection.disconnect()
      document.removeEventListener('visibilitychange', onPageVisibility)
    }
  }

  // Report the CURRENT state once: a panel restored inside a background tab
  // must not start polling until it is really shown.
  notify()
  return disposePanelVisibility
}