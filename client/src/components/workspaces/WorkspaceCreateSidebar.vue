<script setup>
</script>

<template>
  <div class="w-64 border-r border-base-200 bg-base-100 flex flex-col p-6 shrink-0">
    
    <!-- Progress Steps -->
    <div class="space-y-3">
      <div
        v-for="(step, idx) in steps"
        :key="step.id"
        class="cursor-pointer transition-all"
        :class="[
          'py-3 px-4 rounded-lg flex items-center gap-3',
          activeSection === step.id
            ? 'bg-primary/10 border-l-4 border-primary'
            : 'hover:bg-base-200'
        ]"
        @click="$emit('select-section', step.id)"
      >
        <!-- Step Number Badge -->
        <div
          class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm shrink-0"
          :class="[
            activeSection === step.id || isStepComplete(idx)
              ? 'bg-primary text-primary-content'
              : 'bg-base-300 text-base-content/50'
          ]"
        >
          <span v-if="!isStepComplete(idx)">{{ idx + 1 }}</span>
          <i v-else class="fa-solid fa-check"></i>
        </div>

        <!-- Step Label -->
        <div class="flex-1 min-w-0">
          <div class="font-semibold text-sm">{{ step.label }}</div>
          <div class="text-xs text-base-content/50">{{ step.description }}</div>
        </div>

        <!-- Indicator -->
        <i
          v-if="activeSection === step.id"
          class="fa-solid fa-chevron-right text-primary shrink-0"
        ></i>
      </div>
    </div>

    <!-- Divider -->
    <div class="divider my-6"></div>

    <!-- Quick Summary -->
    <div v-if="form.template" class="space-y-2 text-sm">
      <div class="font-semibold text-base-content/70">Selected</div>
      
      <div class="space-y-1 p-2 rounded-lg bg-base-200/30">
        <div class="flex items-center gap-2">
          <i class="fa-solid fa-cube text-info text-xs"></i>
          <span class="text-xs text-base-content/60">Template</span>
        </div>
        <div class="font-medium text-sm">{{ getTemplateName(form.template) }}</div>
      </div>

      <div v-if="form.name" class="space-y-1 p-2 rounded-lg bg-base-200/30">
        <div class="flex items-center gap-2">
          <i class="fa-solid fa-tag text-warning text-xs"></i>
          <span class="text-xs text-base-content/60">Name</span>
        </div>
        <div class="font-medium text-sm truncate">{{ form.name }}</div>
      </div>

      <div v-if="form.project_ids?.length" class="space-y-1 p-2 rounded-lg bg-base-200/30">
        <div class="flex items-center gap-2">
          <i class="fa-solid fa-folder text-success text-xs"></i>
          <span class="text-xs text-base-content/60">Projects</span>
        </div>
        <div class="font-medium text-sm">{{ form.project_ids.length }} selected</div>
      </div>

      <div v-if="form.apps?.length" class="space-y-1 p-2 rounded-lg bg-base-200/30">
        <div class="flex items-center gap-2">
          <i class="fa-solid fa-layer-group text-secondary text-xs"></i>
          <span class="text-xs text-base-content/60">Apps</span>
        </div>
        <div class="font-medium text-sm">{{ form.apps.length }} configured</div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    activeSection: String,
    form: Object,
    isValid: Boolean
  },
  emits: ['select-section'],
  data() {
    return {
      steps: [
        {
          id: 'workspace',
          label: 'Workspace Type',
          description: 'Choose a template'
        },
        {
          id: 'basic',
          label: 'Basic Info',
          description: 'Name & location'
        },
        {
          id: 'configure',
          label: 'Configuration',
          description: 'Projects & apps'
        }
      ]
    }
  },
  methods: {
    isStepComplete(stepIdx) {
      const steps = ['workspace', 'basic', 'configure']
      const currentIdx = steps.indexOf(this.activeSection)
      return stepIdx < currentIdx
    },
    getTemplateName(templateId) {
      const templates = {
        'static-site': 'Static Site',
        'dev-stack': 'Full-Stack Dev',
        'custom': 'Custom'
      }
      return templates[templateId] || 'Unknown'
    }
  }
}
</script>