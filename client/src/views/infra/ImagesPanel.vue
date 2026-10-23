<template>
  <div>
    <!-- ── Empty state ────────────────────────────────────────────────────── -->
    <div v-if="!filteredList.length" class="card bg-base-200 border border-base-300 shadow-sm">
      <div class="card-body items-center text-center py-12">
        <i class="fas fa-hard-drive text-4xl opacity-30"></i>
        <h3 class="card-title mt-2">
          {{ hasImages ? 'No images match your filters' : 'No images found' }}
        </h3>
        <p class="text-sm opacity-60">
          {{ hasImages
            ? 'Try clearing the search box.'
            : 'Pull or build an image and it will be listed here.' }}
        </p>
        <div v-if="hasImages" class="card-actions mt-2">
          <button class="btn btn-sm btn-ghost" @click="clearFilters">
            <i class="fas fa-filter-circle-xmark"></i> Clear filters
          </button>
        </div>
      </div>
    </div>

    <!-- ── Narrow panel (< 42rem / 672px): one card per image ─────────────── -->
    <div v-else-if="layout.compact" class="space-y-2">
      <article v-for="img in filteredList" :key="`card-${img.id}`"
               class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-3 gap-2">
          <div class="flex items-start gap-2 min-w-0">
            <i class="fas fa-hard-drive text-xs opacity-40 mt-1 shrink-0"></i>
            <div class="min-w-0 grow">
              <div class="flex items-center gap-1.5 min-w-0">
                <span class="font-mono text-xs font-semibold truncate">{{ img.repo }}</span>
                <span class="badge badge-xs badge-ghost shrink-0">{{ img.tag }}</span>
              </div>
              <div class="text-[11px] opacity-40 font-mono truncate">{{ img.id }}</div>
            </div>
            <span v-if="img.dangling" class="badge badge-xs badge-warning shrink-0">dangling</span>
          </div>

          <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px]">
            <span><span class="opacity-50">Size</span> <span class="font-mono">{{ fmtBytes(img.size) }}</span></span>
            <span><span class="opacity-50">Created</span> <span class="font-mono">{{ fmtTime(img.created) }}</span></span>
            <span class="badge badge-xs"
                  :class="img.containers ? 'badge-success badge-outline' : 'badge-ghost'">
              {{ img.containers || 0 }} in use
            </span>
          </div>

          <div class="flex items-center gap-1.5 pt-2 border-t border-base-300">
            <button class="btn btn-sm btn-primary btn-outline grow" @click="runImage(img)">
              <i class="fas fa-play"></i> Run
            </button>
            <button class="btn btn-sm btn-square btn-ghost"
                    title="Inspect" aria-label="Inspect" @click="showJson(`${img.repo}:${img.tag}`, img)">
              <i class="fas fa-code"></i>
            </button>
          </div>
        </div>
      </article>
    </div>

    <!-- ── Wide panel (>= 42rem / 672px): list rows ───────────────────────── -->
    <div v-else class="card bg-base-200 border border-base-300 shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="table table-sm">
          <thead>
            <tr>
              <th>Repository</th>
              <th class="w-40">Tag</th>
              <th class="w-28 text-right">Size</th>
              <th class="w-32">Created</th>
              <th class="w-24 text-center">Used by</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="img in filteredList" :key="img.id" class="hover">
              <td>
                <div class="flex items-center gap-2 min-w-0">
                  <i class="fas fa-hard-drive text-xs opacity-40"></i>
                  <span class="font-mono text-xs truncate">{{ img.repo }}</span>
                  <span v-if="img.dangling" class="badge badge-xs badge-warning">dangling</span>
                </div>
                <span class="text-[11px] opacity-40 font-mono">{{ img.id }}</span>
              </td>
              <td class="font-mono text-xs">{{ img.tag }}</td>
              <td class="text-right font-mono text-xs">{{ fmtBytes(img.size) }}</td>
              <td class="text-xs opacity-70">{{ fmtTime(img.created) }}</td>
              <td class="text-center">
                <span class="badge badge-xs" :class="img.containers ? 'badge-success badge-outline' : 'badge-ghost'">
                  {{ img.containers || 0 }}
                </span>
              </td>
              <td>
                <div class="flex justify-end gap-1">
                  <button class="btn btn-xs btn-ghost" title="Inspect"
                          @click="showJson(`${img.repo}:${img.tag}`, img)">
                    <i class="fas fa-code"></i>
                  </button>
                  <button class="btn btn-xs btn-primary btn-outline" title="Run a container from this image"
                          @click="runImage(img)">
                    <i class="fas fa-play"></i> Run
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { state, filteredList, setFilter, fmtBytes, fmtTime, showJson, openRunModal } from './useInfra'
import { layout } from './useInfraLayout'

/** True when the host has images at all (i.e. the empty state is filter-driven). */
const hasImages = computed(() => state.images.length > 0)

function clearFilters() {
  setFilter({ q: '' })
}

/** Pre-fills the "run container" modal with this image. */
function runImage(img) {
  const repo = img.repo === '<none>' ? '' : img.repo
  const tag = img.tag === '<none>' ? '' : img.tag
  openRunModal({
    image: repo ? `${repo}${tag ? `:${tag}` : ''}` : '',
    name: repo ? `${repo.split('/').pop()}-${Date.now().toString().slice(-4)}` : ''
  })
}
</script>