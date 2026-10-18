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
  const match = line.match(/^( {0,3})(`{3,}|~{3,})(.*)$/)
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
 */

// Opening tag: <file_change + at least one attribute on the same line
const FILE_CHANGE_OPEN_REGEX = /^<file_change\s/i
// Closing tag: <file_change/>, <file_change /> or </file_change>
const FILE_CHANGE_CLOSE_REGEX = /^<\/?file_change\s*\/?>\s*$/i
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
  if (!FILE_CHANGE_OPEN_REGEX.test(line.trim())) return null
  return parseFileChangeAttributes(line)
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
 * Parse a full `<file_change>` envelope starting at `startIndex` (the open tag).
 *
 * Returns { block, endIndex } where `endIndex` is the index of the closing
 * marker line (or the last available line while the block is still streaming).
 * Streaming friendly: a block whose closing marker has not arrived yet yields
 * whatever content is available so far with finished=false.
 */
function parseFileChangeBlock(lines, startIndex, getRendererFn = getRenderer) {
  const attrs = parseFileChangeAttributes(lines[startIndex])

  let endIndex = lines.length
  for (let i = startIndex + 1; i < lines.length; i++) {
    if (isFileChangeCloseTag(lines[i])) {
      endIndex = i
      break
    }
  }

  const finished = endIndex < lines.length
  const content = lines.slice(startIndex + 1, endIndex).join('\n')
  const language = attrs.language || 'text'
  const filePath = attrs.path || attrs.file || ''
  const fileName = filePath || generateFileName(language)

  const block = {
    type: language,
    content,
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
 */
function isInsideCodeFence(lines, lineIndex) {
  let currentFence = null
  let nestStack = []
  let inFileChange = false

  for (let i = 0; i < lineIndex; i++) {
    const line = lines[i]

    if (inFileChange) {
      // Inside an envelope everything is verbatim until the closing marker,
      // including nested fences and heading-looking lines.
      if (isFileChangeCloseTag(line)) inFileChange = false
      continue
    }

    // An opening tag only starts a block when we are not already inside a
    // legacy fence (mirrors parseBlocks, where fences win inside code blocks).
    if (!currentFence && getFileChangeOpenTag(line)) {
      inFileChange = true
      continue
    }

    const fence = getFence(line)
    if (!fence) continue

    if (!currentFence) {
      currentFence = fence
      nestStack = [fence]
      continue
    }

    const lastNested = nestStack[nestStack.length - 1]
    if (lastNested && isClosingFence(lines[i], lastNested)) {
      nestStack.pop()
      continue
    }

    if (!nestStack.length && isClosingFence(lines[i], currentFence)) {
      if (isNestedAnonymousFence(lines, i, 'unknown', currentFence)) {
        nestStack.push(fence)
        continue
      }
      currentFence = null
      nestStack = []
    }
  }

  return !!currentFence || inFileChange
}

/**
 * Parse content string into typed blocks with fence handling.
 *
 * CORE BEHAVIOR:
 * - When inside any named code block (type='py', 'js', 'vue', etc.) ALL inner
 *   fences (including mermaid, other language fences, etc.) are treated as
 *   plain content. Only the matching closing fence ends the block.
 * - Markdown blocks (type='markdown') also treat inner fences as content.
 * - A closing fence must match the OUTER opening fence character and length.
 * - `<file_change ...> ... <file_change/>` envelopes are parsed as verbatim
 *   file blocks: their body may contain fences and headings without affecting
 *   the surrounding markdown. Legacy ```lang path fences keep working as
 *   fallback.
 *
 * NESTED BLOCK DEPTH TRACKING:
 * - When a named inner fence opens inside a code block, nestDepth increases.
 * - A closing fence only ends the outer block when nestDepth === 0.
 * - This handles cases like a py file containing a mermaid diagram in its
 *   docstring: the inner ```mermaid...``` does not close the outer ```py block.
 *
 * KEY STABILITY DURING STREAMING:
 * - Finished blocks use content-based hash (stable once closed)
 * - Open/streaming blocks use a structural hash so Vue :key stays stable
 *
 * SINGLE-LINE CONTENT FIX:
 * - All non-empty content generates at least one block
 * - Plain markdown (no fences) defaults to type='markdown'
 */
function parseBlocks(content, getRendererFn = getRenderer) {
  const blocks = []
  const lines = content.split('\n')
  let currentType = 'markdown'
  let currentContent = []
  let currentFileName = ''
  let inCodeBlock = false
  let currentFence = null
  let isAnonymousFence = false
  let blockIndex = 0
  // Tracks how many named inner fences are open inside the current outer block.
  // A closing fence only closes the outer block when nestDepth === 0.
  let nestDepth = 0

  function addBlock(isFinished = false) {
    const blockContent = currentContent.join('\n')
    const trimmedContent = blockContent.trim()

    if (!trimmedContent) {
      resetBlock()
      return
    }

    let finalFileName = currentFileName
    let finalType = currentType

    if (finalType && !isMarkdownBlockType(finalType) && !finalFileName && !isAnonymousFence) {
      finalFileName = generateFileName(finalType)
    }

    const contentHash = generateHash(blockContent)

    blocks.push({
      type: finalType,
      content: blockContent,
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
    currentFence = null
    isAnonymousFence = false
    nestDepth = 0
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    // <file_change> envelope takes priority when not already inside a fence
    if (!inCodeBlock && getFileChangeOpenTag(line)) {
      if (blocks.length > 0) {
        blocks[blocks.length - 1].finished = true
      }
      if (currentContent.length) addBlock(true)
      const fileChange = parseFileChangeBlock(lines, i, getRendererFn)
      blocks.push(fileChange.block)
      blockIndex++
      i = fileChange.endIndex
      continue
    }

    const fence = getFence(line)

    if (inCodeBlock && fence) {
      if (isClosingFence(line, currentFence)) {
        if (nestDepth > 0) {
          // This closes an inner named fence, not the outer block
          nestDepth--
          currentContent.push(line)
        } else {
          // nestDepth === 0: this closes the outer block
          addBlock(true)
          inCodeBlock = false
        }
      } else {
        // Any opening fence inside a code block (named or not) increases depth
        // so the corresponding closing fence is correctly consumed as content.
        if (fence.info && fence.info.trim()) {
          nestDepth++
        }
        currentContent.push(line)
      }
      continue
    }

    if (!inCodeBlock && fence) {
      const hasLanguageInfo = fence.info && fence.info.trim()

      if (hasLanguageInfo) {
        // Mark previous block finished when a new fence opens
        if (blocks.length > 0) {
          blocks[blocks.length - 1].finished = true
        }

        if (currentContent.length) addBlock(true)

        const parts = fence.info.split(/\s+/).filter(Boolean)
        inCodeBlock = true
        currentFence = fence
        currentType = parts[0] || 'text'
        currentFileName = parts[1] || ''
        isAnonymousFence = false
        nestDepth = 0
        continue
      } else {
        // Anonymous fence (no language) - treat as markdown content
        currentContent.push(line)
        continue
      }
    }

    currentContent.push(line)
  }

  if (currentContent.length) {
    addBlock(false)
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
  getRenderer,
  getFence,
  isClosingFence,
  countClosingFencesAhead,
  isNestedAnonymousFence,
  getFileChangeOpenTag,
  isFileChangeCloseTag,
  parseFileChangeAttributes,
  parseFileChangeBlock,
  fileChangeBlocksToFences,
  isInsideCodeFence,
  parseBlocks,
  collectAllChildContent,
  parseChapters,
  parseChapter,
  markAllFinished,
  markLastUnfinished,
  parseChildBlocks,
  generateFileName,
  getExtensionForLanguage
}
