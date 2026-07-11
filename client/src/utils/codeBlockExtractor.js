/**
 * Extracts code blocks with file paths from markdown content
 * Pattern: ```lang /path/to/file
 */
export function extractCodeBlocks(content) {
  if (!content || typeof content !== 'string') return []

  const codeBlocks = []
  const lines = content.split('\n')
  let i = 0

  while (i < lines.length) {
    const line = lines[i]
    const match = line.match(/^```(\w+)\s+(.+)$/)

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