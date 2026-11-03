/**
 * Regression tests for the <file_change> / fence parser.
 *
 * Dependency free on purpose (no test runner is installed), run with:
 *
 *   node tests/fileChangeParser.test.mjs
 */
import assert from 'node:assert/strict'
import parser from '../src/utils/markdownParser.js'
import { extractCodeBlocks } from '../src/utils/codeBlockExtractor.js'

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

// 1. An envelope body may document the envelope itself: the nested
//    `<file_change/>` lives inside a fence and must not end the block.
test('envelope body may contain a fenced example of the envelope', () => {
  const lines = [
    '<file_change path="docs/protocol.md" language="markdown" change_type="update" encoding="text">',
    '# Protocol',
    '',
    '```xml',
    '<file_change path="a.md" language="markdown" change_type="new" encoding="text">',
    'body',
    '<file_change/>',
    '```',
    '',
    'End of document.',
    '<file_change/>'
  ]

  const { block, endIndex } = parser.parseFileChangeBlock(lines, 0)
  assert.equal(block.filePath, 'docs/protocol.md')
  assert.equal(block.finished, true)
  assert.equal(endIndex, 10, 'the real closing marker is the last line')
  assert.match(block.content, /End of document\./)

  const blocks = parser.parseBlocks(lines.join('\n'))
  assert.equal(blocks.length, 1, 'a single file block, no leftover markdown')
  assert.equal(blocks[0].isFileBlock, true)
  assert.match(blocks[0].content, /End of document\./)

  const extracted = extractCodeBlocks(lines.join('\n'))
  assert.equal(extracted.length, 1)
  assert.equal(extracted[0].filePath, 'docs/protocol.md')
  assert.match(extracted[0].content, /End of document\./)
})

// 2. A closing fence followed by trailing spaces must still close the block.
test('legacy fence closes with trailing spaces', () => {
  const content = [
    '```js src/a.js',
    'const a = 1',
    '```   ',
    '',
    '```js src/b.js',
    'const b = 2',
    '```'
  ].join('\n')

  const blocks = extractCodeBlocks(content)
  assert.equal(blocks.length, 2)
  assert.equal(blocks[0].filePath, 'src/a.js')
  assert.equal(blocks[0].content, 'const a = 1')
  assert.equal(blocks[1].filePath, 'src/b.js')
  assert.equal(blocks[1].content, 'const b = 2')
})

// 3. CRLF content leaves a trailing '\r' on every line, which used to keep the
//    legacy scanner running until EOF and swallow the following blocks.
test('CRLF content does not swallow the following blocks', () => {
  const content = [
    '```js src/a.js',
    'const a = 1',
    '```',
    '```js src/b.js',
    'const b = 2',
    '```'
  ].join('\r\n')

  const blocks = extractCodeBlocks(content)
  assert.equal(blocks.length, 2)
  assert.equal(blocks[0].content.trim(), 'const a = 1')
  assert.equal(blocks[1].filePath, 'src/b.js')
})

// 4. A longer fence wrapping ``` examples keeps them verbatim, and the
//    generated fence adapts to the longest run inside the body.
test('longer fences keep inner ``` runs verbatim', () => {
  const content = [
    '<file_change path="docs/example.md" language="markdown" change_type="new" encoding="text">',
    '```js',
    'const a = 1',
    '```',
    '<file_change/>'
  ].join('\n')

  const { block } = parser.parseFileChangeBlock(content.split('\n'), 0)
  assert.equal(block.content, '```js\nconst a = 1\n```')

  const fenced = parser.fileChangeBlocksToFences(content).split('\n')
  assert.equal(fenced[0], '````markdown docs/example.md')
  assert.equal(fenced[fenced.length - 1], '````')
})

// 5. Tags indented by 4+ spaces are indented code blocks (examples), not
//    envelopes; tags at column 0 (or up to 3 spaces) still are.
test('deeply indented tags are not treated as envelopes', () => {
  assert.equal(parser.getFileChangeOpenTag('    <file_change path="a.md">'), null)
  assert.notEqual(parser.getFileChangeOpenTag('  <file_change path="a.md">'), null)
  assert.equal(parser.isFileChangeCloseTag('    <file_change/>'), false)
  assert.equal(parser.isFileChangeCloseTag('  <file_change/>'), true)
})

