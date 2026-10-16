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
 * CODX file block syntax
 * -------------------------------------------------------------------------
 * In addition to legacy ```lang path fences, markdown may carry code blocks
 * using sentinel lines:
 *
 *   @@ CODX_FILE @@
 *   path: <project-relative path>
 *   language: <language id>
 *   change_type: <new|update|delete>
 *   encoding: text
 *   @@ CODX_CONTENT @@
 *   <full file content, verbatim - may itself contain code fences>
 *   @@ CODX_END @@
 *
 * The body between CONTENT and END is taken verbatim, so nested ``` fences
 * (and even heading-looking lines) never leak out of the block.
 */

/**
 * Detect one of the sentinel markers on a single line.
 * Returns 'file' | 'content' | 'end' | null
 */
function getCodedFileMarkers(line) {
  if (line?.indexOf('@') !== 0) return null
  const match = line.trim().match(/^@{2}\s+CODX_(FILE|CONTENT|END)\s+@{2}$/)
  if (!match) return null
  if (match[1] === 'FILE') return 'file'
  if (match[1] === 'CONTENT') return 'content'
  return 'end'
}

/**
 * Parse a single "key: value" metadata line found between FILE and CONTENT
 */
function parseCodedFileMetaLine(line) {
  const match = line.match(/^\s*([A-Za-z_][\w-]*)\s*:\s*(.*?)\s*$/)
  if (!match) return null
  return { key: match[1].toLowerCase().replace(/-/g, '_'), value: match[2] }
}

/**
 * Parse a full CODX file block starting at `startIndex` (the FILE marker).
 *
 * Returns { block, endIndex } where `endIndex` is the last consumed line so
 * the caller can resume right after it. Returns null when the start marker is
 * immediately followed by another FILE marker (malformed nested start).
 *
 * Streaming friendly: when CONTENT/END markers are missing the block is
 * emitted as unfinished with whatever content has arrived so far.
 */
function parseCodedFileBlock(lines, startIndex, getRendererFn = getRenderer) {
  const meta = {}
  let i = startIndex + 1
  let contentStart = -1
  let contentEnd = -1

  // Read metadata until the CONTENT or END marker
  while (i < lines.length) {
    const marker = getCodedFileMarkers(lines[i])
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
      if (getCodedFileMarkers(lines[j]) === 'end') {
        contentEnd = j
        break
      }
    }
    if (contentEnd === -1) contentEnd = lines.length
  }

  const finished = contentEnd < lines.length
  const content = lines.slice(contentStart, contentEnd).join('\n')
  const language = meta.language || 'text'
  const fileName = meta.path || generateFileName(language)

  const block = {
    type: language,
    content,
    hash: generateHash(content),
    fileName,
    renderer: getRendererFn(language, fileName),
    finished,
    // Marks a block that came from the sentinel syntax (always rendered as code)
    isFileBlock: true,
    fileChangeType: meta.change_type || '',
    encoding: meta.encoding || 'text'
  }

  return { block, endIndex: finished ? contentEnd : lines.length - 1 }
}

/**
 * Check if position is inside a code fence (any nesting level) OR inside a
 * CODX file block (whose body is verbatim and must not be re-parsed).
 */
function isInsideCodeFence(lines, lineIndex) {
  let currentFence = null
  let nestStack = []
  let inCodedFile = false

  for (let i = 0; i < lineIndex; i++) {
    const line = lines[i]
    const marker = getCodedFileMarkers(line)

    if (inCodedFile) {
      // Inside a CODX block everything is verbatim until the END marker,
      // including nested fences and heading-looking lines.
      if (marker === 'end') inCodedFile = false
      continue
    }

    // A CODX FILE marker only opens a block when we are not already inside a
    // legacy fence (mirrors parseBlocks, where fences win inside code blocks).
    if (marker === 'file' && !currentFence) {
      inCodedFile = true
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

  return !!currentFence || inCodedFile
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
 * - CODX sentinel blocks (@@ CODX_FILE @@ ... @@ CODX_END @@) are
 *   parsed as verbatim file blocks: their body may contain fences and headings
 *   without affecting the surrounding markdown.
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

    // CODX file block takes priority when not already inside a legacy fence
    if (!inCodeBlock && getCodedFileMarkers(line) === 'file') {
      const coded = parseCodedFileBlock(lines, i, getRendererFn)
      if (coded) {
        if (blocks.length > 0) {
          blocks[blocks.length - 1].finished = true
        }
        if (currentContent.length) addBlock(true)
        blocks.push(coded.block)
        blockIndex++
        i = coded.endIndex
        continue
      }
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

  // All blocks except the last are finished. CODX file blocks keep the
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

      if (nextLevel === level + 1) {
        const childChapter = parseChapter(lines, i)
        children.push(childChapter)
        i = childChapter.endIndex
        continue
      }

      if (nextLevel > level + 1) {
        content.push(line)
        i++
        continue
      }
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
  getCodedFileMarkers,
  parseCodedFileMetaLine,
  parseCodedFileBlock,
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
