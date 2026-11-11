/**
 * Peer identity helpers for the meet WebRTC mesh.
 *
 * Two problems are solved here, both of which used to break the mesh:
 *
 * 1. **Symmetric peer keys.** A peer connection is keyed by a *device-scoped*
 *    id (`username::sessionId`) so a second device of the same account gets its
 *    own connection. The offerer and the answerer must land on the same key,
 *    otherwise the SDP answer and the ICE candidates are looked up under a key
 *    that does not exist and the connection never completes (no remote audio,
 *    no remote video). `findPeerKey` resolves a peer key from whatever the
 *    caller knows (username and, when available, the remote session id) and
 *    falls back gracefully for payloads that omit the session id.
 *
 * 2. **Glare resolution.** Both peers of a session may renegotiate at the same
 *    time (e.g. both turn their camera on). Perfect negotiation needs one side
 *    to be *polite* (rolls its own offer back) and the other *impolite* (keeps
 *    its offer). `isPolite` derives that deterministic role from the two
 *    session ids, which both peers know.
 *
 * The module is intentionally free of browser APIs so it can be unit tested
 * with plain Node (`client/tests/meetPeers.test.mjs`).
 */

/**
 * Build the composite, device-scoped peer key.
 *
 * @param {string} username - participant username (used for display too)
 * @param {string} [sid]    - session discriminator (socket id / device id). When
 *                            missing we degrade to the plain username, which
 *                            keeps the legacy single-device behaviour working.
 * @returns {string}
 */
export function peerIdOf(username, sid) {
  const who = username || 'guest'
  return sid ? `${who}::${sid}` : who
}

/**
 * Resolve the peer-connection key of a remote session.
 *
 * Resolution order (first match wins):
 *   1. `username::sid`  – the canonical device-scoped key;
 *   2. `username`       – a connection created before the session id was known;
 *   3. the only `username::*` key, when exactly one exists;
 *   4. any key ending in `::sid` (a renamed/legacy key for the same session).
 *
 * @param {string[]} keys     - existing peer connection keys
 * @param {string}   username - remote username
 * @param {string}   [sid]    - remote session id, when known
 * @returns {string} the matching key, or `''` when there is none
 */
export function findPeerKey(keys, username, sid) {
  if (!username || !Array.isArray(keys) || !keys.length) return ''
  const deviceKey = peerIdOf(username, sid)
  if (sid && keys.includes(deviceKey)) return deviceKey
  if (keys.includes(username)) return username
  const prefixed = keys.filter(key => key.startsWith(`${username}::`))
  if (prefixed.length === 1) return prefixed[0]
  if (sid) {
    const bySid = keys.find(key => key.endsWith(`::${sid}`))
    if (bySid) return bySid
  }
  return ''
}

/**
 * Decide whether *this* side is the polite peer of a session.
 *
 * Deterministic on both ends: the lexicographically smaller session id is the
 * polite one. When the remote session id is unknown (legacy payload) we default
 * to polite, which makes us yield to the other side's offer instead of leaving
 * both sides waiting.
 *
 * @param {string} localSid
 * @param {string} [remoteSid]
 * @returns {boolean}
 */
export function isPolite(localSid, remoteSid) {
  if (!remoteSid || !localSid) return true
  return String(localSid) < String(remoteSid)
}

/**
 * True when a media transceiver carries the given kind (`audio`/`video`).
 *
 * The receiver track is used first: it is always present for a negotiated
 * m-line, while the sender track is `null` until local media is attached (which
 * is exactly the case after `replaceTrack(null)`).
 *
 * @param {RTCRtpTransceiver} transceiver
 * @param {string} kind
 * @returns {boolean}
 */
export function transceiverHasKind(transceiver, kind) {
  if (!transceiver) return false
  const receiverKind = transceiver.receiver?.track?.kind
  if (receiverKind) return receiverKind === kind
  return transceiver.sender?.track?.kind === kind
}
