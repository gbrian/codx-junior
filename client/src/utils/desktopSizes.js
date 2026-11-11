/**
 * Desktop size choices for the computer-session settings.
 *
 * A computer session either follows the viewer (`auto`, the default: KasmVNC /
 * Selkies resize the remote framebuffer to the browser window) or keeps a fixed
 * resolution. The backend publishes the same list through
 * `GET /api/computers/desktop-sizes`; the presets below mirror
 * `codx/junior/computer/resize.py` and are used when that endpoint is not
 * available (older backend), so the selector always renders.
 */

/** Bounds accepted by the backend for a manual size. */
export const MIN_DESKTOP_WIDTH = 640
export const MAX_DESKTOP_WIDTH = 7680
export const MIN_DESKTOP_HEIGHT = 480
export const MAX_DESKTOP_HEIGHT = 4320

/** Default size used when a custom size is chosen without typing one. */
export const DEFAULT_DESKTOP_WIDTH = 1920
export const DEFAULT_DESKTOP_HEIGHT = 1080

/** Default option: the desktop resizes to the client viewport. */
export const AUTO_DESKTOP_SIZE = {
  id: 'auto',
  label: 'Auto (fit to window)',
  width: 0,
  height: 0,
  auto: true,
  custom: false,
  description: 'The desktop resizes to this window, so it always fills the panel (default)'
}

/** Last option: the caller types the width and height. */
export const CUSTOM_DESKTOP_SIZE = {
  id: 'custom',
  label: 'Custom…',
  width: 0,
  height: 0,
  auto: false,
  custom: true,
  description: `Set the width and height manually (${MIN_DESKTOP_WIDTH}–${MAX_DESKTOP_WIDTH} × ${MIN_DESKTOP_HEIGHT}–${MAX_DESKTOP_HEIGHT})`
}

/** Fixed sizes offered by the selector (`id` is `<width>x<height>`). */
export const DESKTOP_SIZE_PRESETS = [
  { id: '3840x2160', label: '3840 × 2160 (4K UHD)', width: 3840, height: 2160 },
  { id: '2560x1440', label: '2560 × 1440 (QHD)', width: 2560, height: 1440 },
  { id: '1920x1080', label: '1920 × 1080 (Full HD)', width: 1920, height: 1080 },
  { id: '1680x1050', label: '1680 × 1050 (16:10)', width: 1680, height: 1050 },
  { id: '1600x900', label: '1600 × 900 (HD+)', width: 1600, height: 900 },
  { id: '1440x900', label: '1440 × 900 (16:10)', width: 1440, height: 900 },
  { id: '1366x768', label: '1366 × 768 (laptop)', width: 1366, height: 768 },
  { id: '1280x1024', label: '1280 × 1024 (5:4)', width: 1280, height: 1024 },
  { id: '1280x720', label: '1280 × 720 (HD)', width: 1280, height: 720 },
  { id: '1024x768', label: '1024 × 768 (XGA)', width: 1024, height: 768 }
]

/**
 * Build the selector options.
 *
 * @param {Array} [presets] - `presets` returned by `GET /api/computers/desktop-sizes`.
 * @returns {Array} Options, `auto` first and `custom` last.
 */
export function desktopSizeOptions(presets) {
  const source = Array.isArray(presets) && presets.length ? presets : null
  if (!source) {
    return [
      AUTO_DESKTOP_SIZE,
      ...DESKTOP_SIZE_PRESETS.map(preset => ({ ...preset, auto: false, custom: false, description: '' })),
      CUSTOM_DESKTOP_SIZE
    ]
  }
  const options = source
    .map(item => ({
      id: String(item.id || ''),
      label: item.label || item.id || '',
      width: Number(item.width) || 0,
      height: Number(item.height) || 0,
      auto: !!item.auto,
      custom: !!item.custom,
      description: item.description || ''
    }))
    .filter(item => item.id)
  // The list comes from the backend, but the two special entries must exist:
  // without them the selector would lose its default (auto) or its manual mode.
  if (!options.some(option => option.auto)) options.unshift(AUTO_DESKTOP_SIZE)
  if (!options.some(option => option.custom)) options.push(CUSTOM_DESKTOP_SIZE)
  return options
}

/**
 * Id of the option matching the stored session settings.
 *
 * @param {Object} settings - `{ auto, width, height }`.
 * @param {Array} [options] - Selector options (defaults to the built-in presets).
 * @returns {string} `auto`, a preset id or `custom`.
 */
export function desktopSizeId(settings = {}, options = null) {
  if (settings.auto) return 'auto'
  const width = Number(settings.width) || 0
  const height = Number(settings.height) || 0
  const list = options || DESKTOP_SIZE_PRESETS
  const match = list.find(option => !option.auto && !option.custom
    && option.width === width && option.height === height)
  return match ? match.id : 'custom'
}

/**
 * Fields sent to the backend for a chosen option.
 *
 * With `auto` the width/height are kept as the startup size, so leaving auto
 * later returns to the size the user last saw instead of a random one.
 *
 * @param {Object} settings - `{ auto, width, height }`.
 * @returns {Object} `desktop_auto_resize`, `desktop_width` and `desktop_height`.
 */
export function desktopSizePayload({ auto = true, width = 0, height = 0 } = {}) {
  const currentWidth = Number(width) || 0
  const currentHeight = Number(height) || 0
  if (auto) {
    return {
      desktop_auto_resize: true,
      desktop_width: currentWidth || null,
      desktop_height: currentHeight || null
    }
  }
  return {
    desktop_auto_resize: false,
    desktop_width: currentWidth || DEFAULT_DESKTOP_WIDTH,
    desktop_height: currentHeight || DEFAULT_DESKTOP_HEIGHT
  }
}

/**
 * Validate a manual size.
 *
 * @param {Object} settings - `{ auto, width, height }`.
 * @returns {string|null} Error message, or null when the size is valid.
 */
export function validateDesktopSize({ auto = true, width = 0, height = 0 } = {}) {
  if (auto) return null
  const parsedWidth = Number(width)
  const parsedHeight = Number(height)
  if (!Number.isInteger(parsedWidth) || parsedWidth < MIN_DESKTOP_WIDTH || parsedWidth > MAX_DESKTOP_WIDTH) {
    return `Desktop width must be a whole number between ${MIN_DESKTOP_WIDTH} and ${MAX_DESKTOP_WIDTH}.`
  }
  if (!Number.isInteger(parsedHeight) || parsedHeight < MIN_DESKTOP_HEIGHT || parsedHeight > MAX_DESKTOP_HEIGHT) {
    return `Desktop height must be a whole number between ${MIN_DESKTOP_HEIGHT} and ${MAX_DESKTOP_HEIGHT}.`
  }
  return null
}

/**
 * Short human label of the current setting, used in the collapsed summary.
 *
 * @param {Object} settings - `{ auto, width, height }`.
 * @returns {string} e.g. `Auto`, `1920 × 1080` or `Custom`.
 */
export function formatDesktopSize({ auto = true, width = 0, height = 0 } = {}) {
  if (auto) return 'Auto'
  const parsedWidth = Number(width) || 0
  const parsedHeight = Number(height) || 0
  if (!parsedWidth || !parsedHeight) return 'Custom'
  return `${parsedWidth} × ${parsedHeight}`
}