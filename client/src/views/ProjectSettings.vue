<template>
  <div class="flex flex-col gap-2 h-full">
    <div class="text-xl font-medium my-2 flex justify-between px-2">
      Settings
      <div class="grow"></div>
      <div class="flex gap-2 justify-end">
        <button type="button" @click="reloadSettings" class="btn btn-sm btn-outline btn-accent">Reload</button>
        <button type="submit" class="btn  btn-sm btn-primary" @click="saveSettings">Save</button>
      </div>
    </div>
    <div class="grow px-2">
      <div class="flex justify-between mb-2" v-for="(value, key) in projectSettings" :key="key">
        <div class="label-text">{{ key }}</div>
        <div class="w-1/2">
          <input v-if="typeof value === 'boolean'" type="checkbox" v-model="settings[key]" class="toggle" />
          <input v-else type="text" v-model="settings[key]" class="input input-bordered w-full" />
        </div>
      </div>
    </div>
    <div class="flex flex-col gap-2 bg-base-200 p-2">
      <div class="text-xl text-error">Danger zone</div>
      <button class="btn btn-error" @click="deleteProject">
        <div class="flex gap-2" v-if="confirmDelete">
          Confirm delete? <span class="hover:underline">YES</span> / <span  class="hover:underline" @click.stop="confirmDelete = false">NO</span>
        </div>
        <div v-else>
          Delete project
        </div>
      </button>
    </div>
  </div>
</template>

<script>
import { API } from '../api/api'
export default {
  data() {
    return {
      settings: API.lastSettings,
      confirmDelete: false
    };
  },
  async created () {
    this.reloadSettings()
  },
  computed: {
    projectSettings () {
      return this.settings ? Object.keys(this.settings)
        .filter(k => !k.startsWith("_"))
        .sort().reduce((acc, key) => ({
          ...acc,
          [key]: this.settings[key]
        }), {}) : null
    }
  },
  methods: {
    async reloadSettings() {
      this.settings = API.lastSettings
    },
    async saveSettings() {
      await API.settings.write(this.settings)
      this.reloadSettings()
    },
    deleteProject () {
      if (this.confirmDelete) {
        this.$emit('delete')
      } else {
        this.confirmDelete = true
      }
    }
  },
};
</script>