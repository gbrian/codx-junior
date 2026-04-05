<script setup>
</script>

<template>
  <div>
    <h2 class="font-bold text-3xl">{{ board ? 'Edit Board' : 'Add New Board' }}</h2>
    <div class="collapse bg-contain" :style="`background-image:url('${newBoardBackground}')`">
      <input type="radio" name="newboard" v-model="newBoardType" value="manual" />
      <div class="hidden collapse-title text-xl font-medium"><i class="fa-solid fa-gear"></i> Manual settings</div>
      <div class="collapse-content">
        <label class="form-control w-full mt-2">
          <div class="label">
            <span class="label-text font-semibold">Board Name</span>
            <span class="label-text-alt text-error" v-if="isBoardNameTaken">Name already taken</span>
          </div>
          <input type="text" v-model="newBoardName" placeholder="Enter board name" class="input input-bordered w-full" />
        </label>

        <label class="form-control w-full mt-2">
          <div class="label">
            <span class="label-text font-semibold">Description</span>
            <span class="label-text-alt text-base-content/50">Optional</span>
          </div>
          <input type="text" v-model="newBoardDescription" placeholder="Enter board description" class="input input-bordered w-full" />
        </label>

        <label class="form-control w-full mt-2">
          <div class="label">
            <span class="label-text font-semibold">Background Image</span>
            <span class="label-text-alt text-base-content/50">URL</span>
          </div>
          <input type="text" v-model="newBoardBackground" placeholder="Enter board background image URL" class="input input-bordered w-full" />
        </label>

        <label class="form-control w-full mt-2">
          <div class="label">
            <span class="label-text font-semibold">Parent Board</span>
            <span class="label-text-alt text-base-content/50">Optional</span>
          </div>
          <select v-model="newBoardParent" class="select select-bordered w-full">
            <option value="">-- none --</option>
            <option v-for="b in boards" :key="b.id" :value="b.id">{{ b.title }}</option>
          </select>
        </label>

      </div>
    </div>
    <div class="modal-action flex gap-2">
      <button class="btn btn-error" @click="onDeleteBoard">Delete</button>
      <div class="grow"></div>
      <button class="btn" @click="addOrUpdateBoard" :disabled="isBoardNameTaken || !newBoardName">Save</button>
    </div>
  </div>
</template>

<script>
export default {
  props: ['board', 'boards'],
  data() {
    return {
      newBoardType: 'manual',
      newBoardName: this.board?.title || '',
      newBoardDescription: this.board?.description || '',
      newBoardBackground: this.board?.background || '',
      newBoardParent: this.board?.parent_id || null
    }
  },
  computed: {
    // Check if name is taken by another board (not the one being edited)
    isBoardNameTaken() {
      return (
        this.newBoardName &&
        this.newBoardName !== this.board?.title &&
        !!this.$storex.projects.kanban.boards[this.newBoardName]
      )
    }
  },
  methods: {
    addOrUpdateBoard() {
      const boardName = this.newBoardName.trim()
      if (!boardName) return

      // Build updated or new board object without mutating prop
      const existing = this.board
        ? { ...this.$storex.projects.kanban.boards[this.board.title] }
        : { title: boardName, columns: [], id: boardName }

      const updatedBoard = {
        ...existing,
        title: boardName,
        description: this.newBoardDescription?.trim(),
        background: this.newBoardBackground?.trim(),
        parent_id: this.newBoardParent
      }

      // Remove old key if title changed
      if (this.board && this.board.title !== boardName) {
        delete this.$storex.projects.kanban.boards[this.board.title]
      }

      this.$storex.projects.kanban.boards[boardName] = updatedBoard
      this.$storex.projects.saveKanban()
      this.showBoardModal = false
    },

    onDeleteBoard() {
      if (!this.board?.title) return
      delete this.$storex.projects.kanban.boards[this.board.title]
      this.$storex.projects.saveKanban()
      this.showBoardModal = false
    }
  }
}
</script>