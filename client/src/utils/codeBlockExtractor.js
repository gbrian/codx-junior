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
 */

// Opening tag: <file_change + at least one attribute on the same line
const FILE_CHANGE_OPEN_REGEX = /^<file_change\s/i
// Closing tag: <file_change/>, <file_change /> or </file_change>
const FILE_CHANGE_CLOSE_REGEX = /^<\/?file_change\s*\/?>\s*$/i
// Attributes: key="value" or key"value" (missing '=')
const FILE_CHANGE_ATTR_REGEX = /([A-Za-z_][\w-]*)\s*(?:=\s*)?"([^"]*)"/g
const LEGACY_FENCE_REGEX = /^```(\w+)\s+(.+)$/

/**
 * A `<file_change ...>` opening tag carries the metadata on the same line.
 */
function isFileChangeOpenTag(line) {
  if (!line) return false
  return FILE_CHANGE_OPEN_REGEX.test(line.trim())
}

/**
 * A closing marker is the whole line, either self-closed (`<file_change/>`)
 * or as a regular end tag (`</file_change>`).
 */
function isFileChangeCloseTag(line) {
  if (!line) return false
  return FILE_CHANGE_CLOSE_REGEX.test(line.trim())
}

/**
 * Parse the attributes of a `<file_change ...>` opening tag.
 * Keys are normalized to snake_case so `change-type`, `change_type` and
 * `changeType` all resolve to the same entry.
 */
function parseFileChangeAttributes(line) {
  const attrs = {}
  FILE_CHANGE_ATTR_REGEX.lastIndex = 0
  let match
  while ((match = FILE_CHANGE_ATTR_REGEX.exec(line))) {
    const key = match[1].toLowerCase().replace(/-/g, '_')
    attrs[key] = match[2]
  }
  return attrs
}

/**
 * Read a full `<file_change>` envelope starting at `startIndex` (the open tag).
 *
 * Returns { block, endIndex } where `endIndex` is the index of the closing
 * marker line (or the last available line when the block is still streaming).
 * Streaming friendly: a block whose closing marker has not arrived yet yields
 * whatever content is available so far.
 */
function readFileChangeBlock(lines, startIndex) {
  const attrs = parseFileChangeAttributes(lines[startIndex])

  let endIndex = lines.length
  for (let i = startIndex + 1; i < lines.length; i++) {
    if (isFileChangeCloseTag(lines[i])) {
      endIndex = i
      break
    }
  }

  const filePath = attrs.path || attrs.file || ''

  return {
    block: {
      language: attrs.language || 'text',
      filePath,
      content: lines.slice(startIndex + 1, endIndex).join('\n'),
      fileName: filePath ? filePath.split('/').pop() : '',
      changeType: attrs.change_type || attrs.changetype || 'update',
      encoding: attrs.encoding || 'text'
    },
    endIndex
  }
}

/**
 * Extracts code blocks with file paths from markdown content
 */
export function extractCodeBlocks(content) {
  if (!content || typeof content !== 'string') return []

  const codeBlocks = []
  const lines = content.split('\n')
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // <file_change> envelope (verbatim body, may contain code fences)
    if (isFileChangeOpenTag(line)) {
      const parsed = readFileChangeBlock(lines, i)
      if (parsed.block.filePath) codeBlocks.push(parsed.block)
      // Resume right after the closing marker (or after the last available line)
      i = parsed.endIndex + 1
      continue
    }

    const match = line.match(LEGACY_FENCE_REGEX)

    if (match) {
      const language = match[1]
      const filePath = match[2].trim()

      // Only include blocks with file paths
      if (filePath) {
        const blockContent = []
        i++

        // Collect lines until closing ```
        while (i < lines.length && lines[i] !== '```') {
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