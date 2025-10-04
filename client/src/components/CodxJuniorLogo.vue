<template>
  <div class="flex justify-center">
    <div class="avatar" :class="$storex.session.connected ? '' : 'grayscale'">
      <div class="w-8 rounded-full">
        <img src="/only_icon.png" />
      </div>
    </div>
  </div>
</template>