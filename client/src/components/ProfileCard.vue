<script setup>
import ChatIcon from './chat/ChatIcon.vue'
</script>

<template>
  <!-- Full card version (default) -->
  <div v-if="!mini" class="relative group card w-full overflow-hidden border border-base-300 bg-base-100 shadow-md rounded-xl flex flex-col" style="min-height: 320px;">
    <!-- Header strip with category color -->
    <div class="h-2 w-full rounded-t-xl flex-shrink-0"
      :class="{
        'bg-primary': profile.category === 'assistant',
        'bg-secondary': profile.category === 'chat',
        'bg-accent': profile.category === 'agent',
        'bg-info': profile.category === 'file',
        'bg-neutral': profile.category === 'project'
      }">
    </div>

    <!-- Background avatar blur -->
    <div class="absolute inset-0 opacity-10 group-hover:opacity-20 transition-opacity bg-cover bg-center blur-sm"
      :style="`background-image: url(${useAvatar})`">
    </div>

    <div class="relative z-10 flex flex-col flex-1 items-center p-5 gap-2">
      <!-- Avatar + category badge -->
      <div class="indicator flex-shrink-0">
        <span class="indicator-item badge badge-xs badge-success badge-outline">
          {{ profile.category }}</span>
        <div class="avatar">
          <div class="w-20 h-20 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2">
            <img :src="useAvatar" :alt="profile.name" />
          </div>
        </div>
      </div>

      <!-- Name -->
      <div class="flex items-center gap-2 mt-1 flex-shrink-0">
        <div class="avatar tooltip" :data-tip="project?.project_name" v-if="project?.project_icon">
          <div class="w-5 rounded-full">
            <img :src="project.project_icon" />
          </div>
        </div>
        <h2 class="font-bold text-base truncate max-w-[160px]">{{ profile.name }}</h2>
      </div>

      <!-- file_match pill -->
      <span v-if="profile.file_match" class="badge badge-xs badge-outline badge-accent font-mono flex-shrink-0">
        {{ profile.file_match }}
      </span>

      <!-- LLM model pill -->
      <span v-if="profile.llm_model" class="badge badge-xs badge-outline badge-warning font-mono flex-shrink-0">
        <i class="fa-solid fa-brain mr-1"></i>{{ profile.llm_model }}
      </span>

      <!-- Linked profiles -->
      <div class="flex flex-wrap gap-1 justify-center flex-shrink-0">
        <span v-for="p in profile.profiles" :key="p" class="badge badge-xs badge-secondary">{{ p }}</span>
      </div>

      <!-- Description — middle, clipped -->
      <div class="flex-1 w-full flex items-center justify-center overflow-hidden px-1">
        <p class="text-xs text-base-content/70 text-center line-clamp-4">{{ profile.description }}</p>
      </div>

      <!-- Stats row — always at bottom -->
      <div class="stats stats-horizontal shadow-none bg-base-200 rounded-lg text-xs w-full mt-auto flex-shrink-0">
        <div class="stat p-2 text-center">
          <div class="stat-title text-xs">Knowledge</div>
          <div class="stat-value text-base">
            <i class="fa-solid fa-book" :class="profile.use_knowledge ? 'text-info' : 'text-base-content/30'"></i>
          </div>
        </div>
        <div class="stat p-2 text-center">
          <div class="stat-title text-xs">API</div>
          <div class="stat-value text-base">
            <i class="fa-solid fa-share-nodes" :class="profile.api_settings?.active ? 'text-warning' : 'text-base-content/30'"></i>
          </div>
        </div>
        <div class="stat p-2 text-center">
          <div class="stat-title text-xs">Profiles</div>
          <div class="stat-value text-base">{{ profile.profiles?.length || 0 }}</div>
        </div>
        <div class="stat p-2 text-center">
          <div class="stat-title text-xs">Tools</div>
          <div class="stat-value text-base" :class="profile.tools?.length ? 'text-success' : 'text-base-content/30'">
            {{ profile.tools?.length || 0 }}
          </div>
        </div>
        <div class="stat p-2 text-center" v-if="profile.llm_model">
          <div class="stat-title text-xs">Model</div>
          <div class="stat-value text-xs text-warning truncate max-w-[60px]">{{ profile.llm_model }}</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Mini card version for profile selector -->
  <div v-else class="card w-full border border-base-300 bg-base-100 shadow-sm rounded-lg p-3 flex flex-row items-center gap-3 hover:shadow-md transition-shadow">
    <!-- Header strip indicator -->
    <div class="h-8 w-1 rounded-full flex-shrink-0"
      :class="{
        'bg-primary': profile.category === 'assistant',
        'bg-secondary': profile.category === 'chat',
        'bg-accent': profile.category === 'agent',
        'bg-info': profile.category === 'file',
        'bg-neutral': profile.category === 'project'
      }">
    </div>

    <!-- Avatar + name section -->
    <div class="flex items-center gap-2 flex-1 min-w-0">
      <div class="avatar flex-shrink-0">
        <div class="w-10 h-10 rounded-full ring ring-primary ring-offset-base-100 ring-offset-1">
          <img :src="useAvatar" :alt="profile.name" />
        </div>
      </div>

      <div class="flex-1 min-w-0">
        <h3 class="font-semibold text-sm truncate">{{ profile.name }}</h3>
        <p class="text-xs text-base-content/60 truncate">{{ profile.category }}</p>
      </div>
    </div>

    <!-- Quick indicators -->
    <div class="flex items-center gap-2 flex-shrink-0">
      <div v-if="profile.use_knowledge" class="tooltip" data-tip="Uses Knowledge">
        <i class="fa-solid fa-book text-info text-xs"></i>
      </div>
      <div v-if="profile.api_settings?.active" class="tooltip" data-tip="API Active">
        <i class="fa-solid fa-share-nodes text-warning text-xs"></i>
      </div>
      <div v-if="profile.tools?.length" class="tooltip" :data-tip="toolsTooltip">
        <div class="badge badge-xs badge-success">
          {{ profile.tools.length }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    profile: {
      type: Object,
      required: true
    },
    mini: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {}
  },
  computed: {
    project() {
      return this.$projects?.allProjectsById?.[this.profile.project_id] || this.$project
    },
    useAvatar() {
      return this.profile.avatar ||
        `https://gravatar.com/avatar/baa8db8ab2afb7ababc235269e762662?s=400&d=robohash&r=${this.profile.name}`
    },
    toolsTooltip() {
      return this.profile.tools?.join(', ') || 'No tools'
    }
  },
  watch: {},
  methods: {}
}
</script>