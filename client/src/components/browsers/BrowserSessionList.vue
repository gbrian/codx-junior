<script setup>
import { computed, ref, onMounted } from 'vue'
</script>

<template>
  <div class="flex flex-col h-full gap-2 p-3 bg-base-100">
    <!-- Header -->
    <div class="flex items-center justify-between gap-2 flex-shrink-0">
      <h2 class="text-lg font-bold truncate">Browser Sessions</h2>
      <button
        @click="toggleNewForm"
        class="btn btn-sm btn-primary btn-circle flex-shrink-0"
        :title="showNewForm ? 'Cancel' : 'New Session'"
      >
        <i :class="showNewForm ? 'fa-solid fa-times' : 'fa-solid fa-plus'"></i>
      </button>
    </div>

    <!-- New Session Form -->
    <div v-if="showNewForm" class="card bg-base-200 p-3 flex-shrink-0 space-y-2">
      <div class="form-control gap-2 text-sm">
        <label class="label p-0">
          <span class="label-text font-semibold">Session Name</span>
        </label>
        <input
          v-model="newSessionName"
          type="text"
          placeholder="My Browser Session"
          class="input input-bordered input-sm"
          @keyup.enter="handleCreateSession"
        />

        <label class="label p-0 pt-1">
          <span class="label-text font-semibold">URL</span>
        </label>
        <input
          v-model="newSessionUrl"
          type="url"
          placeholder="http://example.com"
          class="input input-bordered input-sm"
          @keyup.enter="handleCreateSession"
        />

        <label class="label cursor-pointer p-0 pt-1">
          <input v-model="newSessionHeadless" type="checkbox" class="checkbox checkbox-sm" />
          <span class="label-text ml-2">Headless Mode</span>
        </label>

        <button
          @click="handleCreateSession"
          class="btn btn-primary btn-sm mt-2"
          :disabled="!newSessionName.trim()"
        >
          Create Session
        </button>
      </div>
    </div>

    <!-- Sessions List -->
    <div class="flex-1 overflow-y-auto space-y-1">
      <div v-if="isLoading" class="flex items-center justify-center py-8">
        <div class="loading loading-spinner loading-sm"></div>
        <span class="ml-2 text-sm">Loading sessions...</span>
      </div>

      <div v-else-if="sessions.length === 0" class="text-center py-8 text-base-content/50">
        <i class="fa-solid fa-inbox text-2xl mb-2 block"></i>
        <p class="text-sm">No browser sessions yet</p>
      </div>

      <div
        v-for="session in sessions"
        :key="session.id"
        @click="handleSelectSession(session.id)"
        class="card p-3 cursor-pointer transition-all"
        :class="[
          selectedSessionId === session.id
            ? 'bg-primary text-primary-content shadow-md'
            : 'bg-base-200 hover:bg-base-300'
        ]"
      >
        <div class="space-y-1">
          <!-- Session Name & Status -->
          <div class="flex items-center justify-between gap-2">
            <h3 class="font-semibold truncate flex-1">{{ session.name }}</h3>
            <span
              v-if="session.status"
              class="badge badge-sm"
              :class="[
                session.status === 'running'
                  ? 'badge-success'
                  : session.status === 'stopped'
                  ? 'badge-warning'
                  : 'badge-ghost'
              ]"
            >
              {{ session.status }}
            </span>
          </div>

          <!-- Session URL (hide on mobile if selected) -->
          <div v-if="!isMobile || selectedSessionId !== session.id" class="text-xs truncate opacity-75">
            {{ session.url }}
          </div>

          <!-- Action Buttons -->
          <div class="flex gap-1 pt-2 flex-wrap">
            <button
              @click="(e) => handleRunSession(session.id, e)"
              class="btn btn-xs btn-success flex-1 min-w-[60px]"
              title="Run Session"
            >
              <i class="fa-solid fa-play"></i>
              <span v-if="!isMobile">Run</span>
            </button>
            <button
              @click="(e) => { e.stopPropagation(); startEditingSession(session.id) }"
              class="btn btn-xs btn-info"
              title="Edit Session"
            >
              <i class="fa-solid fa-gear"></i>
              <span v-if="!isMobile">Edit</span>
            </button>
            <button
              @click="(e) => handleDeleteSession(session.id, e)"
              class="btn btn-xs btn-error"
              title="Delete Session"
            >
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'BrowserSessionList',
  data() {
    return {
      newSessionName: '',
      newSessionUrl: 'http://example.com',
      newSessionHeadless: false
    }
  },
  computed: {
    sessions() {
      return this.$storex.browsers.allSessions
    },
    selectedSessionId() {
      return this.$storex.browsers.selectedSessionId
    },
    isLoading() {
      return this.$storex.browsers.isLoading
    },
    showNewForm() {
      return this.$storex.browsers.showNewSessionForm
    },
    isMobile() {
      return this.$storex.ui.isMobile
    }
  },
  methods: {
    async mounted() {
      await this.$storex.browsers.loadSessions()
    },
    handleSelectSession(sessionId) {
      this.$storex.browsers.selectSession(sessionId)
    },
    async handleCreateSession() {
      if (!this.newSessionName.trim()) {
        this.$storex.ui.addNotification({
          text: 'Session name is required',
          type: 'warning'
        })
        return
      }

      try {
        await this.$storex.browsers.createSession({
          name: this.newSessionName.trim(),
          url: this.newSessionUrl || 'http://example.com',
          headless: this.newSessionHeadless
        })
        this.newSessionName = ''
        this.newSessionUrl = 'http://example.com'
        this.newSessionHeadless = false
      } catch (error) {
        console.error('Failed to create session:', error)
      }
    },
    async handleDeleteSession(sessionId, event) {
      event.stopPropagation()
      if (!confirm('Are you sure you want to delete this session?')) return

      try {
        await this.$storex.browsers.deleteSession(sessionId)
      } catch (error) {
        console.error('Failed to delete session:', error)
      }
    },
    async handleRunSession(sessionId, event) {
      event.stopPropagation()
      try {
        await this.$storex.browsers.runSession(sessionId)
      } catch (error) {
        console.error('Failed to run session:', error)
      }
    },
    toggleNewForm() {
      this.$storex.browsers.toggleNewSessionForm()
    },
    startEditingSession(sessionId) {
      this.$storex.browsers.startEditingSession(sessionId)
    }
  },
  inject: ['$storex'],
  mounted() {
    this.$storex.browsers.loadSessions()
  }
}
</script>