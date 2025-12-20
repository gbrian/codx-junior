<template>
  <div class="flex gap-1">
      <button class="btn btn-xs btn-outline tooltip"
        :class="[
          messageCount ? 'btn-warning' : 'disabled'
        ]"
        data-tip="Review changes"
        @click="$emit('select', 'chat')">
        <i class="fa-solid fa-comments"></i>
      </button>
      
      <button class="btn btn-xs btn-xs btn-outline" 
        data-tip="Copare changes"
        @click="$emit('select', 'diff')" >
        <i class="fa-solid fa-code-merge"></i>
      </button>    
  </div>
</template>
<script>
export default {
  props: ['messageCount'],
  
}
</script>