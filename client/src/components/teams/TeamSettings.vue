<script setup>
import ColorPicker from '../ui/ColorPicker.vue'
</script>

<template>
  <div class="flex flex-col gap-4 p-2 w-96">
    <h3 class="font-bold text-lg flex items-center gap-2">
      <i class="fa-solid fa-people-group text-primary"></i>
      Team Settings
    </h3>

    <!-- Avatar preview + color picker -->
    <div class="flex items-center gap-3">
      <div
        class="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-bold text-white shrink-0"
        :style="{ backgroundColor: draft.color }"
      >
        <img v-if="draft.icon" :src="draft.icon" class="w-full h-full object-cover rounded-2xl" />
        <span v-else>{{ draft.name?.[0]?.toUpperCase() || '?' }}</span>
      </div>
      <div class="flex flex-col gap-1 flex-1">
        <span class="text-xs text-base-content/50">Team Icon Color</span>
        <ColorPicker v-model="draft.color" />
      </div>
    </div>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Team Name *</label>
      <input
        v-model="draft.name"
        type="text"
        class="input input-bordered input-sm"
        placeholder="My Awesome Team"
        @keydown.enter="save"
      />
    </div>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Description</label>
      <textarea
        v-model="draft.description"
        class="textarea textarea-bordered textarea-sm resize-none"
        placeholder="What's this team about?"
        rows="2"
      />
    </div>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Icon URL</label>
      <input
        v-model="draft.icon"
        type="text"
        class="input input-bordered input-sm"
        placeholder="https://..."
      />
    </div>

    <!-- Danger zone -->
    <div class="divider text-xs text-error/60 my-0">Danger Zone</div>
    <button
      class="btn btn-sm btn-error btn-outline w-full"
      @click="$emit('delete', team.id)"
    >
      <i class="fa-solid fa-trash"></i>
      Delete Team
    </button>

    <div class="flex gap-2 justify-end">
      <button class="btn btn-sm" @click="$emit('close')">Cancel</button>
      <button
        class="btn btn-sm btn-primary"
        :disabled="!draft.name?.trim()"
        @click="save"
      >
        Save
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TeamSettings',
  emits: ['save', 'close', 'delete'],
  props: {
    team: { type: Object, required: true }
  },
  data() {
    return {
      draft: {}
    }
  },
  created() {
    this.draft = { ...this.team }
  },
  methods: {
    save() {
      if (!this.draft.name?.trim()) return
      this.$emit('save', { ...this.draft })
    }
  }
}
</script>