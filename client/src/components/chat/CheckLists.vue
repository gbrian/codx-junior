<template>
  <div class="flex gap-2 items-center">
    <div v-for="checkList in checkLists" :key="checkList.title"
      class="badge flex gap-2"
      @click.stop="onEditChecklist(checkList)">
      <div>{{ checkList.title }}</div>
      <div>
        {{ checkList.items.filter(item => item.checked).length }}/{{ checkList.items.length }}
        <i class="fa-regular fa-square-check"></i>
      </div>
      <div class="flex gap-1 items-center" v-if="checkList.items.find(i => i.time)">
        {{ checkList.items.reduce((a, b) => a + parseInt((b.time || 0)), 0) }}
        <i class="fa-solid fa-user-clock"></i>
      </div>
    </div>
    <button class="btn btn-xs" @click.stop="onEditChecklist()">
      <i class="fa-solid fa-plus"></i> List
    </button>
    <modal close="true" @close="onCloseEdit" 
      @paste="onPaste"
      v-if="editChecklist">
      <div class="flex flex-col gap-2">
        <input type="text" v-model="editChecklist.title" class="input input-bordered mb-2" placeholder="Edit Checklist Title"/>
        <div v-for="(item, index) in editChecklist.items" :key="index" class="flex items-center gap-2 mb-2">
          <input type="checkbox" v-model="item.checked" class="checkbox"/>
          <input type="text" v-model="item.title" class="input input-sm input-bordered" placeholder="Edit Item"/>
          <div class="input input-sm input-bordered flex items-center gap-1 w-20">
            <input type="text" class="w-10" v-model="item.time" placeholder="Time"/>
            <i class="fa-solid fa-user-clock"></i>
          </div>
          <div class="grow"></div>
          <button @click.stop="removeItem(index)" class="btn btn-sm btn-error">
            <i class="fa-solid fa-trash-can"></i>
          </button>
        </div>
        <button @click.stop="addItem" class="btn btn-sm btn-primary mb-2">Add Item</button>
        <div class="flex gap-2 justify-end">
          <button @click.stop="onPaste" class="btn">
            <i class="fa-solid fa-paste"></i>
          </button>
          <button @click.stop="discardChanges" class="btn btn-secondary" v-if="selectedChecklist">Discard</button>
          <button @click.stop="saveChecklist" class="btn btn-primary" :disabled="!canSave">Save</button>
        </div>
      </div>
    </modal>
  </div>
</template>

<script>
export default {
  props: ['chat'],
  data() {
    return {
      selectedChecklist: null,
      editChecklist: null
    }
  },
  computed: {
    canSave() {
      if (!this.editChecklist.title) {
        return false
      }
      return true
    },
    checkLists() {
      return this.chat.check_lists
    }
  },
  methods: {
    onEditChecklist(checkList) {
      this.selectedChecklist = checkList
      this.discardChanges()
    },
    addItem() {
      if (this.editChecklist) {
        this.editChecklist.items.push({ title: "", checked: false })
      }
    },
    removeItem(index) {
      if (this.editChecklist) {
        this.editChecklist.items.splice(index, 1)
      }
    },
    saveChecklist() {
      if (this.selectedChecklist) {
        Object.assign(this.selectedChecklist, this.editChecklist)
      } else {
        this.chat.check_lists = [...this.chat.check_lists, this.editChecklist] 
      }
      this.$emit('change', this.selectedChecklist)
      this.onCloseEdit()
    },
    discardChanges() {
      this.editChecklist = this.selectedChecklist ?  
                              { ...this.selectedChecklist,
                                items: [...this.selectedChecklist.items]
                               } : 
                              {
                                title: "",
                                items: []
                              }
    },
    onCloseEdit() {
      this.selectedChecklist = null
      this.editChecklist = null
    },
    async onPaste() {
      const pasteText = await this.$ui.readClipboardText();
      const lines = pasteText.split('\n')
      lines.forEach(line => {
        if (this.editChecklist) {
          this.editChecklist.items.push({ title: line, checked: false })
        }
      })
    }
  }
}
</script>