<script setup>
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="flex gap-2 items-center">
      <div class="badge flex gap-2">
        <span class="text-info"><i class="fa-solid fa-file"></i></span>
        {{ $projects.embeddingsModel }}
      </div>
      <button class="btn btn-sm" @click="$emit('set-setting', { knowledge_enrich_documents: !project.knowledge_enrich_documents })">
        <span class="label-text mr-2">Enrich documents</span>
        <input type="checkbox" class="toggle toggle-sm toggle-primary" :checked="project.knowledge_enrich_documents" />
      </button>
      <button class="btn btn-sm" @click="$emit('set-setting', { knowledge_generate_training_dataset: !project.knowledge_generate_training_dataset })">
        <span class="label-text mr-2">Training data</span>
        <input type="checkbox" class="toggle toggle-sm toggle-primary" :checked="project.knowledge_generate_training_dataset" />
      </button>
    </div>
    <div class="stats stats-sm">
      <div :class="['stat click', activeTab === 0 && 'bg-primary/20']" @click="$emit('set-tab', 0)">
        <div class="stat-figure mt-6">
          <i class="fa-2xl fa-solid fa-file"></i>
        </div>
        <div class="stat-title">Pending</div>
        <div class="stat-value">{{ indexStatus?.total_pending }}</div>
      </div>
      <div :class="['stat click', activeTab === 1 && 'bg-primary/20']" @click="$emit('set-tab', 1)">
        <div class="stat-figure mt-6 text-success">
          <i class="fa-2xl fa-solid fa-puzzle-piece"></i>
        </div>
        <div class="stat-title">Indexed</div>
        <div class="stat-value">{{ indexStatus?.file_count }}</div>
      </div>
      <div :class="['stat click', activeTab === 2 && 'bg-primary/20']" @click="$emit('set-tab', 2)">
        <div class="stat-figure mt-6 text-warning">
          <i class="fa-2xl fa-solid fa-file"></i>
        </div>
        <div class="stat-title">Ignored</div>
        <div class="stat-value">{{ ignoredCount }}</div>
      </div>
      <div class="stat">
        <div class="stat-figure mt-6 text-info">
          <i class="fa-2xl fa-solid fa-book"></i>
        </div>
        <div class="stat-title">Keywords</div>
        <div class="stat-value">{{ indexStatus?.keyword_count }}</div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  emits: ['set-tab', 'set-setting'],
  props: {
    indexStatus: Object,
    activeTab: Number,
    ignoredCount: Number,
    project: Object
  }
}
</script>