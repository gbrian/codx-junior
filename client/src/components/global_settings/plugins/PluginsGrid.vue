<script setup>
import PluginCard from './PluginCard.vue'
import PluginModal from './PluginModal.vue'
import LoadPluginModal from './LoadPluginModal.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-4 p-4">
    <header class="w-full flex justify-between items-center mb-4">
      <h1 class="text-2xl font-bold">Plugins</h1>
      <button @click="showLoader = true" class="btn btn-sm btn-info">Load Plugin</button>
    </header>
    <div class="grid grid-cols-1 @lg:grid-cols-2 @4xl:grid-cols-3 @5xl:grid-cols-4 gap-4">
      <PluginCard
        v-for="plugin in plugins"
        :key="plugin.name"
        :plugin="plugin"
        @click="editablePlugin = plugin"
      />
    </div>
    <modal close="true" @close="editablePlugin = null" v-if="editablePlugin">
      <PluginModal :plugin="editablePlugin" @remove="removePlugin" @save="savePlugin" @close="editablePlugin = null" />
    </modal>
    <LoadPluginModal v-if="showLoader" @close="showLoader = false" @loadPlugin="loadFromfile" />
  </div>
</template>

<script>
export default {
  data() {
    return {
      plugins: [],
      showLoadPlugin: false,
      editablePlugin: null,
      showLoader: false
    }
  },
  methods: {
    async savePlugin() {
      await this.$storex.api.settings.global.plugins.add(this.editablePlugin)
      this.editablePlugin = null
      this.loadPlugins()
    },
    async removePlugin() {
      await this.$storex.api.settings.global.plugins.remove(this.editablePlugin.name)
      this.editablePlugin = null
      this.loadPlugins()
    },
    async loadPlugins() {
      const plugins = await this.$storex.api.settings.global.plugins.list()
      this.plugins = plugins
      this.showLoader = false
    },
    async loadFromfile(filePath) {
      await this.$storex.api.settings.global.plugins.loadFromFile(filePath)
      this.loadPlugins()
    },
    async execPlugin(plugin, context) {
      await this.$storex.api.settings.global.plugins.execPlugin(plugin.plugin_id, context)
      this.loadPlugins()
    }
  },
  mounted() {
    this.loadPlugins()
  }
}
</script>