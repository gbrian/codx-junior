<script setup>
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4"
    @keydown.esc="$emit('close')"
  >
    <div class="bg-[#202124] border border-white/10 rounded-2xl w-full max-w-2xl shadow-2xl max-h-[90vh] flex flex-col">

      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-white/10 shrink-0">
        <h2 class="text-base font-semibold text-white flex items-center gap-2">
          <i class="fa-solid fa-sliders text-primary"></i>
          Settings
        </h2>
        <button @click="$emit('close')" class="btn btn-ghost btn-sm btn-circle text-white/60 hover:text-white">
          <i class="fa-solid fa-xmark text-lg"></i>
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto">
        <div class="p-6 space-y-6">

          <!-- ── CAMERA (top, full-width) ── -->
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <label class="text-sm font-semibold text-white flex items-center gap-2">
                <i class="fa-solid fa-video text-primary"></i>
                Camera
              </label>
              <!-- Camera enable toggle -->
              <label class="flex items-center gap-2 cursor-pointer select-none">
                <span class="text-xs text-white/50">{{ settings.cameraEnabled ? 'On' : 'Off' }}</span>
                <input
                  v-model="settings.cameraEnabled"
                  type="checkbox"
                  class="toggle toggle-primary toggle-sm"
                  @change="onCameraToggle"
                />
              </label>
            </div>

            <!-- Camera preview -->
            <div class="relative w-full aspect-video rounded-xl overflow-hidden bg-[#3c4043] flex items-center justify-center">
              <video
                v-if="settings.cameraEnabled && cameraStream"
                ref="cameraPreview"
                autoplay
                muted
                playsinline
                class="w-full h-full object-cover scale-x-[-1]"
              ></video>
              <!-- Off state -->
              <div v-else class="flex flex-col items-center gap-3 text-white/40">
                <div class="w-16 h-16 rounded-full bg-white/10 flex items-center justify-center">
                  <i class="fa-solid fa-video-slash text-2xl"></i>
                </div>
                <span class="text-xs">Camera is off</span>
              </div>

              <!-- Loading overlay -->
              <div v-if="isLoadingCamera" class="absolute inset-0 flex items-center justify-center bg-black/50">
                <span class="loading loading-spinner loading-md text-primary"></span>
              </div>

              <!-- Camera error -->
              <div v-if="cameraError && settings.cameraEnabled" class="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/60 text-red-400 text-xs px-4 text-center">
                <i class="fa-solid fa-triangle-exclamation text-xl"></i>
                <p>{{ cameraError }}</p>
              </div>
            </div>

            <!-- Camera device selector -->
            <select
              v-model="settings.selectedCamera"
              class="select select-bordered select-sm w-full text-xs bg-[#3c4043] border-white/10 text-white"
              @change="onCameraDeviceChange"
              :disabled="!settings.cameraEnabled"
            >
              <option value="" disabled>Choose camera</option>
              <option
                v-for="device in availableDevices.cameras"
                :key="device.deviceId"
                :value="device.deviceId"
              >
                {{ device.label || `Camera ${device.deviceId.slice(0, 8)}` }}
              </option>
            </select>
          </div>

          <!-- ── DIVIDER ── -->
          <div class="border-t border-white/10"></div>

          <!-- ── MIC + SPEAKER grid ── -->
          <div class="grid grid-cols-2 gap-6">

            <!-- Microphone -->
            <div class="space-y-4">
              <div class="text-sm font-semibold text-white flex items-center gap-2">
                <i class="fa-solid fa-microphone text-primary"></i>
                Microphone
              </div>

              <div class="space-y-2">
                <label class="text-xs font-semibold text-white/50">Device</label>
                <select
                  v-model="settings.selectedMicrophone"
                  class="select select-bordered select-sm w-full text-xs bg-[#3c4043] border-white/10 text-white"
                >
                  <option value="" disabled>Choose microphone</option>
                  <option
                    v-for="device in availableDevices.microphones"
                    :key="device.deviceId"
                    :value="device.deviceId"
                  >
                    {{ device.label || `Mic ${device.deviceId.slice(0, 8)}` }}
                  </option>
                </select>
              </div>

              <!-- Mic level meter -->
              <div class="space-y-1">
                <label class="text-xs text-white/50">Input level</label>
                <div class="h-2 rounded-full bg-white/10 overflow-hidden">
                  <div
                    class="h-full rounded-full bg-primary transition-all duration-75"
                    :style="{ width: micLevel + '%' }"
                  ></div>
                </div>
              </div>

              <button
                @click="testMicrophone"
                :disabled="isTestingMic"
                class="w-full btn btn-outline btn-sm gap-2 border-white/20 text-white/70 hover:text-white"
              >
                <span v-if="isTestingMic" class="loading loading-spinner loading-xs"></span>
                <i v-else class="fa-solid fa-microphone text-xs"></i>
                {{ isTestingMic ? 'Testing…' : 'Test mic' }}
              </button>

              <div class="space-y-1 pt-1">
                <label class="flex items-center gap-2 p-2 rounded-lg hover:bg-white/5 cursor-pointer transition-colors">
                  <input v-model="settings.noiseSuppression" type="checkbox" class="checkbox checkbox-xs checkbox-primary" />
                  <span class="text-xs text-white/70">Noise suppression</span>
                </label>
                <label class="flex items-center gap-2 p-2 rounded-lg hover:bg-white/5 cursor-pointer transition-colors">
                  <input v-model="settings.echoCancellation" type="checkbox" class="checkbox checkbox-xs checkbox-primary" />
                  <span class="text-xs text-white/70">Echo cancellation</span>
                </label>
                <label class="flex items-center gap-2 p-2 rounded-lg hover:bg-white/5 cursor-pointer transition-colors">
                  <input v-model="settings.autoGainControl" type="checkbox" class="checkbox checkbox-xs checkbox-primary" />
                  <span class="text-xs text-white/70">Auto-gain control</span>
                </label>
              </div>
            </div>

            <!-- Speaker -->
            <div class="space-y-4">
              <div class="text-sm font-semibold text-white flex items-center gap-2">
                <i class="fa-solid fa-volume-high text-primary"></i>
                Speaker
              </div>

              <div class="space-y-2">
                <label class="text-xs font-semibold text-white/50">Device</label>
                <select
                  v-model="settings.selectedSpeaker"
                  class="select select-bordered select-sm w-full text-xs bg-[#3c4043] border-white/10 text-white"
                >
                  <option value="" disabled>Choose speaker</option>
                  <option
                    v-for="device in availableDevices.speakers"
                    :key="device.deviceId"
                    :value="device.deviceId"
                  >
                    {{ device.label || `Speaker ${device.deviceId.slice(0, 8)}` }}
                  </option>
                </select>
              </div>

              <!-- Volume slider -->
              <div class="space-y-2">
                <div class="flex items-center justify-between">
                  <label class="text-xs text-white/50">Volume</label>
                  <span class="text-xs font-mono text-white/70">{{ Math.round(settings.speakerVolume) }}%</span>
                </div>
                <input
                  v-model.number="settings.speakerVolume"
                  type="range" min="0" max="100" step="5"
                  class="range range-sm range-primary w-full"
                />
              </div>

              <button
                @click="testSpeaker"
                :disabled="isTestingSpeaker"
                class="w-full btn btn-outline btn-sm gap-2 border-white/20 text-white/70 hover:text-white"
              >
                <span v-if="isTestingSpeaker" class="loading loading-spinner loading-xs"></span>
                <i v-else class="fa-solid fa-volume-high text-xs"></i>
                {{ isTestingSpeaker ? 'Playing…' : 'Test speaker' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="flex gap-3 px-6 py-4 border-t border-white/10 bg-[#2d2f31] shrink-0 rounded-b-2xl">
        <button @click="cancelAndClose" class="flex-1 btn btn-ghost btn-sm text-white/60 hover:text-white">
          Cancel
        </button>
        <button @click="saveSettings" class="flex-1 btn btn-primary btn-sm gap-2">
          <i class="fa-solid fa-check"></i>
          Save
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MeetSettingsModal',
  props: {
    currentSettings: { type: Object, default: () => ({}) }
  },
  emits: ['close', 'save'],
  data() {
    return {
      settings: {
        selectedMicrophone: '',
        selectedSpeaker: '',
        selectedCamera: '',
        microphoneVolume: 80,
        speakerVolume: 80,
        cameraEnabled: false,
        autoGainControl: true,
        noiseSuppression: true,
        echoCancellation: true,
        highPassFilter: true,
        experimentalFeatures: false
      },
      isTestingMic: false,
      isTestingSpeaker: false,
      isLoadingCamera: false,
      cameraStream: null,
      cameraError: null,
      micLevel: 0,
      micAnalyserInterval: null,
      availableDevices: {
        microphones: [],
        speakers: [],
        cameras: []
      }
    }
  },
  created() {
    this.initSettings()
    this.loadDevices()
  },
  beforeUnmount() {
    this.stopCameraStream()
    clearInterval(this.micAnalyserInterval)
  },
  methods: {
    initSettings() {
      if (this.currentSettings && Object.keys(this.currentSettings).length > 0) {
        this.settings = { ...this.settings, ...this.currentSettings }
      }
    },
    async loadDevices() {
      try {
        const result = await this.$storex.meets.enumerateDevices()
        if (result.success) {
          this.availableDevices = {
            microphones: result.microphones || [],
            speakers: result.speakers || [],
            cameras: result.cameras || []
          }
          if (!this.settings.selectedMicrophone && this.availableDevices.microphones.length > 0) {
            this.settings.selectedMicrophone = this.availableDevices.microphones[0].deviceId
          }
          if (!this.settings.selectedSpeaker && this.availableDevices.speakers.length > 0) {
            this.settings.selectedSpeaker = this.availableDevices.speakers[0].deviceId
          }
          if (!this.settings.selectedCamera && this.availableDevices.cameras.length > 0) {
            this.settings.selectedCamera = this.availableDevices.cameras[0].deviceId
          }
          // Auto-start preview if camera was previously enabled
          if (this.settings.cameraEnabled) {
            this.startCameraStream()
          }
        }
      } catch (error) {
        console.error('[MeetSettingsModal] Failed to load devices:', error)
      }
    },
    async onCameraToggle() {
      if (this.settings.cameraEnabled) {
        await this.startCameraStream()
      } else {
        this.stopCameraStream()
      }
    },
    async onCameraDeviceChange() {
      if (this.settings.cameraEnabled && this.cameraStream) {
        this.stopCameraStream()
        await this.startCameraStream()
      }
    },
    async startCameraStream() {
      this.isLoadingCamera = true
      this.cameraError = null
      try {
        const constraints = {
          video: this.settings.selectedCamera
            ? { deviceId: { exact: this.settings.selectedCamera } }
            : true,
          audio: false
        }
        const stream = await navigator.mediaDevices.getUserMedia(constraints)
        this.cameraStream = stream
        // Wait for DOM update then bind to video element
        this.$nextTick(() => {
          if (this.$refs.cameraPreview) {
            this.$refs.cameraPreview.srcObject = stream
          }
        })
      } catch (error) {
        console.error('[MeetSettingsModal] Camera error:', error)
        this.cameraError = error.name === 'NotAllowedError'
          ? 'Camera permission denied. Please allow access in your browser.'
          : error.name === 'NotFoundError'
          ? 'No camera found on this device.'
          : 'Could not start camera: ' + error.message
        this.settings.cameraEnabled = false
      } finally {
        this.isLoadingCamera = false
      }
    },
    stopCameraStream() {
      if (this.cameraStream) {
        this.cameraStream.getTracks().forEach(t => t.stop())
        this.cameraStream = null
      }
    },
    async testMicrophone() {
      this.isTestingMic = true
      try {
        const result = await this.$storex.meets.requestMicrophone({
          deviceId: this.settings.selectedMicrophone || 'default'
        })
        if (result.success && result.stream) {
          result.stream.getTracks().forEach(track => track.stop())
          this.$storex.session.onInfo('Microphone is working ✓')
        } else {
          this.$storex.session.onWarning(result.error || 'Microphone test failed')
        }
      } catch (error) {
        this.$storex.session.onError('Microphone test error')
      } finally {
        this.isTestingMic = false
      }
    },
    async testSpeaker() {
      this.isTestingSpeaker = true
      try {
        const result = await this.$storex.meets.testAudioOutput({ frequency: 1000, duration: 1000 })
        if (result.success) {
          this.$storex.session.onInfo('Speaker is working ✓')
        } else {
          this.$storex.session.onWarning(result.error || 'Speaker test failed')
        }
      } catch (error) {
        this.$storex.session.onError('Speaker test error')
      } finally {
        this.isTestingSpeaker = false
      }
    },
    cancelAndClose() {
      this.stopCameraStream()
      this.$emit('close')
    },
    saveSettings() {
      this.$emit('save', { ...this.settings })
      try {
        localStorage.setItem('meetSettings', JSON.stringify(this.settings))
      } catch (e) {
        console.warn('Failed to save settings:', e)
      }
      this.stopCameraStream()
      this.$emit('close')
    }
  }
}
</script>