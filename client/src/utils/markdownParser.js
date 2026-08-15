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
 * Check if a line is a valid closing fence
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
 * Check if position is inside a code fence (any nesting level)
 */
function isInsideCodeFence(lines, lineIndex) {
  let currentFence = null
  let nestStack = []

  for (let i = 0; i < lineIndex; i++) {
    const fence = getFence(lines[i])
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

  return !!currentFence
}

/**
 * Parse content string into typed blocks with fence handling.
 *
 * KEY STABILITY DURING STREAMING:
 * - Finished blocks use content-based hash (stable once closed)
 * - Open/streaming blocks use a structural hash (type + fileName) so
 *   the Vue :key does NOT change on every new streamed line, preventing
 *   component remounts that reset CodeViewer's collapsed state.
 */
function parseBlocks(content, getRendererFn = getRenderer) {
  const blocks = []
  const lines = content.split('\n')
  let currentType = 'markdown'
  let currentContent = []
  let currentFileName = ''
  let inCodeBlock = false
  let currentFence = null
  let nestedFences = []
  let isAnonymousFence = false
  // ADDED: track sequential index for stable key on open blocks
  let blockIndex = 0

  function addBlock(isFinished = false) {
    const blockContent = currentContent.join('\n')
    let finalFileName = currentFileName
    let finalType = currentType

    if (finalType && !isMarkdownBlockType(finalType) && !finalFileName && !isAnonymousFence) {
      finalFileName = generateFileName(finalType)
    }

    // CHANGED: finished blocks hash by content (stable); open blocks hash by
    // structural identity (type+fileName+index) so the key doesn't change while
    // new lines are being streamed into the same logical block.
    const contentHash = generateHash(blockContent)
    const structuralKey = `${finalType}:${finalFileName}:${blockIndex}`
    const stableHash = isFinished
      ? contentHash
      : generateHash(structuralKey)

    blocks.push({
      type: finalType,
      content: blockContent,
      hash: stableHash,
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
    nestedFences = []
    isAnonymousFence = false
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const fence = getFence(line)

    if (!inCodeBlock && fence) {
      const hasLanguageInfo = fence.info && fence.info.trim()

      if (hasLanguageInfo) {
        // Mark previous block finished when a new fence opens
        if (blocks.length > 0) {
          blocks[blocks.length - 1].finished = true
        }
        
        // CHANGED: pass isFinished=true for completed prior block
        if (currentContent.length) addBlock(true)

        const parts = fence.info.split(/\s+/).filter(Boolean)
        inCodeBlock = true
        currentFence = fence
        currentType = parts[0] || 'text'
        currentFileName = parts[1] || ''
        isAnonymousFence = false
        continue
      } else {
        if (!inCodeBlock) {
          currentContent.push(line)
          continue
        }
      }
    }

    if (!inCodeBlock) {
      currentContent.push(line)
      continue
    }

    const topNested = nestedFences[nestedFences.length - 1]

    if (topNested && isClosingFence(line, topNested)) {
      nestedFences.pop()
      currentContent.push(line)
      continue
    }

    if (isMarkdownBlockType(currentType)) {
      const innerFence = getFence(line)
      if (innerFence && innerFence.info && !isClosingFence(line, currentFence)) {
        nestedFences.push(innerFence)
        currentContent.push(line)
        continue
      }
    }

    const allNestedClosed = !nestedFences.length
    if (allNestedClosed && isClosingFence(line, currentFence)) {
      if (isNestedAnonymousFence(lines, i, currentType, currentFence)) {
        nestedFences.push(currentFence)
        currentContent.push(line)
        continue
      }
      // CHANGED: closing fence found — block is finished
      addBlock(true)
      inCodeBlock = false
      continue
    }

    currentContent.push(line)
  }

  // CHANGED: last open block (streaming) uses stable structural hash (isFinished=false)
  if (currentContent.length) addBlock(false)

  // All blocks except the last are finished
  for (let i = 0; i < blocks.length - 1; i++) {
    blocks[i].finished = true
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
    } else if (!chapters.length && line.trim()) {
      const introContent = []
      while (i < lines.length && (!isHeading(lines[i]) || isInsideCodeFence(lines, i))) {
        introContent.push(lines[i])
        i++
      }
      const fullIntro = introContent.join('\n').trim()
      if (fullIntro) {
        chapters.push({
          level: 0,
          title: 'Introduction',
          content: fullIntro,
          children: [],
          hash: generateHash(fullIntro),
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