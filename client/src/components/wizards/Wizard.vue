<script setup>
</script>
<template>
  <div class="p-4 rounded shadow max-w-md mx-auto">
    <h2 class="text-xl font-semibold mb-4">{{ wizard.title }}</h2>
    <ol class="space-y-2 list-decimal pl-4">
      <li v-for="(text, index) in wizard.steps" :key="index" class="flex items-center">
        <span :class="{'opacity-60': step < index}">
          <span class="loading loading-spinner loading-xs" v-if="step === index"></span>
          <span class="text-success" v-if="step > index">
            <i class="fa-solid fa-circle-check"></i>
          </span>
          {{ text }}
        </span>
      </li>
    </ol>
    <div class="mt-4 text-center">
      <button @click="close" v-if="done" class="btn">
        Close
      </button>
      <button @click="cancel" v-else class="btn btn-error">
        Cancel
      </button>
    </div>
  </div>
</template>
<script>
export default {
  props: ['wizard'],
  data() {
    return {
      step: 0,
      done: false
    }
  },
  mounted() {
    this.runWizard()
  },
  methods: {
    runWizard() {
      this.wizard.next().then(this.wizardStep.bind(this))
    },
    wizardStep({ step, done }) {
      this.step = step
      this.done = done
      if (!this.done) {
        this.runWizard()
      }
    },
    close() {
      this.done = true
      this.$emit('close')
    },
    cancel () {
      this.wizard.cancel()
      this.close()
    }
  }
}
</script>
