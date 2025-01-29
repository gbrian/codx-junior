<script setup>
import { defineProps, defineEmits, ref } from 'vue'

const props = defineProps({
  times: {
    type: Array,
    required: true,
    validator: value => value.length > 0
  }
})

const emit = defineEmits(['time-change'])

const selectedStart = ref(props.times[0])
const selectedEnd = ref(props.times[props.times.length - 1])

function resetTimeSelector() {
  selectedStart.value = null
  selectedEnd.value = null
  emitTimeChange()
  emit('reset')
}

function emitTimeChange() {
  emit('time-change', { start: selectedStart.value, end: selectedEnd.value })
}
</script>

<template>
  <div class="flex flex-row gap-2 items-center">
    <div class="form-control">
      <select v-model="selectedStart" class="select select-xs select-bordered m-1" @change="emitTimeChange">
        <option :selected="!selectedStart">--</option>
        <option v-for="time in times" :key="time" :value="time">{{ time }}</option>
      </select>
    </div>
    <i class="fa-regular fa-clock"></i>
    <div class="form-control">
      <select v-model="selectedEnd" class="select select-xs select-bordered m-1" @change="emitTimeChange">
        <option :selected="!selectedEnd">--</option>
        <option v-for="time in times" :key="time" :value="time">{{ time }}</option>
      </select>
    </div>
    <button class="btn btn-xs" @click="resetTimeSelector">
      <i class="fa-regular fa-circle-xmark"></i>
    </button>
  </div>
</template>