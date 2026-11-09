import parser from './markdownParser.js'

const {
  getFence,
  createFenceTracker,
  trackFence,
  getFileChangeOpenTag,
  normalizeFileChangeTags,
  parseFileChangeBlock
} = parser

/**
 * Extracts code blocks with file paths from markdown content.
 *
 * Two syntaxes are supported:
 *
 *  1. Legacy fenced blocks carrying the file path on the info string:
 *
 *       ```language /path/to/file
 *       <content>
 *       ```
 *
 *  2. <file_change> envelopes, whose body is taken verbatim (it may itself
 *     contain code fences, headings, etc.):
 *
 *       <file_change path="<project-relative path>" language="<language id>" change_type="<new|update|delete>" encoding="text">
 *       <full file content, verbatim — markdown/fences allowed here>
 *       <file_change/>
 *
 *     The closing marker accepts both `<file_change/>` and `</file_change>`,
 *     and attributes may omit the `=` (`change_type"update"`) since models
 *     frequently drop it.
 *
 * Both produce the same block shape so consumers (FileView / PRView / chat
 * file lists) work unchanged.
 *
 * Block bounds are shared with markdownParser: envelopes are resolved by
 * `parseFileChangeBlock` (tags only, fences ignored) and legacy fences by the
 * same counter (`createFenceTracker` / `trackFence`), so both consumers agree
 * on where a block ends even when its body contains code fences or examples of
 * the envelope itself.
 */

// Legacy opening fence: ```lang /path/to/file
const LEGACY_FENCE_REGEX = /^ {0,3}```(\w+)\s+(.+)$/

/**
 * Extracts code blocks with file paths from markdown content
 */
export function extractCodeBlocks(content) {
  if (!content || typeof content !== 'string') return []

  // Markers glued to prose are moved onto their own lines first (no-op otherwise)
  content = normalizeFileChangeTags(content)

  const codeBlocks = []
  const lines = content.split('\n')
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // <file_change> envelope (verbatim body, every fence inside is content)
    if (getFileChangeOpenTag(line)) {
      const { block, endIndex } = parseFileChangeBlock(lines, i)
      if (block.filePath) {
        codeBlocks.push({
          language: block.type,
          filePath: block.filePath,
          content: block.content,
          fileName: block.filePath.split('/').pop(),
          changeType: block.fileChangeType,
          encoding: block.encoding
        })
      }
      // Resume right after the closing marker (or after the last available line)
      i = endIndex + 1
      continue
    }

    // Strip the CR of CRLF sources for the anchored fence match; content lines
    // below keep their original bytes.
    const match = line.replace(/\r$/, '').match(LEGACY_FENCE_REGEX)

    // A fenced block WITHOUT a path is still a fence: skip its body so a
    // <file_change> example inside it is never extracted as a real file.
    if (!match) {
      const fence = getFence(line)
      if (fence && fence.info) {
        const tracker = createFenceTracker(fence)
        i++
        while (i < lines.length) {
          const innerFence = getFence(lines[i])
          if (innerFence && trackFence(tracker, innerFence) === 'close') break
          i++
        }
      }
      i++
      continue
    }

    if (match) {
      const language = match[1]
      const filePath = match[2].trim()
      const fence = getFence(line)

      // Only include blocks with file paths
      if (filePath && fence) {
        // Counter instead of a while/string compare: nested fences increase the
        // counter, only a closing fence of the same delimiter (and at least as
        // long as the innermost open fence) decreases it. The old
        // `lines[i] !== '```'` check broke on trailing spaces, the '\r' of CRLF
        // content, longer fences and ~~~ closers, swallowing the rest of the
        // message.
        const tracker = createFenceTracker(fence)
        const blockContent = []
        i++

        while (i < lines.length) {
          const innerFence = getFence(lines[i])
          if (innerFence && trackFence(tracker, innerFence) === 'close') break
          blockContent.push(lines[i])
          i++
        }

        codeBlocks.push({
          language,
          filePath,
          content: blockContent.join('\n'),
          fileName: filePath.split('/').pop()
        })
      }
    }
    i++
  }

  return codeBlocks
}

/**
 * Checks if content has extractable code blocks with file paths
 */
export function hasCodeBlocksWithPaths(content) {
  return extractCodeBlocks(content).length > 0
}
