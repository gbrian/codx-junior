<script setup>
</script>

<template>
  <div class="dropdown dropdown-top">
    <div tabindex="0" role="button" class="click tooltip -mb-2 badge badge-xs badge-outline badge-warning" 
    :data-tip="selectedModelLabel">
      <span class="text-xs max-w-20 truncate" v-if="selectedModel">
        {{ selectedModel }}
      </span>
      <span class="text-xs opacity-50" v-else>default</span>
    </div>
    <ul tabindex="0" class="dropdown-content menu bg-base-200 rounded-box z-[1] w-60 p-2 shadow max-h-60 overflow-auto gap-1">
      <li>
        <a class="btn btn-sm btn-ghost justify-start"
          :class="!selectedModel && 'btn-active'"
          @click="$emit('model-changed', '')">
          <span>-- default --</span>
        </a>
      </li>
      <li v-for="model in models" :key="model.name">
        <a class="btn btn-sm btn-ghost justify-start"
          :class="selectedModel === model.name && 'btn-active'"
          @click="$emit('model-changed', model.name)">
          <span class="truncate">{{ model.name }}</span>
          <span class="text-xs opacity-50 truncate" v-if="model.ai_model">({{ model.ai_model }})</span>
        </a>
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  props: ['selectedModel', 'models'],
  emits: ['model-changed'],
  computed: {
    selectedModelLabel() {
      if (!this.selectedModel) return 'Default model'
      const model = this.models?.find(m => m.name === this.selectedModel)
      return model ? `${model.name}${model.ai_model ? ' (' + model.ai_model + ')' : ''}` : this.selectedModel
    }
  }
}
</script>