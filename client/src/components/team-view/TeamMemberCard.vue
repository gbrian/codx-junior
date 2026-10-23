<script setup>
import { roleMeta, avatarUrl } from './config'
</script>

<template>
  <!-- Compact card (board columns) -->
  <div
    v-if="compact"
    class="group card bg-base-100 border border-base-content/10 rounded-lg p-2 cursor-pointer hover:border-base-content/30 transition-colors"
    :draggable="draggable"
    role="button"
    tabindex="0"
    :aria-label="`Edit ${member.name}`"
    @click="open"
    @keydown.enter.prevent="open"
    @keydown.space.prevent="open"
  >
    <div class="flex items-center gap-2">
      <div class="avatar shrink-0">
        <div class="w-8 rounded-full">
          <img :src="avatar" :alt="member.name" />
        </div>
      </div>
      <div class="min-w-0 flex-1">
        <div class="text-sm font-semibold truncate">{{ member.name }}</div>
      </div>
      <!-- Role: icon only, coloured (replaces the "Assistant"/"Chat" badge) -->
      <span class="shrink-0" :class="roleTextColor" :title="role.label" :aria-label="role.label">
        <i :class="role.icon" class="text-xs"></i>
      </span>
      <!-- Remove from this team ("-"). Deletion of the member lives only in the
           member settings drawer (with confirmation). -->
      <button
        v-if="canRemoveFromTeam"
        type="button"
        class="btn btn-ghost btn-xs btn-square text-error opacity-0 group-hover:opacity-100 focus:opacity-100 shrink-0"
        :title="`Remove ${member.name} from ${team.name}`"
        @click.stop="removeFromTeam"
      >
        <i class="fa-solid fa-minus text-xs"></i>
      </button>
    </div>
  </div>

  <!-- Grid card -->
  <article
    v-else
    class="group card bg-base-100 border border-base-content/10 rounded-xl overflow-hidden cursor-pointer hover:border-base-content/30 hover:bg-base-200/60 transition-colors"
    role="button"
    tabindex="0"
    :aria-label="`Edit ${member.name}`"
    @click="open"
    @keydown.enter.prevent="open"
    @keydown.space.prevent="open"
  >
    <!-- Top strip: colour of the member's ROLE (profile type), not the team —
         a member can belong to several teams. -->
    <div class="h-1 w-full" :class="roleBarClass" :title="role.label"></div>

    <div class="p-3 flex flex-col gap-3">
      <div class="flex items-start gap-3">
        <div class="avatar shrink-0">
          <div class="w-11 rounded-full ring ring-base-300 ring-offset-1 ring-offset-base-100">
            <img :src="avatar" :alt="member.name" />
          </div>
        </div>

        <div class="min-w-0 flex-1">
          <h3 class="font-semibold text-sm truncate">{{ member.name }}</h3>
        </div>

        <div class="flex gap-1 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
          <button
            type="button"
            class="btn btn-ghost btn-xs btn-square"
            :title="`Edit ${member.name}`"
            @click.stop="open"
          >
            <i class="fa-solid fa-pen text-xs"></i>
          </button>
          <!-- Remove from this team ("-"). No delete here: members are only
               deleted from the member settings, after confirmation. -->
          <button
            v-if="canRemoveFromTeam"
            type="button"
            class="btn btn-ghost btn-xs btn-square text-error"
            :title="`Remove ${member.name} from ${team.name}`"
            @click.stop="removeFromTeam"
          >
            <i class="fa-solid fa-minus text-xs"></i>
          </button>
        </div>
      </div>

      <p class="text-xs text-base-content/60 leading-snug line-clamp-2 min-h-[2.25rem]">
        {{ member.description || 'No description yet' }}
      </p>

      <!-- Footer: stats on the left, coloured role icon top-right -->
      <div class="flex items-start gap-3 text-[11px] text-base-content/50 border-t border-base-content/10 pt-2">
        <span class="inline-flex items-center gap-1" :class="member.guardrails?.enabled ? 'text-info' : ''" title="Guardrails">
          <i class="fa-solid fa-shield-halved"></i>{{ member.guardrails?.enabled ? 'On' : 'Off' }}
        </span>
        <span class="inline-flex items-center gap-1" :class="member.tools?.length ? 'text-success' : ''" title="Skills">
          <i class="fa-solid fa-wrench"></i>{{ member.tools?.length || 0 }}
        </span>
        <span v-if="member.llm_model" class="inline-flex items-center gap-1 truncate" :title="member.llm_model">
          <i class="fa-solid fa-brain"></i>{{ member.llm_model }}
        </span>
        <!-- Role: icon only, coloured, footer top-right -->
        <span class="ml-auto shrink-0" :class="roleTextColor" :title="role.label" :aria-label="role.label">
          <i :class="role.icon" class="text-xs"></i>
        </span>
      </div>
    </div>
  </article>
</template>

<script>
export default {
  name: 'TeamMemberCard',
  props: {
    member: { type: Object, required: true },
    team: { type: Object, default: null },
    // Compact = the draggable card used inside the board columns.
    compact: { type: Boolean, default: false },
    draggable: { type: Boolean, default: false }
  },
  emits: ['edit', 'remove-from-team'],
  computed: {
    role() {
      return roleMeta(this.member.category)
    },
    // Reuse the role badge colour as a text colour (e.g. badge-primary → text-primary).
    roleTextColor() {
      return (this.role.badge || 'badge-ghost').replace('badge-', 'text-')
    },
    // Top strip colour reflects the ROLE (profile type), not the team.
    roleBarClass() {
      const badge = this.role.badge || ''
      return badge ? badge.replace('badge-', 'bg-') : 'bg-base-300'
    },
    avatar() {
      return avatarUrl(this.member)
    },
    // Membership can only be removed from a real API team — never from the
    // derived "Unassigned" virtual group (id starting with "__").
    canRemoveFromTeam() {
      return !!this.team?.id && !String(this.team.id).startsWith('__')
    }
  },
  methods: {
    open() {
      this.$emit('edit', this.member)
    },
    removeFromTeam() {
      this.$emit('remove-from-team', { member: this.member, team: this.team })
    }
  }
}
</script>

<!-- Made with ❤️ by codx-junior -->