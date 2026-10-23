<script setup>
import { ref, computed, watch } from 'vue'
</script>

<template>
  <div class="flex flex-col h-full bg-base-100">
    <!-- Empty State -->
    <div v-if="!selectedSession && !isEditing" class="flex items-center justify-center h-full text-base-content/50">
      <div class="text-center">
        <i class="fa-solid fa-browser text-4xl mb-3 block opacity-25"></i>
        <p class="text-sm">Select a session to view details</p>
      </div>
    </div>

    <!-- View Mode -->
    <div v-else-if="!isEditing" class="flex flex-col h-full overflow-y-auto">
      <!-- Header -->
      <div class="sticky top-0 bg-base-100 border-b border-base-content/10 p-4 space-y-3 flex-shrink-0">
        <div class="flex items-center justify-between gap-2">
          <h3 class="text-lg font-bold truncate">{{ selectedSession.name }}</h3>
          <span
            v-if="selectedSession.status"
            class="badge"
            :class="[
              selectedSession.status === 'running'
                ? 'badge-success'
                : selectedSession.status === 'stopped'
                ? 'badge-warning'
                : 'badge-ghost'
            ]"
          >
            {{ selectedSession.status }}
          </span>
        </div>

        <!-- Action Buttons -->
        <div class="flex gap-2">
          <button
            @click="handleRunSession"
            class="btn btn-success flex-1"
          >
            <i class="fa-solid fa-play"></i>
            Run Session
          </button>
          <button
            @click="startEditingSession"
            class="btn btn-info"
          >
            <i class="fa-solid fa-gear"></i>
            <span v-if="!isMobile">Edit</span>
          </button>
        </div>
      </div>

      <!-- Session Details -->
      <div class="p-4 space-y-4 flex-1">
        <!-- URL -->
        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">URL</span>
          </label>
          <p class="text-sm break-all text-base-content/75">{{ selectedSession.url }}</p>
        </div>

        <!-- Created Date -->
        <div v-if="selectedSession.created_at" class="form-control">
          <label class="label">
            <span class="label-text font-semibold">Created</span>
          </label>
          <p class="text-sm text-base-content/75">
            {{ new Date(selectedSession.created_at).toLocaleString() }}
          </p>
        </div>

        <!-- Profile -->
        <div v-if="selectedSession.profile" class="form-control">
          <label class="label">
            <span class="label-text font-semibold">Profile</span>
          </label>
          <p class="text-sm text-base-content/75">{{ selectedSession.profile }}</p>
        </div>

        <!-- Resolution -->
        <div v-if="selectedSession.resolution" class="form-control">
          <label class="label">
            <span class="label-text font-semibold">Resolution</span>
          </label>
          <p class="text-sm text-base-content/75">{{ selectedSession.resolution }}</p>
        </div>

        <!-- Headless Mode -->
        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">Headless Mode</span>
          </label>
          <p class="text-sm text-base-content/75">
            <i :class="selectedSession.headless ? 'fa-solid fa-check text-success' : 'fa-solid fa-times text-error'"></i>
            {{ selectedSession.headless ? 'Enabled' : 'Disabled' }}
          </p>
        </div>
      </div>
    </div>

    <!-- Edit Mode -->
    <div v-else class="flex flex-col h-full overflow-y-auto">
      <!-- Header -->
      <div class="sticky top-0 bg-base-100 border-b border-base-content/10 p-4 flex-shrink-0">
        <h3 class="text-lg font-bold">Edit Session</h3>
      </div>

      <!-- Edit Form -->
      <div class="p-4 space-y-4 flex-1">
        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">Session Name *</span>
          </label>
          <input
            v-model="editFormData.name"
            type="text"
            placeholder="Session name"
            class="input input-bordered"
          />
        </div>

        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">URL</span>
          </label>
          <input
            v-model="editFormData.url"
            type="url"
            placeholder="http://example.com"
            class="input input-bordered"
          />
        </div>

        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">Profile</span>
          </label>
          <input
            v-model="editFormData.profile"
            type="text"
            placeholder="default"
            class="input input-bordered"
          />
        </div>

        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">Resolution</span>
          </label>
          <input
            v-model="editFormData.resolution"
            type="text"
            placeholder="1920x1080"
            class="input input-bordered"
          />
        </div>

        <div class="form-control">
          <label class="label cursor-pointer">
            <input
              v-model="editFormData.headless"
              type="checkbox"
              class="checkbox"
            />
            <span class="label-text ml-3 font-semibold">Headless Mode</span>
          </label>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="border-t border-base-content/10 p-4 flex gap-2 flex-shrink-0">
        <button
          @click="handleSaveSession"
          class="btn btn-success flex-1"
          :disabled="saving"
        >
          <span v-if="saving" class="loading loading-spinner loading-sm"></span>
          <i v-else class="fa-solid fa-save"></i>
          Save
        </button>
        <button
          @click="handleCancelEdit"
          class="btn btn-ghost flex-1"
          :disabled="saving"
        >
          Cancel
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'BrowserSessionPanel',
  data() {
    return {
      editFormData: {},
      saving: false
    }
  },
  computed: {
    selectedSession() {
      return this.$storex.browsers.selectedSession
    },
    editingSessionId() {
      return this.$storex.browsers.editingSessionId
    },
    isEditing() {
      return this.editingSessionId !== null
    },
    isMobile() {
      return this.$storex.ui.isMobile
    }
  },
  watch: {
    editingSessionId(newId) {
      if (newId) {
        const session = this.$storex.browsers.sessionById(newId)
        if (session) {
          this.editFormData = { ...session }
        }
      } else {
        this.editFormData = {}
      }
    }
  },
  methods: {
    async handleSaveSession() {
      if (!this.editFormData.name?.trim()) {
        this.$storex.ui.addNotification({
          text: 'Session name is required',
          type: 'warning'
        })
        return
      }

      this.saving = true
      try {
        await this.$storex.browsers.updateSession(this.editFormData)
      } catch (error) {
        console.error('Failed to save session:', error)
      } finally {
        this.saving = false
      }
    },
    handleCancelEdit() {
      this.$storex.browsers.stopEditingSession()
      this.editFormData = {}
    },
    async handleRunSession() {
      if (this.selectedSession?.id) {
        try {
          await this.$storex.browsers.runSession(this.selectedSession.id)
        } catch (error) {
          console.error('Failed to run session:', error)
        }
      }
    },
    startEditingSession() {
      this.$storex.browsers.startEditingSession(this.selectedSession.id)
    }
  },
  inject: ['$storex']
}
</script>