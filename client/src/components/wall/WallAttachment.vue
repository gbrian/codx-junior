<script setup>
</script>

<template>
  <div v-if="attachment" class="mt-2 rounded-2xl border border-base-content/10 overflow-hidden">
    <!-- Attached images (pasted / uploaded) -->
    <div v-if="attachment.type === 'images'" class="relative">
      <div class="grid grid-cols-2 gap-1">
        <img
          v-for="(img, ix) in visibleImages"
          :key="ix"
          :src="img.src"
          :alt="img.name || 'attachment'"
          loading="lazy"
          class="w-full aspect-video object-cover bg-base-200"
        />
      </div>
      <span
        v-if="attachment.images.length > visibleImages.length"
        class="absolute bottom-2 right-2 badge badge-sm bg-black/60 text-white border-0"
      >
        +{{ attachment.images.length - visibleImages.length }}
      </span>
    </div>

    <!-- Audio notes (recorded voice messages / uploaded audio) -->
    <div v-else-if="attachment.type === 'audio'" class="p-3 flex flex-col gap-2 bg-base-content/5">
      <div class="flex items-center gap-2 text-xs font-semibold text-base-content/60">
        <i class="fa-solid fa-microphone-lines text-primary"></i>
        {{ attachment.audios.length }} audio note(s)
      </div>
      <audio
        v-for="(audio, ix) in attachment.audios"
        :key="ix"
        :src="audio.src"
        :title="audio.name"
        controls
        preload="metadata"
        class="w-full"
      ></audio>
    </div>

    <!-- Generic attached files -->
    <div v-else-if="attachment.type === 'files'" class="p-3">
      <div class="text-xs text-base-content/50 mb-2">
        <i class="fa-solid fa-paperclip"></i> {{ attachment.files.length }} attachment(s)
      </div>
      <ul class="divide-y divide-base-content/10">
        <li v-for="(file, ix) in attachment.files" :key="ix" class="py-1 text-xs font-mono truncate">
          {{ file.path }}
        </li>
      </ul>
    </div>

    <!-- Changed files -->
    <div v-else-if="attachment.type === 'code'" class="p-3">
      <div class="text-xs text-base-content/50 mb-2">
        <i class="fa-solid fa-code"></i> {{ attachment.files.length }} file(s)
      </div>
      <ul class="divide-y divide-base-content/10">
        <li v-for="(file, ix) in attachment.files" :key="ix" class="py-1 text-xs font-mono truncate">
          {{ file.path }}
        </li>
      </ul>
    </div>

    <!-- Board / task move -->
    <div v-else-if="attachment.type === 'board'" class="p-3 bg-base-200/50">
      <div class="flex items-center gap-2 text-xs font-semibold text-base-content/60">
        <i class="fa-brands fa-trello"></i> {{ attachment.board || 'Board' }}
      </div>
      <div class="mt-2 flex items-center gap-2 text-sm">
        <span class="badge badge-outline badge-sm">{{ attachment.to || 'new' }}</span>
        <span v-if="attachment.task" class="font-semibold truncate">{{ attachment.task }}</span>
      </div>
    </div>

    <!-- Pull request -->
    <div v-else-if="attachment.type === 'pr'" class="p-3">
      <div class="flex items-center gap-2">
        <span class="badge badge-secondary badge-sm">
          <i class="fa-solid fa-code-pull-request"></i> Pull request
        </span>
        <span class="text-sm font-semibold truncate">{{ attachment.title || 'Review changes' }}</span>
      </div>
      <div v-if="attachment.from || attachment.to" class="mt-2 flex items-center gap-2 text-xs font-mono text-base-content/60">
        <span class="px-2 py-0.5 rounded bg-base-200">{{ attachment.from || '—' }}</span>
        <i class="fa-solid fa-arrow-right"></i>
        <span class="px-2 py-0.5 rounded bg-base-200">{{ attachment.to || '—' }}</span>
      </div>
    </div>

    <!-- Live or ended meet -->
    <div v-else-if="attachment.type === 'meet'" class="p-3" :class="isMeetEnded ? 'bg-base-content/5' : 'bg-error/5'">
      <div class="flex items-center gap-2">
        <i class="fa-solid fa-video" :class="isMeetEnded ? 'text-base-content/50' : 'text-error'"></i>
        <span class="text-sm font-semibold">{{ attachment.title || 'Meet' }}</span>

        <!-- Ended: quiet, non-actionable badge -->
        <span v-if="isMeetEnded" class="ml-auto inline-flex items-center gap-1 text-xs font-semibold text-base-content/50">
          <i class="fa-solid fa-clock-rotate-left"></i> ENDED
        </span>
        <!-- Live: pulsing indicator -->
        <span v-else class="ml-auto inline-flex items-center gap-1 text-xs font-semibold text-error">
          <span class="w-2 h-2 rounded-full bg-error animate-pulse"></span> LIVE
        </span>
      </div>
      <div class="mt-2 flex items-center gap-2">
        <span class="text-xs text-base-content/50">{{ (attachment.participants || []).length }} participant(s)</span>
        <button v-if="!isMeetEnded" class="btn btn-error btn-xs ml-auto" @click.stop="$emit('action', 'join-meet')">Join</button>
      </div>
    </div>

    <!-- Knowledge / index progress -->
    <div v-else-if="attachment.type === 'progress'" class="p-3">
      <div class="flex items-center justify-between text-xs mb-1">
        <span class="text-base-content/60"><i class="fa-solid fa-database"></i> Indexed</span>
        <span class="font-semibold">{{ attachment.indexed }}/{{ attachment.total }}</span>
      </div>
      <progress class="progress progress-warning w-full" :value="attachment.indexed" :max="attachment.total || 1"></progress>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    attachment: { type: Object, default: null }
  },
  emits: ['action'],
  computed: {
    // An ended meet (from `meetHistory`) renders a neutral card with no Join
    // action; only a live meet keeps the pulsing LIVE badge + Join button.
    isMeetEnded() {
      return this.attachment?.status === 'ended'
    },
    // Keep the preview compact — the "+N" badge covers the rest.
    visibleImages() {
      return (this.attachment?.images || []).slice(0, 4)
    }
  }
}
</script>