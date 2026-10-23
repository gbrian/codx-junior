/**
 * Microphone input-level monitor.
 *
 * Wraps the Web Audio API to turn a microphone MediaStream into a stream of
 * normalised input levels (0–100) that the UI can use to draw a level meter or
 * to detect when the user is actually speaking.
 *
 * The monitor is deliberately tiny and self-contained: create one with
 * `createMicLevelMonitor({ onLevel })`, call `start(stream)` when the mic opens
 * and `stop()` when it closes. All Web Audio nodes are created lazily and torn
 * down on stop, so no AudioContext is ever left running.
 */

// Input level (0–100) at/above which the mic counts as picking up speech. Kept
// in sync with the store's `isMicSpeaking` getter so the pulse agrees with the
// boolean the UI reads.
const DEFAULT_SPEAKING_THRESHOLD = 12
const MAX_LEVEL = 100
// Raw RMS for a normal speaking voice is tiny compared to full scale, so we
// amplify it to make the 0–100 meter and the speaking threshold intuitive.
const RMS_GAIN = 300

export function createMicLevelMonitor ({
  onLevel,
  onSpeaking,
  threshold = DEFAULT_SPEAKING_THRESHOLD,
  pollMs = 100
} = {}) {
  let audioContext = null
  let analyser = null
  let source = null
  let buffer = null
  let timer = null
  let speaking = false

  function computeLevel () {
    if (!analyser || !buffer) return 0
    analyser.getByteTimeDomainData(buffer)
    let sumSquares = 0
    for (let i = 0; i < buffer.length; i++) {
      const v = (buffer[i] - 128) / 128
      sumSquares += v * v
    }
    const rms = Math.sqrt(sumSquares / buffer.length)
    return Math.min(MAX_LEVEL, Math.round(rms * RMS_GAIN))
  }

  function tick () {
    const level = computeLevel()
    if (typeof onLevel === 'function') onLevel(level)
    const isSpeaking = level >= threshold
    if (isSpeaking !== speaking) {
      speaking = isSpeaking
      if (typeof onSpeaking === 'function') onSpeaking(speaking)
    }
  }

  function start (stream) {
    const hasAudio = stream && stream.getAudioTracks && stream.getAudioTracks().length > 0
    if (!hasAudio) return
    // Re-bind cleanly to whatever stream is current.
    stop()
    const Ctx = window.AudioContext || window.webkitAudioContext
    if (!Ctx) return
    try {
      audioContext = new Ctx()
      source = audioContext.createMediaStreamSource(stream)
      analyser = audioContext.createAnalyser()
      analyser.fftSize = 512
      buffer = new Uint8Array(analyser.fftSize)
      source.connect(analyser)
      // Some browsers keep the context suspended until a gesture; the mic is
      // opened from a click, so this usually resolves immediately.
      if (audioContext.state === 'suspended') audioContext.resume()
      timer = setInterval(tick, pollMs)
    } catch (error) {
      console.warn('[audioLevel] failed to start mic monitor', error)
      stop()
    }
  }

  function stop () {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    if (source) {
      try { source.disconnect() } catch (e) { /* ignore */ }
      source = null
    }
    if (audioContext) {
      try { audioContext.close() } catch (e) { /* ignore */ }
      audioContext = null
    }
    analyser = null
    buffer = null
    // Report silence so any meter built on this returns to zero.
    if (typeof onLevel === 'function') onLevel(0)
    if (speaking) {
      speaking = false
      if (typeof onSpeaking === 'function') onSpeaking(false)
    }
  }

  return { start, stop }
}

export default { createMicLevelMonitor }