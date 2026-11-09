/**
 * Hash generator for stable block keys
 */
function generateHash(str) {
  let hash = 0
  for (const char of str) {
    hash = (hash << 5) - hash + char.charCodeAt(0)
    hash |= 0
  }
  return hash
}

/**
 * Heading detection helpers
 */
function isHeading(line) {
  return /^#{1,6}\s+/.test(line)
}

function getHeadingLevel(line) {
  const match = line.match(/^(#+)\s+/)
  return match ? match[1].length : 0
}

function getHeadingText(line) {
  return line.replace(/^#+\s+/, '').trim()
}

function getHeaderLine(content) {
  const lines = content.split('\n')
  return lines.length > 0 && isHeading(lines[0]) ? lines[0] : ''
}

function isMarkdownBlockType(blockType) {
  return ['markdown', 'md', 'text'].includes(blockType)
}

/**
 * Get common file extension for language
 */
function getExtensionForLanguage(language) {
  const extensions = {
    'js': 'js',
    'javascript': 'js',
    'ts': 'ts',
    'typescript': 'ts',
    'python': 'py',
    'py': 'py',
    'java': 'java',
    'c': 'c',
    'cpp': 'cpp',
    'csharp': 'cs',
    'cs': 'cs',
    'php': 'php',
    'ruby': 'rb',
    'rb': 'rb',
    'go': 'go',
    'rust': 'rs',
    'rs': 'rs',
    'html': 'html',
    'css': 'css',
    'scss': 'scss',
    'json': 'json',
    'yaml': 'yaml',
    'yml': 'yml',
    'xml': 'xml',
    'sql': 'sql',
    'bash': 'sh',
    'sh': 'sh',
    'shell': 'sh',
    'vue': 'vue',
    'react': 'jsx',
    'jsx': 'jsx',
    'tsx': 'tsx'
  }
  return extensions[language.toLowerCase()] || language.toLowerCase()
}

/**
 * Generate synthetic filename from language type
 */
function generateFileName(language) {
  if (!language || language === 'text') return 'content.txt'
  const ext = getExtensionForLanguage(language)
  return `content.${ext}`
}

/**
 * Strip first heading line from content
 */
function stripHeaderFromContent(content) {
  const lines = content.split('\n')
  if (lines.length > 0 && isHeading(lines[0])) {
    return lines.slice(1).join('\n').trim()
  }
  return content
}

/**
 * Chapter body without the heading line, preserving every other line verbatim.
 *
 * Unlike stripHeaderFromContent this does NOT trim, so block line offsets stay
 * aligned with the chapter source (required to save a block in place).
 */
function getChapterBody(content) {
  const lines = String(content ?? '').split('\n')
  return lines.length > 0 && isHeading(lines[0]) ? lines.slice(1).join('\n') : String(content ?? '')
}

/**
 * Select renderer based on block type and file path
 */
function getRenderer(blockType, fileName) {
  if (fileName) return 'code'
  if (blockType === 'markdown' || blockType === 'md') return 'md'
  if (blockType === 'html') return blockType
  return 'code'
}

/**
 * Detect fence markers (``` or ~~~) with optional info string
 */
function getFence(line) {
  // CRLF sources keep the '\r' after splitting on '\n'; it must not stop the
  // anchored match (and must never leak into the info string).
  const match = String(line ?? '').replace(/\r$/, '').match(/^( {0,3})(`{3,}|~{3,})(.*)$/)
  if (!match) return null
  return {
    char: match[2][0],
    length: match[2].length,
    info: match[3].trim()
  }
}

/**
 * Check if a line is a valid closing fence for the given opening fence.
 * A closing fence must:
 * - Use the same character (` or ~)
 * - Have length >= opening fence length
 * - Have no info string
 */
function isClosingFence(line, fence) {
  const lineFence = getFence(line)
  return !!(
    lineFence &&
    fence &&
    lineFence.char === fence.char &&
    lineFence.length >= fence.length &&
    !lineFence.info
  )
}

/**
 * Count matching closing fences ahead from index
 */
function countClosingFencesAhead(lines, fromIndex, fence) {
  let count = 0
  for (let i = fromIndex + 1; i < lines.length; i++) {
    if (isClosingFence(lines[i], fence)) count++
  }
  return count
}

/**
 * Decide if an anonymous fence should open a nested block or close the outer one
 */
function isNestedAnonymousFence(lines, index, currentType, currentFence) {
  const isMarkdownBlock = isMarkdownBlockType(currentType)
  return isMarkdownBlock && countClosingFencesAhead(lines, index, currentFence) >= 2
}

/**
 * Fenced block tracker
 * -------------------------------------------------------------------------
 * A fenced block is tracked with a COUNTER, never with a flag: `lengths`
 * holds one entry per open fence of the block's own delimiter, so nesting is
 * additive and the block only ends when the counter returns to zero.
 *
 * - Opening fences of the same delimiter are counted (their closing fence must
 *   NOT end the outer block).
 * - Closing fences are bare runs: they must use the same delimiter and be at
 *   least as long as the innermost open fence.
 * - Everything else (the other delimiter, `<file_change>` tags, plain text) is
 *   body content and never touches the counter.
 */

/**
 * Language/type of a fence: first word of its info string, lowercased.
 */
function getFenceType(fence) {
  if (!fence || !fence.info) return ''
  return fence.info.split(/\s+/)[0].toLowerCase()
}

/**
 * Create the counter of a block opened by `openFence`.
 */
function createFenceTracker(openFence) {
  return {
    char: openFence.char,
    type: getFenceType(openFence),
    lengths: [openFence.length]
  }
}

/**
 * Feed the fence found on a line into the tracker of the open block.
 *
 * Returns 'close' when the outermost fence closes (the block ends) and
 * 'content' when the line belongs to the body (nested fences included).
 */
function trackFence(tracker, lineFence) {
  if (!tracker || !lineFence || lineFence.char !== tracker.char) return 'content'

  if (!lineFence.info) {
    // Closing fence: must reach the innermost open fence length
    const innermost = tracker.lengths[tracker.lengths.length - 1]
    if (lineFence.length < innermost) return 'content'
    tracker.lengths.pop()
    return tracker.lengths.length ? 'content' : 'close'
  }

  // Opening fence of the same delimiter: count it, so its own closing fence
  // does not end the outer block
  tracker.lengths.push(lineFence.length)
  return 'content'
}

/**
 * File change XML syntax
 * -------------------------------------------------------------------------
 * In addition to legacy ```lang path fences, markdown may carry file blocks
 * wrapped in an XML envelope:
 *
 *   <file_change path="<project-relative path>" language="<language id>" change_type="<new|update|delete>" encoding="text">
 *   <full file content, verbatim - may itself contain code fences or headings>
 *   <file_change/>
 *
 * The body is taken verbatim, so nested ``` fences (and even heading-looking
 * lines) never leak out of the block. Both the self-closing `<file_change/>`
 * and the regular `</file_change>` closing tags are accepted, and attributes
 * may omit the `=` (`change_type"update"`) since models frequently drop it.
 *
 * A <file_change> block IGNORES EVERY OTHER FENCE KIND: while it is open, ```
 * and ~~~ lines are plain content and can neither open nor close nor mask
 * anything. Only the tags move the DEPTH COUNTER: the envelope being parsed is
 * depth 1, a nested `<file_change ...>` adds one and every closing marker
 * removes one; the block ends when the count returns to zero. Nested envelopes
 * are therefore verbatim content of the outer block, never separate blocks.
 */

// Opening tag: <file_change + at least one attribute on the same line.
// Indented up to 3 spaces like a markdown fence, never deeper (an example
// indented by 4+ spaces is an indented code block, not an envelope).
const FILE_CHANGE_OPEN_REGEX = /^ {0,3}<file_change\s/i
// Closing tag: <file_change/>, <file_change /> or </file_change>
const FILE_CHANGE_CLOSE_REGEX = /^ {0,3}<\/?file_change\s*\/?>\s*$/i
// Attributes: key="value" or key"value" (missing '=')
const FILE_CHANGE_ATTR_REGEX = /([A-Za-z_][\w-]*)\s*(?:=\s*)?"([^"]*)"/g

/**
 * Parse the attributes of a `<file_change ...>` opening tag.
 * Keys are normalized to snake_case so `change-type`, `change_type` and
 * `changeType` all resolve to the same entry.
 */
function parseFileChangeAttributes(line) {
  const attrs = {}
  if (!line) return attrs
  FILE_CHANGE_ATTR_REGEX.lastIndex = 0
  let match
  while ((match = FILE_CHANGE_ATTR_REGEX.exec(line))) {
    const key = match[1].toLowerCase().replace(/-/g, '_')
    attrs[key] = match[2]
  }
  return attrs
}

/**
 * Detect a `<file_change ...>` opening tag and return its attributes.
 * Returns null when the line is not an opening tag.
 */
function getFileChangeOpenTag(line) {
  if (!line) return null
  if (!FILE_CHANGE_OPEN_REGEX.test(line)) return null
  return parseFileChangeAttributes(line)
}

/**
 * A closing marker is the whole line, either self-closed (`<file_change/>`)
 * or as a regular end tag (`</file_change>`).
 */
function isFileChangeCloseTag(line) {
  if (!line) return false
  return FILE_CHANGE_CLOSE_REGEX.test(line)
}

/**
 * Normalization of <file_change> tags
 * -------------------------------------------------------------------------
 * Model output frequently glues prose and markers on a single line:
 *
 *   Here it is: <file_change path="a.md" ...>const a = 1<file_change/> Done.
 *
 * Both tag regexes used by the parser are ANCHORED (`^ ... $`), so a glued
 * marker is invisible to them: the envelope is not detected at all (the raw
 * tag is rendered in the chat) or the block never closes and swallows the rest
 * of the message. This pre-pass moves every marker onto its own line while
 * leaving verbatim regions untouched:
 *
 *  - fenced blocks:   a fenced example documents the syntax, never a real file
 *  - envelope bodies: the body is the file content
 *
 * Boundaries are located with getFileChangeOpenTag / isFileChangeCloseTag, the
 * very helpers used by parseFileChangeBlock, so normalizer and parser can never
 * disagree about where a block starts or ends. The pass is idempotent, so it is
 * safe to run on content that has already been normalized.
 */

// Any complete tag anywhere in a line (used only to locate markers in prose)
const FILE_CHANGE_ANY_TAG_REGEX = /<\/?file_change\b[^>]*>/gi

// One-entry memo: chat content is re-parsed on every streaming chunk
let normalizeCache = { input: null, output: null }

/** True when `index` sits inside an inline code span (`...`). */
function isInsideInlineCode(line, index) {
  let ticks = 0
  for (let i = 0; i < index; i++) if (line[i] === '`') ticks++
  return ticks % 2 === 1
}

/**
 * Split a line into text/tag pieces.
 * Returns null when the line carries no promotable marker, so the caller can
 * push it through byte-identically.
 */
function splitFileChangePieces(line) {
  FILE_CHANGE_ANY_TAG_REGEX.lastIndex = 0
  const pieces = []
  let cursor = 0
  let found = false
  let match

  while ((match = FILE_CHANGE_ANY_TAG_REGEX.exec(line))) {
    const start = match.index
    const tag = match[0].trim()
    const prefix = line.slice(cursor, start)

    // Only real markers are promoted: a `<file_change>` without attributes or
    // a lookalike is prose the parser ignores as well.
    if (!isFileChangeCloseTag(tag) && !getFileChangeOpenTag(tag)) continue

    // Guards: escaped marker, inline-code mention, indented code block example
    if (prefix.endsWith('\\')) continue
    if (isInsideInlineCode(line, start)) continue
    if (!prefix.trim() && prefix.length >= 4) continue

    found = true
    if (prefix.trim()) pieces.push({ type: 'text', text: prefix })
    pieces.push({ type: 'tag', text: tag })
    cursor = start + match[0].length
  }

  if (!found) return null
  const rest = line.slice(cursor)
  if (rest.trim()) pieces.push({ type: 'text', text: rest })
  return pieces
}

/**
 * Make every <file_change> open/close marker the only content of its line.
 *
 * States:
 *  - prose:    markers are located and split onto their own lines
 *  - fence:    lines are verbatim (a fenced example documents the syntax)
 *  - envelope: lines are verbatim; only a marker glued to text is split, so
 *              the depth counter of parseFileChangeBlock keeps balancing
 *
 * Detection ignores the trailing '\r' of CRLF lines while the output keeps it,
 * so file line endings are never rewritten.
 */
function normalizeFileChangeTags(content) {
  if (!content || typeof content !== 'string') return content || ''
  if (!/<\/?file_change/i.test(content)) return content
  if (normalizeCache.input === content) return normalizeCache.output

  const lines = content.split('\n')
  const output = []
  let mode = 'prose'
  let fenceTracker = null
  let envelopeDepth = 0

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const scan = line.endsWith('\r') ? line.slice(0, -1) : line

    if (mode === 'fence') {
      output.push(line)
      const fence = getFence(scan)
      if (fence && trackFence(fenceTracker, fence) === 'close') {
        mode = 'prose'
        fenceTracker = null
      }
      continue
    }

    // Outside an envelope a fence opens a verbatim region. Bare fences are
    // included on purpose: protecting an example is always safer than
    // promoting a marker that lives inside it.
    if (mode === 'prose') {
      const fence = getFence(scan)
      if (fence) {
        output.push(line)
        fenceTracker = createFenceTracker(fence)
        mode = 'fence'
        continue
      }
    }

    const pieces = splitFileChangePieces(scan)
    if (!pieces) {
      output.push(line)
      continue
    }

    for (const piece of pieces) {
      // Keep the '\r' that was stripped from the scanned line
      output.push(scan === line ? piece.text : `${piece.text}\r`)
      if (piece.type !== 'tag') continue

      if (isFileChangeCloseTag(piece.text)) {
        if (mode === 'envelope') {
          envelopeDepth--
          if (envelopeDepth <= 0) mode = 'prose'
        }
      } else if (mode === 'envelope') {
        envelopeDepth++
      } else {
        mode = 'envelope'
        envelopeDepth = 1
      }
    }
  }

  const normalized = output.join('\n')
  normalizeCache = { input: content, output: normalized }
  return normalized
}

/**
 * Parse a full `<file_change>` envelope starting at `startIndex` (the open tag).
 *
 * Returns { block, endIndex } where `endIndex` is the index of the closing
 * marker line (or the last available line while the block is still streaming).
 * Streaming friendly: a block whose closing marker has not arrived yet yields
 * whatever content is available so far with finished=false.
 *
 * Only `<file_change>` tags are counted: every fence (``` / ~~~, any language)
 * inside the body is content and can never end the block, which is what makes
 * the boundary deterministic even for a document that shows markdown examples.
 */
function parseFileChangeBlock(lines, startIndex, getRendererFn = getRenderer) {
  const attrs = parseFileChangeAttributes(lines[startIndex])

  let endIndex = lines.length
  // Depth counter instead of a flag: the envelope being parsed is depth 1, a
  // nested `<file_change ...>` adds one and every closing marker removes one.
  // The block only ends when the count reaches zero.
  let depth = 1
  // Last closing marker seen, used as a safety valve for a body that never
  // balances (an opening-tag example with no closing marker).
  let lastCloseIndex = null

  for (let i = startIndex + 1; i < lines.length; i++) {
    const line = lines[i]

    // While a <file_change> block is open, other fences are content only: no
    // getFence() call happens here on purpose.
    if (getFileChangeOpenTag(line)) {
      depth++
      continue
    }

    if (!isFileChangeCloseTag(line)) continue

    depth--
    lastCloseIndex = i
    if (depth === 0) {
      endIndex = i
      break
    }
  }

  // Unbalanced body: end at the last closing marker seen so a stray example of
  // the opening tag can never swallow the rest of the message.
  if (depth > 0 && lastCloseIndex !== null) {
    endIndex = lastCloseIndex
  }

  const finished = endIndex < lines.length
  const content = lines.slice(startIndex + 1, endIndex).join('\n')
  const language = attrs.language || 'text'
  const filePath = attrs.path || attrs.file || ''
  const fileName = filePath || generateFileName(language)

  const block = {
    type: language,
    content,
    // Source span of the body (line indices, end exclusive) so an editor can
    // replace exactly this block in the original markdown without touching a
    // duplicate elsewhere in the message.
    bodyStartLine: startIndex + 1,
    bodyEndLine: endIndex,
    // Finished blocks hash by content (stable once closed); open blocks hash
    // by structural identity so the Vue :key does not change while streaming.
    hash: finished ? generateHash(content) : generateHash(`${language}:${fileName}`),
    fileName,
    filePath,
    renderer: getRendererFn(language, fileName),
    finished,
    // Marks a block that came from the XML envelope (always rendered as code)
    isFileBlock: true,
    fileChangeType: attrs.change_type || 'update',
    encoding: attrs.encoding || 'text'
  }

  return { block, endIndex: finished ? endIndex : lines.length - 1 }
}

/**
 * Rewrite every `<file_change>` envelope into a standard fenced code block so
 * plain markdown renderers (markdown-it) display it highlighted, with the same
 * file path info string used by legacy blocks.
 *
 * The fence length adapts to the body, so nested ``` fences stay verbatim
 * inside the generated block.
 */
function fileChangeBlocksToFences(content) {
  if (!content || typeof content !== 'string') return content

  // Markers glued to prose are moved onto their own lines first (no-op otherwise)
  content = normalizeFileChangeTags(content)

  const lines = content.split('\n')
  const output = []
  let i = 0

  while (i < lines.length) {
    if (!getFileChangeOpenTag(lines[i])) {
      output.push(lines[i])
      i++
      continue
    }

    const { block, endIndex } = parseFileChangeBlock(lines, i)
    const longestRun = (block.content.match(/`{3,}/g) || [])
      .reduce((max, run) => Math.max(max, run.length), 0)
    const fence = '`'.repeat(Math.max(3, longestRun + 1))
    const info = [block.type, block.filePath].filter(Boolean).join(' ')

    output.push(`${fence}${info}`)
    if (block.content.length) output.push(block.content)
    output.push(fence)

    i = endIndex + 1
  }

  return output.join('\n')
}

/**
 * Check if position is inside a code fence (any nesting level) OR inside a
 * `<file_change>` envelope (whose body is verbatim and must not be re-parsed).
 *
 * Uses the same counter rules as parseBlocks, so both agree on block bounds.
 */
function isInsideCodeFence(lines, lineIndex) {
  let fenceTracker = null

  for (let i = 0; i < lineIndex; i++) {
    const line = lines[i]

    // A <file_change> block hides its whole body (headings included) and
    // ignores fences, so it is resolved in a single step by the shared parser.
    if (!fenceTracker && getFileChangeOpenTag(line)) {
      const { endIndex } = parseFileChangeBlock(lines, i)
      if (endIndex >= lineIndex) return true
      i = endIndex
      continue
    }

    const fence = getFence(line)
    if (!fence) continue

    if (!fenceTracker) {
      // Only a fence with an info string opens a block (parseBlocks rule)
      if (fence.info) fenceTracker = createFenceTracker(fence)
      continue
    }

    if (trackFence(fenceTracker, fence) === 'close') fenceTracker = null
  }

  return !!fenceTracker
}

/**
 * Parse content string into typed blocks with fence handling.
 *
 * CORE BEHAVIOR:
 * - A block opened by a fence keeps that fence's delimiter: only closing
 *   fences of the same delimiter can end it, nested fences of the same
 *   delimiter are counted, and any other kind of fence is content.
 * - This handles cases like a py file containing a mermaid diagram in its
 *   docstring: the inner ```mermaid...``` does not close the outer ```py block.
 * - `<file_change ...> ... <file_change/>` envelopes are parsed as verbatim
 *   file blocks: inside them EVERY fence is content, so neither a ``` line nor
 *   a nested envelope can end the block early. Legacy ```lang path fences keep
 *   working as fallback.
 *
 * COUNTERS, NOT FLAGS:
 * - Fenced blocks use a tracker whose `lengths` counter grows with nested
 *   opening fences and shrinks with matching closing fences.
 * - Envelopes use a tag depth counter (see parseFileChangeBlock).
 *
 * KEY STABILITY DURING STREAMING:
 * - Finished blocks use content-based hash (stable once closed)
 * - Open/streaming blocks use a structural hash so Vue :key stays stable
 *
 * SINGLE-LINE CONTENT FIX:
 * - All non-empty content generates at least one block
 * - Plain markdown (no fences) defaults to type='markdown'
 *
 * MARKDOWN FENCES AS CODE BLOCKS:
 * - Fenced blocks tagged markdown/md/text get a synthetic fileName like every
 *   other fenced block, so they render through the Code component (highlighted
 *   code) instead of being re-rendered as markdown. Plain prose (no fence) is
 *   left as markdown so it keeps normal document formatting.
 */
function parseBlocks(content, getRendererFn = getRenderer) {
  // Markers glued to prose are moved onto their own lines first (no-op otherwise)
  content = normalizeFileChangeTags(content)

  const blocks = []
  const lines = content.split('\n')
  let currentType = 'markdown'
  let currentContent = []
  let currentFileName = ''
  let isAnonymousFence = false
  let blockIndex = 0
  // Source span of the markdown block being collected (line indices, end
  // exclusive). Every block keeps its own span so an editor can rewrite the
  // exact lines it owns instead of guessing by content (duplicate blocks are
  // common: two identical fenced snippets in one message).
  let currentStartLine = 0
  let currentEndLine = 0
  // First body line of the fenced block currently being collected.
  let fenceBodyStartLine = 0
  // Counter of the fenced block currently open (null when not inside a fence).
  let fenceTracker = null
  // Tracks whether the block being built originates from a fence (```...```).
  // Used so fenced markdown/md/text blocks also become code blocks.
  let currentIsFence = false

  function addBlock(isFinished = false, startLine = currentStartLine, endLine = currentEndLine) {
    const blockContent = currentContent.join('\n')
    const trimmedContent = blockContent.trim()

    if (!trimmedContent) {
      resetBlock()
      return
    }

    let finalFileName = currentFileName
    let finalType = currentType

    // Generate a synthetic fileName when the block comes from a fence (any
    // language, including markdown/md/text) OR when its type is a real
    // language. This routes fenced markdown blocks through the Code component
    // so they render as code blocks as well, while plain prose (no fence)
    // keeps rendering as markdown.
    if (finalType && !finalFileName && !isAnonymousFence && (currentIsFence || !isMarkdownBlockType(finalType))) {
      finalFileName = generateFileName(finalType)
    }

    const contentHash = generateHash(blockContent)

    blocks.push({
      type: finalType,
      content: blockContent,
      bodyStartLine: startLine,
      bodyEndLine: endLine,
      hash: contentHash,
      fileName: finalFileName,
      renderer: getRendererFn(finalType, finalFileName),
      finished: isFinished
    })

    blockIndex++
    resetBlock()
  }

  function resetBlock() {
    currentType = 'markdown'
    currentContent = []
    currentFileName = ''
    isAnonymousFence = false
    currentIsFence = false
    currentStartLine = 0
    currentEndLine = 0
  }

  function pushContent(line, lineIndex) {
    if (!currentContent.length) currentStartLine = lineIndex
    currentContent.push(line)
    currentEndLine = lineIndex + 1
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    // <file_change> envelope takes priority when not already inside a fence
    if (!fenceTracker && getFileChangeOpenTag(line)) {
      if (blocks.length > 0) {
        blocks[blocks.length - 1].finished = true
      }
      if (currentContent.length) addBlock(true, currentStartLine, i)
      const fileChange = parseFileChangeBlock(lines, i, getRendererFn)
      blocks.push(fileChange.block)
      blockIndex++
      i = fileChange.endIndex
      continue
    }

    const fence = getFence(line)

    // Inside a fenced block: the tracker counts only fences of the block's own
    // delimiter. Everything else (other delimiter, tags, text) is content.
    if (fenceTracker) {
      if (fence && trackFence(fenceTracker, fence) === 'close') {
        addBlock(true, fenceBodyStartLine, i)
        fenceTracker = null
      } else {
        pushContent(line, i)
      }
      continue
    }

    // Outside any block only a fence with an info string opens a block; a bare
    // fence is markdown content (same rule in DocumentSummary/isInsideCodeFence)
    if (fence && fence.info) {
      // Mark previous block finished when a new fence opens
      if (blocks.length > 0) {
        blocks[blocks.length - 1].finished = true
      }

      if (currentContent.length) addBlock(true, currentStartLine, i)

      fenceTracker = createFenceTracker(fence)
      fenceBodyStartLine = i + 1
      const parts = fence.info.split(/\s+/).filter(Boolean)
      currentType = fenceTracker.type || parts[0] || 'text'
      currentFileName = parts[1] || ''
      isAnonymousFence = false
      currentIsFence = true
      continue
    }

    pushContent(line, i)
  }

  if (currentContent.length) {
    // A fenced block that never closes (still streaming) owns every line up to
    // EOF; a plain markdown block does as well.
    addBlock(false, fenceTracker ? fenceBodyStartLine : currentStartLine, lines.length)
  }

  // All blocks except the last are finished. File change blocks keep the
  // finished flag resolved during parsing so an open (streaming) file block
  // is not force-completed.
  for (let i = 0; i < blocks.length - 1; i++) {
    if (!blocks[i].isFileBlock) {
      blocks[i].finished = true
    }
  }

  return blocks
}

/**
 * Replace the body of the block at `blockIndex` with `newContent`.
 *
 * The replacement targets the line span recorded by parseBlocks, so an
 * identical block elsewhere in the document is never touched. Returns the
 * original content when the index is out of range.
 */
function replaceBlockContent(content, blockIndex, newContent) {
  const source = String(content ?? '')
  const normalized = normalizeFileChangeTags(source)
  const blocks = parseBlocks(normalized)
  const block = blocks[blockIndex]
  if (!block || block.bodyStartLine == null || block.bodyEndLine == null) {
    return source
  }

  const lines = normalized.split('\n')
  const replacement = String(newContent ?? '').split('\n')
  lines.splice(block.bodyStartLine, block.bodyEndLine - block.bodyStartLine, ...replacement)
  return lines.join('\n')
}

/**
 * Replace a block inside a chapter's content (heading preserved, body only).
 */
function replaceBlockInChapterContent(chapterContent, blockIndex, newContent) {
  const source = String(chapterContent ?? '')
  const lines = source.split('\n')
  const hasHeader = lines.length > 0 && isHeading(lines[0])
  const header = hasHeader ? lines[0] : null
  const body = hasHeader ? lines.slice(1).join('\n') : source
  const nextBody = replaceBlockContent(body, blockIndex, newContent)
  if (!hasHeader) return nextBody
  return `${header}\n${nextBody}`
}

/**
 * Serialize a parsed chapter tree back to markdown.
 *
 * `override` lets a caller replace one chapter (and optionally its children)
 * without touching the rest of the document:
 *   { path: [0, 2], content: '...', replaceChildren: true }
 *
 * The parse tree keeps a chapter's own lines separately from its children, so
 * joining them with newlines reproduces the original source (blank lines that
 * separated a section from its first child are part of the parent content).
 */
function serializeChapters(chapters, override = null) {
  const list = chapters || []
  return list
    .map((chapter, index) => serializeChapter(chapter, [index], override))
    .join('\n')
}

function serializeChapter(chapter, path, override) {
  const isTarget = !!override?.path &&
    override.path.length === path.length &&
    override.path.every((part, index) => part === path[index])

  const ownContent = isTarget ? override.content : chapter.content
  if (isTarget && override.replaceChildren) return ownContent

  const parts = [ownContent]
  const children = chapter.children || []
  children.forEach((child, index) => {
    parts.push(serializeChapter(child, [...path, index], override))
  })
  return parts.join('\n')
}

/**
 * Collect full markdown output of a chapter with children
 */
function collectAllChildContent(chapter) {
  const headerLine = getHeaderLine(chapter.content.split('\n')[0])
  let contentWithoutHeader = stripHeaderFromContent(chapter.content || '')
  let allContent = contentWithoutHeader

  if (chapter.children && chapter.children.length > 0) {
    for (let i = 0; i < chapter.children.length; i++) {
      const childFullContent = collectAllChildContent(chapter.children[i])
      allContent += '\n' + childFullContent
    }
  }

  return headerLine ? headerLine + '\n\n' + allContent : allContent
}

/**
 * Parse content into chapter objects with nested children
 */
function parseChapters(content, loading) {
  // Markers glued to prose are moved onto their own lines first (no-op otherwise)
  content = normalizeFileChangeTags(content)

  const lines = content.split('\n')
  const chapters = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    if (isHeading(line) && !isInsideCodeFence(lines, i)) {
      const chapter = parseChapter(lines, i)
      chapters.push(chapter)
      i = chapter.endIndex
    } else if (!chapters.length) {
      const noHeadingContent = []
      while (i < lines.length && (!isHeading(lines[i]) || isInsideCodeFence(lines, i))) {
        noHeadingContent.push(lines[i])
        i++
      }
      const fullContent = noHeadingContent.join('\n').trim()
      if (fullContent) {
        chapters.push({
          level: 0,
          title: null,
          content: fullContent,
          children: [],
          hash: generateHash(fullContent),
          finished: false
        })
      }
    } else {
      i++
    }
  }

  if (!loading) {
    markAllFinished(chapters)
  } else if (chapters.length > 0) {
    markLastUnfinished(chapters)
  }

  return chapters
}

/**
 * Parse a single chapter from lines, including child/chapter sections
 */
function parseChapter(lines, startIndex) {
  const headingLine = lines[startIndex]
  const level = getHeadingLevel(headingLine)
  const title = getHeadingText(headingLine)
  const content = [headingLine]
  const children = []
  let i = startIndex + 1

  while (i < lines.length) {
    const line = lines[i]

    if (isHeading(line) && !isInsideCodeFence(lines, i)) {
      const nextLevel = getHeadingLevel(line)

      if (nextLevel <= level) break

      // Any deeper heading becomes a child chapter, even when levels are
      // skipped (e.g. "## A" followed by "#### B"). This guarantees EVERY
      // heading renders as its own ChapterBlock, so it always exposes the
      // copy / create-task / edit menu instead of being flattened into the
      // parent markdown content (which has no copy UI).
      const childChapter = parseChapter(lines, i)
      children.push(childChapter)
      i = childChapter.endIndex
      continue
    }

    content.push(line)
    i++
  }

  return {
    level,
    title,
    content: content.join('\n'),
    children,
    hash: generateHash(content),
    endIndex: i,
    finished: false
  }
}

/**
 * Recursively mark all chapters as completed
 */
function markAllFinished(chapters) {
  for (let i = 0; i < chapters.length; i++) {
    const chapter = chapters[i]
    chapter.finished = true
    if (chapter.children && chapter.children.length > 0) {
      markAllFinished(chapter.children)
    }
  }
}

/**
 * Recursively find last chapter and mark it unfinished
 */
function markLastUnfinished(chapters) {
  if (!chapters.length) return
  for (let i = chapters.length - 1; i >= 0; i--) {
    const chapter = chapters[i]
    if (chapter.children && chapter.children.length > 0) {
      markLastUnfinished(chapter.children)
      return
    }
    chapter.finished = false
    return
  }
}

/**
 * Parse blocks inside a child chapter content
 */
function parseChildBlocks(contentWithoutHeader, getRendererFn = getRenderer) {
  return parseBlocks(contentWithoutHeader || '', getRendererFn)
}

export default {
  generateHash,
  isHeading,
  getHeadingLevel,
  getHeadingText,
  stripHeaderFromContent,
  getChapterBody,
  getRenderer,
  getFence,
  getFenceType,
  isClosingFence,
  countClosingFencesAhead,
  isNestedAnonymousFence,
  createFenceTracker,
  trackFence,
  getFileChangeOpenTag,
  isFileChangeCloseTag,
  parseFileChangeAttributes,
  isInsideInlineCode,
  splitFileChangePieces,
  normalizeFileChangeTags,
  parseFileChangeBlock,
  fileChangeBlocksToFences,
  isInsideCodeFence,
  parseBlocks,
  replaceBlockContent,
  replaceBlockInChapterContent,
  serializeChapters,
  collectAllChildContent,
  parseChapters,
  parseChapter,
  markAllFinished,
  markLastUnfinished,
  parseChildBlocks,
  generateFileName,
  getExtensionForLanguage
}
