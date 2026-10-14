/**
 * Google-Meet-style meeting code helpers.
 *
 * A meeting code is a short, human-friendly identifier that is easy to read
 * aloud and share: three letters, a dash, four letters, a dash and three more
 * letters (e.g. "abc-defg-hij").
 *
 * We use the code *itself* as the meet identifier, so the code is all the
 * backend needs to resolve a meet — "join by code" is simply "join by meetId".
 * Meets created earlier with arbitrary ids keep working: any value that is not
 * a valid code is returned unchanged so it can still act as a meet id.
 */

// Lowercase letters only, minus the visually ambiguous ones (l, i, o).
const CODE_ALPHABET = 'abcdefghjkmnpqrstuvwxyz'
const CODE_LENGTH = 10
const CODE_PATTERN = /^[a-z]{3}-[a-z]{4}-[a-z]{3}$/

function randomChunk(length) {
  let out = ''
  const crypto = typeof window !== 'undefined' ? window.crypto : null
  if (crypto?.getRandomValues) {
    const bytes = new Uint8Array(length)
    crypto.getRandomValues(bytes)
    for (let i = 0; i < length; i++) {
      out += CODE_ALPHABET[bytes[i] % CODE_ALPHABET.length]
    }
    return out
  }
  for (let i = 0; i < length; i++) {
    out += CODE_ALPHABET[Math.floor(Math.random() * CODE_ALPHABET.length)]
  }
  return out
}

/**
 * Generate a new, shareable meeting code, e.g. "abc-defg-hij".
 * @returns {string}
 */
export function generateMeetCode() {
  return `${randomChunk(3)}-${randomChunk(4)}-${randomChunk(3)}`
}

/**
 * Normalise user input into a canonical code (lowercase, grouped 3-4-3).
 *
 * If the input is not code-shaped (e.g. a legacy meet id such as
 * "meet_1731_ab12"), the trimmed raw value is returned so it can still be used
 * as a meet identifier.
 *
 * @param {string} input
 * @returns {string}
 */
export function normalizeMeetCode(input) {
  if (!input) return ''
  const raw = String(input).trim()
  const compact = raw.toLowerCase().replace(/[^a-z0-9]/g, '')
  if (compact.length === CODE_LENGTH && /^[a-z]+$/.test(compact)) {
    return `${compact.slice(0, 3)}-${compact.slice(3, 7)}-${compact.slice(7)}`
  }
  return raw
}

/**
 * True when the value is a valid, canonical meeting code.
 * @param {string} input
 * @returns {boolean}
 */
export function isValidMeetCode(input) {
  return CODE_PATTERN.test(normalizeMeetCode(input))
}

/**
 * Format a code (or meet id) for display. Valid codes are grouped as
 * "xxx-xxxx-xxx"; anything else is returned unchanged.
 * @param {string} input
 * @returns {string}
 */
export function formatMeetCode(input) {
  const code = normalizeMeetCode(input)
  return CODE_PATTERN.test(code) ? code : (input || '')
}

export default { generateMeetCode, normalizeMeetCode, isValidMeetCode, formatMeetCode }