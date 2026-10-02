<script setup>
</script>

<template>
  <div class="flex flex-col gap-4 p-4 min-w-72">
    <h3 class="font-bold text-lg">{{ isEdit ? 'Edit view' : 'New view' }}</h3>

    <div class="flex flex-col gap-2">
      <label class="text-sm opacity-70">View name</label>
      <input
        v-model="form.name"
        type="text"
        class="input input-bordered w-full"
        placeholder="View name..."
        @keyup.enter="confirm"
        ref="nameInput"
      />
    </div>

    <div class="flex gap-2 justify-end mt-2">
      <button class="btn btn-ghost btn-sm" @click="$emit('close')">Cancel</button>

      <!-- Save copy: only shown in edit mode -->
      <button
        v-if="isEdit"
        class="btn btn-outline btn-sm"
        @click="saveCopy"
        :disabled="!form.name || !form.name.trim()"
        title="Save current desktop layout as a new view with this name"
      >
        <i class="fa-solid fa-copy"></i>
        Save copy
      </button>

      <button
        class="btn btn-primary btn-sm"
        @click="confirm"
        :disabled="!form.name || !form.name.trim()"
      >
        {{ isEdit ? 'Rename' : 'Create' }}
      </button>
    </div>
  </div>
</template>

<script>
export default {
  emits: ['close', 'confirm'],
  props: {
    view: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      form: {
        name: ''
      }
    }
  },
  computed: {
    isEdit() {
      return !!this.view
    }
  },
  mounted() {
    this.form.name = this.view?.name || ''
    this.$nextTick(() => this.$refs.nameInput?.focus())
  },
  methods: {
    async confirm() {
      const name = this.form.name.trim()
      if (!name) return

      if (this.isEdit) {
        // Rename existing view
        await this.$storex.ui.renameView({ oldName: this.view.name, newName: name })
      } else {
        // Save new view and reset the desktop grid so user starts fresh
        await this.$storex.ui.saveView(name)
        await this.$storex.ui.resetDesktop()
      }

      this.$emit('confirm', { name })
      this.$emit('close')
    },

    // Save current desktop layout as a copy under the new name (no reset)
    async saveCopy() {
      const name = this.form.name.trim()
      if (!name) return
      await this.$storex.ui.saveView(name)
      this.$emit('confirm', { name })
      this.$emit('close')
    }
  }
}
</script>