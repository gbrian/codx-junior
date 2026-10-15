<script setup>
import IconSelector from '@/components/ui/IconSelector.vue'
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="$emit('close')"></div>

    <div
      class="relative card bg-base-100 border border-base-content/10 shadow-2xl w-full max-w-md max-h-[92vh] overflow-y-auto"
      role="dialog"
      aria-modal="true"
      :aria-label="title"
    >
      <div class="card-body gap-4">
        <div class="flex items-center justify-between">
          <h2 class="card-title text-lg flex items-center gap-2">
            <i class="fa-solid fa-people-group text-primary"></i>
            {{ title }}
          </h2>
          <button type="button" class="btn btn-ghost btn-sm btn-square" aria-label="Close" @click="$emit('close')">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <!-- Team card preview: logo image with a colour ring, or a rounded
             square filled with the colour (showing the chosen icon). -->
        <div class="flex items-center gap-4">
          <div
            class="w-14 h-14 rounded-xl flex items-center justify-center shrink-0 overflow-hidden"
            :style="{
              backgroundColor: form.logo ? 'transparent' : form.color,
              boxShadow: `0 0 0 3px ${form.color}`
            }"
            :aria-label="`Team colour ${form.color}`"
          >
            <img
              v-if="form.logo"
              :src="form.logo"
              class="w-full h-full object-cover rounded-xl"
              :alt="`${form.name || 'Team'} logo`"
            />
            <i v-else :class="form.icon || 'fa-solid fa-people-group'" class="text-white text-lg"></i>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-xs text-base-content/50">Pick a colour</span>
            <div class="flex flex-wrap gap-1">
              <button
                v-for="color in palette"
                :key="color"
                type="button"
                class="w-5 h-5 rounded-md border-2 transition-all"
                :style="{ backgroundColor: color }"
                :class="form.color === color ? 'border-base-content scale-110' : 'border-transparent'"
                :aria-label="`Colour ${color}`"
                @click="form.color = color"
              />
            </div>
          </div>
        </div>

        <div>
          <label class="label-text text-xs font-semibold pb-1 block">Team name *</label>
          <input
            ref="nameInput"
            v-model="form.name"
            type="text"
            class="input input-sm input-bordered w-full"
            placeholder="e.g. Engineering"
            @keydown.enter="submit"
          />
        </div>

        <div>
          <label class="label-text text-xs font-semibold pb-1 block">
            <i class="fa-regular fa-image mr-1"></i> Logo image URL
          </label>
          <div class="flex items-center gap-2">
            <input
              v-model="form.logo"
              type="text"
              class="input input-sm input-bordered w-full min-w-0 flex-1"
              placeholder="https://example.com/logo.png"
            />
            <!-- Icon selector: a single button placed right after the image URL
                 input. The picked Font Awesome class is copied into the icon
                 input below (both bind to `form.icon`). -->
            <IconSelector v-model="form.icon" button-only label="Team icon" placeholder="Search icons…" />
          </div>
          <p class="text-[11px] text-base-content/40 mt-1">Shown instead of the colour. Leave empty to use the colour and icon.</p>
        </div>

        <div>
          <label class="label-text text-xs font-semibold pb-1 block">
            <i class="fa-solid fa-icons mr-1"></i> Team icon
          </label>
          <input
            v-model="form.icon"
            type="text"
            class="input input-sm input-bordered w-full font-mono"
            placeholder="fa-solid fa-people-group"
          />
          <p class="text-[11px] text-base-content/40 mt-1">Pick an icon with the button above — its Font Awesome class is copied here. Shown inside the colour square when no logo image is set.</p>
        </div>

        <div>
          <label class="label-text text-xs font-semibold pb-1 block">Description</label>
          <textarea
            v-model="form.description"
            rows="2"
            class="textarea textarea-bordered textarea-sm w-full resize-none"
            placeholder="What is this team responsible for?"
          ></textarea>
        </div>

        <!-- Members (edit only): remove a member from this team -->
        <div v-if="isEditing" class="border-t border-base-content/10 pt-3 flex flex-col gap-2">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold uppercase tracking-wide text-base-content/60">Members</span>
            <span class="badge badge-sm">{{ members.length }}</span>
          </div>
          <div v-if="members.length" class="flex flex-wrap gap-1 max-h-36 overflow-y-auto">
            <span
              v-for="m in members"
              :key="m.name"
              class="badge badge-outline badge-sm gap-1"
            >
              {{ m.name }}
              <button
                type="button"
                class="hover:text-error"
                :title="`Remove ${m.name} from this team`"
                :disabled="saving"
                @click="$emit('remove-member', m.name)"
              >
                <i class="fa-solid fa-xmark text-[10px]"></i>
              </button>
            </span>
          </div>
          <p v-else class="text-xs text-base-content/40 italic">No members in this team yet.</p>
        </div>

        <!-- Delete team (edit only) -->
        <div v-if="isEditing" class="border-t border-base-content/10 pt-3 flex flex-col gap-2">
          <div class="text-sm font-semibold text-error">Delete team</div>
          <p class="text-[11px] text-base-content/50">Permanently delete this team. Members stay in the project and keep their other teams.</p>
          <button
            type="button"
            class="btn btn-sm btn-error w-fit"
            :disabled="saving"
            @click="$emit('delete', team)"
          >
            <i class="fa-solid fa-trash"></i> Delete team
          </button>
        </div>

        <div class="card-actions justify-end">
          <button type="button" class="btn btn-sm btn-ghost" @click="$emit('close')">Cancel</button>
          <button
            type="button"
            class="btn btn-sm btn-primary"
            :disabled="saving || !form.name.trim()"
            @click="submit"
          >
            <span v-if="saving" class="loading loading-spinner loading-xs"></span>
            <i v-else :class="isEditing ? 'fa-solid fa-floppy-disk' : 'fa-solid fa-plus'"></i>
            {{ isEditing ? 'Save changes' : 'Create team' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
// Dual-purpose dialog: creates a new team, or edits/deletes an existing one
// when `team` is provided. Membership is handled through the teams API
// (`/api/teams/{id}/members`) and is NOT part of the saved team payload.
export default {
  name: 'CreateTeamDialog',
  props: {
    /** Team to edit. When null/absent the dialog creates a new team. */
    team: { type: Object, default: null },
    /** Member objects belonging to `team` (edit mode only). */
    members: { type: Array, default: () => [] },
    saving: { type: Boolean, default: false }
  },
  emits: ['submit', 'delete', 'remove-member', 'close'],
  data() {
    return {
      form: {
        name: this.team?.name || '',
        description: this.team?.description || '',
        color: this.team?.color || '#6366f1',
        icon: this.team?.icon || 'fa-solid fa-people-group',
        logo: this.team?.logo || ''
      },
      palette: [
        '#6366f1', '#8b5cf6', '#ec4899', '#ef4444',
        '#f97316', '#eab308', '#22c55e', '#14b8a6',
        '#3b82f6', '#06b6d4', '#64748b', '#1e293b'
      ]
    }
  },
  computed: {
    isEditing() {
      return !!this.team?.id
    },
    title() {
      return this.isEditing ? 'Edit team' : 'Create team'
    }
  },
  watch: {
    team: {
      immediate: true,
      deep: true,
      handler(team) {
        this.form = {
          name: team?.name || '',
          description: team?.description || '',
          color: team?.color || '#6366f1',
          icon: team?.icon || 'fa-solid fa-people-group',
          logo: team?.logo || ''
        }
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
    submit() {
      const name = (this.form.name || '').trim()
      if (!name || this.saving) return
      this.$emit('submit', {
        id: this.team?.id || null,
        name,
        description: (this.form.description || '').trim(),
        color: this.form.color,
        icon: this.form.icon,
        logo: (this.form.logo || '').trim()
      })
    }
  }
}
</script>

<!-- Made with ❤️ by codx-junior -->