/**
 * Tests for the browser annotation model.
 *
 * Dependency free on purpose (no test runner is installed), run with:
 *
 *   node tests/browserAnnotations.test.mjs
 */
import assert from 'node:assert/strict'
import {
  annotationBounds,
  annotationColorName,
  clamp01,
  createAnnotation,
  describeAnnotations,
  findAnnotationAt,
  translateAnnotation
} from '../src/utils/browserAnnotations.js'

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

test('createAnnotation keeps normalized points and unique ids', () => {
  const first = createAnnotation({ tool: 'pen', point: { x: 0.2, y: 0.3 } })
  const second = createAnnotation({ tool: 'pen', point: { x: 0.2, y: 0.3 } })
  assert.equal(first.tool, 'pen')
  assert.deepEqual(first.points, [{ x: 0.2, y: 0.3 }, { x: 0.2, y: 0.3 }])
  assert.notEqual(first.id, second.id)
  assert.ok(first.createdAt > 0)
})

test('coordinates are clamped to the page', () => {
  assert.equal(clamp01(-3), 0)
  assert.equal(clamp01(42), 1)
  const op = createAnnotation({ tool: 'rect', point: { x: -1, y: 5 } })
  assert.equal(op.x, 0)
  assert.equal(op.y, 1)
})

test('annotationBounds normalizes a rectangle drawn bottom-up', () => {
  const rect = createAnnotation({ tool: 'rect', point: { x: 0.6, y: 0.6 } })
  rect.w = -0.2
  rect.h = -0.1
  const bounds = annotationBounds(rect)
  assert.ok(Math.abs(bounds.x - 0.4) < 1e-9)
  assert.ok(Math.abs(bounds.y - 0.5) < 1e-9)
  assert.ok(Math.abs(bounds.w - 0.2) < 1e-9)
  assert.ok(Math.abs(bounds.h - 0.1) < 1e-9)
})

test('annotationBounds honours an explicitly resized text box', () => {
  const text = createAnnotation({ tool: 'text', point: { x: 0.2, y: 0.3 }, text: 'A resized label' })
  text.w = 0.25
  text.h = 0.08
  const bounds = annotationBounds(text)
  assert.ok(Math.abs(bounds.x - 0.2) < 1e-9)
  assert.ok(Math.abs(bounds.y - 0.3) < 1e-9)
  assert.ok(Math.abs(bounds.w - 0.25) < 1e-9)
  assert.ok(Math.abs(bounds.h - 0.08) < 1e-9)
})

test('annotationBounds uses the sticky-note height after resizing', () => {
  const note = createAnnotation({ tool: 'note', point: { x: 0.1, y: 0.1 }, text: 'note' })
  note.w = 0.3
  note.h = 0.2
  const bounds = annotationBounds(note)
  assert.ok(Math.abs(bounds.w - 0.3) < 1e-9)
  assert.ok(Math.abs(bounds.h - 0.2) < 1e-9)
})

test('findAnnotationAt returns the topmost matching mark', () => {
  const bottom = createAnnotation({ tool: 'rect', point: { x: 0.2, y: 0.2 } })
  bottom.w = 0.4
  bottom.h = 0.3
  const top = createAnnotation({ tool: 'note', point: { x: 0.3, y: 0.3 }, text: 'Top' })
  top.h = 0.2
  assert.equal(findAnnotationAt([bottom, top], { x: 0.35, y: 0.35 })?.id, top.id)
  assert.equal(findAnnotationAt([bottom], { x: 0.9, y: 0.9 }), null)
})

test('arrows are hit-tested along their line, not only at the endpoints', () => {
  const arrow = createAnnotation({ tool: 'arrow', point: { x: 0.1, y: 0.1 } })
  arrow.points[1] = { x: 0.5, y: 0.5 }
  assert.equal(findAnnotationAt([arrow], { x: 0.3, y: 0.3 })?.id, arrow.id)
})

test('translateAnnotation moves the whole mark and clamps at the edges', () => {
  const note = createAnnotation({ tool: 'note', point: { x: 0.2, y: 0.2 }, text: 'Move me' })
  const moved = translateAnnotation(note, 0.1, 0.05)
  assert.ok(Math.abs(moved.x - 0.3) < 1e-9)
  assert.ok(Math.abs(moved.y - 0.25) < 1e-9)
  assert.equal(note.x, 0.2, 'the original annotation is untouched')

  const clamped = translateAnnotation(note, -1, -1)
  assert.equal(clamped.x, 0)
  assert.equal(clamped.y, 0)
})

test('describeAnnotations names the tools, colors and note text', () => {
  const arrow = createAnnotation({ tool: 'arrow', point: { x: 0.1, y: 0.2 }, color: '#ef4444' })
  arrow.points[1] = { x: 0.6, y: 0.7 }
  const note = createAnnotation({ tool: 'note', point: { x: 0.2, y: 0.8 }, color: '#f59e0b', text: 'Click the login button' })
  note.h = 0.1
  const lines = describeAnnotations([arrow, note]).join('\n')
  assert.match(lines, /Marks on the page: 1 arrow, 1 sticky note/)
  assert.match(lines, /red arrow from 10%,20% to 60%,70%/)
  assert.match(lines, /amber sticky note .*"Click the login button"/)
  assert.equal(annotationColorName('#3b82f6'), 'blue')
})

test('describeAnnotations accepts an empty board', () => {
  assert.deepEqual(describeAnnotations([]), ['The drawing has no marks yet.'])
})

test('describeAnnotations caps a very long list of marks', () => {
  const ops = Array.from({ length: 45 }, (_, index) => createAnnotation({
    tool: 'text',
    point: { x: 0.1, y: index / 50 },
    text: `label ${index}`
  }))
  const text = describeAnnotations(ops).join('\n')
  assert.match(text, /…and 5 more marks not listed\./)
})

if (failed) {
  console.error(`\n${failed} test(s) failed`)
  process.exit(1)
}
console.log('\nall browser annotation tests passed')
