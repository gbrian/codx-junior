<script setup>
import KanbanBoardSidebar from './KanbanBoardSidebar.vue'
import SprintBoardCanvas from './SprintBoardCanvas.vue'
import SprintBoardGantt from './SprintBoardGantt.vue'
import SprintBoardModals from './SprintBoardModals.vue'
import KanbanList from '../KanbanList.vue'
import PlanningView from './PlanningView.vue'
import FollowupView from './FollowupView.vue'
import TaskTableView from './TaskTableView.vue'
import BoardAssistantChat from './BoardAssistantChat.vue'
import BoardTransferModal from './BoardTransferModal.vue'
import VerticalSplitter from '@/components/layout/VerticalSplitter.vue'
import ChatView from '@/views/ChatView.vue'
import ChatIcon from '@/components/chat/ChatIcon.vue'
</script>

<template>
  <div class="kanban-board-view flex flex-col h-full overflow-hidden relative">

    <!-- Board list overlay (available from kanban and sprint views) -->
    <transition name="fade-slide">
      <div
        v-if="showBoardList"
        class="absolute inset-0 z-40 bg-base-100 flex flex-col overflow-hidden"
      >
        <!-- Back bar -->
        <div class="shrink-0 flex items-center gap-3 px-4 py-3 border-b border-base-100 bg-base-200">
          <button
            @click="showBoardList = false"
            class="btn btn-ghost btn-sm gap-1.5 text-base-content/60"
          >
            <i class="fa-solid fa-arrow-left text-xs"></i>
            <span class="text-xs">Back to board</span>
          </button>
          <span class="text-xs font-semibold text-base-content/40 uppercase tracking-wide">
            All Boards
          </span>
        </div>

        <!-- KanbanList -->
        <div class="flex-1 overflow-auto p-4">
          <KanbanList
            @select="onSelectBoardFromList"
            @new-board="openNewBoardModal"
            @bookmark="onBookmark"
          />
        </div>
      </div>
    </transition>

    <!-- ── Board toolbar (kanban & sprint) ── -->
    <!--
      One toolbar for both board flavours. The two implementations were merged
      instead of duplicated: the identity block, the view switcher, the search
      field and the board/column actions all address the same board, so they are
      rendered once and only the affordances that differ are conditional:
        • sprint boards switch boards through a dropdown (kanban boards use the
          sidebar + board list),
        • sprint boards own a stats toggle (kanban boards have no sprint stats),
        • "Add existing" only exists where sprint membership exists.
    -->
    <div
      class="shrink-0 flex flex-wrap items-center gap-1.5 px-3 py-2 border-b border-base-100 bg-base-200 z-20"
    >
      <!-- Board identity: sprint dropdown -->
      <div v-if="isSprintBoard" class="dropdown">
        <button
          tabindex="0"
          role="button"
          class="btn btn-sm btn-ghost gap-2"
          :title="isVirtualBoard ? 'No board chats' : 'Switch sprint'"
        >
          <i :class="['fa-solid text-xs', isVirtualBoard ? 'fa-inbox text-warning' : 'fa-calendar-days text-primary']"></i>
          <span class="font-medium text-sm truncate max-w-[16rem]">{{ activeBoardTitle }}</span>
          <span v-if="isVirtualBoard" class="badge badge-xs badge-warning badge-outline gap-1">
            <i class="fa-solid fa-inbox text-[8px]"></i> no board
          </span>
          <span v-else class="badge badge-xs badge-primary badge-outline gap-1">
            <i class="fa-solid fa-layer-group text-[8px]"></i> sprint
          </span>
          <i class="fa-solid fa-chevron-down text-xs opacity-60"></i>
        </button>
        <ul
          tabindex="0"
          class="dropdown-content menu bg-base-200 border border-base-100 rounded-box z-40 w-72 p-1 mt-1 shadow-lg"
        >
          <li class="menu-title text-xs opacity-50">Sprint boards</li>
          <li v-for="b in sprintBoards" :key="b.id">
            <a
              class="flex items-center gap-2"
              :class="activeBoard?.id === b.id ? 'active' : ''"
              @click="onSelectSprint(b.id)"
            >
              <i :class="['fa-solid fa-calendar-days text-xs', activeBoard?.id === b.id ? 'text-primary' : 'opacity-40']"></i>
              <span class="text-sm truncate">{{ b.title }}</span>
            </a>
          </li>
          <li v-if="!sprintBoards.length" class="menu-title text-xs opacity-40">No sprints yet</li>
        </ul>
      </div>

      <!-- Board identity: kanban title + counters -->
      <div v-else class="flex flex-col min-w-0">
        <span class="font-semibold text-sm text-base-content truncate">
          {{ activeBoard?.title || 'Select a board' }}
        </span>
        <span class="text-xs text-base-content/40">
          {{ activeColumns.length }} columns · {{ sidebarTasks.length }} tasks
        </span>
      </div>

      <!-- Virtual board: read-only catch-all hint instead of create actions -->
      <span v-if="isVirtualBoard" class="badge badge-sm badge-ghost gap-1.5 text-base-content/50">
        <i class="fa-solid fa-inbox text-xs"></i>
        chats without a board
      </span>

      <!-- Browse all boards (kanban & sprint) -->
      <button
        class="btn btn-ghost btn-xs gap-1.5 text-base-content/40 hover:text-primary"
        title="Browse all boards"
        aria-label="Browse all boards"
        @click="showBoardList = true"
      >
        <i class="fa-solid fa-table-list text-xs"></i>
        <span class="hidden sm:inline text-xs">All boards</span>
      </button>

      <!-- Sprint stats (hidden by default) -->
      <button
        v-if="isSprintBoard"
        class="btn btn-ghost btn-xs gap-1.5"
        :class="showStats ? 'text-primary' : 'text-base-content/40 hover:text-primary'"
        :aria-pressed="showStats"
        title="Toggle sprint stats"
        @click="showStats = !showStats"
      >
        <i class="fa-solid fa-chart-simple text-xs"></i>
        <span class="hidden sm:inline text-xs">Stats</span>
      </button>

      <div class="grow"></div>

      <!-- View switcher (board / table / gantt / planning / follow-up) -->
      <div class="join">
        <button
          v-for="tab in viewTabs"
          :key="tab.id"
          class="btn btn-xs join-item gap-1.5"
          :class="activeView === tab.id ? 'btn-primary' : 'btn-ghost text-base-content/40'"
          :aria-pressed="activeView === tab.id"
          :title="tab.title || tab.label"
          @click="activeView = tab.id"
        >
          <i :class="tab.icon" class="text-xs"></i>
          <span class="hidden sm:inline text-xs">{{ tab.label }}</span>
          <span
            v-if="tab.count != null"
            class="badge badge-xs"
            :class="activeView === tab.id ? 'badge-primary' : 'badge-ghost text-base-content/40'"
          >{{ tab.count }}</span>
        </button>
      </div>

      <!-- Search (the table view brings its own, richer search) -->
      <label v-if="activeView !== 'table'" class="input input-sm input-bordered flex items-center gap-2 w-44">
        <i class="fa-solid fa-magnifying-glass text-xs text-base-content/40"></i>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search tasks…"
          class="grow bg-transparent outline-none text-xs min-w-0"
        />
        <button v-if="searchQuery" class="btn btn-ghost btn-xs btn-circle" @click="searchQuery = ''">
          <i class="fa-solid fa-xmark text-xs"></i>
        </button>
      </label>

      <div class="w-px self-stretch bg-base-100 my-1"></div>

      <!-- Column management -->
      <button
        v-if="!isVirtualBoard"
        class="btn btn-ghost btn-xs gap-1.5 text-base-content/40 hover:text-primary"
        title="Add column"
        aria-label="Add column"
        @click="openNewColumn"
      >
        <i class="fa-solid fa-table-columns text-xs"></i>
        <span class="hidden sm:inline text-xs">New column</span>
      </button>

      <!-- Export / import this board (with all tasks) -->
      <button
        v-if="!isVirtualBoard"
        class="btn btn-ghost btn-xs gap-1.5 text-base-content/40 hover:text-primary"
        title="Export or import board"
        aria-label="Export or import board"
        @click="showTransfer = true"
      >
        <i class="fa-solid fa-right-left text-xs"></i>
        <span class="hidden sm:inline text-xs">Transfer</span>
      </button>

      <!-- Board settings: name, description, background, assistant & participants -->
      <button
        v-if="!isVirtualBoard"
        class="btn btn-ghost btn-xs gap-1.5 text-base-content/40 hover:text-primary"
        title="Board settings"
        aria-label="Board settings"
        @click="openEditBoardModal"
      >
        <i class="fa-solid fa-gear text-xs"></i>
        <span class="hidden sm:inline text-xs">Board</span>
      </button>

      <!-- New board (kanban) / new sprint (sprint board) -->
      <button
        v-if="!isVirtualBoard"
        class="btn btn-ghost btn-xs gap-1.5 text-base-content/40 hover:text-primary"
        :title="isSprintBoard ? 'New sprint' : 'New board'"
        @click="openNewBoardModal"
      >
        <i class="fa-solid fa-plus text-xs"></i>
        <span class="hidden sm:inline text-xs">{{ isSprintBoard ? 'New sprint' : 'New board' }}</span>
      </button>

      <!-- Add existing (sprint membership) -->
      <button
        v-if="isSprintBoard && !isVirtualBoard"
        class="btn btn-sm btn-ghost border border-base-100 gap-1.5"
        @click="openAddExisting"
      >
        <i class="fa-solid fa-folder-plus text-xs"></i>
        <span class="text-xs font-medium">Add existing</span>
      </button>

      <!-- New task (starts in the first column) -->
      <button
        v-if="!isVirtualBoard"
        class="btn btn-primary btn-sm gap-1.5"
        @click="openNewTask({})"
      >
        <i class="fa-solid fa-plus text-xs"></i>
        <span class="hidden sm:inline text-xs font-medium">New Task</span>
      </button>

      <!-- Board assistant: chat with the profile assigned to the board (board
           settings → Board assistant) or with ProjectManager by default. The
           conversations are created ON the board — as a card in its first
           column — so they can be continued from the board itself. -->
      <BoardAssistantChat
        v-if="activeBoardId"
        :boardId="activeBoardId"
        :boardType="boardModalsType"
        :boardName="activeBoard?.title"
        :columns="columns"
        :project="project || $projects.activeProject"
        :readOnly="isVirtualBoard"
        @open-chat="onSelectTask"
        @created="onAssistantChatCreated"
        @edit-board="openEditBoardModal"
      />
    </div>

    <!-- ── Sprint progress + total cost ── -->
    <div v-if="isSprintBoard" class="shrink-0 flex items-center gap-3 px-4 py-2 border-b border-base-100">
      <progress class="progress progress-primary h-1.5 w-full max-w-md" :value="progress" max="100"></progress>
      <span class="text-xs text-base-content/40 shrink-0">{{ progress }}% done</span>

      <!-- Total cost of the sprint (sum of every column) -->
      <span
        class="ml-auto flex items-center gap-1 text-xs font-semibold shrink-0 tabular-nums tooltip tooltip-bottom"
        :class="totalCost > 0 ? 'text-amber-400' : 'text-base-content/30'"
        :data-tip="costTooltip"
      >
        <i class="fa-solid fa-coins text-xs"></i>
        {{ formatCoins(totalCost) }}
        <span v-if="totalBudget > 0" class="opacity-60 font-normal">/ {{ formatCoins(totalBudget) }}</span>
      </span>
    </div>

    <!-- ── Sprint stats panel (hidden by default; toggle in the toolbar) ── -->
    <div
      v-if="isSprintBoard && showStats"
      class="shrink-0 flex flex-wrap items-stretch gap-3 px-4 py-3 border-b border-base-100 bg-base-200/30"
    >
      <!-- Total days (oldest → newest task) -->
      <div class="flex flex-col justify-center rounded-lg bg-base-200 border border-base-100 px-4 py-2.5 min-w-[8.5rem]">
        <span class="text-[10px] uppercase tracking-wider text-base-content/40 flex items-center gap-1.5">
          <i class="fa-solid fa-calendar-day text-primary text-xs"></i> Duration
        </span>
        <div class="flex items-baseline gap-1 mt-1">
          <span class="text-2xl font-bold tabular-nums leading-none">{{ totalDays }}</span>
          <span class="text-xs text-base-content/40">{{ totalDays === 1 ? 'day' : 'days' }}</span>
        </div>
        <span class="text-[10px] text-base-content/40 mt-1" :title="createdRangeTooltip">{{ createdRangeLabel }}</span>
      </div>

      <!-- Average ticket cost -->
      <div class="flex flex-col justify-center rounded-lg bg-base-200 border border-base-100 px-4 py-2.5 min-w-[8.5rem]">
        <span class="text-[10px] uppercase tracking-wider text-base-content/40 flex items-center gap-1.5">
          <i class="fa-solid fa-coins text-amber-400 text-xs"></i> Avg ticket
        </span>
        <div class="flex items-baseline gap-1 mt-1">
          <span
            class="text-2xl font-bold tabular-nums leading-none"
            :class="averageCost > 0 ? 'text-amber-400' : 'text-base-content/30'"
          >
            {{ formatCoins(averageCost) }}
          </span>
          <span class="text-xs text-base-content/40">cxj</span>
        </div>
        <span class="text-[10px] text-base-content/40 mt-1">
          over {{ totalTasks }} {{ totalTasks === 1 ? 'task' : 'tasks' }}
        </span>
      </div>

      <!-- Tasks per user -->
      <div class="flex flex-col rounded-lg bg-base-200 border border-base-100 px-3 py-2.5 min-w-[15rem] flex-1">
        <span class="text-[10px] uppercase tracking-wider text-base-content/40 flex items-center gap-1.5">
          <i class="fa-solid fa-user text-info text-xs"></i> Tasks per user
          <span class="ml-auto normal-case tracking-normal text-base-content/30">done / total</span>
        </span>
        <div v-if="tasksByUser.length" class="flex flex-col gap-1.5 mt-2 max-h-28 overflow-y-auto pr-1">
          <div v-for="entry in tasksByUser" :key="entry.name" class="flex items-center gap-2">
            <span
              class="w-4 h-4 rounded-full bg-primary/20 text-primary text-[9px] font-semibold flex items-center justify-center shrink-0"
            >{{ initial(entry.name) }}</span>
            <span class="text-xs truncate flex-1 min-w-0" :title="entry.name">{{ entry.name }}</span>
            <progress
              class="progress progress-success h-1 w-12 shrink-0"
              :value="entry.total ? (entry.done / entry.total) * 100 : 0"
              max="100"
            ></progress>
            <span class="text-[10px] tabular-nums text-base-content/50 shrink-0 w-8 text-right">
              {{ entry.done }}/{{ entry.total }}
            </span>
          </div>
        </div>
        <span v-else class="text-[11px] text-base-content/30 mt-2 italic">No assignees</span>
      </div>

      <!-- Tasks per profile -->
      <div class="flex flex-col rounded-lg bg-base-200 border border-base-100 px-3 py-2.5 min-w-[15rem] flex-1">
        <span class="text-[10px] uppercase tracking-wider text-base-content/40 flex items-center gap-1.5">
          <i class="fa-solid fa-user-gear text-secondary text-xs"></i> Tasks per profile
          <span class="ml-auto normal-case tracking-normal text-base-content/30">done / total</span>
        </span>
        <div v-if="tasksByProfile.length" class="flex flex-col gap-1.5 mt-2 max-h-28 overflow-y-auto pr-1">
          <div v-for="entry in tasksByProfile" :key="entry.name" class="flex items-center gap-2">
            <span
              class="w-4 h-4 rounded-full bg-secondary/20 text-secondary text-[9px] font-semibold flex items-center justify-center shrink-0"
            >{{ initial(entry.name) }}</span>
            <span class="text-xs truncate flex-1 min-w-0" :title="entry.name">{{ entry.name }}</span>
            <progress
              class="progress progress-success h-1 w-12 shrink-0"
              :value="entry.total ? (entry.done / entry.total) * 100 : 0"
              max="100"
            ></progress>
            <span class="text-[10px] tabular-nums text-base-content/50 shrink-0 w-8 text-right">
              {{ entry.done }}/{{ entry.total }}
            </span>
          </div>
        </div>
        <span v-else class="text-[11px] text-base-content/30 mt-2 italic">No profiles</span>
      </div>
    </div>

    <!-- ── Planning view (global, not board scoped — rendered full width) ── -->
    <PlanningView v-if="activeView === 'planning'" class="flex-1 min-h-0" />

    <!-- ── Follow-up view (global, not board scoped — rendered full width) ── -->
    <FollowupView v-else-if="activeView === 'followup'" class="flex-1 min-h-0" />

    <!-- ── Board workspace: board (left) + inline task detail (right) ── -->
    <VerticalSplitter
      v-else
      class="flex-1 min-h-0"
      :panels="boardSplitterPanels"
      :split="!isMobile"
      :show-handle="!isMobile"
    >

      <!-- Left: board sidebar (kanban) + the active board rendering -->
      <template #left>
        <div class="relative flex h-full min-h-0 w-full overflow-hidden">
          <!-- Mobile scrim: tapping the canvas collapses the sidebar drawer -->
          <transition name="fade">
            <div
              v-if="sidebarOverlay"
              class="absolute inset-0 z-30 bg-black/50 backdrop-blur-[1px]"
              @click="sidebarCompact = true"
            ></div>
          </transition>

          <!-- Sidebar (kanban boards only: sprint boards switch through the
               toolbar dropdown and render no task list) -->
          <KanbanBoardSidebar
            v-if="!isSprintBoard"
            :boards="boards"
            :activeBoard="activeBoard"
            :columns="activeColumns"
            :activeColumnFilter="activeColumnFilter"
            :tasks="sidebarTasks"
            :selectedTaskId="activeSelectionId"
            :isCompact="sidebarCompact"
            :searchQuery="searchQuery"
            :class="sidebarOverlay ? 'absolute inset-y-0 left-0 z-40 shadow-2xl' : ''"
            @select-board="onSelectBoard"
            @toggle-column-filter="onToggleColumnFilter"
            @select-task="onSelectTask"
            @new-task="openNewTask"
            @new-board="openNewBoardModal"
            @new-column="openNewColumn"
            @update-search="onUpdateSearch"
            @toggle-compact="sidebarCompact = !sidebarCompact"
            @show-board-list="showBoardList = true"
          />

          <!-- Board rendering: table / gantt / canvas -->
          <div class="flex-1 min-w-0 flex flex-col overflow-hidden">

            <!-- Table: find tasks with advanced filtering -->
            <!-- Rendered INSIDE this board view, so it is scoped to the open
                 board and does not offer the board filter (see `inBoardView`). -->
            <TaskTableView
              v-if="activeView === 'table'"
              class="flex-1 min-h-0"
              :boardId="activeBoardId"
              :selectedTaskId="activeSelectionId"
              :inBoardView="true"
              @open-task="onSelectTask"
            />

            <!-- Gantt timeline (sprint boards) -->
            <SprintBoardGantt
              v-else-if="isSprintBoard && activeView === 'gantt'"
              class="flex-1 min-h-0"
              :columns="filteredColumns"
              :selectedTaskId="activeSelectionId"
              @open-task="onSelectTask"
              @open-task-window="onOpenTaskWindow"
            />

            <!-- Shared canvas (SprintBoardCanvas), configured per board type.
                 Kept mounted (`v-show`) so switching views keeps scroll and
                 selection, as the kanban board always did. -->
            <SprintBoardCanvas
              v-show="activeView === 'board'"
              class="flex-1 min-h-0"
              :columns="canvasColumns"
              :selectedTaskId="activeSelectionId"
              :background="activeBoard?.background || null"
              :allowCreate="!isVirtualBoard"
              :allowReorderColumns="!isVirtualBoard"
              :allowNewColumn="!isVirtualBoard"
              :allowEditColumn="!isVirtualBoard"
              :allowActions="isSprintBoard && !isVirtualBoard"
              :reorderable="!isSprintBoard"
              @open-task="onSelectTask"
              @open-task-window="onOpenTaskWindow"
              @new-task="openNewTask"
              @new-column="openNewColumn"
              @edit-column="onEditColumn"
              @move-task="onMoveTask"
              @reorder-columns="onReorderColumns"
              @reorder-tasks="onReorderTasks"
              @add-subtask="onAddSubtask"
              @remove-task="onRemoveTask"
            />
          </div>
        </div>
      </template>

      <!-- Right: inline task detail rendered with ChatView (desktop only) -->
      <template #right v-if="sideTask && !isMobile">
        <div class="flex flex-col h-full min-h-0 w-full bg-base-100">

          <!-- Slim pane toolbar: task name + window/close actions -->
          <div class="shrink-0 flex items-center gap-2 px-2 py-1.5 border-b border-base-100">
            <ChatIcon :mode="sideTask.mode" class="text-xs shrink-0" />
            <span class="flex-1 min-w-0 text-sm font-semibold truncate" :title="sideTask.name">
              {{ sideTask.name || 'Task' }}
            </span>

            <!-- Open in a new window (desktop only) -->
            <button
              v-if="!isMobile"
              class="btn btn-ghost btn-xs gap-1.5 text-base-content/50 hover:text-primary"
              title="Open in a new window"
              aria-label="Open in a new window"
              @click="onOpenTaskWindow(sideTask)"
            >
              <i class="fa-solid fa-up-right-from-square text-xs"></i>
            </button>

            <button
              class="btn btn-ghost btn-xs text-base-content/50 hover:text-error"
              title="Close"
              aria-label="Close task detail"
              @click="closeSideTask"
            >
              <i class="fa-solid fa-xmark text-xs"></i>
            </button>
          </div>

          <!-- Chat rendered through the shared ChatView (its own load/init) -->
          <div class="flex-1 min-h-0 overflow-hidden">
            <ChatView
              :key="sideTask.id"
              :chat="sideTask"
              class="h-full"
              @chats="closeSideTask"
            />
          </div>
        </div>
      </template>
    </VerticalSplitter>

    <!-- Modals (shared by both board flavours — SprintBoardModals) -->
    <SprintBoardModals
      ref="modals"
      :boardType="boardModalsType"
      :boardTitle="activeBoard?.title"
      :sprintId="activeBoard?.id"
      :sprintTitle="activeBoard?.title"
      :columns="modalsColumns"
      :editingColumn="editingColumn"
      :allowColumnDelete="isSprintBoard && !isVirtualBoard"
      @task-created="onTaskCreated"
      @tasks-added="onTasksAdded"
      @column-created="onColumnCreated"
      @column-updated="onColumnUpdated"
      @column-deleted="onColumnDeleted"
      @board-created="onBoardCreated"
      @board-updated="onBoardUpdated"
      @board-delete="onBoardDelete"
    />

    <!-- Export / import board (kanban & sprint) -->
    <BoardTransferModal
      v-if="showTransfer"
      :boardId="activeBoardId"
      :project="project"
      @close="showTransfer = false"
      @imported="onBoardImported"
    />
  </div>
