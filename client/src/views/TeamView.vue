<script setup>
import TeamMemberCard from '@/components/team-view/TeamMemberCard.vue'
import TeamMemberDrawer from '@/components/team-view/TeamMemberDrawer.vue'
import AddTeamMemberDialog from '@/components/team-view/AddTeamMemberDialog.vue'
import AddMembersToTeamDialog from '@/components/team-view/AddMembersToTeamDialog.vue'
import CreateTeamDialog from '@/components/team-view/CreateTeamDialog.vue'
import {
  ROLE_META,
  roleMeta,
  avatarUrl,
  EMPTY_GUARDRAILS,
  toLocalTeam,
  toApiTeam
} from '@/components/team-view/config'
</script>

<template>
  <div class="h-full w-full flex flex-col bg-base-100 overflow-hidden">
    <!-- Header -->
    <header class="shrink-0 border-b border-base-content/10 bg-base-100/60 backdrop-blur px-4 md:px-6 py-3">
      <div class="flex items-center gap-2 flex-wrap">
        <div class="flex items-center gap-2.5 mr-auto min-w-0">
          <div class="w-9 h-9 rounded-xl grid place-items-center bg-primary/15 text-primary shrink-0">
            <i class="fa-solid fa-people-group"></i>
          </div>
          <div class="min-w-0">
            <h1 class="text-base md:text-lg font-bold leading-tight truncate">Your Team</h1>
            <p class="text-[11px] md:text-xs text-base-content/50 hidden sm:block">
              Describe who your AI teammates are, what they do and how they behave
            </p>
          </div>
        </div>

        <div class="join shrink-0">
          <button
            type="button"
            class="join-item btn btn-sm gap-1"
            :class="view === 'grid' ? 'btn-active' : ''"
            title="Group by team"
            @click="view = 'grid'"
          >
            <i class="fa-solid fa-table-cells-large"></i>
            <span class="hidden md:inline">By team</span>
          </button>
          <button
            type="button"
            class="join-item btn btn-sm gap-1"
            :class="view === 'board' ? 'btn-active' : ''"
            title="Board view"
            @click="view = 'board'"
          >
            <i class="fa-solid fa-table-columns"></i>
            <span class="hidden md:inline">Board</span>
          </button>
        </div>

        <!-- Reload teams + members from the API -->
        <button
          type="button"
          class="btn btn-sm btn-ghost shrink-0 gap-1"
          title="Reload teams"
          :disabled="loading || saving"
          @click="reload"
        >
          <i class="fa-solid fa-rotate" :class="loading ? 'animate-spin' : ''"></i>
        </button>

        <!-- Create team: distinct "add" icon + always-visible label (short on mobile) -->
        <button
          type="button"
          class="btn btn-sm shrink-0 gap-1"
          title="Create team"
          :disabled="saving"
          @click="openCreateTeam"
        >
          <i class="fa-solid fa-circle-plus"></i>
          <span class="hidden md:inline">Create team</span>
          <span class="md:hidden">Team</span>
        </button>

        <!-- Add member: person-add icon + always-visible label (short on mobile) -->
        <button
          type="button"
          class="btn btn-sm btn-primary shrink-0 gap-1"
          title="Add member"
          @click="openAdd"
        >
          <i class="fa-solid fa-user-plus"></i>
          <span class="hidden md:inline">Add member</span>
          <span class="md:hidden">Member</span>
        </button>
      </div>
    </header>

    <!-- Stats (single compact row; labels hidden on mobile) -->
    <section class="shrink-0 px-4 md:px-6 pt-3">
      <div class="flex items-center gap-2 overflow-x-auto">
        <div class="flex items-center gap-1.5 rounded-lg bg-base-200 border border-base-content/10 px-2 py-1 shrink-0" title="Members">
          <i class="fa-solid fa-users text-primary text-[11px]"></i>
          <span class="text-sm font-bold leading-none">{{ stats.members }}</span>
          <span class="hidden md:inline text-[11px] text-base-content/50">Members</span>
        </div>
        <div class="flex items-center gap-1.5 rounded-lg bg-base-200 border border-base-content/10 px-2 py-1 shrink-0" title="Teams">
          <i class="fa-solid fa-table-cells-large text-info text-[11px]"></i>
          <span class="text-sm font-bold leading-none">{{ stats.teams }}</span>
          <span class="hidden md:inline text-[11px] text-base-content/50">Teams</span>
        </div>
        <div class="flex items-center gap-1.5 rounded-lg bg-base-200 border border-base-content/10 px-2 py-1 shrink-0" title="Skills in use">
          <i class="fa-solid fa-wrench text-success text-[11px]"></i>
          <span class="text-sm font-bold leading-none">{{ stats.skills }}</span>
          <span class="hidden md:inline text-[11px] text-base-content/50">Skills</span>
        </div>
        <div class="flex items-center gap-1.5 rounded-lg bg-base-200 border border-base-content/10 px-2 py-1 shrink-0" title="Guardrailed members">
          <i class="fa-solid fa-shield-halved text-warning text-[11px]"></i>
          <span class="text-sm font-bold leading-none">{{ stats.guardrails }}</span>
          <span class="hidden md:inline text-[11px] text-base-content/50">Guardrailed</span>
        </div>
      </div>
    </section>

    <!-- Toolbar: search, filters modal and team chips -->
    <div class="shrink-0 px-4 md:px-6 pt-3 pb-3 flex flex-col gap-2">
      <div class="flex items-center gap-2">
        <div class="relative flex-1 min-w-0">
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-base-content/40">
            <i class="fa-solid fa-magnifying-glass text-xs"></i>
          </span>
          <input
            v-model="search"
            type="search"
            class="input input-sm input-bordered w-full pl-9"
            placeholder="Search members…"
            aria-label="Search team members"
          />
        </div>

        <button type="button" class="btn btn-sm shrink-0 gap-1" title="Filters" @click="filtersOpen = true">
          <i class="fa-solid fa-sliders"></i>
          <span class="hidden sm:inline">Filters</span>
          <span v-if="activeFilterCount" class="badge badge-xs badge-primary">{{ activeFilterCount }}</span>
        </button>
      </div>

      <!-- Team chips: activate/deactivate each team (and "All") in the view -->
      <div
        v-if="teams.length"
        class="flex items-center gap-1.5 overflow-x-auto pb-0.5"
        role="group"
        aria-label="Filter by team"
      >
        <span class="text-[11px] text-base-content/40 shrink-0" title="Teams">
          <i class="fa-solid fa-table-cells-large"></i>
        </span>
        <button
          type="button"
          class="badge badge-sm gap-1 cursor-pointer transition-colors shrink-0"
          :class="allTeamsActive ? 'badge-primary' : 'badge-ghost opacity-70'"
          :aria-pressed="allTeamsActive"
          title="Show all teams"
          @click="selectAllTeams"
        >
          <i class="fa-solid fa-layer-group text-[10px]"></i> All
        </button>
        <button
          v-for="t in teams"
          :key="t.id"
          type="button"
          class="badge badge-sm gap-1 cursor-pointer transition-colors shrink-0"
          :class="isTeamActive(t.id) ? 'badge-primary' : 'badge-ghost opacity-70'"
          :aria-pressed="isTeamActive(t.id)"
          :title="isTeamActive(t.id) ? `Hide ${t.name}` : `Show ${t.name}`"
          @click="toggleTeamChip(t.id)"
        >
          <span class="w-2 h-2 rounded-full shrink-0" :style="{ backgroundColor: t.color }"></span>
          {{ t.name }}
        </button>
      </div>
    </div>

    <!-- Roster: scrolls for grid/list; the board fills the height and each
         column scrolls on its own. -->
    <div
      class="flex-1 min-h-0 px-4 md:px-6"
      :class="isBoardView ? 'overflow-hidden pb-2' : 'overflow-auto pb-8'"
    >
      <!-- Loading -->
      <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-4 mt-1">
        <div v-for="n in 6" :key="n" class="card bg-base-200 border border-base-content/10 p-4 gap-3">
          <div class="flex gap-3">
            <div class="skeleton w-11 h-11 rounded-full"></div>
            <div class="flex-1 flex flex-col gap-2">
              <div class="skeleton h-3 w-3/5"></div>
              <div class="skeleton h-2 w-2/5"></div>
            </div>
          </div>
          <div class="skeleton h-2 w-full"></div>
          <div class="skeleton h-2 w-4/5"></div>
        </div>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 py-20 text-center" role="alert">
        <div class="w-14 h-14 rounded-2xl grid place-items-center bg-error/15 text-error">
          <i class="fa-solid fa-triangle-exclamation text-2xl"></i>
        </div>
        <h2 class="font-semibold">We couldn't load your team</h2>
        <p class="text-sm text-base-content/50">{{ error }}</p>
        <button type="button" class="btn btn-sm btn-primary mt-1" @click="load">
          <i class="fa-solid fa-rotate"></i> Retry
        </button>
      </div>

      <!-- Empty -->
      <div v-else-if="!members.length" class="flex flex-col items-center justify-center gap-3 py-20 text-center">
        <div class="w-14 h-14 rounded-2xl grid place-items-center bg-primary/15 text-primary">
          <i class="fa-solid fa-people-group text-2xl"></i>
        </div>
        <h2 class="font-semibold">No team members yet</h2>
        <p class="text-sm text-base-content/50 max-w-sm">
          Add your first teammate to describe their role and how they should behave.
        </p>
        <button type="button" class="btn btn-sm btn-primary mt-1" @click="openAdd">
          <i class="fa-solid fa-user-plus"></i> Add member
        </button>
      </div>

      <!-- No results (grid only — the board always renders so its virtual
           "All" column stays available regardless of the team filter). -->
      <div v-else-if="!hasResults && view !== 'board'" class="flex flex-col items-center justify-center gap-3 py-20 text-center">
        <div class="w-14 h-14 rounded-2xl grid place-items-center bg-base-200 text-base-content/40">
          <i class="fa-solid fa-magnifying-glass text-2xl"></i>
        </div>
        <h2 class="font-semibold">No members match your filters</h2>
        <p class="text-sm text-base-content/50">Try adjusting the search, the team chips or the filters.</p>
        <button type="button" class="btn btn-sm btn-outline mt-1" @click="clearFilters">Clear filters</button>
      </div>

      <!-- Grid by team: each team is a self-contained panel (colour accent bar +
           header divider) with generous spacing so its boundary is obvious. -->
      <template v-else-if="view === 'grid'">
        <div class="flex flex-col gap-6 md:gap-8">
          <section
            v-for="group in groupedMembers"
            :key="group.team.id"
            class="rounded-2xl border-y border-r border-l-4 border-base-content/10 bg-base-200/40 p-4 md:p-5"
            :style="{ borderLeftColor: group.team.color }"
          >
            <div class="flex items-center gap-2 mb-4 pb-3 border-b border-base-content/10">
              <!-- Team card: logo image with colour ring, or colour square + icon -->
              <span
                class="w-7 h-7 rounded-lg flex items-center justify-center overflow-hidden shrink-0"
                :style="{
                  backgroundColor: group.team.logo ? 'transparent' : group.team.color,
                  boxShadow: `0 0 0 2px ${group.team.color}`
                }"
                :title="group.team.name"
              >
                <img
                  v-if="group.team.logo"
                  :src="group.team.logo"
                  class="w-full h-full object-cover rounded-lg"
                  :alt="group.team.name"
                />
                <i v-else :class="group.team.icon || 'fa-solid fa-people-group'" class="text-white text-xs"></i>
              </span>
              <h2 class="font-semibold text-sm">{{ group.team.name }}</h2>
              <span class="badge badge-sm">{{ group.members.length }}</span>
              <template v-if="isRealTeam(group.team)">
                <!-- "+" add members to this team -->
                <button
                  type="button"
                  class="btn btn-ghost btn-xs btn-square"
                  :title="`Add members to ${group.team.name}`"
                  :disabled="saving"
                  @click="openAddMembersToTeam(group.team)"
                >
                  <i class="fa-solid fa-plus text-xs"></i>
                </button>
                <!-- Team settings -->
                <button
                  type="button"
                  class="btn btn-ghost btn-xs btn-square"
                  :title="`Edit ${group.team.name}`"
                  @click="openTeamEditor(group.team)"
                >
                  <i class="fa-solid fa-gear text-xs"></i>
                </button>
              </template>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-4">
              <TeamMemberCard
                v-for="member in group.members"
                :key="`${group.team.id}-${member.name}`"
                :member="member"
                :team="group.team"
                @edit="openEditor"
                @remove-from-team="removeMemberFromTeam"
              />
            </div>
          </section>
        </div>
      </template>

      <!-- Board: virtual "All" column + one column per active team. Fills the
           height; each column scrolls vertically when it has more members. -->
      <div v-else class="h-full flex gap-4 items-stretch overflow-x-auto overflow-y-hidden pb-1">
        <div v-if="!boardColumns.length && !members.length" class="w-full flex flex-col items-center justify-center gap-2 py-16 text-center">
          <div class="w-14 h-14 rounded-2xl grid place-items-center bg-base-200 text-base-content/40">
            <i class="fa-solid fa-table-columns text-2xl"></i>
          </div>
          <h2 class="font-semibold">No teams yet</h2>
          <p class="text-sm text-base-content/50">Create a team to organise your members.</p>
          <button type="button" class="btn btn-sm btn-primary mt-1" @click="openCreateTeam">
            <i class="fa-solid fa-circle-plus"></i> Create team
          </button>
        </div>

        <template v-else>
          <div
            v-for="team in boardColumns"
            :key="team.id"
            class="w-72 shrink-0 h-full rounded-xl border bg-base-200/50 flex flex-col overflow-hidden transition-colors"
            :class="[
              isAllTeam(team) ? 'border-info/40' : 'border-base-content/10',
              dragOverTeamId === team.id
                ? (dragFromAll
                    ? 'border-info ring-2 ring-info/50'
                    : (dragCopy ? 'border-success ring-2 ring-success/50' : 'border-primary ring-2 ring-primary/50'))
                : ''
            ]"
            @dragover="onDragOver(team, $event)"
            @dragleave="onDragLeave(team)"
            @drop.prevent="onDrop(team, $event)"
          >
            <div class="shrink-0 flex items-center gap-2 px-3 py-2.5 border-b border-base-content/10">
              <!-- Team card: logo image with colour ring, or colour square + icon -->
              <span
                class="w-6 h-6 rounded-md flex items-center justify-center overflow-hidden shrink-0"
                :style="{
                  backgroundColor: team.logo ? 'transparent' : team.color,
                  boxShadow: `0 0 0 2px ${team.color}`
                }"
                :title="team.name"
              >
                <img
                  v-if="team.logo"
                  :src="team.logo"
                  class="w-full h-full object-cover rounded-md"
                  :alt="team.name"
                />
                <i v-else :class="team.icon || 'fa-solid fa-people-group'" class="text-white text-[10px]"></i>
              </span>
              <span class="text-sm font-semibold truncate">{{ team.name }}</span>

              <!-- Virtual "All" column: filter to unassigned members only -->
              <label
                v-if="isAllTeam(team)"
                class="shrink-0 flex items-center gap-1 cursor-pointer select-none"
                :title="allUnassignedOnly ? 'Showing unassigned members only' : 'Show unassigned members only'"
              >
                <input
                  type="checkbox"
                  class="checkbox checkbox-xs checkbox-info"
                  v-model="allUnassignedOnly"
                  aria-label="Show unassigned members only"
                />
                <span class="text-[10px] text-base-content/50">Unassigned</span>
              </label>

              <!-- Drop mode indicator (assign from "All" / copy / move) -->
              <span
                v-if="dragging && dragOverTeamId === team.id"
                class="badge badge-sm gap-1 shrink-0"
                :class="dragFromAll ? 'badge-info' : (dragCopy ? 'badge-success' : 'badge-primary')"
              >
                <i class="fa-solid" :class="dragFromAll ? 'fa-user-plus' : (dragCopy ? 'fa-copy' : 'fa-arrow-right')"></i>
                {{ dragFromAll ? 'Assign' : (dragCopy ? 'Copy' : 'Move') }}
              </span>

              <!-- Real teams only: add members + settings -->
              <template v-if="isRealTeam(team)">
                <button
                  type="button"
                  class="btn btn-ghost btn-xs btn-square"
                  :title="`Add members to ${team.name}`"
                  :disabled="saving"
                  @click="openAddMembersToTeam(team)"
                >
                  <i class="fa-solid fa-plus text-xs"></i>
                </button>
                <button
                  type="button"
                  class="btn btn-ghost btn-xs btn-square"
                  :title="`Edit ${team.name}`"
                  @click="openTeamEditor(team)"
                >
                  <i class="fa-solid fa-gear text-xs"></i>
                </button>
              </template>
              <span class="badge badge-sm ml-auto">{{ boardMembers(team).length }}</span>
            </div>
            <div class="flex flex-col gap-2 p-2 min-h-0 flex-1 overflow-y-auto">
              <div
                v-for="member in boardMembers(team)"
                :key="`${team.id}-${member.name}`"
                draggable="true"
                :class="dragging && dragging.name === member.name ? 'opacity-50' : ''"
                @dragstart="onDragStart(member, team, $event)"
                @dragend="onDragEnd"
              >
                <TeamMemberCard
                  compact
                  draggable
                  :member="member"
                  :team="team"
                  @edit="openEditor"
                  @remove-from-team="removeMemberFromTeam"
                />
              </div>
              <div v-if="!boardMembers(team).length" class="text-xs text-base-content/30 text-center py-6">
                {{ isAllTeam(team) ? (allUnassignedOnly ? 'No unassigned members' : 'No members') : 'Drop members here' }}
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- Filters modal -->
    <div v-if="filtersOpen" class="fixed inset-0 z-50 flex items-end sm:items-center justify-center sm:p-4">
      <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="filtersOpen = false"></div>

      <div
        class="relative w-full sm:max-w-md bg-base-100 border border-base-content/10 rounded-t-2xl sm:rounded-2xl shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-label="Filters"
      >
        <div class="flex items-center justify-between px-4 py-3 border-b border-base-content/10">
          <h2 class="font-semibold flex items-center gap-2">
            <i class="fa-solid fa-sliders text-primary"></i> Filters
          </h2>
          <button type="button" class="btn btn-ghost btn-sm btn-square" aria-label="Close filters" @click="filtersOpen = false">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="p-4 flex flex-col gap-4">
          <div>
            <label class="label-text text-xs font-semibold pb-1 block">Role</label>
            <select v-model="roleFilter" class="select select-sm select-bordered w-full">
              <option value="">All roles</option>
              <option v-for="(meta, key) in roleMetaMap" :key="key" :value="key">{{ meta.label }}</option>
            </select>
          </div>

          <div>
            <label class="label-text text-xs font-semibold pb-1 block">Sort by</label>
            <select v-model="sort" class="select select-sm select-bordered w-full">
              <option value="name">Name</option>
              <option value="role">Role</option>
            </select>
          </div>

          <p class="text-[11px] text-base-content/40 flex items-center gap-1">
            <i class="fa-solid fa-circle-info"></i>
            Teams are filtered with the chips above the list.
          </p>
        </div>

        <div class="flex items-center gap-2 px-4 py-3 border-t border-base-content/10">
          <button type="button" class="btn btn-sm btn-ghost mr-auto" :disabled="!hasFilters" @click="clearFilters">
            <i class="fa-solid fa-filter-circle-xmark"></i> Clear all
          </button>
          <button type="button" class="btn btn-sm btn-primary" @click="filtersOpen = false">Done</button>
        </div>
      </div>
    </div>

    <!-- Editor drawer (member settings) -->
    <TeamMemberDrawer
      v-if="selectedMember"
      :member="selectedMember"
      :members="members"
      :tools="tools"
      :saving="saving"
      @save="saveMember"
      @delete="askDelete"
      @close="closeEditor"
    />

    <!-- Add member dialog (creates a new profile) -->
    <AddTeamMemberDialog
      v-if="addOpen"
      :teams="teams"
      :default-team-ids="selectedTeamIds"
      :saving="saving"
      @create="addMember"
      @close="addOpen = false"
    />

    <!-- Add members to a team dialog -->
    <AddMembersToTeamDialog
      v-if="addMembersTeam"
      :team="addMembersTeam"
      :teams="teams"
      :members="members"
      :saving="saving"
      @add="addMembersToTeam"
      @close="closeAddMembersToTeam"
    />

    <!-- Create / edit team dialog -->
    <CreateTeamDialog
      v-if="teamDialogOpen"
      :team="editingTeam"
      :members="editingTeamMembers"
      :saving="saving"
      @submit="saveTeam"
      @delete="deleteTeam"
      @remove-member="onRemoveMemberFromTeam"
      @close="closeTeamDialog"
    />

    <!-- Delete member confirmation -->
    <div v-if="confirmDelete" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="confirmDelete = null"></div>
      <div class="relative card bg-base-100 border border-base-content/10 shadow-2xl w-full max-w-md" role="dialog" aria-modal="true" aria-label="Confirm delete">
        <div class="card-body gap-4">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl grid place-items-center bg-error/15 text-error">
              <i class="fa-solid fa-triangle-exclamation text-lg"></i>
            </div>
            <h2 class="card-title text-lg">Remove team member?</h2>
          </div>
          <p class="text-sm text-base-content/60">
            This will permanently remove
            <b>{{ confirmDelete.name }}</b>
            from the project. This action cannot be undone.
          </p>
          <div class="card-actions justify-end">
            <button type="button" class="btn btn-sm btn-ghost" @click="confirmDelete = null">Cancel</button>
            <button type="button" class="btn btn-sm btn-error" :disabled="saving" @click="deleteMember">
              <span v-if="saving" class="loading loading-spinner loading-xs"></span>
              <i v-else class="fa-solid fa-trash"></i>
              Remove
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Drag mode indicator: assign (from "All"), copy (Ctrl/Cmd) or move -->
    <div
      v-if="dragging"
      class="fixed bottom-4 right-4 z-[70] flex items-center gap-2 rounded-full bg-base-100 border border-base-content/10 shadow-2xl px-4 py-2 text-xs font-medium"
      role="status"
      aria-live="polite"
    >
      <i class="fa-solid" :class="dragFromAll ? 'fa-user-plus text-info' : (dragCopy ? 'fa-copy text-success' : 'fa-hand-pointer text-primary')"></i>
      <span v-if="dragFromAll">
        <i class="fa-solid fa-user-plus mr-1 text-info"></i>Assigning “{{ dragging.name }}” to a team
      </span>
      <span v-else-if="dragCopy">
        <i class="fa-solid fa-copy mr-1 text-success"></i>Copying “{{ dragging.name }}”
      </span>
      <span v-else>
        Moving “{{ dragging.name }}” — hold <kbd class="kbd kbd-xs">Ctrl</kbd> to copy
      </span>
    </div>
  </div>
