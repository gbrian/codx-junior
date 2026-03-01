<script setup>
import PluginModal from './PluginModal.vue';
</script>

<template>
  <div class="card shadow hover:shadow-lg cursor-pointer bg-base-100 border">
    <div class="card-body flex flex-col">
      <h2 class="card-title">{{ plugin.name }}</h2>
      <p>{{ plugin.description }}</p>
      <div class="grow"></div>
      <div>
        {{ plugin.extends.join(',') }}
      </div>
      <button @click.stop="toggleModal" class="btn btn-primary mt-2">Test</button>
    </div>
  </div>
  <modal close="true" @close="showModal = false" v-if="showModal">
    <PluginModal :plugin="plugin" @save="handleSave" />
  </modal>
  
</template>
<script>
export default {
  props: ['plugin'],
  data() {
    return {
      showModal: false,
    }
  },
  methods: {
    toggleModal() {
      this.showModal = !this.showModal
    },
    handleSave() {
      // Construct dictionary from arguments
      const argumentDict = this.plugin.arguments.reduce((acc, arg) => {
        acc[arg.name] = arg.default_value
        return acc
      }, {})
      this.$emit('test', argumentDict)
      this.showModal = false
    }
  }
}
</script>