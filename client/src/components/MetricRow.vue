<script setup>
</script>
<template>
  <div class="flex justify-between items-center bg-base-100 rounded px-2 py-0.5">
    <span class="opacity-60">{{ label }}</span>
    <span :class="highlight ? 'text-warning font-bold font-mono' : 'font-mono'">{{ value }}</span>
  </div>
</template>
<script>
export default {
  props: ['label', 'value', 'highlight']
}
</script>