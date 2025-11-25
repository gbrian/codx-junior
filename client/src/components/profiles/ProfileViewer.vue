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
    </div>
    <div class="bg-base-300 p-4 rounded-md">
      <div class="font-semibold">Description</div>
      <div class="mt-2">{{ profile.description }}</div>
    </div>
    <div class="bg-base-300 p-4 rounded-md">
      <div class="font-semibold">Content</div>
      <Markdown class="mt-2 p-2 rounded-md bg-base-100 border border-slate-700" :text="profile.content" />
    </div>
  </div>
</template>

<script>
export default {
  props: ['profile']
}
</script>