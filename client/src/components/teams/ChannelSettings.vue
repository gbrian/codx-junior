<script setup>
import ChatIcon from '@/components/chat/ChatIcon.vue'
</script>

<template>
  <div class="flex flex-col gap-4 p-2 w-96">
    <h3 class="font-bold text-lg flex items-center gap-2">
      <ChatIcon :mode="draft.mode" />
      Channel Settings
    </h3>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Channel Name *</label>
      <input
        v-model="draft.name"
        type="text"
        class="input input-bordered input-sm"
        placeholder="general"
        @keydown.enter="save"
      />
    </div>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Description</label>
      <input
        v-model="draft.description"
        type="text"
        class="input input-bordered input-sm"
        placeholder="Channel purpose..."
      />
    </div>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Channel Type</label>
      <div class="flex flex-col gap-2">
        <label
          v-for="opt in modeOptions"
          :key="opt.value"
          class="flex items-center gap-3 p-2 rounded-lg border cursor-pointer transition-all"
          :class="draft.mode === opt.value
            ? 'border-primary bg-primary/10'
            : 'border-base-content/20 hover:border-base-content/40'"
        >
          <input type="radio" class="radio radio-primary radio-sm" :value="opt.value" v-model="draft.mode" />
          <ChatIcon :mode="opt.value" class="w-4" />
          <div>
            <div class="text-sm font-semibold">{{ opt.label }}</div>
            <div class="text-xs text-base-content/50">{{ opt.desc }}</div>
          </div>
        </label>
      </div>
    </div>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Pinned</label>
      <input type="checkbox" class="toggle toggle-primary toggle-sm" v-model="draft.pinned" />
    </div>

    <!-- Danger zone -->
    <div class="divider text-xs text-error/60 my-0">Danger Zone</div>
    <button class="btn btn-sm btn-error btn-outline w-full" @click="$emit('delete')">
      <i class="fa-solid fa-trash"></i>
      Delete Channel
    </button>

    <div class="flex gap-2 justify-end">
      <button class="btn btn-sm" @click="$emit('close')">Cancel</button>
      <button class="btn btn-sm btn-primary" :disabled="!draft.name?.trim()" @click="save">
        Save
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ChannelSettings',
  emits: ['save', 'close', 'delete'],
  props: {
    channel: { type: Object, required: true }
  },
  data() {
    return {
      draft: {},
      modeOptions: [
        { value: 'topic', label: 'Text Channel', desc: 'Great for group discussions' },
        { value: 'chat', label: 'Chat', desc: 'Quick back-and-forth messages' },
        { value: 'task', label: 'Document', desc: 'Collaborative document editing' }
      ]
    }
  },
  created() {
    this.draft = { ...this.channel }
  },
  methods: {
    save() {
      if (!this.draft.name?.trim()) return
      this.$emit('save', { ...this.draft })
    }
  }
}
</script>