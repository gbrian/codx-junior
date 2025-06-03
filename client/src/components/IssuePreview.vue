<script setup>
import moment from 'moment'
</script>
<template>
  <div class="py-2 px-4 bg-base-100 rounded-md">
    <h3 class="font-semibold">
      <div>
        <a class="text-blue-600 text-xs hover:underline">
          <span>{{ issue.repo.repository.owner_login }}/{{ issue.repo.repository.name }}</span>
        </a>
      </div>
      <div class="flex items-center">
        <a class="hover:underline">
          <span>{{ issue.hl_title }}</span>
        </a>
      </div>
    </h3>
    <div class="text-xs">
    {{ issue.hl_text }}
    </div>
    <div class="flex justify-between">
      <ul class="flex items-center space-x-2 mt-1 text-sm text-gray-600">
        <li class="flex items-center">
          <img :src="issue.author_avatar_url" :title="issue.author_name" class="w-4 h-4 rounded-full mr-1">
          {{ issue.authorName }}
        </li>
        <span>·</span>
        <li class="flex items-center">
          <i class="fa-solid fa-comments"></i>
          {{ issue.numComments }}
        </li>
        <span>·</span>
        <li class="text-xs">
          Opened&nbsp;<span>{{ moment(issue.created).fromNow() }}</span>
        </li>
      </ul>
      <div class="flex space-x-2 mt-3">
        <div v-for="label in issue.labels" :key="label" class="badge badge-sm badge-outline">
          {{ label }}
        </div>
      </div>
    </div>  
  </div>
</template>

<script>
export default {
  props: {
    issue: Object
  }
}
</script>
