<script setup>
import ChatIcon from '@/components/chat/ChatIcon.vue'
</script>

<template>
  <div class="flex flex-col gap-4 p-2 w-96">
    <h3 class="font-bold text-lg flex items-center gap-2">
      <i class="fa-solid fa-plus text-primary"></i>
      Create Channel
    </h3>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Channel Name *</label>
      <input
        v-model="form.name"
        type="text"
        class="input input-bordered input-sm"
        placeholder="general"
        @keydown.enter="submit"
        ref="nameInput"
      />
    </div>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Description</label>
      <input
        v-model="form.description"
        type="text"
        class="input input-bordered input-sm"
        placeholder="What's this channel about?"
      />
    </div>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Type</label>
      <div class="grid grid-cols-3 gap-2">
        <label
          v-for="opt in modeOptions"
          :key="opt.value"
          class="flex flex-col items-center gap-1 p-2 rounded-lg border cursor-pointer transition-all text-center"
          :class="form.mode === opt.value
            ? 'border-primary bg-primary/10 text-primary'
            : 'border-base-content/20 hover:border-base-content/40'"
        >
          <input type="radio" class="hidden" :value="opt.value" v-model="form.mode" />
          <ChatIcon :mode="opt.value" class="text-lg" />
          <span class="text-xs font-semibold">{{ opt.label }}</span>
        </label>
      </div>
    </div>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Category</label>
      <select class="select select-bordered select-sm" v-model="form.categoryId">
        <option v-for="cat in categories" :key="cat.id" :value="cat.id">
          {{ cat.name }}
        </option>
      </select>
    </div>

    <div class="flex gap-2 justify-end">
      <button class="btn btn-sm" @click="$emit('close')">Cancel</button>
      <button
        class="btn btn-sm btn-primary"
        :disabled="!form.name?.trim() || loading"
        :class="loading ? 'loading' : ''"
        @click="submit"
      >
        Create
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CreateChannelDialog',
  emits: ['created', 'close'],
  props: {
    team: { type: Object, required: true },
    defaultCategoryId: { type: String, default: null }
  },
  data() {
    return {
      loading: false,
      form: {
        name: '',
        description: '',
        mode: 'topic',
        categoryId: null
      },
      modeOptions: [
        { value: 'topic', label: 'Text' },
        { value: 'chat', label: 'Chat' },
        { value: 'task', label: 'Document' }
      ]
    }
  },
  created() {
    this.form.categoryId = this.defaultCategoryId || this.categories[0]?.id || null
  },
  mounted() {
    this.$nextTick(() => this.$refs.nameInput?.focus())
  },
  computed: {
    categories() {
      return this.team?.categories || []
    }
  },
  methods: {
    async submit() {
      if (!this.form.name?.trim()) return
      this.loading = true
      try {
        const channel = await this.$storex.teams.createChannel({
          teamId: this.team.id,
          categoryId: this.form.categoryId,
          channelData: {
            name: this.form.name.trim().toLowerCase().replace(/\s+/g, '-'),
            description: this.form.description.trim(),
            mode: this.form.mode
          }
        })
        this.$emit('created', channel)
      } finally {
        this.loading = false
      }
    }
  }
}
</script>