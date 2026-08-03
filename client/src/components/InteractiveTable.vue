<script setup>
import { nextTick } from 'vue'
</script>

<template>
  <div class="interactive-table-wrapper border border-base-300 rounded-lg overflow-hidden mb-4 bg-base-100">
    <!-- Toolbar -->
    <div class="flex flex-wrap gap-2 p-3 bg-base-200 border-b border-base-300">
      <button 
        @click="toggleEditMode" 
        class="btn btn-sm gap-1 text-xs"
        :class="isEditMode ? 'btn-primary' : 'btn-outline'"
        title="Toggle edition mode"
      >
        <i :class="isEditMode ? 'fa-solid fa-lock-open' : 'fa-solid fa-lock'"></i>
        {{ isEditMode ? 'Lock' : 'Edit' }}
      </button>

      <template v-if="isEditMode">
        <button 
          @click="addRow" 
          class="btn btn-sm btn-outline gap-1 text-xs"
          title="Add new row"
        >
          <i class="fa-solid fa-plus"></i> Row
        </button>
        <button 
          @click="addColumn" 
          class="btn btn-sm btn-outline gap-1 text-xs"
          title="Add new column"
        >
          <i class="fa-solid fa-plus"></i> Column
        </button>
        <button 
          @click="deleteSelected" 
          :disabled="!hasSelection"
          class="btn btn-sm btn-outline gap-1 text-xs disabled:opacity-50"
          title="Delete selected rows"
        >
          <i class="fa-solid fa-trash"></i> Delete
        </button>
        <button 
          @click="copySelected" 
          :disabled="!hasSelection"
          class="btn btn-sm btn-outline gap-1 text-xs disabled:opacity-50"
          title="Copy selected cells (Ctrl+C)"
        >
          <i class="fa-solid fa-copy"></i> Copy
        </button>
        <button 
          @click="pasteSelected" 
          :disabled="!clipboard"
          class="btn btn-sm btn-outline gap-1 text-xs disabled:opacity-50"
          title="Paste (Ctrl+V)"
        >
          <i class="fa-solid fa-paste"></i> Paste
        </button>
      </template>

      <div class="flex-1"></div>
      <span class="text-xs text-base-content opacity-60 self-center">
        {{ isEditMode ? `${selectedCells.size} cell(s) selected` : 'View mode' }}
      </span>
    </div>

    <!-- Table Container -->
    <div class="overflow-x-auto" @mouseup="endDragSelection">
      <table class="w-full border-collapse bg-base-100">
        <thead>
          <tr class="bg-base-300 border-b border-base-300">
            <!-- Select All Checkbox -->
            <th v-if="isEditMode" class="w-10 p-2 text-center sticky left-0 bg-base-300 border-r border-base-300">
              <input 
                type="checkbox" 
                @change="toggleSelectAll"
                :checked="allRowsSelected"
                class="cursor-pointer w-4 h-4"
              />
            </th>
            <!-- Header Cells -->
            <th 
              v-for="(header, colIdx) in headers" 
              :key="`header-${colIdx}`"
              class="p-2 text-left font-semibold text-sm border-r border-base-300 whitespace-nowrap bg-base-300"
              :class="{ 
                'cursor-pointer hover:bg-primary hover:bg-opacity-10 group relative': isEditMode,
                'bg-primary bg-opacity-20': isEditMode && selectedColumns.has(colIdx)
              }"
              @click="isEditMode && selectColumn(colIdx)"
            >
              <div class="flex items-center justify-between gap-2">
                <span>{{ header }}</span>
                <button 
                  v-if="isEditMode"
                  @click.stop="deleteColumn(colIdx)"
                  class="opacity-0 group-hover:opacity-100 text-base-content opacity-40 hover:text-error transition-opacity text-xs"
                  title="Delete column"
                >
                  <i class="fa-solid fa-times"></i>
                </button>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr 
            v-for="(row, rowIdx) in dataRows" 
            :key="`row-${rowIdx}`"
            class="border-b border-base-300"
            :class="{ 
              'hover:bg-base-200 transition-colors': isEditMode,
              'bg-primary bg-opacity-10': isEditMode && isRowSelected(rowIdx)
            }"
          >
            <!-- Row Checkbox -->
            <td v-if="isEditMode" class="w-10 p-2 text-center sticky left-0 bg-base-100 border-r border-base-300">
              <input 
                type="checkbox" 
                @change="toggleSelectRow(rowIdx)"
                :checked="selectedRows.has(rowIdx)"
                class="cursor-pointer w-4 h-4"
              />
            </td>

            <!-- Data Cells -->
            <td 
              v-for="(cell, colIdx) in row" 
              :key="`cell-${rowIdx}-${colIdx}`"
              class="p-2 border-r border-base-300 text-sm min-w-24"
              :class="{ 
                'group relative cursor-cell': isEditMode,
                'bg-primary bg-opacity-20 border-2 border-primary': isEditMode && isSelected(rowIdx, colIdx),
                'bg-base-100': !isEditMode || !isSelected(rowIdx, colIdx)
              }"
              @click="isEditMode && selectCell(rowIdx, colIdx, $event)"
              @dblclick="isEditMode && editCell(rowIdx, colIdx)"
              @mousedown="isEditMode && startDragSelection(rowIdx, colIdx, $event)"
              @mouseover="isEditMode && updateDragSelection(rowIdx, colIdx)"
            >
              <!-- Display Mode -->
              <div 
                v-if="!isEditing(rowIdx, colIdx)"
                class="truncate p-1 rounded"
                :class="{ 'group-hover:bg-base-300 transition-colors': isEditMode }"
              >
                {{ cell || '–' }}
              </div>

              <!-- Edit Mode -->
              <input 
                v-else
                v-model="dataRows[rowIdx][colIdx]"
                type="text"
                class="input input-sm input-bordered w-full"
                @keydown.enter="saveCell(rowIdx, colIdx)"
                @keydown.escape="cancelEdit"
                @blur="saveCell(rowIdx, colIdx)"
                @click.stop
                autofocus
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty State -->
    <div 
      v-if="dataRows.length === 0"
      class="p-8 text-center text-base-content opacity-50 bg-base-200"
    >
      <p class="text-sm">No data in table. Click "Edit" to get started.</p>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    initialData: {
      type: Array,
      required: true
    },
    tableIndex: {
      type: Number,
      required: true
    },
    useFirstRowAsHeader: {
      type: Boolean,
      default: true
    }
  },
  emits: ['update-table'],
  data() {
    return {
      tableData: [],
      headerRow: [],
      selectedRows: new Set(),
      selectedColumns: new Set(),
      selectedCells: new Set(),
      editingCell: null,
      clipboard: null,
      lastSelectedCell: null,
      isDragging: false,
      dragStart: null,
      dragEnd: null,
      isEditMode: true
    }
  },
  computed: {
    headers() {
      // Use first row as headers if option enabled and data exists
      if (this.useFirstRowAsHeader && this.headerRow.length > 0) {
        return this.headerRow
      }
      
      // Fallback to auto-generated headers
      if (!this.dataRows.length) return []
      const headerCount = this.dataRows[0].length
      return Array.from({ length: headerCount }, (_, idx) => {
        const letter = String.fromCharCode(65 + (idx % 26))
        const prefix = idx >= 26 ? Math.floor(idx / 26) : ''
        return `${prefix}${letter}`
      })
    },
    dataRows() {
      // Return all rows except first if using first row as header
      return this.useFirstRowAsHeader && this.tableData.length > 0 
        ? this.tableData.slice(1) 
        : this.tableData
    },
    hasSelection() {
      return this.selectedRows.size > 0 || this.selectedColumns.size > 0 || this.selectedCells.size > 0
    },
    allRowsSelected() {
      return this.dataRows.length > 0 && this.selectedRows.size === this.dataRows.length
    }
  },
  watch: {
    tableData: {
      handler(newData) {
        this.$emit('update-table', {
          index: this.tableIndex,
          data: JSON.parse(JSON.stringify(newData))
        })
      },
      deep: true
    }
  },
  mounted() {
    this.initializeData()
    document.addEventListener('keydown', this.handleKeyDown)
  },
  beforeUnmount() {
    document.removeEventListener('keydown', this.handleKeyDown)
  },
  methods: {
    initializeData() {
      this.tableData = JSON.parse(JSON.stringify(this.initialData))
      
      // Extract header row if option enabled
      if (this.useFirstRowAsHeader && this.tableData.length > 0) {
        this.headerRow = [...this.tableData[0]]
      }
    },
    toggleEditMode() {
      this.isEditMode = !this.isEditMode
      this.clearSelection()
    },
    clearSelection() {
      this.selectedRows.clear()
      this.selectedColumns.clear()
      this.selectedCells.clear()
      this.editingCell = null
    },
    getCellKey(rowIdx, colIdx) {
      return `${rowIdx},${colIdx}`
    },
    parseKey(key) {
      const [row, col] = key.split(',').map(Number)
      return { row, col }
    },
    isSelected(rowIdx, colIdx) {
      const key = this.getCellKey(rowIdx, colIdx)
      return this.selectedCells.has(key) || 
             this.selectedRows.has(rowIdx) || 
             this.selectedColumns.has(colIdx)
    },
    isRowSelected(rowIdx) {
      return this.selectedRows.has(rowIdx) || 
             Array.from(this.selectedCells).some(key => {
               const { row } = this.parseKey(key)
               return row === rowIdx
             })
    },
    isEditing(rowIdx, colIdx) {
      return this.editingCell === this.getCellKey(rowIdx, colIdx)
    },
    getRangeOfCells(startRow, startCol, endRow, endCol) {
      const cells = new Set()
      const minRow = Math.min(startRow, endRow)
      const maxRow = Math.max(startRow, endRow)
      const minCol = Math.min(startCol, endCol)
      const maxCol = Math.max(startCol, endCol)
      
      for (let r = minRow; r <= maxRow; r++) {
        for (let c = minCol; c <= maxCol; c++) {
          cells.add(this.getCellKey(r, c))
        }
      }
      return cells
    },
    startDragSelection(rowIdx, colIdx, event) {
      if (event.button !== 0) return
      if (this.isEditing(rowIdx, colIdx)) return
      
      this.isDragging = true
      this.dragStart = { row: rowIdx, col: colIdx }
      this.dragEnd = { row: rowIdx, col: colIdx }
      
      if (!event.ctrlKey && !event.metaKey && !event.shiftKey) {
        this.selectedCells.clear()
        this.selectedRows.clear()
        this.selectedColumns.clear()
      }
      
      const rangeCells = this.getRangeOfCells(rowIdx, colIdx, rowIdx, colIdx)
      rangeCells.forEach(cell => this.selectedCells.add(cell))
      this.lastSelectedCell = { row: rowIdx, col: colIdx }
    },
    updateDragSelection(rowIdx, colIdx) {
      if (!this.isDragging || !this.dragStart) return
      
      this.dragEnd = { row: rowIdx, col: colIdx }
      
      this.selectedCells.clear()
      const rangeCells = this.getRangeOfCells(
        this.dragStart.row, 
        this.dragStart.col, 
        this.dragEnd.row, 
        this.dragEnd.col
      )
      rangeCells.forEach(cell => this.selectedCells.add(cell))
    },
    endDragSelection() {
      this.isDragging = false
    },
    selectCell(rowIdx, colIdx, event) {
      if (this.isDragging) return
      
      const key = this.getCellKey(rowIdx, colIdx)
      
      if (event.shiftKey && this.lastSelectedCell) {
        this.selectedCells.clear()
        const rangeCells = this.getRangeOfCells(
          this.lastSelectedCell.row,
          this.lastSelectedCell.col,
          rowIdx,
          colIdx
        )
        rangeCells.forEach(cell => this.selectedCells.add(cell))
      } else if (event.ctrlKey || event.metaKey) {
        this.selectedCells.has(key) ? this.selectedCells.delete(key) : this.selectedCells.add(key)
      } else {
        this.selectedCells.clear()
        this.selectedRows.clear()
        this.selectedColumns.clear()
        this.selectedCells.add(key)
      }
      
      this.lastSelectedCell = { row: rowIdx, col: colIdx }
    },
    toggleSelectRow(rowIdx) {
      this.selectedRows.has(rowIdx) ? this.selectedRows.delete(rowIdx) : this.selectedRows.add(rowIdx)
      this.selectedColumns.clear()
      this.selectedCells.clear()
    },
    selectColumn(colIdx) {
      this.selectedColumns.clear()
      this.selectedRows.clear()
      this.selectedCells.clear()
      this.selectedColumns.add(colIdx)
    },
    toggleSelectAll() {
      if (this.allRowsSelected) {
        this.selectedRows.clear()
      } else {
        this.selectedRows.clear()
        for (let i = 0; i < this.dataRows.length; i++) {
          this.selectedRows.add(i)
        }
      }
      this.selectedColumns.clear()
      this.selectedCells.clear()
    },
    editCell(rowIdx, colIdx) {
      this.editingCell = this.getCellKey(rowIdx, colIdx)
    },
    saveCell(rowIdx, colIdx) {
      this.editingCell = null
    },
    cancelEdit() {
      this.editingCell = null
    },
    addRow() {
      const colCount = this.tableData[0]?.length || 3
      const newRow = new Array(colCount).fill('')
      this.tableData.push(newRow)
    },
    deleteRow(rowIdx) {
      // Adjust index for data rows (skip header if applicable)
      const dataRowIdx = this.useFirstRowAsHeader ? rowIdx + 1 : rowIdx
      this.tableData.splice(dataRowIdx, 1)
      this.selectedRows.delete(rowIdx)
    },
    addColumn() {
      this.tableData.forEach(row => row.push(''))
    },
    deleteColumn(colIdx) {
      this.tableData.forEach(row => row.splice(colIdx, 1))
      this.selectedColumns.delete(colIdx)
    },
    deleteSelected() {
      if (this.selectedRows.size === 0 && this.selectedCells.size === 0) return
      
      if (this.selectedRows.size > 0) {
        const rowsToDelete = Array.from(this.selectedRows)
          .sort((a, b) => b - a)
          .map(idx => this.useFirstRowAsHeader ? idx + 1 : idx)
        rowsToDelete.forEach(idx => this.tableData.splice(idx, 1))
        this.selectedRows.clear()
      } else if (this.selectedCells.size > 0) {
        this.selectedCells.forEach(key => {
          const { row, col } = this.parseKey(key)
          const dataRowIdx = this.useFirstRowAsHeader ? row + 1 : row
          this.tableData[dataRowIdx][col] = ''
        })
      }
      this.selectedCells.clear()
    },
    copySelected() {
      if (this.selectedRows.size > 0) {
        const rows = Array.from(this.selectedRows)
          .sort((a, b) => a - b)
          .map(idx => {
            const dataRowIdx = this.useFirstRowAsHeader ? idx + 1 : idx
            return this.tableData[dataRowIdx]
          })
        this.clipboard = { type: 'rows', data: rows }
        navigator.clipboard.writeText(rows.map(row => row.join('\t')).join('\n'))
      } else if (this.selectedCells.size > 0) {
        const cells = Array.from(this.selectedCells)
        const cellArray = cells.map(key => {
          const { row, col } = this.parseKey(key)
          const dataRowIdx = this.useFirstRowAsHeader ? row + 1 : row
          return { row, col, value: this.tableData[dataRowIdx][col] }
        })
        
        const rows = cellArray.map(c => c.row)
        const cols = cellArray.map(c => c.col)
        const minRow = Math.min(...rows)
        const maxRow = Math.max(...rows)
        const minCol = Math.min(...cols)
        const maxCol = Math.max(...cols)
        
        const grid = []
        for (let r = minRow; r <= maxRow; r++) {
          const row = []
          for (let c = minCol; c <= maxCol; c++) {
            const cell = cellArray.find(ch => ch.row === r && ch.col === c)
            row.push(cell ? cell.value : '')
          }
          grid.push(row)
        }
        
        this.clipboard = { 
          type: 'cells', 
          data: grid,
          bounds: { minRow, maxRow, minCol, maxCol }
        }
        navigator.clipboard.writeText(grid.map(row => row.join('\t')).join('\n'))
      }
    },
    pasteSelected() {
      if (!this.clipboard || !this.lastSelectedCell) return
      
      const { row: startRow, col: startCol } = this.lastSelectedCell
      const dataStartRow = this.useFirstRowAsHeader ? startRow + 1 : startRow
      
      if (this.clipboard.type === 'rows') {
        this.clipboard.data.forEach((rowData, idx) => {
          if (dataStartRow + idx < this.tableData.length) {
            this.tableData[dataStartRow + idx] = [...rowData]
          }
        })
      } else if (this.clipboard.type === 'cells') {
        this.clipboard.data.forEach((rowData, rIdx) => {
          rowData.forEach((cellValue, cIdx) => {
            const targetRow = dataStartRow + rIdx
            const targetCol = startCol + cIdx
            if (targetRow < this.tableData.length && targetCol < this.tableData[0].length) {
              this.tableData[targetRow][targetCol] = cellValue
            }
          })
        })
      }
    },
    handleKeyDown(e) {
      if (!this.isEditMode) return
      
      if (e.ctrlKey || e.metaKey) {
        if (e.key === 'c' || e.key === 'C') {
          e.preventDefault()
          this.copySelected()
        } else if (e.key === 'v' || e.key === 'V') {
          e.preventDefault()
          this.pasteSelected()
        }
      }
    }
  }
}
</script>