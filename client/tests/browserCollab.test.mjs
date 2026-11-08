/**
 * Tests for the browser collaboration transport envelope.
 *
 * The tests use the local BroadcastChannel mirror (the same code path used by
 * tabs of one browser), so no WebRTC peer is required.
 *
 *   node tests/browserCollab.test.mjs
 */
import assert from 'node:assert/strict'
import {
  broadcastBrowserCollab,
  getCollabClientId
} from '../src/utils/browserCollab.js'

let failed = 0

async function test(name, fn) {
  try {
    await fn()
    console.log(`ok - ${name}`)
  } catch (err) {
    failed++
    console.error(`not ok - ${name}`)
    console.error(`  ${err.message}`)
  }
}

function collect(timeout = 120) {
  const receiver = new BroadcastChannel('codx-browser-collab')
  const messages = []
  receiver.onmessage = event => messages.push(event.data)
  return {
    messages,
    close: () => receiver.close(),
    wait: () => new Promise(resolve => setTimeout(resolve, timeout))
  }
}

await test('broadcasts an envelope with the sender client id', async () => {
  const collector = collect()
  broadcastBrowserCollab(null, {
    kind: 'presence',
    sessionId: 'session-1',
    user: { username: 'tester' }
  })
  await collector.wait()
  collector.close()
  assert.equal(collector.messages.length, 1)
  const message = JSON.parse(collector.messages[0])
  assert.equal(message.scope, 'codx-browser-collab')
  assert.equal(message.clientId, getCollabClientId())
  assert.equal(message.kind, 'presence')
  assert.equal(message.sessionId, 'session-1')
})

await test('splits large payloads into reassemblable chunks', async () => {
  const collector = collect()
  const text = 'x'.repeat(120 * 1024)
  broadcastBrowserCollab(null, {
    kind: 'annotation',
    action: 'add',
    sessionId: 'session-2',
    op: { id: 'op-1', tool: 'text', text }
  })
  await collector.wait(200)
  collector.close()
  assert.ok(collector.messages.length > 1, 'the payload must be chunked')
  const chunks = collector.messages.map(raw => JSON.parse(raw))
  assert.ok(chunks.every(chunk => chunk.chunk))
  assert.equal(chunks[0].chunk.total, chunks.length)
  const reassembled = chunks
    .sort((a, b) => a.chunk.index - b.chunk.index)
    .map(chunk => chunk.data)
    .join('')
  const message = JSON.parse(reassembled)
  assert.equal(message.op.text.length, text.length)
  assert.equal(message.kind, 'annotation')
})

await test('does not put a local-only message on a meeting channel', async () => {
  // No WebRTC channels exist in this process; the call must still deliver the
  // local BroadcastChannel copy exactly once (not one per branch).
  const collector = collect()
  broadcastBrowserCollab(null, { kind: 'presence', sessionId: 'session-3' })
  await collector.wait()
  collector.close()
  assert.equal(collector.messages.length, 1)
})

if (failed) {
  console.error(`\n${failed} test(s) failed`)
  process.exit(1)
}
console.log('\nall browser collaboration tests passed')
process.exit(0)