// 6. An unfenced nested envelope is content of the outer block (depth counter),
//    never a second file and never an early end of the outer block.
test('unfenced nested envelope stays inside the outer block', () => {
  const lines = [
    '<file_change path="a.md" language="markdown" change_type="update" encoding="text">',
    'intro',
    '<file_change path="b.md" language="markdown" change_type="new" encoding="text">',
    'inner',
    '<file_change/>',
    'outer tail',
    '<file_change/>'
  ]

  const { block, endIndex } = parser.parseFileChangeBlock(lines, 0)
  assert.equal(block.filePath, 'a.md')
  assert.equal(block.finished, true)
  assert.equal(endIndex, 6, 'the outer closing marker, not the inner one')
  assert.match(block.content, /outer tail/)

  const extracted = extractCodeBlocks(lines.join('\n'))
  assert.equal(extracted.length, 1, 'the nested envelope is content, not a second file')
  assert.equal(extracted[0].filePath, 'a.md')
  assert.match(extracted[0].content, /inner/)

  const withHeading = [...lines, '## After']
  assert.equal(parser.isInsideCodeFence(withHeading, 4), true, 'nested body is verbatim envelope content')
  assert.equal(parser.isInsideCodeFence(withHeading, 7), false, 'the heading is outside the envelope')
})

// 7. A nested envelope inside its own fenced example must not end the block
//    (fences are ignored inside an envelope, so the counter stays balanced).
test('nested envelope inside its own fenced example does not end the block', () => {
  const lines = [
    '<file_change path="docs/protocol.md" language="markdown" change_type="update" encoding="text">',
    '```xml',
    '<file_change path="a.md" language="markdown" change_type="new" encoding="text">',
    'body',
    '<file_change/>',
    '```',
    'tail',
    '<file_change/>'
  ]

  const { block, endIndex } = parser.parseFileChangeBlock(lines, 0)
  assert.equal(endIndex, 7)
  assert.equal(block.finished, true)
  assert.match(block.content, /tail/)
})

// 8. Unbalanced body (an example of the opening tag with no closing marker):
//    the block still ends at the last closing marker, so a single stray tag
//    cannot swallow the rest of the message.
test('unbalanced body ends at the last closing marker', () => {
  const lines = [
    '<file_change path="a.md" language="markdown" change_type="update" encoding="text">',
    'example of an opening tag:',
    '<file_change path="b.md" language="markdown" change_type="new" encoding="text">',
    'tail',
    '<file_change/>'
  ]

  const { block, endIndex } = parser.parseFileChangeBlock(lines, 0)
  assert.equal(endIndex, 4, 'the only closing marker available')
  assert.equal(block.finished, true)
  assert.match(block.content, /tail/)
})

// 9. While streaming, a nested envelope without any closing marker keeps the
//    block open (structural hash, no flicker).
test('streaming nested envelope stays unfinished', () => {
  const lines = [
    '<file_change path="a.md" language="markdown" change_type="update" encoding="text">',
    '<file_change path="b.md" language="markdown" change_type="new" encoding="text">',
    'partial conte'
  ]

  const { block, endIndex } = parser.parseFileChangeBlock(lines, 0)
  assert.equal(block.filePath, 'a.md')
  assert.equal(block.finished, false)
  assert.equal(endIndex, lines.length - 1)
})

// 10. The reported bug: while a <file_change> block is open, ``` lines are
//     content only. They must not open a fence, close one, or mask the closing
//     marker, so the block ends exactly at its own closing tag.
test('fences inside a <file_change> block are content only', () => {
  const lines = [
    '<file_change path="docs/guide.md" language="markdown" change_type="update" encoding="text">',
    '# Guide',
    '',
    'A block opens with:',
    '```',
    'and closes with the same marker:',
    '```',
    '```js',
    'const a = 1',
    '```',
    'Still inside the file block.',
    '<file_change/>',
    '',
    'After the block.'
  ]

  const { block, endIndex } = parser.parseFileChangeBlock(lines, 0)
  assert.equal(endIndex, 11, 'ends at the closing tag, not at a fence')
  assert.equal(block.finished, true)
  assert.match(block.content, /Still inside the file block\./)

  const blocks = parser.parseBlocks(lines.join('\n'))
  assert.equal(blocks.length, 2, 'the file block plus the trailing markdown')
  assert.equal(blocks[0].isFileBlock, true)
  assert.match(blocks[0].content, /const a = 1/)
  assert.match(blocks[1].content, /After the block\./)

  const extracted = extractCodeBlocks(lines.join('\n'))
  assert.equal(extracted.length, 1)
  assert.match(extracted[0].content, /Still inside the file block\./)
})

