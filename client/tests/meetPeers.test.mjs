/**
 * Tests for the meet peer-identity helpers.
 *
 * These cover the exact bug that made a call silent: the offerer and the
 * answerer resolved a different peer key, so the SDP answer and the ICE
 * candidates were looked up under a key that did not exist.
 *
 *   node tests/meetPeers.test.mjs
 */
import assert from 'node:assert/strict'
import {
  findPeerKey,
  isPolite,
  peerIdOf,
  transceiverHasKind
} from '../src/utils/meetPeers.js'

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

await test('peerIdOf builds a device-scoped key and degrades without a sid', () => {
  assert.equal(peerIdOf('gbrian', 's1'), 'gbrian::s1')
  assert.equal(peerIdOf('gbrian'), 'gbrian')
  assert.equal(peerIdOf('', 's1'), 'guest::s1')
})

await test('findPeerKey matches the device-scoped key first', () => {
  const keys = ['gbrian::s1', 'admin::s2']
  assert.equal(findPeerKey(keys, 'gbrian', 's1'), 'gbrian::s1')
})

await test('findPeerKey falls back to the plain username (legacy payload)', () => {
  // The offerer created the connection before it knew the remote session id.
  assert.equal(findPeerKey(['gbrian'], 'gbrian', 's1'), 'gbrian')
  assert.equal(findPeerKey(['gbrian', 'admin::s2'], 'gbrian', ''), 'gbrian')
})

await test('findPeerKey resolves the only session of that username', () => {
  assert.equal(findPeerKey(['gbrian::s1'], 'gbrian', 'unknown'), 'gbrian::s1')
})

await test('findPeerKey resolves a renamed key by the session id', () => {
  assert.equal(findPeerKey(['old-name::s1'], 'gbrian', 's1'), 'old-name::s1')
})

await test('findPeerKey ignores other participants and empty input', () => {
  assert.equal(findPeerKey(['admin::s2'], 'gbrian', 's1'), '')
  assert.equal(findPeerKey([], 'gbrian', 's1'), '')
  assert.equal(findPeerKey(['gbrian::s1'], '', 's1'), '')
  assert.equal(findPeerKey(undefined, 'gbrian', 's1'), '')
})

await test('findPeerKey does not guess between two sessions of the same user', () => {
  // Two devices of one account: only an exact sid match is safe.
  const keys = ['gbrian::phone', 'gbrian::desktop']
  assert.equal(findPeerKey(keys, 'gbrian', 'phone'), 'gbrian::phone')
  assert.equal(findPeerKey(keys, 'gbrian', ''), '')
})

await test('isPolite is deterministic for both ends', () => {
  assert.equal(isPolite('aaa', 'bbb'), true)
  assert.equal(isPolite('bbb', 'aaa'), false)
  // Only one side is polite → perfect-negotiation conflict resolution.
  assert.notEqual(isPolite('aaa', 'bbb'), isPolite('bbb', 'aaa'))
})

await test('isPolite defaults to polite when a session id is missing', () => {
  assert.equal(isPolite('aaa', ''), true)
  assert.equal(isPolite('', 'bbb'), true)
})

await test('transceiverHasKind prefers the receiver track', () => {
  assert.equal(transceiverHasKind({ receiver: { track: { kind: 'video' } }, sender: { track: null } }, 'video'), true)
  assert.equal(transceiverHasKind({ receiver: { track: { kind: 'audio' } }, sender: { track: null } }, 'video'), false)
  // Receiver track unavailable → fall back to the sender track.
  assert.equal(transceiverHasKind({ receiver: null, sender: { track: { kind: 'audio' } } }, 'audio'), true)
  assert.equal(transceiverHasKind(null, 'audio'), false)
})

if (failed) {
  console.error(`\n${failed} test(s) failed`)
  process.exit(1)
}
console.log('\nall peer-identity tests passed')
