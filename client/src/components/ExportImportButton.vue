<template>
  <div class="dropdown dropdown-hover dropdown-bottom dropdown-end">
    <modal v-if="showImport" :close="true" @close="showImport = false">
      <div class="flex flex-col gap-2">
        <div class="text-xl">Paste your JSON settings here</div>
        <textarea v-model="importData" class="textarea textarea-bordered w-full"></textarea>
        <button class="btn btn-sm btn-primary" @click="submit">Import</button>
      </div>
    </modal>
    <div tabindex="0" role="button" class="btn btn-sm m-1"><i class="fa-solid fa-bars"></i></div>
    <ul tabindex="0" class="dropdown-content menu bg-base-300 rounded-box z-50 w-52 p-2 shadow-sm">
      <slot></slot>
      <li @click="exportSettings"><a>Export</a></li>
      <li @click="importSettings"><a>Import</a></li>
    </ul>
  </div>

</template>

<script>
export default {
  props: ['data'],
  data() {
    return {
      showImport: false,
      importData: null
    }
  },
  methods:{
    exportSettings() {
      const settingsText = JSON.stringify(this.data, null, 2)
      this.$ui.copyTextToClipboard(settingsText)
    },
    importSettings() {
      this.showImport = true
    },
    submit() {
      this.showImport = false
      this.$emit('change', JSON.parse(this.importData))
    }
  }
}
</script>