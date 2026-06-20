<script setup>
</script>

<template>
  <div class="flex flex-col gap-4 p-2 w-96">
    <h3 class="font-bold text-lg flex items-center gap-2">
      <i class="fa-solid fa-people-group text-primary"></i>
      Create Team
    </h3>

    <!-- Color + preview -->
    <div class="flex items-center gap-4">
      <div
        class="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-bold text-white shrink-0 cursor-pointer"
        :style="{ backgroundColor: form.color }"
      >
        {{ form.name?.[0]?.toUpperCase() || '?' }}
      </div>
      <div class="flex flex-col gap-1">
        <span class="text-xs text-base-content/50">Pick color</span>
        <div class="flex flex-wrap gap-1">
          <button
            v-for="color in palette"
            :key="color"
            class="w-5 h-5 rounded-md border-2 transition-all"
            :style="{ backgroundColor: color }"
            :class="form.color === color ? 'border-white scale-110' : 'border-transparent'"
            @click="form.color = color"
          />
        </div>
      </div>
    </div>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Team Name *</label>
      <input
        v-model="form.name"
        type="text"
        class="input input-bordered input-sm"
        placeholder="My Team"
        @keydown.enter="submit"
        ref="nameInput"
      />
    </div>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Description</label>
      <textarea
        v-model="form.description"
        class="textarea textarea-bordered textarea-sm resize-none"
        placeholder="What's this team about?"
        rows="2"
      />
    </div>

    <div class="flex gap-2 justify-end">
      <button class="btn btn-sm" @click="$emit('close')">Cancel</button>
      <button
        class="btn btn-sm btn-primary"
        :disabled="!form.name?.trim()"
        @click="submit"
      >
        Create
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CreateTeamDialog',
  emits: ['created', 'close'],
  data() {
    return {
      form: {
        name: '',
        description: '',
        color: '#6366f1'
      },
      palette: [
        '#6366f1', '#8b5cf6', '#ec4899', '#ef4444',
        '#f97316', '#eab308', '#22c55e', '#14b8a6',
        '#3b82f6', '#06b6d4', '#64748b', '#1e293b'
      ]
    }
  },
  mounted() {
    this.$nextTick(() => this.$refs.nameInput?.focus())
  },
  methods: {
    submit() {
      if (!this.form.name?.trim()) return
      const team = this.$storex.teams.createTeam({
        name: this.form.name.trim(),
        description: this.form.description.trim(),
        color: this.form.color
      })
      this.$emit('created', team)
    }
  }
}
</script>