/**
 * Context-menu state shared by the git view sections.
 *
 * The host renders one `GitContextMenu` bound to `contextMenuState` and passes
 * item lists built with `contextMenuItem` / `contextMenuDivider`. Item
 * `run` callbacks are executed (and awaited) by `onContextMenuSelect`, so a
 * failing operation never leaves an unhandled promise rejection.
 *
 * Components with `notice` / `error` data get the copy/error feedback directly;
 * the rest forward it through the `context-menu-notice` and
 * `context-menu-error` events.
 *
 * @example
 * // in the component
 * mixins: [contextMenuMixin]
 *
 * // opening the menu
 * this.openContextMenu(event, 'Branch main', [
 *   this.contextMenuItem('checkout', 'Checkout', 'fa-arrow-right-to-bracket', () => this.onCheckout('main')),
 *   this.contextMenuDivider('delete'),
 *   this.contextMenuItem('delete', 'Delete branch', 'fa-trash', () => this.deleteBranch('main'), { danger: true })
 * ])
 */
export const contextMenuMixin = {
  data() {
    return {
      contextMenuState: {
        visible: false,
        position: { x: 0, y: 0 },
        title: '',
        items: []
      }
    }
  },
  methods: {
    /**
     * Open the shared menu at the pointer position.
     *
     * @param {MouseEvent} event - Contextmenu event.
     * @param {string} title - Small header shown above the items.
     * @param {Array} items - Menu items; empty lists are ignored.
     */
    openContextMenu(event, title, items) {
      const list = (items || []).filter(Boolean)
      if (!list.length) return
      event?.preventDefault?.()
      event?.stopPropagation?.()
      this.contextMenuState = {
        visible: true,
        position: { x: event?.clientX || 0, y: event?.clientY || 0 },
        title: title || '',
        items: list
      }
    },

    closeContextMenu() {
      if (!this.contextMenuState.visible) return
      this.contextMenuState = {
        ...this.contextMenuState,
        visible: false,
        items: []
      }
    },

    /** Build one menu entry */
    contextMenuItem(key, label, icon, run, options = {}) {
      return { key, label, icon, run, ...options }
    },

    /** Build a separator entry */
    contextMenuDivider(key = 'divider') {
      return { key, divider: true }
    },

    /**
     * Execute the selected item.
     *
     * The menu closes first so the operation feedback is visible. Errors are
     * reported through `context-menu-error` (or the component `error` data),
     * keeping the handling identical to the regular action buttons.
     */
    onContextMenuSelect(item) {
      this.closeContextMenu()
      if (!item?.run) return
      try {
        const result = item.run()
        if (result && typeof result.catch === 'function') {
          result.catch(error => this.reportContextMenuError(error))
        }
      } catch (error) {
        this.reportContextMenuError(error)
      }
    },

    reportContextMenuError(error) {
      const message = error?.response?.data?.detail || error?.message || String(error)
      console.error('[GitView] context menu action failed:', error)
      if (Object.prototype.hasOwnProperty.call(this.$data, 'error')) {
        this.error = message
      } else {
        this.$emit('context-menu-error', message)
      }
    },

    /** Copy text and report the result with the host's own feedback UI */
    copyText(text, message = 'Copied to clipboard') {
      if (!text) return
      try {
        const result = navigator.clipboard?.writeText(String(text))
        if (result && typeof result.catch === 'function') {
          result.catch(error => this.reportContextMenuError(error))
        }
      } catch (error) {
        this.reportContextMenuError(error)
        return
      }
      if (Object.prototype.hasOwnProperty.call(this.$data, 'notice')) {
        this.notice = message
      } else {
        this.$emit('context-menu-notice', message)
      }
    }
  }
}

export default contextMenuMixin
