<script setup>
</script>

<template>
  <div class="flex flex-col h-full bg-base-200">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-base-content/10">
      <h2 class="text-base font-semibold flex items-center gap-2">
        <i class="fa-solid fa-sliders text-primary"></i>
        Media Settings
      </h2>
      <button
        @click="$emit('collapse')"
        class="btn btn-ghost btn-sm btn-circle"
        title="Collapse settings"
      >
        <i class="fa-solid fa-chevron-right"></i>
      </button>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto space-y-4 p-4">
      <!-- Microphone Settings -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <label class="text-sm font-semibold">Microphone</label>
          <button
            @click="testMicrophone"
            :disabled="isTestingMic"
            class="btn btn-ghost btn-xs gap-1"
            :class="isTestingMic ? 'loading' : ''"
          >
            <i class="fa-solid fa-play text-xs"></i>
            Test
          </button>
        </div>

        <!-- Microphone Selection -->
        <select
          v-model="settings.selectedMicrophone"
          @change="updateSettings"
          class="select select-bordered select-sm w-full text-xs"
        >
          <option value="" disabled>Select microphone</option>
          <option
            v-for="device in availableDevices.microphones"
            :key="device.deviceId"
            :value="device.deviceId"
          >
            {{ device.label || `Microphone ${device.deviceId.slice(0, 8)}` }}
          </option>
        </select>

        <!-- Microphone Volume Level -->
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <label class="text-xs text-base-content/60">Volume</label>
            <span class="text-xs font-mono bg-base-300 px-2 py-1 rounded">
              {{ Math.round(settings.microphoneVolume) }}%
            </span>
          </div>
          <input
            v-model.number="settings.microphoneVolume"
            @input="updateSettings"
            type="range"
            min="0"
            max="100"
            step="5"
            class="range range-sm w-full"
          />
          <div class="flex justify-between text-xs text-base-content/40 px-1">
            <span>Quiet</span>
            <span>Loud</span>
          </div>
        </div>

        <!-- Auto Gain Control -->
        <label class="flex items-center gap-2 p-2 rounded-lg hover:bg-base-content/5 cursor-pointer transition-colors">
          <input
            v-model="settings.autoGainControl"
            @change="updateSettings"
            type="checkbox"
            class="checkbox checkbox-sm"
          />
          <span class="text-xs font-medium flex-1">Auto-gain control</span>
          <i class="fa-solid fa-info-circle text-xs text-base-content/40"></i>
        </label>

        <!-- Noise Suppression -->
        <label class="flex items-center gap-2 p-2 rounded-lg hover:bg-base-content/5 cursor-pointer transition-colors">
          <input
            v-model="settings.noiseSuppression"
            @change="updateSettings"
            type="checkbox"
            class="checkbox checkbox-sm"
            checked
          />
          <span class="text-xs font-medium flex-1">Noise suppression</span>
          <i class="fa-solid fa-info-circle text-xs text-base-content/40"></i>
        </label>
      </div>

      <!-- Divider -->
      <div class="divider my-2"></div>

      <!-- Speaker Settings -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <label class="text-sm font-semibold">Speaker</label>
          <button
            @click="testSpeaker"
            :disabled="isTestingSpeaker"
            class="btn btn-ghost btn-xs gap-1"
            :class="isTestingSpeaker ? 'loading' : ''"
          >
            <i class="fa-solid fa-play text-xs"></i>
            Test
          </button>
        </div>

        <!-- Speaker Selection -->
        <select
          v-model="settings.selectedSpeaker"
          @change="updateSettings"
          class="select select-bordered select-sm w-full text-xs"
        >
          <option value="" disabled>Select speaker</option>
          <option
            v-for="device in availableDevices.speakers"
            :key="device.deviceId"
            :value="device.deviceId"
          >
            {{ device.label || `Speaker ${device.deviceId.slice(0, 8)}` }}
          </option>
        </select>

        <!-- Speaker Volume Level -->
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <label class="text-xs text-base-content/60">Volume</label>
            <span class="text-xs font-mono bg-base-300 px-2 py-1 rounded">
              {{ Math.round(settings.speakerVolume) }}%
            </span>
          </div>
          <input
            v-model.number="settings.speakerVolume"
            @input="updateSettings"
            type="range"
            min="0"
            max="100"
            step="5"
            class="range range-sm w-full"
          />
          <div class="flex justify-between text-xs text-base-content/40 px-1">
            <span>Quiet</span>
            <span>Loud</span>
          </div>
        </div>
      </div>

      <!-- Divider -->
      <div class="divider my-2"></div>

      <!-- Camera Settings (Coming Soon) -->
      <div class="space-y-3 opacity-50 cursor-not-allowed">
        <div class="flex items-center gap-2">
          <label class="text-sm font-semibold flex-1">Camera</label>
          <span class="badge badge-sm badge-warning gap-1">
            <i class="fa-solid fa-clock text-xs"></i>
            Coming Soon
          </span>
        </div>
        <select disabled class="select select-bordered select-sm w-full text-xs">
          <option>Camera (disabled)</option>
        </select>
      </div>

      <!-- Divider -->
      <div class="divider my-2"></div>

      <!-- Advanced Settings -->
      <div class="space-y-3">
        <div class="text-xs font-semibold text-base-content/60 uppercase">Advanced</div>

        <!-- Echo Cancellation -->
        <label class="flex items-center gap-2 p-2 rounded-lg hover:bg-base-content/5 cursor-pointer transition-colors">
          <input
            v-model="settings.echoCancellation"
            @change="updateSettings"
            type="checkbox"
            class="checkbox checkbox-sm"
            checked
          />
          <span class="text-xs font-medium flex-1">Echo cancellation</span>
        </label>

        <!-- High Pass Filter -->
        <label class="flex items-center gap-2 p-2 rounded-lg hover:bg-base-content/5 cursor-pointer transition-colors">
          <input
            v-model="settings.highPassFilter"
            @change="updateSettings"
            type="checkbox"
            class="checkbox checkbox-sm"
            checked
          />
          <span class="text-xs font-medium flex-1">High-pass filter</span>
        </label>

        <!-- Experimental Features -->
        <label class="flex items-center gap-2 p-2 rounded-lg hover:bg-base-content/5 cursor-pointer transition-colors">
          <input
            v-model="settings.experimentalFeatures"
            @change="updateSettings"
            type="checkbox"
            class="checkbox checkbox-sm"
          />
          <span class="text-xs font-medium flex-1">Experimental features</span>
        </label>
      </div>

      <!-- Info Box -->
      <div class="p-3 rounded-lg bg-info/10 border border-info/30 text-xs text-info space-y-1 mt-4">
        <div class="flex items-start gap-2">
          <i class="fa-solid fa-info-circle mt-0.5 shrink-0"></i>
          <div>
            <p class="font-semibold mb-0.5">Tip:</p>
            <p class="text-info/80">Use the Test buttons to verify your audio devices before joining a call.</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="flex gap-3 p-4 border-t border-base-content/10 bg-base-300">
      <button
        @click="resetSettings"
        class="flex-1 btn btn-ghost btn-sm"
      >
        Reset
      </button>
      <button
        @click="saveSettings"
        class="flex-1 btn btn-primary btn-sm"
      >
        Save
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MeetSettingsPanel',
  props: {
    currentSettings: { type: Object, default: () => ({}) }
  },
  emits: ['collapse', 'save'],
  data() {
    return {
      settings: {
        selectedMicrophone: '',
        selectedSpeaker: '',
        microphoneVolume: 80,
        speakerVolume: 80,
        autoGainControl: true,
        noiseSuppression: true,
        echoCancellation: true,
        highPassFilter: true,
        experimentalFeatures: false
      },
      isTestingMic: false,
      isTestingSpeaker: false,
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
  methods: {
    async initSettings() {
      // Load from current settings or defaults
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

          // Set default device if not already set
          if (!this.settings.selectedMicrophone && this.availableDevices.microphones.length > 0) {
            this.settings.selectedMicrophone = this.availableDevices.microphones[0].deviceId
          }
          if (!this.settings.selectedSpeaker && this.availableDevices.speakers.length > 0) {
            this.settings.selectedSpeaker = this.availableDevices.speakers[0].deviceId
          }
        }
      } catch (error) {
        console.error('[MeetSettingsPanel] Failed to load devices:', error)
      }
    },
    async testMicrophone() {
      this.isTestingMic = true
      try {
        const result = await this.$storex.meets.requestMicrophone({
          deviceId: this.settings.selectedMicrophone || 'default'
        })

        if (result.success && result.stream) {
          // Stop the stream immediately
          result.stream.getTracks().forEach(track => track.stop())
          this.$storex.session.onInfo('Microphone is working')
        } else {
          this.$storex.session.onWarning(result.error || 'Microphone test failed')
        }
      } catch (error) {
        console.error('Microphone test failed:', error)
        this.$storex.session.onError('Microphone test error')
      } finally {
        this.isTestingMic = false
      }
    },
    async testSpeaker() {
      this.isTestingSpeaker = true
      try {
        const result = await this.$storex.meets.testAudioOutput({
          frequency: 1000,
          duration: 1000
        })

        if (result.success) {
          this.$storex.session.onInfo('Speaker is working')
        } else {
          this.$storex.session.onWarning(result.error || 'Speaker test failed')
        }
      } catch (error) {
        console.error('Speaker test failed:', error)
        this.$storex.session.onError('Speaker test error')
      } finally {
        this.isTestingSpeaker = false
      }
    },
    updateSettings() {
      // Validation or processing can happen here if needed
    },
    resetSettings() {
      this.initSettings()
      this.$storex.session.onInfo('Settings reset to default')
    },
    saveSettings() {
      this.$emit('save', this.settings)
      // Optionally save to store/localStorage
      try {
        localStorage.setItem('meetSettings', JSON.stringify(this.settings))
      } catch (e) {
        console.warn('Failed to save settings to localStorage:', e)
      }
    }
  }
}
</script>