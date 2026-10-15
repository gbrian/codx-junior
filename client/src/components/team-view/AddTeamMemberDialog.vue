<script setup>
import { ROLE_META } from './config'
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="$emit('close')"></div>

    <div
      class="relative card bg-base-100 border border-base-content/10 shadow-2xl w-full max-w-md max-h-[92vh] overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-label="Add team member"
    >
      <div class="card-body gap-4">
        <div class="flex items-center justify-between">
          <h2 class="card-title text-lg">Add a team member</h2>
          <button type="button" class="btn btn-ghost btn-sm btn-square" aria-label="Close" @click="$emit('close')">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="flex flex-col gap-3">
          <div>
            <label class="label-text text-xs font-semibold pb-1 block">Full name *</label>
            <input
              ref="nameInput"
              v-model="form.name"
              type="text"
              class="input input-sm input-bordered w-full"
              placeholder="e.g. Jamie Lee"
              @keydown.enter="submit"
            />
          </div>

          <div>
            <label class="label-text text-xs font-semibold pb-1 block">Role</label>
            <select v-model="form.category" class="select select-sm select-bordered w-full">
              <option v-for="(meta, key) in roleMetaMap" :key="key" :value="key">{{ meta.label }}</option>
            </select>
          </div>

          <!-- Teams (multiple) -->
          <div>
            <div class="flex items-center justify-between">
              <span class="label-text text-xs font-semibold">Teams</span>
              <span class="badge badge-sm">{{ form.teamIds.length }} selected</span>
            </div>
            <p class="text-[11px] text-base-content/40 mb-2">A member can belong to multiple teams.</p>
            <div v-if="teams.length" class="flex flex-wrap gap-1">
              <button
                v-for="t in teams"
                :key="t.id"
                type="button"
                class="badge badge-sm cursor-pointer transition-colors"
                :class="isTeamSelected(t.id) ? 'badge-primary' : 'badge-ghost'"
                :aria-pressed="isTeamSelected(t.id)"
                @click="toggleTeam(t.id)"
              >
                <i class="fa-solid mr-1" :class="isTeamSelected(t.id) ? 'fa-check' : 'fa-plus'"></i>
                {{ t.name }}
              </button>
            </div>
            <p v-else class="text-xs text-base-content/50">No teams yet — create one first.</p>
          </div>

          <div>
            <label class="label-text text-xs font-semibold pb-1 block">Start from a template</label>
            <select v-model="form.template" class="select select-sm select-bordered w-full" @change="onTemplateChanged">
              <option v-for="(tpl, key) in templates" :key="key" :value="key">{{ tpl.label }}</option>
            </select>
          </div>
        </div>

        <div class="card-actions justify-end">
          <button type="button" class="btn btn-sm btn-ghost" @click="$emit('close')">Cancel</button>
          <button type="button" class="btn btn-sm btn-primary" :disabled="saving || !form.name.trim()" @click="submit">
            <span v-if="saving" class="loading loading-spinner loading-xs"></span>
            <i v-else class="fa-solid fa-plus"></i>
            Add member
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
// Personas reused for quick-start templates (kept in sync with the drawer).
const PERSONA = {
  support: [
    'You are a friendly support agent. You answer customer questions clearly and empathetically.',
    '',
    '- Never invent policies — ask to check the knowledge base.',
    '- Escalate to a human when the request is sensitive.'
  ].join('\n'),
  engineer: [
    'You are a senior software engineer on the platform team. You write clean, tested code and explain trade-offs.',
    '',
    '- Prefer small, reviewable changes.',
    '- Always mention the tests that were run.'
  ].join('\n'),
  agent: [
    'You are an autonomous agent. You plan a short set of steps, execute them with your skills and report the results.',
    '',
    '- Stop and ask when a step is ambiguous.',
    '- Never take destructive actions without confirmation.'
  ].join('\n')
}

const TEMPLATES = {
  blank: { label: 'Blank', category: 'assistant', description: '', content: '' },
  support: { label: 'Support Agent', category: 'chat', description: 'Friendly first-line support responder.', content: PERSONA.support },
  engineer: { label: 'Engineer', category: 'assistant', description: 'General-purpose coding assistant.', content: PERSONA.engineer },
  agent: { label: 'Autonomous Agent', category: 'agent', description: 'Autonomous agent that works on multi-step tasks.', content: PERSONA.agent }
}

export default {
  name: 'AddTeamMemberDialog',
  props: {
    teams: { type: Array, default: () => [] },
    /** Team ids to preselect (many-to-many membership). */
    defaultTeamIds: { type: Array, default: () => [] },
    saving: { type: Boolean, default: false }
  },
  emits: ['create', 'close'],
  data() {
    return {
      roleMetaMap: ROLE_META,
      templates: TEMPLATES,
      form: {
        name: '',
        category: 'assistant',
        teamIds: [...(this.defaultTeamIds || [])],
        template: 'blank',
        description: '',
        content: ''
      }
    }
  },
  mounted() {
    window.addEventListener('keydown', this.onKeydown)
    this.$nextTick(() => this.$refs.nameInput?.focus())
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onKeydown)
  },
  methods: {
    onKeydown(event) {
      if (event.key === 'Escape') this.$emit('close')
    },
    isTeamSelected(teamId) {
      return this.form.teamIds.includes(teamId)
    },
    toggleTeam(teamId) {
      this.form.teamIds = this.isTeamSelected(teamId)
        ? this.form.teamIds.filter(id => id !== teamId)
        : [...this.form.teamIds, teamId]
    },
    onTemplateChanged() {
      const tpl = this.templates[this.form.template]
      if (!tpl) return
      this.form.category = tpl.category
      this.form.description = tpl.description
      this.form.content = tpl.content
    },
    submit() {
      const name = (this.form.name || '').trim()
      if (!name || this.saving) return
      this.$emit('create', {
        name,
        category: this.form.category,
        teamIds: [...this.form.teamIds],
        description: this.form.description,
        content: this.form.content
      })
    }
  }
}
</script>

<!-- Made with ❤️ by codx-junior -->