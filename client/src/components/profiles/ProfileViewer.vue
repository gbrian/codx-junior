<script setup>
</script>

<template>
  <div class="profile-viewer px-4 mx-auto flex flex-col gap-4">
    <div class="text-xl font-bold flex gap-2 items-center">
      <div class="avatar">
        <div class="w-6 rounded">
          <img :src="profile.avatar" />
        </div>
      </div>
      {{ profile.name }}
      <span
        class="badge badge-sm gap-1"
        :class="profile.guardrails?.enabled ? 'badge-info' : 'badge-ghost'"
        :title="profile.guardrails?.enabled ? 'Guardrails enabled' : 'Guardrails disabled'"
      >
        <i class="fa-solid fa-shield-halved"></i>
        {{ profile.guardrails?.enabled ? 'Guardrails' : 'No guardrails' }}
      </span>
    </div>
    <div class="bg-base-300 p-4 rounded-md">
      <div class="font-semibold">Description</div>
      <div class="mt-2">{{ profile.description }}</div>
    </div>
    <div v-if="profile.guardrails?.enabled" class="bg-base-300 p-4 rounded-md">
      <div class="font-semibold flex items-center gap-2">
        <i class="fa-solid fa-shield-halved text-info"></i> Guardrails
      </div>
      <div class="mt-2 flex flex-col gap-2 text-sm">
        <div v-if="profile.guardrails.scope">
          <span class="font-semibold">Scope:</span> {{ profile.guardrails.scope }}
        </div>
        <div v-if="profile.guardrails.scope_keywords?.length" class="flex flex-wrap gap-1 items-center">
          <span class="font-semibold">Keywords:</span>
          <span
            v-for="keyword in profile.guardrails.scope_keywords"
            :key="keyword"
            class="badge badge-xs badge-outline"
          >{{ keyword }}</span>
        </div>
        <div class="flex flex-wrap gap-1 items-center">
          <span class="font-semibold">Allowed tools:</span>
          <template v-if="profile.guardrails.allowed_tools?.length">
            <span
              v-for="tool in profile.guardrails.allowed_tools"
              :key="tool"
              class="badge badge-xs badge-info"
            >{{ tool }}</span>
          </template>
          <span v-else class="text-base-content/60 text-xs">None</span>
        </div>
      </div>
    </div>
    <div class="bg-base-300 p-4 rounded-md">
      <div class="font-semibold">Content</div>
      <Markdown class="mt-2 p-2 rounded-md bg-base-100 border border-base-100" :text="profile.content" />
    </div>
  </div>
</template>

<script>
export default {
  props: ['profile']
}
</script>