// 11. Fenced blocks count nested fences of their own delimiter: the inner pair
//     does not end the outer block early.
test('nested fence of the same delimiter does not end the block', () => {
  const content = [
    '```js',
    'before',
    '```js',
    'nested code',
    '```',
    'after',
    '```'
  ].join('\n')

  const blocks = parser.parseBlocks(content)
  assert.equal(blocks.length, 1)
  assert.equal(blocks[0].type, 'js')
  assert.equal(blocks[0].content, 'before\n```js\nnested code\n```\nafter')
})

// 12. A fence of another language inside a block is counted as nesting too, so
//     a mermaid diagram inside a js block does not truncate the js block.
test('a different fenced language inside a block does not end it', () => {
  const content = [
    '```js',
    'const a = 1',
    '```mermaid',
    'graph TD',
    '```',
    'const b = 2',
    '```'
  ].join('\n')

  const blocks = parser.parseBlocks(content)
  assert.equal(blocks.length, 1)
  assert.equal(blocks[0].type, 'js')
  assert.match(blocks[0].content, /const b = 2/)
  assert.match(blocks[0].content, /graph TD/)
})

// 13. A fence of the other delimiter is content and never closes the block.
test('the other delimiter does not close a block', () => {
  const content = [
    '```js',
    'const a = 1',
    '~~~',
    'const b = 2',
    '```'
  ].join('\n')

  const blocks = parser.parseBlocks(content)
  assert.equal(blocks.length, 1)
  assert.equal(blocks[0].content, 'const a = 1\n~~~\nconst b = 2')
})

// 14. Two consecutive envelopes stay two blocks (the last closing marker of the
//     message is never reused as the end of the first block).
test('consecutive envelopes stay separate blocks', () => {
  const content = [
    '<file_change path="a.md" language="markdown" change_type="update" encoding="text">',
    'a body',
    '<file_change/>',
    '<file_change path="b.md" language="markdown" change_type="new" encoding="text">',
    'b body',
    '<file_change/>'
  ].join('\n')

  const blocks = parser.parseBlocks(content)
  assert.equal(blocks.length, 2)
  assert.equal(blocks[0].filePath, 'a.md')
  assert.equal(blocks[1].filePath, 'b.md')

  const extracted = extractCodeBlocks(content)
  assert.equal(extracted.length, 2)
  assert.equal(extracted[0].content, 'a body')
  assert.equal(extracted[1].content, 'b body')
})

// 15. Prose glued before the opening tag used to hide the envelope from the
//     anchored regex: the tag leaked into the markdown output.
test('prose glued before the opening tag is moved out of the block', () => {
  const content = [
    'Here is the file: <file_change path="a.md" language="js" change_type="update" encoding="text">',
    'const a = 1',
    '<file_change/>'
  ].join('\n')

  const blocks = parser.parseBlocks(content)
  assert.equal(blocks.length, 2)
  assert.equal(blocks[0].isFileBlock, undefined, 'the prose is plain markdown')
  assert.match(blocks[0].content, /Here is the file:/)
  assert.equal(blocks[1].isFileBlock, true)
  assert.equal(blocks[1].filePath, 'a.md')
  assert.equal(blocks[1].content, 'const a = 1')

  const extracted = extractCodeBlocks(content)
  assert.equal(extracted.length, 1)
  assert.equal(extracted[0].content, 'const a = 1')
})

// 16. Text glued after the closing marker used to keep the block open and
//     swallow the rest of the message.
test('text glued after the closing marker becomes its own block', () => {
  const content = [
    '<file_change path="a.md" language="js" change_type="update" encoding="text">',
    'body',
    '<file_change/> Done with this file.'
  ].join('\n')

  const blocks = parser.parseBlocks(content)
  assert.equal(blocks.length, 2)
  assert.equal(blocks[0].isFileBlock, true)
  assert.equal(blocks[0].content, 'body')
  assert.equal(blocks[0].finished, true)
  assert.match(blocks[1].content, /Done with this file\./)
})

