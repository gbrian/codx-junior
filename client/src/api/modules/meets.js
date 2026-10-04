/**
 * Meets API Module - WebRTC and Meet Management
 * 
 * Provides endpoints for:
 * - Device enumeration and permissions
 * - Meet session management
 * - WebRTC signaling
 * - Device settings
 */

export const meetsModule = (API) => ({
  /**
   * Get available audio/video devices
   * Backend: GET /api/meets/devices
   */
  async getDevices() {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices()
      
      const microphones = []
      const speakers = []
      const cameras = []

      devices.forEach(device => {
        const label = device.label || `${device.kind} ${device.deviceId}`
        const deviceInfo = { 
          deviceId: device.deviceId, 
          label,
          kind: device.kind 
        }
        
        switch (device.kind) {
          case 'audioinput':
            microphones.push(deviceInfo)
            break
          case 'audiooutput':
            speakers.push(deviceInfo)
            break
          case 'videoinput':
            cameras.push(deviceInfo)
            break
        }
      })

      return { microphones, speakers, cameras, success: true }
    } catch (error) {
      console.error('[meets] Failed to enumerate devices:', error)
      return { 
        microphones: [], 
        speakers: [], 
        cameras: [], 
        success: false, 
        error: error.message 
      }
    }
  },

  /**
   * Request microphone access
   * Backend: POST /api/meets/request-microphone
   */
  async requestMicrophone({ deviceId = 'default' } = {}) {
    try {
      const constraints = {
        audio: deviceId === 'default'
          ? true
          : { deviceId: { exact: deviceId } },
        video: false
      }

      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      return { stream, success: true }
    } catch (error) {
      console.error('[meets] Failed to get microphone:', error)
      const errorType = error.name === 'NotAllowedError' 
        ? 'permission_denied'
        : error.name === 'NotFoundError'
        ? 'device_not_found'
        : 'unknown_error'
      
      return { 
        stream: null, 
        success: false, 
        errorType,
        error: error.message 
      }
    }
  },

  /**
   * Request camera access
   * Backend: POST /api/meets/request-camera
   */
  async requestCamera({ deviceId = 'default' } = {}) {
    try {
      const constraints = {
        audio: false,
        video: deviceId === 'default'
          ? true
          : { deviceId: { exact: deviceId } }
      }

      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      return { stream, success: true }
    } catch (error) {
      console.error('[meets] Failed to get camera:', error)
      const errorType = error.name === 'NotAllowedError' 
        ? 'permission_denied'
        : error.name === 'NotFoundError'
        ? 'device_not_found'
        : 'unknown_error'
      
      return { 
        stream: null, 
        success: false, 
        errorType,
        error: error.message 
      }
    }
  },

  /**
   * Request both microphone and camera
   * Backend: POST /api/meets/request-media
   */
  async requestMedia({ micDeviceId = 'default', camDeviceId = 'default' } = {}) {
    try {
      const constraints = {
        audio: micDeviceId === 'default'
          ? true
          : { deviceId: { exact: micDeviceId } },
        video: camDeviceId === 'default'
          ? true
          : { deviceId: { exact: camDeviceId } }
      }

      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      return { stream, success: true }
    } catch (error) {
      console.error('[meets] Failed to get media:', error)
      return { 
        stream: null, 
        success: false,
        error: error.message 
      }
    }
  },

  /**
   * Initiate a new meet (backend will create signaling session)
   * Backend: POST /api/meets/initiate
   */
  async initiateMeet({ meetId, name, participants } = {}) {
    try {
      const result = await API.post('/api/meets/initiate', {
        meetId,
        name,
        participants,
        timestamp: new Date().getTime()
      })
      return result
    } catch (error) {
      console.error('[meets] Failed to initiate meet:', error)
      throw error
    }
  },

  /**
   * Join an existing meet
   * Backend: POST /api/meets/join
   */
  async joinMeet({ meetId } = {}) {
    try {
      const result = await API.post('/api/meets/join', {
        meetId,
        timestamp: new Date().getTime()
      })
      return result
    } catch (error) {
      console.error('[meets] Failed to join meet:', error)
      throw error
    }
  },

  /**
   * Leave a meet
   * Backend: POST /api/meets/leave
   */
  async leaveMeet({ meetId } = {}) {
    try {
      const result = await API.post('/api/meets/leave', {
        meetId,
        timestamp: new Date().getTime()
      })
      return result
    } catch (error) {
      console.error('[meets] Failed to leave meet:', error)
      throw error
    }
  },

  /**
   * End a meet (only initiator)
   * Backend: POST /api/meets/end
   */
  async endMeet({ meetId } = {}) {
    try {
      const result = await API.post('/api/meets/end', {
        meetId,
        timestamp: new Date().getTime()
      })
      return result
    } catch (error) {
      console.error('[meets] Failed to end meet:', error)
      throw error
    }
  },

  /**
   * Get meet info/status
   * Backend: GET /api/meets/:meetId
   */
  async getMeetInfo({ meetId } = {}) {
    try {
      const result = await API.get(`/api/meets/${meetId}`)
      return result
    } catch (error) {
      console.error('[meets] Failed to get meet info:', error)
      throw error
    }
  },

  /**
   * List active meets
   * Backend: GET /api/meets
   */
  async listActiveMeets() {
    try {
      const result = await API.get('/api/meets')
      return result
    } catch (error) {
      console.error('[meets] Failed to list meets:', error)
      throw error
    }
  },

  /**
   * WebRTC Signaling - Send SDP offer
   * Backend: POST /api/meets/:meetId/signal/offer
   */
  async sendOffer({ meetId, offer, to } = {}) {
    try {
      const result = await API.post(`/api/meets/${meetId}/signal/offer`, {
        offer,
        to,
        timestamp: new Date().getTime()
      })
      return result
    } catch (error) {
      console.error('[meets] Failed to send offer:', error)
      throw error
    }
  },

  /**
   * WebRTC Signaling - Send SDP answer
   * Backend: POST /api/meets/:meetId/signal/answer
   */
  async sendAnswer({ meetId, answer, to } = {}) {
    try {
      const result = await API.post(`/api/meets/${meetId}/signal/answer`, {
        answer,
        to,
        timestamp: new Date().getTime()
      })
      return result
    } catch (error) {
      console.error('[meets] Failed to send answer:', error)
      throw error
    }
  },

  /**
   * WebRTC Signaling - Add ICE candidate
   * Backend: POST /api/meets/:meetId/signal/ice-candidate
   */
  async addIceCandidate({ meetId, candidate, to } = {}) {
    try {
      const result = await API.post(`/api/meets/${meetId}/signal/ice-candidate`, {
        candidate,
        to,
        timestamp: new Date().getTime()
      })
      return result
    } catch (error) {
      console.error('[meets] Failed to send ice candidate:', error)
      throw error
    }
  },

  /**
   * Test audio output
   * Browser: Creates audio context and plays tone
   */
  async testAudioOutput({ frequency = 1000, duration = 1000 } = {}) {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)()
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()

      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)

      oscillator.frequency.value = frequency
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime)
      oscillator.start()

      return new Promise(resolve => {
        setTimeout(() => {
          oscillator.stop()
          resolve({ success: true })
        }, duration)
      })
    } catch (error) {
      console.error('[meets] Audio test failed:', error)
      return { success: false, error: error.message }
    }
  }
})