<script setup>
import ProjectDetailt from '../ProjectDetailt.vue'
</script>

<template>
  <div class="w-full">
    <h2 class="font-bold text-3xl mb-6">
      {{ isEditing ? 'Edit Board' : 'Add New Board' }}
    </h2>

    <div class="space-y-4">
      <!-- Board name input -->
      <div class="form-control">
        <label class="label">
          <span class="label-text font-semibold">Board Name</span>
          <span class="label-text-alt text-error" v-if="isBoardNameTaken">
            Name already taken
          </span>
        </label>
        <input 
          type="text" 
          v-model="formData.title" 
          placeholder="Enter board name" 
          class="input input-bordered w-full"
          :class="{ 'input-error': isBoardNameTaken }"
        />
      </div>

      <!-- Board description -->
      <div class="form-control">
        <label class="label">
          <span class="label-text font-semibold">Description</span>
          <span class="label-text-alt text-base-content/50">Optional</span>
        </label>
        <textarea 
          v-model="formData.description" 
          placeholder="Enter board description" 
          class="textarea textarea-bordered w-full"
          rows="3"
        ></textarea>
      </div>

      <!-- Background image URL -->
      <div class="form-control">
        <label class="label">
          <span class="label-text font-semibold">Background Image URL</span>
          <span class="label-text-alt text-base-content/50">Optional</span>
        </label>
        <input 
          type="text" 
          v-model="formData.background" 
          placeholder="https://example.com/image.jpg" 
          class="input input-bordered w-full"
        />
        <div 
          v-if="formData.background" 
          class="mt-3 h-24 rounded bg-cover bg-center opacity-60"
          :style="{ backgroundImage: `url(${formData.background})` }"
        ></div>
      </div>

      <!-- Parent board selector -->
      <div class="form-control">
        <label class="label">
          <span class="label-text font-semibold">Parent Board</span>
          <span class="label-text-alt text-base-content/50">Optional</span>
        </label>
        <select v-model="formData.parent_id" class="select select-bordered w-full">
          <option :value="null">-- None --</option>
          <option v-for="b in parentBoardOptions" :key="b.title" :value="b.title">
            {{ b.title }}
          </option>
        </select>
        <div v-if="!isEditing && formData.parent_id" class="label-text-alt text-base-content/50 mt-1">
          <i class="fa-solid fa-info-circle"></i> This board will be a child of {{ formData.parent_id }}
        </div>
      </div>

      <!-- Project selector -->
      <div class="form-control">
        <label class="label">
          <span class="label-text font-semibold">Project</span>
          <span class="label-text-alt text-base-content/50">Optional</span>
        </label>
        <ProjectDetailt 
          v-model="formData.project_id" 
          :options="{ showFolders: false, showIcon: true, showSelector: true }"
        />
      </div>
    </div>

    <!-- Delete confirmation warning -->
    <div 
      v-if="confirmDelete" 
      class="mt-6 p-4 bg-error/10 border border-error rounded-lg flex items-center gap-3"
    >
      <i class="fa-solid fa-triangle-exclamation text-error text-xl"></i>
      <div class="flex-1">
        <p class="font-semibold text-error">Delete this board?</p>
        <p class="text-sm text-error/80">This action cannot be undone. All tasks in this board will be deleted.</p>
      </div>
      <button 
        class="btn btn-sm btn-ghost"
        @click="confirmDelete = false"
      >
        Cancel
      </button>
    </div>

    <!-- Action buttons -->
    <div class="modal-action mt-6 flex gap-2">
      <button 
        class="btn btn-error" 
        @click="onDeleteClick" 
        v-if="isEditing"
        :disabled="confirmDelete"
      >
        <span v-if="!confirmDelete">
          <i class="fa-solid fa-trash"></i> Delete
        </span>
        <span v-else>
          <i class="fa-solid fa-exclamation"></i> Confirm Delete?
        </span>
      </button>
      <div class="grow"></div>
      <button 
        class="btn btn-ghost" 
        @click="$emit('cancel')"
      >
        Cancel
      </button>
      <button 
        class="btn btn-primary" 
        @click="saveBoard"
        :disabled="!formData.title?.trim() || isBoardNameTaken"
      >
        <i class="fa-solid fa-save"></i> Save
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    board: {
      type: Object,
      default: null
    },
    boards: {
      type: Array,
      default: () => []
    },
    currentBoardId: {
      type: String,
      default: null
    }
  },
  data() {
    return {
      formData: {
        title: '',
        description: '',
        background: '',
        parent_id: null,
        project_id: null
      },
      originalTitle: null,
      confirmDelete: false
    }
  },
  computed: {
    isEditing() {
      return !!this.board?.title
    },
    isBoardNameTaken() {
      const title = this.formData.title?.trim()
      if (!title || title === this.originalTitle) return false
      return this.boards.some(b => b.title === title)
    },
    parentBoardOptions() {
      // Filter out current board from parent options - use title as identifier
      return this.boards.filter(b => b.title !== this.board?.title)
    }
  },
  watch: {
    board: {
      handler(newBoard) {
        if (newBoard?.title) {
          // Editing existing board
          this.formData = {
            title: newBoard.title || '',
            description: newBoard.description || '',
            background: newBoard.background || '',
            parent_id: newBoard.parent_id || null,
            project_id: newBoard.project_id || null
          }
          this.originalTitle = newBoard.title
        } else {
          // Creating new board - initialize with current board as parent
          this.resetForm()
          if (this.currentBoardId && !this.isEditing) {
            this.formData.parent_id = this.currentBoardId
          }
        }
        this.confirmDelete = false
      },
      deep: true,
      immediate: true
    }
  },
  methods: {
    saveBoard() {
      const title = this.formData.title?.trim()
      if (!title || this.isBoardNameTaken) return

      this.$emit('save', {
        originalTitle: this.originalTitle,
        board: {
          ...this.formData,
          title,
          description: this.formData.description?.trim() || '',
          background: this.formData.background?.trim() || ''
        }
      })
    },
    onDeleteClick() {
      if (!this.confirmDelete) {
        this.confirmDelete = true
        return
      }
      this.$emit('delete', this.board)
      this.resetForm()
    },
    resetForm() {
      this.formData = {
        title: '',
        description: '',
        background: '',
        parent_id: null,
        project_id: null
      }
      this.originalTitle = null
      this.confirmDelete = false
    }
  }
}
</script>