<template>
  <div class="flex gap-1">
      <button class="btn btn-xs btn-outline tooltip"
        data-tip="Review changes"
        @click="$emit('select', 'message')">
        <i class="fa-solid fa-message"></i>
      </button>

      <button class="btn btn-xs btn-outline tooltip"
        data-tip="Review changes"
        @click="$emit('select', 'chat')">
        <i class="fa-solid fa-comments"></i>
      </button>
      
      <button class="btn btn-xs btn-xs btn-outline" 
        data-tip="Copare changes"
        @click="$emit('select', 'diff')" >
        <i class="fa-solid fa-code-merge"></i>
      </button>

      <button class="btn btn-xs btn-xs btn-outline" 
        data-tip="Show file content"
        @click="$emit('select', 'file')">
        <i class="fa-solid fa-file-lines"></i>
      </button>    
  </div>
</template>
<script>
export default {
}
</script>