</template>

<script>
// Virtual group used by the grid view for members that are not part of any API
// team yet. It is derived from the data (never persisted) — purely a UI
// affordance so unassigned members stay visible.
const UNASSIGNED_TEAM = { id: '__unassigned__', name: 'Unassigned', color: '#71717a' }

// Virtual "All" column shown first in the board view. It always lists every
// member; dragging a member OUT of it only ASSIGNS them to the target team
// (there is nothing to remove them from, as the group is derived, not stored).
const ALL_TEAM = { id: '__all__', name: 'All', color: '#0ea5e9', icon: 'fa-solid fa-layer-group' }

export default {
  name: 'TeamView',
  // `params` is supplied by dockview when the app runs as a desktop panel.
  props: ['params'],
  data() {
    return {
      teams: [],
      members: [],
      tools: [],
      loading: true,
      error: null,
      view: 'board', // grid | board — board is the default view
      search: '',
      roleFilter: '',
      // Active team ids (chips). An EMPTY list means "all teams" (the "All"
      // chip). This drives which teams are visible in the view.
      selectedTeamIds: [],
      sort: 'name',
      filtersOpen: false,
      // Virtual "All" column: when true, show only members without any team.
      allUnassignedOnly: false,
      selectedMember: null,
      addOpen: false,
      addMembersTeam: null,
      teamDialogOpen: false,
      editingTeam: null,
      confirmDelete: null,
      saving: false,
      // Drag & drop state: the member being dragged + its source team.
      dragging: null,        // { name, fromTeamId }
      dragCopy: false,       // true while Ctrl/Cmd is held (copy instead of move)
      dragOverTeamId: null,  // team currently hovered
      roleMetaMap: ROLE_META
    }
  },
  computed: {
    filteredMembers() {
      const q = (this.search || '').trim().toLowerCase()
      const selected = this.selectedTeamIds
      const list = this.members.filter(member => {
        const matchSearch = !q ||
          [member.name, member.description, member.category].join(' ').toLowerCase().includes(q)
        const matchRole = !this.roleFilter || member.category === this.roleFilter
        // No chips selected ⇒ all teams; otherwise the member must belong to
        // at least one of the selected teams (union).
        const matchTeam = !selected.length ||
          this.memberTeamIds(member).some(id => selected.includes(id))
        return matchSearch && matchRole && matchTeam
      })

      return [...list].sort(this.sortMembers)
    },
    // Members matching the global search/role filters but IGNORING the team
    // chips. Backs the virtual "All" board column so the team filter never
    // hides members there — only the "Unassigned" toggle narrows it.
    membersWithoutTeamFilter() {
      const q = (this.search || '').trim().toLowerCase()
      const list = this.members.filter(member => {
        const matchSearch = !q ||
          [member.name, member.description, member.category].join(' ').toLowerCase().includes(q)
        const matchRole = !this.roleFilter || member.category === this.roleFilter
        return matchSearch && matchRole
      })

      return [...list].sort(this.sortMembers)
    },
    // Teams currently visible, driven by the chips (empty selection ⇒ all).
    activeTeams() {
      return this.teams.filter(team => this.isTeamActive(team.id))
    },
    // True when no team is filtered out — i.e. the "All" chip is on.
    allTeamsActive() {
      return this.selectedTeamIds.length === 0
    },
    // Filtered members that belong to no (real) team.
    unassignedMembers() {
      return this.filteredMembers.filter(member => this.memberTeamIds(member).length === 0)
    },
    // Unassigned members for the virtual "All" column — derived from the
    // team-filter-independent list so the toggle keeps working when a team is
    // filtered out (unassigned members belong to no team, so a team filter must
    // not remove them from "All").
    boardUnassignedMembers() {
      return this.membersWithoutTeamFilter.filter(member => this.memberTeamIds(member).length === 0)
    },
    groupedMembers() {
      // A member may belong to several teams, so they appear under each of
      // them. Members in no team fall into the derived "Unassigned" group.
      // Only ACTIVE teams (chips) render a group.
      const groups = this.activeTeams.map(team => ({ team, members: this.membersOf(team.id) }))
      const unassigned = this.unassignedMembers
      if (unassigned.length) {
        groups.push({ team: UNASSIGNED_TEAM, members: unassigned })
      }
      return groups.filter(group => group.members.length)
    },
    // Board columns: the virtual "All" column first, then every ACTIVE team.
    boardColumns() {
      return [ALL_TEAM, ...this.activeTeams]
    },
    // True when the current drag originated from the virtual "All" column.
    dragFromAll() {
      return this.dragging?.fromTeamId === ALL_TEAM.id
    },
    // True when the board branch is actually rendered — drives whether the
    // roster container scrolls (grid/list) or clips so columns scroll.
    // Independent of the team chips: the "All" column is always available.
    isBoardView() {
      return this.view === 'board'
        && !this.loading
        && !this.error
        && this.members.length > 0
    },
    stats() {
      const skills = new Set(this.members.flatMap(m => m.tools || []))
      return {
        members: this.members.length,
        teams: this.teams.length,
        skills: skills.size,
        guardrails: this.members.filter(m => m.guardrails?.enabled).length
      }
    },
    hasResults() {
      return this.filteredMembers.length > 0
    },
    hasFilters() {
      return !!(this.search || this.roleFilter || this.selectedTeamIds.length)
    },
    // Number of active non-search filters (search has its own inline field).
    activeFilterCount() {
      return [
        this.roleFilter,
        this.selectedTeamIds.length ? 'teams' : ''
      ].filter(Boolean).length
    },
    // Members belonging to the team currently open in the edit dialog.
    editingTeamMembers() {
      if (!this.editingTeam?.id) return []
      return this.allMembersOf(this.editingTeam.id)
    }
  },
  watch: {
    // Reload when the active project changes (mobile project switch / desktop panel).
    $project() {
      this.load()
    }
  },
  created() {
    // A specific team can be deep-linked ("/:projectName/team/:teamId").
    // In desktop mode dockview exposes the panel params as `this.params.params`.
    const teamId = this.$route?.params?.teamId
      || this.params?.params?.teamId
      || this.params?.teamId
      || null
    if (teamId) this.selectedTeamIds = [teamId]
    this.load()
  },
  mounted() {
    // Track the Ctrl/Cmd modifier so the drag indicator reacts live.
    window.addEventListener('keydown', this.onModifierChange)
    window.addEventListener('keyup', this.onModifierChange)
    window.addEventListener('blur', this.resetDrag)
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onModifierChange)
    window.removeEventListener('keyup', this.onModifierChange)
    window.removeEventListener('blur', this.resetDrag)
  },
  methods: {
    avatarUrl,

    // Shared name/role comparator so every member list stays consistently sorted.
    sortMembers(a, b) {
      if (this.sort === 'role') {
        return roleMeta(a.category).label.localeCompare(roleMeta(b.category).label)
      }
      return (a.name || '').localeCompare(b.name || '')
    },

    // ── Team visibility chips ─────────────────────────────────────────────
    // A team is active when nothing is selected (all) or it is in the set.
    isTeamActive(teamId) {
      return this.selectedTeamIds.length === 0 || this.selectedTeamIds.includes(teamId)
    },
    // "All" chip: clear the selection so every team is visible again.
    selectAllTeams() {
      this.selectedTeamIds = []
    },
    // Toggle a team chip. Starting from "all", clicking a team excludes the
    // others; selecting every team again normalises back to "all" (empty).
    toggleTeamChip(teamId) {
      const ids = this.teams.map(t => t.id)
      if (!this.selectedTeamIds.length) {
        this.selectedTeamIds = ids.filter(id => id !== teamId)
        return
      }
      const selected = new Set(this.selectedTeamIds)
      if (selected.has(teamId)) {
        selected.delete(teamId)
      } else {
        selected.add(teamId)
      }
      const next = ids.filter(id => selected.has(id))
      this.selectedTeamIds = next.length === ids.length ? [] : next
    },

    // ── Data (API is the single source of truth) ──────────────────────────
    async load() {
      const project = this.$project
      if (!project?.$api) {
        // Project not ready yet — the `$project` watcher will retry.
        this.loading = false
        return
      }
      this.loading = true
      this.error = null
      try {
        const [members, tools] = await Promise.all([
          project.$api.profiles.list(),
          project.$api.profiles.tools().catch(() => [])
        ])
        this.members = members || []
        this.tools = tools || []
        await this.loadTeams()
      } catch (e) {
        console.error('[TeamView] Failed to load team', e)
        this.error = e?.message || 'Failed to load your team'
      } finally {
        this.loading = false
      }
    },

    // Teams come ONLY from the project-scoped teams API — no client fallback.
    async loadTeams() {
      const project = this.$project
      if (!project?.$api?.teams) {
        this.teams = []
        return
      }
      try {
        const apiTeams = await project.$api.teams.list()
        this.teams = (apiTeams || []).map(toLocalTeam)
        // Drop stale ids (deleted teams) so the chips stay consistent.
        const validIds = new Set(this.teams.map(t => t.id))
        this.selectedTeamIds = this.selectedTeamIds.filter(id => validIds.has(id))
      } catch (e) {
        console.error('[TeamView] Failed to load teams', e)
        this.teams = []
      }
    },

    async reloadMembers() {
      this.members = await this.$project.$api.profiles.list()
    },

    // Manual refresh: re-read teams AND members from the API.
    async reload() {
      if (this.loading || this.saving) return
      await this.load()
      this.$ui.addNotification({ text: 'Team reloaded', type: 'success' })
    },

    // ── Team dialog (create / edit / delete) ──────────────────────────────
    openCreateTeam() {
      this.editingTeam = null
      this.teamDialogOpen = true
    },
    openTeamEditor(team) {
      if (!this.isRealTeam(team)) return
      this.editingTeam = team
      this.teamDialogOpen = true
    },
    closeTeamDialog() {
      this.teamDialogOpen = false
      this.editingTeam = null
    },
    isRealTeam(team) {
      return !!team?.id && !String(team.id).startsWith('__')
    },
    isAllTeam(team) {
      return !!team && team.id === ALL_TEAM.id
    },
    async saveTeam(payload) {
      const api = this.$project?.$api?.teams
      if (!payload?.name?.trim() || !api) {
        this.$ui.addNotification({ text: 'Teams API not available', type: 'error' })
        return
      }
      this.saving = true
      try {
        const existing = payload.id ? this.teams.find(t => t.id === payload.id) : null
        // Membership is managed through the members endpoint; never clobber it
        // here, so we always send the team's current profiles back.
        const apiTeam = toApiTeam({
          id: payload.id || undefined,
          name: payload.name,
          description: payload.description,
          color: payload.color,
          icon: payload.icon,
          logo: payload.logo,
          profiles: existing?.profiles || []
        })
        const saved = payload.id ? await api.update(apiTeam) : await api.create(apiTeam)
        await this.loadTeams()
        this.closeTeamDialog()
        this.$ui.addNotification({
          text: `Team “${saved.name}” ${payload.id ? 'updated' : 'created'}`,
          type: 'success'
        })
      } catch (e) {
        console.error('[TeamView] Failed to save team', e)
        this.$ui.addNotification({ text: 'Failed to save team', type: 'error' })
      } finally {
        this.saving = false
      }
    },
    async deleteTeam() {
      const team = this.editingTeam
      if (!this.isRealTeam(team) || this.saving) return
      this.saving = true
      try {
        await this.$project.$api.teams.delete(team.id)
        await this.loadTeams()
        this.closeTeamDialog()
        this.$ui.addNotification({ text: `Team “${team.name}” deleted`, type: 'success' })
      } catch (e) {
        console.error('[TeamView] Failed to delete team', e)
        this.$ui.addNotification({ text: 'Failed to delete team', type: 'error' })
      } finally {
        this.saving = false
      }
    },
    // Remove a single member from the team currently open in the dialog.
    async onRemoveMemberFromTeam(memberName) {
      const team = this.editingTeam
      if (!this.isRealTeam(team) || !memberName) return
      this.saving = true
      try {
        await this.$project.$api.teams.removeMembers(team.id, { profiles: [memberName] })
        await this.loadTeams()
        this.$ui.addNotification({ text: `“${memberName}” removed from ${team.name}`, type: 'success' })
      } catch (e) {
        console.error('[TeamView] Failed to remove member from team', e)
        this.$ui.addNotification({ text: 'Failed to remove member from team', type: 'error' })
      } finally {
        this.saving = false
      }
    },

    // ── Membership (many-to-many) ─────────────────────────────────────────
    // Every team whose `profiles` list contains the member (a member can be in
    // several teams).
    memberTeamIds(member) {
      return this.teams
        .filter(t => (t.profiles || []).includes(member.name))
        .map(t => t.id)
    },
    membersOf(teamId) {
      return this.filteredMembers.filter(member => this.memberTeamIds(member).includes(teamId))
    },
    allMembersOf(teamId) {
      return this.members.filter(member => this.memberTeamIds(member).includes(teamId))
    },
    // Members shown in a board column. The virtual "All" column works from the
    // FULL roster — independent of the team chips — and only narrows to the
    // unassigned members when the toggle is on. Every other column shows only
    // its own (team-filtered) members.
    boardMembers(team) {
      if (this.isAllTeam(team)) {
        return this.allUnassignedOnly ? this.boardUnassignedMembers : this.membersWithoutTeamFilter
      }
      return this.membersOf(team.id)
    },

    // ── Add members to a team ("+") ───────────────────────────────────────
    openAddMembersToTeam(team) {
      if (!this.isRealTeam(team)) return
      this.addMembersTeam = team
    },
    closeAddMembersToTeam() {
      this.addMembersTeam = null
    },
    async addMembersToTeam({ teamId, profiles }) {
      const api = this.$project?.$api?.teams
      if (!api || !teamId || !profiles?.length) return
      this.saving = true
      try {
        await api.addMembers(teamId, { profiles })
        await this.loadTeams()
        const team = this.teams.find(t => t.id === teamId)
        this.closeAddMembersToTeam()
        this.$ui.addNotification({
          text: `${profiles.length} member(s) added to ${team?.name || 'the team'}`,
          type: 'success'
        })
      } catch (e) {
        console.error('[TeamView] Failed to add members to team', e)
        this.$ui.addNotification({ text: 'Failed to add members to team', type: 'error' })
      } finally {
        this.saving = false
      }
    },

    // ── Remove member from a team ("-") ───────────────────────────────────
    async removeMemberFromTeam({ member, team }) {
      const api = this.$project?.$api?.teams
      if (!api || !this.isRealTeam(team) || !member?.name) return
      this.saving = true
      try {
        await api.removeMembers(team.id, { profiles: [member.name] })
        await this.loadTeams()
        this.$ui.addNotification({ text: `“${member.name}” removed from ${team.name}`, type: 'success' })
      } catch (e) {
        console.error('[TeamView] Failed to remove member from team', e)
        this.$ui.addNotification({ text: 'Failed to remove member from team', type: 'error' })
      } finally {
        this.saving = false
      }
    },

    // ── Drag & drop: ASSIGN (from "All") / MOVE (default) / COPY (Ctrl/Cmd) ─
    // Track the Ctrl/Cmd modifier during a drag so the UI can show a copy sign.
    onModifierChange(event) {
      this.dragCopy = !!(event.ctrlKey || event.metaKey)
    },
    resetDrag() {
      this.dragging = null
      this.dragCopy = false
      this.dragOverTeamId = null
    },
    onDragStart(member, team, event) {
      this.dragging = { name: member.name, fromTeamId: team?.id || null }
      this.dragCopy = !!(event?.ctrlKey || event?.metaKey)
      if (event?.dataTransfer) {
        event.dataTransfer.effectAllowed = 'copyMove'
        event.dataTransfer.setData('text/plain', member.name)
      }
    },
    onDragEnd() {
      this.resetDrag()
    },
    onDragOver(team, event) {
      // The virtual "All" column is source-only — never a drop target.
      if (this.isAllTeam(team)) return
      // Prevent default only for real columns so `drop` never fires on "All".
      if (event?.preventDefault) event.preventDefault()
      // Keep the copy flag accurate even if a keydown was missed.
      this.dragCopy = !!(event?.ctrlKey || event?.metaKey)
      this.dragOverTeamId = team.id
      if (event?.dataTransfer) {
        event.dataTransfer.dropEffect = (this.dragFromAll || this.dragCopy) ? 'copy' : 'move'
      }
    },
    onDragLeave(team) {
      if (this.dragOverTeamId === team.id) this.dragOverTeamId = null
    },
    onDrop(team, event) {
      if (this.isAllTeam(team)) return
      const drag = this.dragging
      if (!drag) return
      const copy = this.dragCopy || !!(event?.ctrlKey || event?.metaKey)
      if (drag.fromTeamId === ALL_TEAM.id) {
        // Dragged out of the virtual "All" column: only ASSIGN to the target.
        this.assignMemberToTeam(drag.name, team.id)
      } else if (copy) {
        this.copyMemberToTeam(drag.name, team.id)
      } else {
        this.moveMemberToTeam(drag.name, drag.fromTeamId, team.id)
      }
      this.resetDrag()
    },

    // Assign (from the virtual "All" column): add the member to the target team
    // only. There is nothing to remove them from since "All" is not stored.
    async assignMemberToTeam(memberName, teamId) {
      const api = this.$project?.$api?.teams
      if (!api || !teamId || !memberName) return
      const team = this.teams.find(t => t.id === teamId)
      if (team && (team.profiles || []).includes(memberName)) return
      try {
        await api.addMembers(teamId, { profiles: [memberName] })
        await this.loadTeams()
        this.$ui.addNotification({ text: `“${memberName}” assigned to ${team?.name || 'the team'}`, type: 'success' })
      } catch (e) {
        console.error('[TeamView] Failed to assign member to team', e)
        this.$ui.addNotification({ text: 'Failed to assign member to team', type: 'error' })
      }
    },

    // Copy: add the member to the target team (keeps their other teams).
    async copyMemberToTeam(memberName, teamId) {
      const api = this.$project?.$api?.teams
      if (!api || !teamId || !memberName) return

      const team = this.teams.find(t => t.id === teamId)
      if (team && (team.profiles || []).includes(memberName)) return

      try {
        await api.addMembers(teamId, { profiles: [memberName] })
        // Re-read from the API so the UI always mirrors the persisted state.
        await this.loadTeams()
        this.$ui.addNotification({ text: `“${memberName}” copied to ${team?.name || 'the team'}`, type: 'success' })
      } catch (e) {
        console.error('[TeamView] Failed to copy member to team', e)
        this.$ui.addNotification({ text: 'Failed to copy member to team', type: 'error' })
      }
    },

    // Move: remove the member from the source team and add them to the target.
    async moveMemberToTeam(memberName, fromTeamId, toTeamId) {
      const api = this.$project?.$api?.teams
      if (!api || !memberName || !toTeamId) return
      if (fromTeamId === toTeamId) return

      this.saving = true
      try {
        if (fromTeamId && this.isRealTeam({ id: fromTeamId })) {
          await api.removeMembers(fromTeamId, { profiles: [memberName] })
        }
        await api.addMembers(toTeamId, { profiles: [memberName] })
        await this.loadTeams()
        const toTeam = this.teams.find(t => t.id === toTeamId)
        this.$ui.addNotification({ text: `“${memberName}” moved to ${toTeam?.name || 'the team'}`, type: 'success' })
      } catch (e) {
        console.error('[TeamView] Failed to move member to team', e)
        this.$ui.addNotification({ text: 'Failed to move member to team', type: 'error' })
      } finally {
        this.saving = false
      }
    },

    // ── Editor (member settings) ──────────────────────────────────────────
    openEditor(member) {
      this.selectedMember = member
    },
    closeEditor() {
      this.selectedMember = null
    },
    async saveMember({ profile }) {
      if (!profile?.name?.trim() || this.saving) return
      this.saving = true
      try {
        // Only the profile is saved here — team membership is managed from the
        // team side ("+", "-", team settings), never from the member settings.
        await this.$project.$api.profiles.save(profile)
        await this.reloadMembers()
        this.closeEditor()
        this.$ui.addNotification({ text: `Changes to “${profile.name}” saved`, type: 'success' })
      } catch (e) {
        console.error('[TeamView] Failed to save member', e)
        this.$ui.addNotification({ text: 'Failed to save member', type: 'error' })
      } finally {
        this.saving = false
      }
    },

    // ── Add member (new profile) ──────────────────────────────────────────
    openAdd() {
      this.addOpen = true
    },
    async addMember(payload) {
      if (!payload?.name || this.saving) return
      this.saving = true
      try {
        const profile = {
          name: payload.name.trim(),
          category: payload.category,
          avatar: '',
          description: payload.description || '',
          content: payload.content || '',
          llm_model: '',
          file_match: '',
          profiles: [],
          tools: [],
          api_settings: { active: false, modelName: '', modelDescription: '' },
          guardrails: { ...EMPTY_GUARDRAILS },
          project_id: this.$project.project_id
        }
        await this.$project.$api.profiles.save(profile)

        const api = this.$project?.$api?.teams
        const teamIds = payload.teamIds || []
        if (api && teamIds.length) {
          for (const teamId of teamIds) {
            await api.addMembers(teamId, { profiles: [profile.name] })
          }
        }
        await this.loadTeams()

        await this.reloadMembers()
        this.addOpen = false
        this.$ui.addNotification({ text: `“${profile.name}” added to the team`, type: 'success' })
      } catch (e) {
        console.error('[TeamView] Failed to add member', e)
        this.$ui.addNotification({ text: 'Failed to add member', type: 'error' })
      } finally {
        this.saving = false
      }
    },

    // ── Delete member (only from member settings, with confirmation) ──────
    askDelete(payload) {
      this.confirmDelete = payload?.profile || payload
    },
    async deleteMember() {
      const member = this.confirmDelete
      if (!member || this.saving) return
      this.saving = true
      try {
        // Drop the member from every team it belongs to, then delete the profile.
        const api = this.$project?.$api?.teams
        if (api) {
          const teamIds = this.memberTeamIds(member)
          for (const teamId of teamIds) {
            await api.removeMembers(teamId, { profiles: [member.name] })
          }
        }

        await this.$project.$api.profiles.delete(member.name)
        await this.loadTeams()
        await this.reloadMembers()

        if (this.selectedMember?.name === member.name) this.closeEditor()
        this.confirmDelete = null
        this.$ui.addNotification({ text: `“${member.name}” removed`, type: 'success' })
      } catch (e) {
        console.error('[TeamView] Failed to remove member', e)
        this.$ui.addNotification({ text: 'Failed to remove member', type: 'error' })
      } finally {
        this.saving = false
      }
    },

    clearFilters() {
      this.search = ''
      this.roleFilter = ''
      this.selectedTeamIds = []
    }
  }
}
</script>

<!-- Made with ❤️ by codx-junior -->