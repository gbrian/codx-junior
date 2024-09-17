<template>
  <div class="flex flex-col gap-2 h-full">
    <div class="text-xl font-medium my-2 flex justify-between">
      GPT Settings
      <div class="grow"></div>
      <div class="flex gap-2 justify-end">
        <button type="button" @click="reloadSettings" class="btn btn-sm btn-outline btn-accent">Reload</button>
        <button type="submit" class="btn  btn-sm btn-primary" @click="saveSettings">Save</button>
      </div>
    </div>
    <div class="grow relative overflow-auto">
      <div class="absolute top-0 left-0 right-0 bottom-0">
        <div class="flex justify-between mb-2" v-for="(value, key) in projectSettings" :key="key">
          <div class="label-text">{{ key }}</div>
          <div class="w-1/2">
            <input v-if="typeof value === 'boolean'" type="checkbox" v-model="settings[key]" class="toggle" />
            <input v-else type="text" v-model="settings[key]" class="input input-bordered w-full" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { API } from '../api/api'
export default {
  data() {
    return {
      settings: null,
    };
  },
  async created () {
    this.reloadSettings()
  },
  computed: {
    projectSettings () {
      return this.settings ? Object.keys(this.settings).sort().reduce((acc, key) => ({
        ...acc,
        [key]: this.settings[key]
      }), {}) : null
    }
  },
  methods: {
    async reloadSettings() {
      const { data: settings } = await API.settings.read()
      this.settings = settings
    },
    async saveSettings() {
      await API.settings.write(this.settings)
      this.reloadSettings()
    },
  },
};
</script>