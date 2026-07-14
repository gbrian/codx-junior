<template>
  <div class="space-y-3">
    <div v-for="(template, id) in templates" :key="id" class="card border-2 cursor-pointer transition-all"
      :class="[
        selected?.id === id ? 'border-primary bg-primary/5' : 'border-base-200 hover:border-primary/50'
      ]"
      @click="$emit('select', template)"
    >
      <div class="card-body p-4 flex-row items-center gap-4">
        <div class="w-12 h-12 rounded-lg flex items-center justify-center text-xl shrink-0"
          :class="`bg-${template.color}/10 text-${template.color}`"
        >
          <i :class="`fa-solid ${template.icon}`"></i>
        </div>
        <div class="flex-1">
          <h3 class="font-bold">{{ template.name }}</h3>
          <p class="text-sm text-base-content/60">{{ template.description }}</p>
        </div>
        <div class="shrink-0">
          <input
            type="radio"
            class="radio"
            :checked="selected?.id === id"
            @change="$emit('select', template)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    templates: Object,
    selected: Object
  },
  emits: ['select']
}
</script>