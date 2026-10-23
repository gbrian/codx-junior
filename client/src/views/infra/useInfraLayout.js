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