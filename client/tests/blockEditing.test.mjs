/**
 * Regression tests for in-place block editing.
 *
 * Dependency free on purpose (no test runner is installed), run with:
 *
 *   node tests/blockEditing.test.mjs
 */
import assert from 'node:assert/strict'
import parser from '../src/utils/markdownParser.js'

let failed = 0

function test(name, fn) {
  try {
    fn()
    console.log(`ok - ${name}`)
  } catch (err) {
    failed++
    console.error(`not ok - ${name}`)
    console.error(`  ${err.message}`)
  }
}

const duplicateDiagram = `# Diagram

\`\`\`mermaid
graph TD
  A-->B
\`\`\`

## Copy

\`\`\`mermaid
graph TD
  A-->B
\`\`\`
`

test('parseBlocks records the source span of each block body', () => {
  const blocks = parser.parseBlocks(duplicateDiagram)
  const fenced = blocks.filter(block => block.type === 'mermaid')
  assert.equal(fenced.length, 2)
  assert.deepEqual(fenced.map(block => block.content), ['graph TD\n  A-->B', 'graph TD\n  A-->B'])
  for (const block of blocks) {
    assert.ok(Number.isInteger(block.bodyStartLine), 'bodyStartLine must be an integer')
    assert.ok(Number.isInteger(block.bodyEndLine), 'bodyEndLine must be an integer')
    assert.ok(block.bodyEndLine > block.bodyStartLine, 'the body span must not be empty')
  }
})

test('replaceBlockContent edits the selected duplicate only', () => {
  const blocks = parser.parseBlocks(duplicateDiagram)
  const secondMermaid = blocks.findIndex(block => block.type === 'mermaid')
  const target = blocks.filter(block => block.type === 'mermaid')[1]
  const index = blocks.indexOf(target)
  assert.ok(secondMermaid >= 0)

  const updated = parser.replaceBlockContent(duplicateDiagram, index, 'graph LR\n  X-->Y')
  assert.ok(updated.includes('graph TD\n  A-->B'), 'the first diagram must be untouched')
  assert.ok(updated.includes('graph LR\n  X-->Y'), 'the second diagram must be replaced')
  assert.equal(updated.match(/graph TD/g).length, 1)
})

test('replaceBlockInChapterContent preserves the heading and child sections', () => {
  const chapters = parser.parseChapters(duplicateDiagram)
  assert.equal(chapters.length, 1)
  assert.equal(chapters[0].title, 'Diagram')

  const blocks = parser.parseBlocks(parser.getChapterBody(chapters[0].content))
  const mermaidIndex = blocks.findIndex(block => block.type === 'mermaid')
  const nextChapter = parser.replaceBlockInChapterContent(
    chapters[0].content,
    mermaidIndex,
    'graph LR\n  P-->Q'
  )

  assert.ok(nextChapter.startsWith('# Diagram'))
  assert.ok(nextChapter.includes('graph LR\n  P-->Q'))
  // The chapter's own source excludes child sections; the document serializer
  // re-attaches them when the chapter is stitched back into the message.
  assert.ok(!nextChapter.includes('## Copy'))

  const updated = parser.serializeChapters(chapters, {
    path: [0],
    content: nextChapter,
    replaceChildren: false
  })
  assert.ok(updated.includes('# Diagram'))
  assert.ok(updated.includes('## Copy'))
  assert.ok(updated.includes('graph LR\n  P-->Q'))
  assert.equal(updated.match(/graph TD/g).length, 1)
})

test('serializeChapters round-trips a parsed document exactly', () => {
  assert.equal(parser.serializeChapters(parser.parseChapters(duplicateDiagram)), duplicateDiagram)
})

test('chapter-level replacement can replace a section including its children', () => {
  const chapters = parser.parseChapters(duplicateDiagram)
  const replacement = `# Diagram\n\nNew body.\n\n## Copy\n\nNew child.\n`
  const updated = parser.serializeChapters(chapters, {
    path: [0],
    content: replacement,
    replaceChildren: true
  })
  assert.equal(updated, replacement)
})

test('replaceBlockContent edits the body of a <file_change> envelope', () => {
  const source = [
    'Intro',
    '',
    '<file_change path="src/a.js" language="javascript" change_type="update" encoding="text">',
    'const a = 1',
    '<file_change/>',
    '',
    'Tail'
  ].join('\n')
  const blocks = parser.parseBlocks(source)
  const fileBlockIndex = blocks.findIndex(block => block.isFileBlock)
  assert.ok(fileBlockIndex >= 0)

  const updated = parser.replaceBlockContent(source, fileBlockIndex, 'const a = 2')
  assert.ok(updated.includes('const a = 2'))
  assert.ok(updated.includes('<file_change path="src/a.js"'))
  assert.ok(updated.includes('<file_change/>'))
  assert.ok(updated.startsWith('Intro'))
  assert.ok(updated.endsWith('Tail'))
})
