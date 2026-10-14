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
 *  2. CODX sentinel file blocks, whose body is taken verbatim (it may itself
 *     contain fences, headings, etc.):
 *
 *       @@ CODX_FILE @@
 *       path: <project-relative path>
 *       language: <language id>
 *       change_type: <new|update|delete>
 *       encoding: text
 *       @@ CODX_CONTENT @@
 *       <content>
 *       @@ CODX_END @@
 *
 * Both produce the same block shape so consumers (FileView / PRView / chat
 * file lists) work unchanged.
 */

const CODX_MARKER_REGEX = /^@{2}\s+CODX_(FILE|CONTENT|END)\s+@{2}$/
const LEGACY_FENCE_REGEX = /^```(\w+)\s+(.+)$/

/**
 * Detect a CODX sentinel marker on a single line.
 * Returns 'file' | 'content' | 'end' | null
 */
function getCodedFileMarker(line) {
  if (line?.indexOf('@') !== 0) return null
  const match = line.trim().match(CODX_MARKER_REGEX)
  if (!match) return null
  if (match[1] === 'FILE') return 'file'
  if (match[1] === 'CONTENT') return 'content'
  return 'end'
}

/**
 * Parse a single "key: value" metadata line found between the FILE and
 * CONTENT markers.
 */
function parseCodedFileMetaLine(line) {
  const match = line.match(/^\s*([A-Za-z_][\w-]*)\s*:\s*(.*?)\s*$/)
  if (!match) return null
  return { key: match[1].toLowerCase().replace(/-/g, '_'), value: match[2] }
}

/**
 * Read a full CODX file block starting at `startIndex` (the FILE marker).
 *
 * Returns { block, endIndex } where `endIndex` is the index of the last
 * consumed line, or null when the start marker is malformed (nested start).
 * Streaming friendly: a block whose CONTENT/END markers have not arrived yet
 * yields whatever content is available so far.
 */
function readCodedFileBlock(lines, startIndex) {
  const meta = {}
  let i = startIndex + 1
  let contentStart = -1
  let contentEnd = -1

  while (i < lines.length) {
    const marker = getCodedFileMarker(lines[i])
    if (marker === 'content') {
      contentStart = i + 1
      break
    }
    if (marker === 'end') {
      // Empty body: the CONTENT marker was omitted
      contentStart = i
      contentEnd = i
      break
    }
    if (marker === 'file') {
      // Malformed: a new block opened before this one closed
      return null
    }
    const parsed = parseCodedFileMetaLine(lines[i])
    if (parsed) meta[parsed.key] = parsed.value
    i++
  }

  if (contentStart === -1) {
    // Metadata still streaming - no CONTENT marker yet
    contentStart = lines.length
    contentEnd = lines.length
  } else if (contentEnd === -1) {
    // Find the END marker from the content start
    for (let j = contentStart; j < lines.length; j++) {
      if (getCodedFileMarker(lines[j]) === 'end') {
        contentEnd = j
        break
      }
    }
    if (contentEnd === -1) contentEnd = lines.length
  }

  const filePath = meta.path || meta.file || ''
  const language = meta.language || 'text'

  return {
    block: {
      language,
      filePath,
      content: lines.slice(contentStart, contentEnd).join('\n'),
      fileName: filePath ? filePath.split('/').pop() : ''
    },
    endIndex: contentEnd
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

    // CODX sentinel file block (verbatim body, may contain code fences)
    if (getCodedFileMarker(line) === 'file') {
      const coded = readCodedFileBlock(lines, i)
      if (coded) {
        if (coded.block.filePath) codeBlocks.push(coded.block)
        // Resume right after the END marker (or after the last available line)
        i = coded.endIndex + 1
        continue
      }
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