// 17. An inline-code mention documents the syntax: it is never promoted.
test('inline code mentions of the tag are not promoted', () => {
  const content = 'Use `<file_change path="a.md" language="js" change_type="update" encoding="text">` to open a file block.'

  const blocks = parser.parseBlocks(content)
  assert.equal(blocks.length, 1)
  assert.equal(blocks[0].isFileBlock, undefined)
  assert.equal(extractCodeBlocks(content).length, 0)
})

// 18. A tag indented by 4+ spaces is an indented code block example.
test('deeply indented glued tags are not promoted', () => {
  const content = [
    '    <file_change path="a.md" language="js" change_type="update" encoding="text">',
    '    body',
    '    <file_change/>'
  ].join('\n')

  const blocks = parser.parseBlocks(content)
  assert.equal(blocks.length, 1)
  assert.equal(blocks[0].isFileBlock, undefined)
  assert.equal(extractCodeBlocks(content).length, 0)
})

// 19. Two full envelopes on a single line stay two separate blocks.
test('two envelopes on a single line stay separate blocks', () => {
  const content = '<file_change path="a.md" language="markdown" change_type="update" encoding="text">a body<file_change/><file_change path="b.md" language="markdown" change_type="new" encoding="text">b body<file_change/>'

  const blocks = parser.parseBlocks(content)
  assert.equal(blocks.length, 2)
  assert.equal(blocks[0].filePath, 'a.md')
  assert.equal(blocks[0].content, 'a body')
  assert.equal(blocks[1].filePath, 'b.md')
  assert.equal(blocks[1].content, 'b body')

  const extracted = extractCodeBlocks(content)
  assert.equal(extracted.length, 2)
  assert.equal(extracted[0].content, 'a body')
  assert.equal(extracted[1].content, 'b body')
})

// 20. Normalization runs again on already normalized content (parseBlocks can
//     receive a chapter that was normalized by parseChapters).
test('normalization is idempotent', () => {
  const raw = 'text <file_change path="a.md" language="markdown" change_type="new" encoding="text">body<file_change/> tail'
  const once = parser.normalizeFileChangeTags(raw)
  const twice = parser.normalizeFileChangeTags(once)
  assert.equal(twice, once)
  assert.equal(parser.normalizeFileChangeTags(twice), twice)
})

// 21. The body may start on the same line as the opening tag: the content is
//     exactly what sits between the markers, without stray newlines.
test('body may start on the opening tag line', () => {
  const content = '<file_change path="a.md" language="js" change_type="update" encoding="text">const a = 1<file_change/>'

  const blocks = parser.parseBlocks(content)
  assert.equal(blocks.length, 1)
  assert.equal(blocks[0].filePath, 'a.md')
  assert.equal(blocks[0].content, 'const a = 1')

  const { block } = parser.parseFileChangeBlock(parser.normalizeFileChangeTags(content).split('\n'), 0)
  assert.equal(block.content, 'const a = 1')
})

// 22. Content without tags (or with well placed tags) is returned untouched,
//     CRLF included: file line endings are never rewritten.
test('normalization leaves tag-free and CRLF content untouched', () => {
  const plain = 'para one\r\n\r\npara two\r\n'
  assert.equal(parser.normalizeFileChangeTags(plain), plain)

  const fenced = ['```js src/a.js', 'const a = 1', '```'].join('\r\n') + '\r\n'
  assert.equal(parser.normalizeFileChangeTags(fenced), fenced)

  const envelope = [
    '<file_change path="a.md" language="js" change_type="update" encoding="text">',
    'const a = 1',
    '<file_change/>',
    ''
  ].join('\r\n')
  assert.equal(parser.normalizeFileChangeTags(envelope), envelope)
})

// 23. A fenced example in prose documents the syntax: its tags stay verbatim.
test('tags inside a fenced example in prose are not promoted', () => {
  const content = [
    'Example:',
    '```xml',
    '<file_change path="a.md" language="markdown" change_type="new" encoding="text">',
    'body',
    '<file_change/>',
    '```'
  ].join('\n')

  assert.equal(parser.normalizeFileChangeTags(content), content)

  const blocks = parser.parseBlocks(content)
  assert.equal(blocks.filter((block) => block.isFileBlock).length, 0)
  assert.equal(extractCodeBlocks(content).length, 0)
})

if (failed) {
  console.error(`\n${failed} test(s) failed`)
  process.exit(1)
}
console.log('\nall parser tests passed')