</template>

<script>
// Views this component can render.
//   board  · table   → both flavours
//   gantt            → sprint boards (sprint timeline)
//   planning/followup→ kanban boards (global planning views)
const KANBAN_VIEWS = ['board', 'table', 'planning', 'followup']
const SPRINT_VIEWS = ['board', 'table', 'gantt']
const VALID_VIEWS = ['board', 'table', 'gantt', 'planning', 'followup']

export default {
  props: {
    project: { type: Object, default: null },
    // Dockview/app panels receive the app params (e.g. { view: 'planning' }).
    // In router mode no prop is passed, so we also read the route query (?view=planning).
    params: { type: Object, default: () => ({}) }
  },
  data() {
    return {
      // The active board lives here (NOT in the store) so several board panels
      // can each show a different board at the same time.
      activeBoardId: null,
      // Board requested through the app params / route, snapshotted once at
      // creation so later app-info writes can't redirect it to the fallback.
      initialRequestedBoardId: null,
      // Whether the requested board has already been applied (see `boards`)
      boardAppliedFromParams: false,
      activeView: 'board',
      sidebarCompact: false,
      activeColumnFilter: 'all',
      selectedTaskId: null,
      // Task shown in the inline detail pane (right side). Separate from
      // `selectedTaskId` so the pane can be closed without losing highlight.
      sideTaskId: null,
      searchQuery: '',
      editingColumn: null,
      showBoardList: false,
      // Export / import board modal (kanban & sprint share it)
      showTransfer: false,
      // Sprint stats panel (duration · avg cost · tasks per user/profile).
      // Hidden by default — the toolbar "Stats" button reveals/hides it.
      showStats: false
    }
  },
  created() {
    // Snapshot the board requested through the app params / route *before* we
    // publish anything, so `syncAppInfo` can't make it point at the fallback.
    this.initialRequestedBoardId = this.resolveRequestedBoardId()
    // Load the board requested through the app params / route; fall back to the
    // first available board when the panel was opened without a specific one.
    this.activeBoardId = this.initialBoardId
    this.boardAppliedFromParams = !!this.initialRequestedBoardId &&
      this.activeBoardId === this.initialRequestedBoardId
    // Apply the requested view, but only when the open board supports it
    // (planning/follow-up are kanban-only, gantt is sprint-only)
    this.activeView = this.isViewAllowed(this.requestedView) ? this.requestedView : 'board'
    // Mobile: start with the board sidebar collapsed to maximise canvas space
    this.sidebarCompact = this.isMobile
    // Fall back to the board list only when the board view has no active board
    this.showBoardList = this.activeView === 'board' && !this.activeBoardId
    // Publish the board to the app info so the tab shows its name. If the boards
    // were not loaded yet, this re-runs once they arrive (see `boards` watcher).
    this.syncAppInfo()
    // Single mode: mirror the open board in the route so a refresh reopens it.
    this.syncRouteParams()
  },
  computed: {
    // Resolve a requested initial view from app params (multiple shapes) or the route query
    requestedView() {
      const candidates = [
        this.params?.view,
        this.params?.params?.view,
        this.$route?.query?.view
      ]
      return candidates.find(v => VALID_VIEWS.includes(v)) || null
    },
    // Live app host for this panel — read from the store so runtime app-info
    // updates (such as the active board) are reflected without recreating the
    // panel. Falls back to the static panel snapshot.
    app() {
      const snapshot = this.params?.app || this.params?.params?.app || null
      const tabId = snapshot?.tabId
      return (tabId && this.$storex.ui.openApps[tabId]) || snapshot || null
    },
    // Tab id of the app/panel hosting this board view (used to update app info)
    appTabId() {
      return this.app?.tabId || this.params?.params?.app?.tabId || null
    },
    // Resolve the initial board from the board requested through params/route
    // (snapshotted in `created`), falling back to the first available board.
    initialBoardId() {
      const requested = this.initialRequestedBoardId
      if (requested && this.$storex.kanban.boardById(requested)) return requested
      return this.$storex.kanban.allBoards[0]?.id || null
    },
    isMobile() {
      return this.$ui.isMobile
    },
    // On mobile the expanded sidebar floats over the canvas instead of pushing it
    sidebarOverlay() {
      return !this.isSprintBoard && this.isMobile && !this.sidebarCompact
    },
    boards() {
      return this.$storex.kanban.allBoards
    },
    activeBoard() {
      return this.$storex.kanban.boardById(this.activeBoardId)
    },
    activeBoardTitle() {
      return this.activeBoard?.title || 'Sprint'
    },
    // Sprint boards replace the kanban canvas/sidebar with the sprint shell
    isSprintBoard() {
      return this.activeBoard?.type === 'sprint'
    },
    // The synthetic "No board" board: it surfaces board-less chats read-only
    isVirtualBoard() {
      return !!this.activeBoard?.virtual
    },
    // Flavour handed to the shared modals (enables the kanban column picker)
    boardModalsType() {
      return this.isSprintBoard ? 'sprint' : 'kanban'
    },
    // Sprints listed in the selector.
    //
    // Built from `storedBoards` (the persisted kanban document) instead of the
    // slug of getters: those append the chats-derived virtual "No board" board,
    // which reads `updated_at` / `lastMessageAt` / `board` / `mode` of EVERY
    // chat. The virtual board can never be a sprint target anyway.
    sprintBoards() {
      return (this.$storex.kanban.storedBoards || []).filter(b => b.type === 'sprint')
    },
    // Columns as stored on the board document (kanban columns, sprint columns
    // when the sprint was customized). Used by the sidebar, the toolbar counters
    // and the kanban column dialog.
    activeColumns() {
      return this.activeBoard?.columns || []
    },
    // Built columns of the open board — the single grouping of its tasks:
    //   • kanban : stored columns + the virtual "no column" bucket
    //   • sprint : status columns + the virtual "unclassified" bucket
    columns() {
      if (!this.activeBoardId) return []
      return this.isSprintBoard
        ? this.$storex.kanban.sprintColumns(this.activeBoardId)
        : this.$storex.kanban.buildViewColumns(this.activeBoardId, null)
    },
    // Text-filtered columns (sprint search: name + description)
    filteredColumns() {
      const query = this.searchQuery?.trim().toLowerCase()
      if (!query) return this.columns
      return this.columns.map(col => ({
        ...col,
        tasks: (col.tasks || []).filter(t =>
          `${t.name || ''} ${t.description || ''}`.toLowerCase().includes(query)
        )
      }))
    },
    // Kanban column-filter pills (single column shown at a time)
    filteredViewColumns() {
      if (this.activeColumnFilter === 'all') return this.columns
      return this.columns.filter(c => c.title === this.activeColumnFilter)
    },
    // Columns the canvas renders: the kanban column filter is a column filter,
    // the sprint search is a text filter.
    canvasColumns() {
      return this.isSprintBoard ? this.filteredColumns : this.filteredViewColumns
    },
    // Columns handed to the modals: sprint boards edit the built status columns
    // (title/status/icon/colour), kanban boards edit the stored board columns.
    modalsColumns() {
      return this.isSprintBoard ? this.columns : this.activeColumns
    },
    // Chat record shown in the inline detail pane (null hides the pane)
    sideTask() {
      if (!this.sideTaskId) return null
      return (this.$storex.chats.chats || {})[this.sideTaskId] || null
    },
    // Task highlighted by the board renderings: the local selection wins over
    // the globally active chat
    activeSelectionId() {
      return this.selectedTaskId || this.$storex.chats.activeChatId || null
    },
    // Splitter sizing: the board takes the full width until the detail pane
    // (ChatView) opens, then board + inline task share the space. Only used on
    // desktop — on mobile the splitter is disabled (see `:split`).
    boardSplitterPanels() {
      return {
        left: { defaultSize: this.sideTask ? 60 : 100, minSize: 30 },
        right: { defaultSize: 40, minSize: 25 }
      }
    },
    // Tasks of the open kanban board (chat.board === board id)
    boardChats() {
      return this.$storex.kanban.boardChats(this.activeBoardId)
    },
    // Sidebar task list (kanban): column filter + free text search
    sidebarTasks() {
      if (this.isSprintBoard) return []
      const query = this.searchQuery?.toLowerCase()?.trim()
      const tasks = this.activeColumnFilter === 'all'
        ? this.boardChats
        : this.boardChats.filter(c => (c.column || '--none--') === this.activeColumnFilter)

      if (!query) return tasks

      return tasks.filter(task => {
        const inName = task.name?.toLowerCase().includes(query)
        const inMessages = task.messages?.some(m => m.content?.toLowerCase().includes(query))
        const inFiles = task.file_list?.some(f => f.toLowerCase().includes(query))
        const inProfiles = task.profiles?.some(p => p.toLowerCase().includes(query))
        return inName || inMessages || inFiles || inProfiles
      })
    },
    // Tabs offered by the open board. Counts mirror what each view lists.
    viewTabs() {
      if (this.isSprintBoard) {
        return [
          { id: 'board', label: 'Board', icon: 'fa-solid fa-table-columns', count: this.totalTasks },
          { id: 'table', label: 'Table', icon: 'fa-solid fa-table-list', count: this.totalTasks },
          { id: 'gantt', label: 'Gantt', icon: 'fa-solid fa-chart-gantt', count: null, title: 'Gantt timeline' }
        ]
      }

      const planning = this.$storex.planning
      return [
        { id: 'board', label: 'Board', icon: 'fa-solid fa-columns', count: this.sidebarTasks.length },
        { id: 'table', label: 'Table', icon: 'fa-solid fa-table-list', count: this.boardChats.length },
        { id: 'planning', label: 'Planning', icon: 'fa-solid fa-list-check', count: planning?.allTasks?.length || 0 },
        { id: 'followup', label: 'Follow-up', icon: 'fa-solid fa-chart-line', count: planning?.metrics?.overdue || 0 }
      ]
    },

    // ── Sprint stats ─────────────────────────────────────────────────────────
    // Every task of the sprint (columns are the single source of grouping)
    allTasks() {
      return this.columns.reduce((acc, col) => acc.concat(col.tasks || []), [])
    },
    totalTasks() {
      return this.allTasks.length
    },
    // The "done" column is the one whose STATUS is done, ignoring case
    // ("Done" and "done" are the same status).
    doneCount() {
      const done = this.columns.find(c => this.sameStatus(c.status, 'done'))
      return done ? done.tasks.length : 0
    },
    progress() {
      return this.totalTasks ? Math.round((this.doneCount / this.totalTasks) * 100) : 0
    },
    // Total cost (cxj) spent across every task of the sprint
    totalCost() {
      return this.columns.reduce((sum, col) =>
        sum + (col.tasks || []).reduce((s, t) => s + (t.cost || 0), 0), 0)
    },
    // Sum of all task budgets, when defined
    totalBudget() {
      return this.columns.reduce((sum, col) =>
        sum + (col.tasks || []).reduce((s, t) => s + (t.estimation_cost || 0), 0), 0)
    },
    costTooltip() {
      const label = `${this.totalTasks} task${this.totalTasks === 1 ? '' : 's'}`
      if (this.totalBudget > 0) {
        return `Total sprint cost: ${this.formatCoins(this.totalCost)} of ${this.formatCoins(this.totalBudget)} cxj (${label})`
      }
      return `Total sprint cost: ${this.formatCoins(this.totalCost)} cxj (${label})`
    },
    // Task creation dates, oldest first
    taskDates() {
      return this.allTasks
        .map(t => t.created_at)
        .filter(Boolean)
        .map(d => new Date(d))
        .filter(d => !Number.isNaN(d.getTime()))
        .sort((a, b) => a - b)
    },
    oldestTaskDate() {
      return this.taskDates[0] || null
    },
    newestTaskDate() {
      return this.taskDates[this.taskDates.length - 1] || null
    },
    // Total days spanned by the sprint: from the oldest task to the newest one
    totalDays() {
      if (!this.oldestTaskDate || !this.newestTaskDate) return 0
      return Math.max(0, Math.round((this.newestTaskDate - this.oldestTaskDate) / 86400000))
    },
    createdRangeLabel() {
      if (!this.oldestTaskDate) return 'No tasks yet'
      const fmt = date => date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
      if (this.totalDays === 0) return `since ${fmt(this.oldestTaskDate)}`
      return `${fmt(this.oldestTaskDate)} → ${fmt(this.newestTaskDate)}`
    },
    createdRangeTooltip() {
      if (!this.oldestTaskDate) return 'No tasks yet'
      const fmt = date => date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
      return `Oldest task: ${fmt(this.oldestTaskDate)} · Newest task: ${fmt(this.newestTaskDate)}`
    },
    // Average cost of a ticket (total spent ÷ number of tasks)
    averageCost() {
      if (!this.totalTasks) return 0
      return this.totalCost / this.totalTasks
    },
    // Tasks grouped by assignee (a task counts once per user it carries)
    tasksByUser() {
      return this.groupTasks(this.allTasks, 'users', 'Unassigned')
    },
    // Tasks grouped by profile (a task counts once per profile it carries)
    tasksByProfile() {
      return this.groupTasks(this.allTasks, 'profiles', 'No profile')
    }
  },
  watch: {
    // Apply a view requested through params/route (e.g. /kanban?view=planning)
    requestedView(view) {
      this.activeView = this.isViewAllowed(view) ? view : 'board'
    },
    // Keep the sidebar collapsed whenever we cross into the mobile breakpoint
    isMobile(mobile) {
      this.sidebarCompact = mobile
    },
    // The board type owns which views exist (planning/follow-up only for kanban
    // boards, gantt only for sprints) and the tab title shows the board name.
    activeBoard(board) {
      if (!this.isViewAllowed(this.activeView, board)) {
        this.activeView = 'board'
      }
      this.syncAppInfo()
      this.syncRouteParams()
    },
    // Switching boards invalidates the inline task detail pane
    activeBoardId() {
      this.sideTaskId = null
      this.editingColumn = null
    },
    // Single (non-desktop) mode: reopen the board addressed by the URL whenever
    // the route changes (refresh, back/forward, deep link or a link to another
    // board).
    '$route.params.board'(boardId) {
      if (this.$route?.name !== 'kanban') return
      if (!boardId || boardId === this.activeBoardId) return
      if (!this.$storex.kanban.boardById(boardId)) return
      this.boardAppliedFromParams = true
      this.activeBoardId = boardId
      this.selectedTaskId = null
      this.activeColumnFilter = 'all'
      this.showBoardList = false
    },
    // If the selected board disappears (deleted / renamed / project change),
    // fall back to the first available board. Also applies a board requested
    // through params that only becomes available after the boards finish
    // loading (reload case), so each panel keeps its own board.
    boards(boards) {
      const requested = this.initialRequestedBoardId
      if (requested && !this.boardAppliedFromParams && this.$storex.kanban.boardById(requested)) {
        this.boardAppliedFromParams = true
        this.activeBoardId = requested
        this.selectedTaskId = null
        this.showBoardList = false
        return
      }
      if (this.activeBoardId && !this.$storex.kanban.boardById(this.activeBoardId)) {
        this.activeBoardId = boards[0]?.id || null
        this.showBoardList = this.activeView === 'board' && !this.activeBoardId
      }
    },
    // Switching back to the board view without an active board shows the board list
    activeView(view) {
      if (view === 'board' && !this.activeBoardId) {
        this.showBoardList = true
      }
    },
    project() {
      // The project changed: the previously requested board no longer applies
      this.boardAppliedFromParams = true
      this.activeBoardId = null
      this.selectedTaskId = null
      this.searchQuery = ''
      this.activeColumnFilter = 'all'
      this.showBoardList = false
    }
  },
  methods: {
    // ── Views ────────────────────────────────────────────────────────────────
    // A view only exists while the open board supports it: planning/follow-up
    // are kanban views, gantt is the sprint timeline.
    isViewAllowed(view, board = null) {
      const target = board || this.activeBoard
      const allowed = target?.type === 'sprint' ? SPRINT_VIEWS : KANBAN_VIEWS
      return allowed.includes(view)
    },

    // ── Board assistant ──────────────────────────────────────────────────────
    // A chat created from the board assistant is a normal board card (it lands
    // in the board's first column), so it is opened in the inline detail pane
    // right away — from there it can be continued like any other conversation.
    onAssistantChatCreated(chat) {
      if (!chat?.id) return
      this.onSelectTask(chat)
    },
    // Board requested through the app params (persisted per panel) or the route
    resolveRequestedBoardId() {
      return [
        // Live app params — updated when the board changes (persisted per panel)
        this.app?.params?.board,
        // Panel params snapshot (kept in sync by `updateAppParams`)
        this.params?.board,
        this.params?.params?.board,
        // Route (router mode)
        this.$route?.params?.board,
        this.$route?.query?.board
      ].find(Boolean) || null
    },
    // Publish the active board to the hosting app's info so the desktop tab can
    // display the board name and the layout restores the same board on reload.
    syncAppInfo() {
      const tabId = this.appTabId
      if (!tabId) return
      // Nothing resolved yet — don't clobber the board persisted in the params
      if (!this.activeBoardId || !this.activeBoard) return
      this.$storex.ui.updateAppParams({
        tabId,
        params: {
          board: this.activeBoardId,
          boardName: this.activeBoard?.title || null
        }
      })
    },
    // Single (non-desktop) mode only: keep the route in sync with the open board
    // (id + name) so a refresh or a back-navigation reopens the same board.
    // Desktop mode tracks the board through the panel params (`syncAppInfo`)
    // instead, so this is a no-op whenever the kanban route is not active.
    syncRouteParams() {
      if (this.$route?.name !== 'kanban') return
      const boardId = this.activeBoardId
      const board = this.activeBoard
      if (!boardId || !board) return

      const boardName = board.title || null
      const params = this.$route.params || {}
      const settled = params.board === boardId &&
        (params.boardName || null) === (boardName || null)
      if (settled) return

      const nextParams = { ...params, board: boardId }
      if (boardName) nextParams.boardName = boardName
      else delete nextParams.boardName

      this.$router
        .replace({ name: 'kanban', params: nextParams, query: this.$route.query })
        .catch(() => {})
    },

    // ── Board selection ──────────────────────────────────────────────────────
    onSelectBoard(boardId) {
      // A manual selection wins over the board requested through params
      this.boardAppliedFromParams = true
      this.activeBoardId = boardId
      this.selectedTaskId = null
      this.activeColumnFilter = 'all'
      this.showBoardList = false
    },
    // Sprint selector: same selection, and the dropdown loses focus so it closes
    onSelectSprint(boardId) {
      this.onSelectBoard(boardId)
      document.activeElement?.blur()
    },
    onSelectBoardFromList(boardTitle) {
      this.boardAppliedFromParams = true
      this.activeBoardId = boardTitle
      this.selectedTaskId = null
      this.activeColumnFilter = 'all'
      this.showBoardList = false
    },
    onBookmark(board) {
      this.$storex.kanban.toggleBookmark(board.title)
    },
    onToggleColumnFilter(colTitle) {
      this.activeColumnFilter = this.activeColumnFilter === colTitle ? 'all' : colTitle
    },
    onUpdateSearch(query) {
      this.searchQuery = query
    },

    // ── Task selection / detail pane ─────────────────────────────────────────
    // Default task selection: open it inline in the right-side detail pane
    // (rendered with ChatView inside the VerticalSplitter). Clicking the card
    // that is already open toggles the pane closed. Mobile has no room for the
    // pane (and no splitter), so it keeps the previous behaviour.
    onSelectTask(task) {
      if (!task) {
        this.selectedTaskId = null
        this.sideTaskId = null
        return
      }
      // Card already shown in the pane → toggle it closed
      if (this.sideTaskId === task.id) {
        this.selectedTaskId = null
        this.sideTaskId = null
        return
      }
      this.selectedTaskId = task.id
      if (this.isMobile) {
        this.$chats.setActiveChat(task)
        return
      }
      this.sideTaskId = task.id
      // Make sure the full history is loaded before ChatView renders it
      this.$storex.chats.loadUninitialized(task)
    },
    // Ctrl/Cmd+click or the "open in a new window" icon: original behaviour,
    // the task is opened in its own window / panel.
    onOpenTaskWindow(task) {
      if (!task) return
      this.selectedTaskId = task.id
      this.$chats.setActiveChat(task)
    },
    closeSideTask() {
      this.sideTaskId = null
    },

    // ── Task creation ────────────────────────────────────────────────────────
    // `status` is the target sprint column's status, `column` the target kanban
    // column (the canvas passes both, each board uses the one it groups by).
    openNewTask(opts = {}) {
      // The virtual board is read-only — it must not create tasks
      if (this.isVirtualBoard) return
      this.$refs.modals?.openNewTask(opts)
    },
    openAddExisting() {
      if (this.isVirtualBoard) return
      this.$refs.modals?.openAddExisting()
    },
    // "+" on a card → create a subtask linked to that task, landing in the same
    // column (status) as its parent.
    onAddSubtask(task) {
      if (this.isVirtualBoard || !task) return
      this.openNewTask({
        parentId: task.id,
        status: task.status || null,
        column: task.column || null
      })
    },
    // Fallback content when the task is seeded with files/images but no text.
    // `addMessage` rejects empty content, so this must always be non-empty.
    defaultTaskMessage({ files, attachments }) {
      const names = [
        ...(files || []).map(f => f.split('/').reverse()[0]),
        ...(attachments || []).map(a => a.file_name)
      ].filter(Boolean)
      return names.length
        ? `Work on the attached content:\n${names.map(n => `- ${n}`).join('\n')}`
        : 'Run this task.'
    },
    // Unified task creation — same richness both boards offer (initial message,
    // files, attachments, assignees, deadline, cost budget, Run).
    async onTaskCreated(payload) {
      if (!this.activeBoard) return
      const {
        name, column, mode, status, profiles, llm_model,
        project_id, users, deadline, estimation_cost,
        message, files, attachments, parentId, run
      } = payload

      // Core task:
      //   • kanban → board + destination column + optional parent link
      //   • sprint → sprint membership + destination status
      const chat = this.isSprintBoard
        ? await this.$storex.kanban.newSprintTask({
            name,
            status,
            mode,
            profiles,
            llm_model,
            parentId: parentId || null,
            project_id: project_id || null,
            sprintId: this.activeBoardId
          })
        : await this.$storex.kanban.newTask({
            name,
            column,
            mode,
            profiles,
            llm_model,
            board: this.activeBoardId,
            parentId: parentId || null,
            project_id: project_id || null
          })
      if (!chat) return

      // Preferences the create payload does not persist are written through the
      // shared metadata endpoint so none of them is silently dropped.
      const updates = {}
      if (this.isSprintBoard && project_id) updates.project_id = project_id
      if (users?.length) updates.users = users
      if (deadline) updates.deadline = deadline
      if (estimation_cost != null) updates.estimation_cost = estimation_cost
      if (files?.length) updates.file_list = files

      if (Object.keys(updates).length) {
        await this.$storex.chats.updateChatInfo({ chat, updates })
      }

      // The initial message (text + files + attachments) becomes the task's
      // first user message so the agent has something to work with.
      const hasInitialContent = !!(message || files?.length || attachments?.length)
      if (hasInitialContent) {
        const userMessage = this.$service.chat.getUserMessage({
          message: message || this.defaultTaskMessage({ files, attachments }),
          files: files || [],
          profiles: profiles || [],
          attachments: attachments || [],
          user: this.$user?.username
        })
        await this.$storex.chats.addMessage({ chat, message: userMessage })

        // "Run" → create the task and start processing it immediately
        if (run) {
          await this.$storex.projects.chatWihProject(chat)
        }
      }

      // Kanban keeps the created task open in the inline detail pane; a sprint
      // board stays on the board (its card is already highlighted by the store).
      if (!this.isSprintBoard) this.onSelectTask(chat)
    },
    // Add existing tasks to the sprint (sprint membership)
    async onTasksAdded({ taskIds }) {
      if (this.isVirtualBoard || !taskIds?.length) return
      await this.$storex.kanban.addTasksToSprint({ taskIds, sprintId: this.activeBoardId })
    },
    // Remove a task from the sprint (keeps the task itself)
    async onRemoveTask(task) {
      if (this.isVirtualBoard || !task?.id) return
      await this.$storex.kanban.removeTaskFromSprint({ taskId: task.id, sprintId: this.activeBoardId })
    },

    // ── Columns ──────────────────────────────────────────────────────────────
    openNewColumn() {
      if (this.isVirtualBoard) return
      // Brand new column (the dialog reads `editingColumn`)
      this.editingColumn = null
      this.$refs.modals?.openNewColumn()
    },
    onEditColumn(colTitle) {
      if (this.isVirtualBoard) return
      // Title, id and status all address the column, compared ignoring case
      const column = this.isSprintBoard
        ? this.columns.find(c =>
            c.title === colTitle
            || c.id === colTitle
            || this.sameStatus(c.status, colTitle))
        : this.activeColumns.find(c => c.title === colTitle)
      this.editingColumn = column || null
      this.$refs.modals?.openNewColumn()
    },
    async onColumnCreated({ title, status, icon, color, profiles, project_id }) {
      if (this.isVirtualBoard || !title?.trim() || !this.activeBoard) return
      if (this.isSprintBoard) {
        await this.$storex.kanban.addSprintColumn({
          boardId: this.activeBoardId,
          title,
          status,
          icon,
          color,
          profiles,
          // Project tasks created in this column are assigned to
          project_id
        })
        return
      }
      await this.$storex.kanban.addColumn({
        boardId: this.activeBoardId,
        title,
        color,
        profiles,
        // Project tasks created in this column are assigned to
        project_id
      })
    },
    async onColumnUpdated({ id, title, status, icon, color, profiles, project_id }) {
      if (this.isVirtualBoard || !title?.trim() || !this.activeBoard) return
      if (this.isSprintBoard) {
        await this.$storex.kanban.updateSprintColumn({
          boardId: this.activeBoardId,
          id,
          title,
          status,
          icon,
          color,
          profiles,
          project_id
        })
      } else {
        await this.$storex.kanban.updateColumn({
          boardId: this.activeBoardId,
          id,
          title,
          color,
          profiles,
          // Project tasks created in this column are assigned to
          project_id
        })
      }
      this.editingColumn = null
    },
    async onColumnDeleted({ id }) {
      // Only sprint columns can be removed (the dialog is disabled elsewhere)
      if (!this.isSprintBoard || this.isVirtualBoard || !id) return
      await this.$storex.kanban.removeSprintColumn({ boardId: this.activeBoardId, id })
      this.editingColumn = null
    },
    // Persist a new column order.
    //   • kanban → columns group `chat.column`, so the tasks are written back
    //   • sprint → columns group `chat.status`, only the order changes
    async onReorderColumns(reorderedColumns) {
      if (this.isVirtualBoard || !reorderedColumns?.length) return
      if (this.isSprintBoard) {
        await this.$storex.kanban.syncSprintColumnOrder({
          boardId: this.activeBoardId,
          columns: reorderedColumns
        })
        return
      }
      await this.$storex.kanban.syncColumnOrder({
        boardId: this.activeBoardId,
        viewColumns: reorderedColumns
      })
    },
    // Within-column task reordering (kanban only)
    async onReorderTasks({ columnTitle, taskIds }) {
      if (this.isSprintBoard || this.isVirtualBoard) return
      await this.$storex.kanban.reorderTasksInColumn({
        boardId: this.activeBoardId,
        columnTitle,
        taskIds
      })
    },
    // Cross-column move:
    //   • kanban → writes chat.column
    //   • sprint → writes chat.status
    // The column emits both values (`toColumn` / `status`), each board uses its own.
    async onMoveTask({ taskId, toColumn, status }) {
      if (!taskId) return
      if (this.isSprintBoard) {
        await this.$storex.kanban.moveSprintStatus({ taskId, status })
        return
      }
      await this.$storex.kanban.moveTask({ taskId, toColumn })
    },

    // ── Board settings / creation / deletion / transfer ───────────────────────
    openNewBoardModal() {
      if (this.isVirtualBoard) return
      // New boards inherit the current flavour (sprint boards create sprints)
      this.$refs.modals?.openNewBoard({ type: this.isSprintBoard ? 'sprint' : 'kanban' })
    },
    openEditBoardModal() {
      if (!this.activeBoard) return
      this.$refs.modals?.openEditBoard(this.activeBoard)
    },
    async onBoardCreated({ title, description, type, background }) {
      if (!title?.trim()) return
      const created = await this.$storex.kanban.addBoard({
        title,
        description,
        type,
        background,
        // A board created from the board view becomes a child of the open board
        parent_id: this.activeBoard?.id || null
      })
      if (created) {
        // Open the freshly created (child) board
        this.boardAppliedFromParams = true
        this.activeBoardId = created.title
        this.selectedTaskId = null
        this.activeColumnFilter = 'all'
        this.showBoardList = false
      }
    },
    // Board settings save. The board document merges what is provided, so the
    // assistant (assignee) is persisted next to the name, description, background
    // and participants the dialog edits.
    async onBoardUpdated({ originalTitle, board }) {
      await this.$storex.kanban.saveBoard({ originalTitle, board })
      // Follow the board when it was renamed while being the active one
      if (originalTitle && board.title && originalTitle !== board.title
        && this.activeBoardId === originalTitle) {
        this.boardAppliedFromParams = true
        this.activeBoardId = board.title
      }
    },
    // Delete a board (kanban or sprint). Invoked from the shared board settings
    // modal. Kanban boards can optionally delete their tasks; sprint tasks are
    // always kept and only leave the sprint. The `boards` watcher re-selects a
    // fallback board when the active one is gone.
    async onBoardDelete({ boardId, deleteChats } = {}) {
      const board = this.$storex.kanban.boardById(boardId)
      if (!board || board.virtual) return
      const boardTitle = board.title
      await this.$storex.kanban.deleteBoard({ board, deleteChats })
      this.selectedTaskId = null
      this.sideTaskId = null
      this.activeColumnFilter = 'all'
      this.$ui?.addNotification?.({ text: `Board "${boardTitle}" deleted` })
    },
    // Focus the freshly imported board so the user lands on it right away.
    // Boards copied/moved into ANOTHER project are not part of this project's
    // kanban (`boardById` resolves per active project), so they must not clear
    // the current selection — the source board (or its fallback) stays open.
    onBoardImported({ boardId }) {
      this.showTransfer = false
      if (!boardId || !this.$storex.kanban.boardById(boardId)) {
        return
      }
      this.boardAppliedFromParams = true
      this.activeBoardId = boardId
      this.selectedTaskId = null
      this.sideTaskId = null
      this.activeColumnFilter = 'all'
      this.showBoardList = false
    },

    // ── Formatting helpers (sprint stats) ────────────────────────────────────
    formatCoins(val) {
      if (val == null) return '-'
      if (val >= 1_000_000) return (val / 1_000_000).toFixed(2) + 'M'
      if (val >= 1_000) return (val / 1_000).toFixed(2) + 'K'
      return Number(val).toFixed(2)
    },
    // First letter of a name, used as the avatar fallback in the stats lists
    initial(name) {
      return (name || '?').trim().charAt(0).toUpperCase() || '?'
    },
    // Statuses are free text typed by the user, so they are compared ignoring
    // case: the "Done" column with status "Done" is the same as one using "done".
    normalizeStatus(value) {
      return (value == null ? '' : String(value)).trim().toLowerCase()
    },
    sameStatus(a, b) {
      return this.normalizeStatus(a) === this.normalizeStatus(b)
    },
    // Group tasks by the values of an array field (`users` / `profiles`), keeping
    // a done and total count per value. Sorted by "done" so whoever closes more
    // tickets comes first. A task with no value is counted under `fallback`.
    groupTasks(tasks, field, fallback) {
      const map = {}
      tasks.forEach(task => {
        const names = task[field]?.length ? task[field] : [fallback]
        names.forEach(name => {
          if (!map[name]) map[name] = { name, total: 0, done: 0 }
          map[name].total += 1
          // The task status compares ignoring case ("Done" === "done")
          if (this.sameStatus(task.status, 'done')) map[name].done += 1
        })
      })
      return Object.values(map)
        .sort((a, b) =>
          (b.done - a.done) || (b.total - a.total) || a.name.localeCompare(b.name))
    }
  }
}
</script>

<style scoped>
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-12px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>