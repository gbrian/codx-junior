<script setup>
import Selector from './Selector.vue'
</script>

<template>
  <Selector
    :items="formattedModels"
    :selected-items="selectedModelItem"
    label="Model"
    icon="fa-solid fa-brain"
    :is-single-select="true"
    :allow-deselect="true"
    :empty-label="'default'"
    @update:selected-items="onModelSelected"
  >
    <!-- Custom model card rendering -->
    <template #default="{ item, selected }">
      <div class="flex flex-col items-center gap-1 p-2 rounded-lg cursor-pointer transition-all hover:bg-base-300"
        :class="selected ? 'bg-primary text-primary-content' : 'bg-base-100'"
        :title="item.description"
      >
        <div class="relative">
          <div class="w-8 h-8 rounded-full bg-base-300 flex items-center justify-center">
            <i class="fa-solid fa-brain text-xs"></i>
          </div>
          <div
            v-if="selected"
            class="absolute -top-1 -right-1 bg-success text-white rounded-full w-4 h-4 flex items-center justify-center text-xs"
          >
            ✓
          </div>
        </div>
        <span class="text-xs font-medium text-center truncate w-full">{{ item.name }}</span>
        <span class="text-xs opacity-75 text-center truncate w-full">{{ item.description }}</span>
      </div>
    </template>
  </Selector>
</template>

<script>
export default {
  props: {
    selectedModel: String,
    models: {
      type: Array,
      default: () => []
    }
  },
  emits: ['model-changed'],
  computed: {
    formattedModels() {
      return (this.models || []).map(model => ({
        name: model.name,
        description: model.ai_model || model.description,
        avatar: null
      }))
    },
    selectedModelItem() {
      if (!this.selectedModel) return []
      const model = this.formattedModels.find(m => m.name === this.selectedModel)
      return model ? [model] : []
    }
  },
  methods: {
    onModelSelected(selectedItems) {
      const modelName = selectedItems.length > 0 ? selectedItems[0].name : null
      this.$emit('model-changed', modelName)
    }
  }
}
</script>