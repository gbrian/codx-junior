<template>
  <!-- ────────────────────────────────────────────────────────────────────────
       Management dashboard — "Team Command Center".
       Mounted both as a desktop dockview panel AND as the welcome route ("/" and
       "/:projectName"), so every layout decision is driven by the panel WIDTH
       (ResizeObserver), never by the window.
       ──────────────────────────────────────────────────────────────────────── -->
  <div ref="rootEl" class="management-dashboard flex h-full w-full min-h-0 overflow-hidden bg-base-100"
       :class="compact ? 'flex-col' : 'flex-row'">

    <!-- ── Left rail (wide panel) ─────────────────────────────────────────── -->
    <aside v-if="!compact"
           class="w-56 shrink-0 flex flex-col gap-1 p-2 overflow-y-auto border-r border-base-300 bg-base-200">
      <div class="flex items-center gap-2 px-2 py-3">
        <div class="w-9 h-9 rounded-xl grid place-items-center text-white font-bold bg-gradient-to-br from-primary to-secondary">
          MG
        </div>
        <div class="min-w-0">
          <div class="text-sm font-bold leading-tight truncate">Management</div>
          <div class="text-[10px] opacity-60 truncate">{{ d.projectScopeLabel }} · live view</div>
        </div>
      </div>

      <div class="text-[10px] uppercase tracking-wider opacity-50 px-3 pt-2 pb-1">Sections</div>
      <button v-for="section in d.SECTIONS" :key="section.id"
              class="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-left transition-colors"
              :class="d.state.section === section.id ? 'bg-primary/15 text-primary font-semibold' : 'hover:bg-base-300/60'"
              :aria-current="d.state.section === section.id ? 'page' : undefined"
              @click="d.setSection(section.id)">
        <i :class="section.icon" class="w-4 text-center"></i>
        <span class="flex-1 truncate">{{ section.label }}</span>
        <span v-if="section.id === 'blockers' && d.attention.length"
              class="badge badge-xs badge-error">{{ d.attention.length }}</span>
      </button>

      <div class="mt-auto pt-3 border-t border-base-300">
        <div class="px-2 py-1 text-[10px] opacity-50">
          <div v-if="d.state.lastUpdated">updated {{ d.relTime(d.state.lastUpdated) }}</div>
          <div v-else>not loaded yet</div>
        </div>
      </div>
    </aside>

    <!-- ── Left rail (narrow panel: off-canvas drawer) ─────────────────────── -->
    <div v-if="compact && d.state.railOpen" class="fixed inset-0 z-40 bg-black/50" @click="d.state.railOpen = false"></div>
    <aside v-if="compact && d.state.railOpen"
           class="fixed inset-y-0 left-0 z-50 w-64 flex flex-col gap-1 p-2 overflow-y-auto bg-base-200 shadow-xl">
      <div class="flex items-center gap-2 px-2 py-3">
        <div class="w-9 h-9 rounded-xl grid place-items-center text-white font-bold bg-gradient-to-br from-primary to-secondary">MG</div>
        <div class="min-w-0 flex-1">
          <div class="text-sm font-bold leading-tight">Management</div>
          <div class="text-[10px] opacity-60 truncate">{{ d.projectScopeLabel }} · live view</div>
        </div>
        <button class="btn btn-ghost btn-xs btn-square" aria-label="Close navigation" @click="d.state.railOpen = false">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
      <button v-for="section in d.SECTIONS" :key="'m-' + section.id"
              class="flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm text-left"
              :class="d.state.section === section.id ? 'bg-primary/15 text-primary font-semibold' : 'hover:bg-base-300/60'"
              @click="d.setSection(section.id)">
        <i :class="section.icon" class="w-4 text-center"></i>
        <span class="flex-1">{{ section.label }}</span>
        <span v-if="section.id === 'blockers' && d.attention.length" class="badge badge-xs badge-error">{{ d.attention.length }}</span>
      </button>
    </aside>

    <!-- ── Content column ─────────────────────────────────────────────────── -->
    <div class="flex-1 flex flex-col min-w-0 min-h-0">
      <header class="relative z-30 shrink-0 border-b border-base-300 bg-base-100/95 backdrop-blur px-3 py-2 flex flex-wrap items-center gap-2">
        <button v-if="compact" class="btn btn-ghost btn-sm btn-square" aria-label="Open navigation"
                @click="d.state.railOpen = true">
          <i class="fa-solid fa-bars"></i>
        </button>

        <div class="min-w-0 flex-1">
          <h1 class="text-base font-bold leading-tight flex items-center gap-2">
            {{ currentSection.title }}
            <span class="badge badge-xs badge-success">live</span>
          </h1>
          <p class="text-[11px] opacity-60 truncate">{{ currentSection.subtitle }}</p>
        </div>

        <!-- time window: applies to every section -->
        <div class="join" role="group" aria-label="Time range">
          <button v-for="range in d.RANGES" :key="range.id" class="btn btn-xs join-item"
                  :class="d.state.range === range.id ? 'btn-primary' : 'btn-ghost'"
                  :aria-pressed="d.state.range === range.id"
                  @click="d.setRange(range.id)">
            {{ range.label }}
          </button>
        </div>

        <!-- project scope: multi-select, shared by every section -->
        <ProjectFilter
          :projects="d.projects"
          :selected="d.selectedProjectIds"
          @toggle="d.toggleProject($event)"
          @all="d.selectAllProjects()"
          @none="d.clearProjectSelection()"
        />

        <button class="btn btn-ghost btn-sm btn-square relative" aria-label="Show blockers"
                @click="d.setSection('blockers')">
          <i class="fa-solid fa-bell"></i>
          <span v-if="d.attention.length"
                class="absolute -top-1 -right-1 min-w-4 h-4 px-1 rounded-full bg-error text-error-content text-[9px] font-bold grid place-items-center">
            {{ d.attention.length }}
          </span>
        </button>

        <button class="btn btn-ghost btn-sm btn-square" aria-label="Ask the AI assistant"
                @click="d.toggleAssistant()">
          <i class="fa-solid fa-wand-magic-sparkles"></i>
        </button>

        <!-- Panel actions: a native popover, so it renders in the top layer and
             is never painted under the section content below the header. -->
        <button type="button" class="btn btn-ghost btn-sm btn-square"
                :popovertarget="menuPanelId"
                :style="`anchor-name:--${menuPanelId}-anchor`"
                aria-haspopup="true"
                :aria-expanded="menuOpen ? 'true' : 'false'"
                aria-label="Dashboard menu">
          <i class="fa-solid fa-ellipsis"></i>
        </button>

        <div :id="menuPanelId"
             ref="menuPanelEl"
             popover
             role="menu"
             aria-label="Dashboard menu"
             class="dashboard-menu w-60 rounded-box border border-base-300 bg-base-200 p-1.5 shadow-xl"
             :style="`position-anchor:--${menuPanelId}-anchor`"
             @toggle="menuOpen = $event.newState === 'open'">
          <button type="button" class="dashboard-menu-row" role="menuitem"
                  @click="runMenuAction(d.refresh)">
            <i class="fa-solid fa-arrows-rotate w-4"></i>
            <span class="flex-1">Refresh</span>
            <span class="text-[10px] opacity-50">{{ d.state.lastUpdated ? d.relTime(d.state.lastUpdated) : 'never' }}</span>
          </button>
          <button v-if="d.hasProjectFilter" type="button" class="dashboard-menu-row" role="menuitem"
                  @click="runMenuAction(d.selectAllProjects)">
            <i class="fa-solid fa-layer-group w-4"></i>
            <span class="flex-1">Include all projects</span>
          </button>
          <button v-if="d.state.filters[currentSection.id]" type="button" class="dashboard-menu-row" role="menuitem"
                  @click="runMenuAction(() => d.clearFilters(currentSection.id))">
            <i class="fa-solid fa-eraser w-4"></i>
            <span class="flex-1">Clear {{ currentSection.label }} filters</span>
          </button>
        </div>
      </header>

      <!-- The cost section hosts the shared analytics dashboard, which brings its
           own padding and scroll area: the slot is full-bleed for it only. -->
      <main class="flex-1 min-h-0"
            :class="d.state.section === 'cost' ? 'overflow-hidden p-0' : 'overflow-y-auto p-3 md:p-4'">
        <!-- states -->
        <div v-if="d.state.error[currentSection.id]" class="alert alert-error mb-3">
          <i class="fa-solid fa-circle-exclamation"></i>
          <span class="text-sm">{{ d.state.error[currentSection.id] }}</span>
          <button class="btn btn-xs btn-ghost" @click="d.load(currentSection.id)">Retry</button>
        </div>

        <div v-if="loading && !sectionReady" class="grid gap-3">
          <div class="skeleton h-20 w-full rounded-box"></div>
          <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
            <div v-for="i in 6" :key="i" class="skeleton h-24 rounded-box"></div>
          </div>
          <div class="skeleton h-64 w-full rounded-box"></div>
        </div>

        <template v-else>
          <!-- ════════════════════ PULSE ════════════════════ -->
          <div v-if="d.state.section === 'pulse'" class="space-y-3">
            <!-- first look = urgency -->
            <section v-if="d.attention.length" class="rounded-box border border-error/40 bg-error/10 p-3">
              <div class="flex items-center gap-2 flex-wrap">
                <i class="fa-solid fa-triangle-exclamation text-error"></i>
                <h2 class="text-sm font-bold">
                  {{ d.attention.length }} thing{{ d.attention.length === 1 ? '' : 's' }} need you now
                </h2>
                <span class="badge badge-sm badge-error">
                  {{ d.attention.filter(item => item.severity >= 3).length }}
                </span>
                <div class="flex-1"></div>
                <button class="btn btn-xs btn-ghost" @click="d.setSection('blockers')">
                  All blockers <i class="fa-solid fa-chevron-right ml-1"></i>
                </button>
              </div>
              <div class="mt-2 space-y-1.5">
                <button v-for="item in d.attention.slice(0, 4)" :key="item.task.id"
                        class="w-full flex items-center gap-2 rounded-lg px-2 py-1.5 text-left bg-base-100/60 hover:bg-base-100 transition-colors"
                        @click="d.openTask(item.task.id)">
                  <span class="w-2 h-2 rounded-full shrink-0"
                        :class="item.severity >= 3 ? 'bg-error' : item.severity >= 2 ? 'bg-warning' : 'bg-info'"></span>
                  <span class="min-w-0 flex-1">
                    <span class="block text-xs font-semibold truncate">{{ item.task.name }}</span>
                    <span class="flex items-center gap-1 min-w-0 text-[11px] opacity-60">
                      <ProjectTag :project-id="item.task.project_id" :name="item.task.project_name"
                                  :color="item.task.project_color" size="xxs" class="shrink-0" />
                      <span class="truncate">
                        · {{ reasonLabel(item.reason) }}
                        <template v-if="item.task.block_reason"> · {{ item.task.block_reason }}</template>
                        · {{ d.dueLabel(item.task).text }}
                      </span>
                    </span>
                  </span>
                  <span class="badge badge-xs" :class="d.REASON_META[item.reason]?.badge">{{ reasonLabel(item.reason) }}</span>
                  <i class="fa-solid fa-chevron-right text-[10px] opacity-40"></i>
                </button>
              </div>
            </section>

            <section v-else class="rounded-box border border-success/40 bg-success/10 p-3 flex items-center gap-2">
              <i class="fa-solid fa-circle-check text-success"></i>
              <div>
                <div class="text-sm font-bold">Nothing urgent — delivery is running as planned.</div>
                <div class="text-xs opacity-70">
                  {{ d.metrics.active }} active · {{ d.metrics.done }} completed · next demo
                  {{ d.nextDemo ? d.fmtDate(d.nextDemo.demo_date) : 'not scheduled' }}
                </div>
              </div>
            </section>

            <!-- KPIs -->
            <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-2.5">
              <button class="rounded-box border border-base-300 bg-base-200 p-2.5 text-left hover:border-primary/50"
                      @click="d.setSection('work')">
                <div class="text-[10px] uppercase tracking-wide opacity-60">Active work</div>
                <div class="text-2xl font-bold leading-tight">{{ d.metrics.active }}</div>
                <div class="text-[11px] opacity-60">{{ d.metrics.total }} tasks in window</div>
              </button>
              <button class="rounded-box border bg-base-200 p-2.5 text-left hover:border-primary/50"
                      :class="d.metrics.blocked ? 'border-error/40' : 'border-base-300'"
                      @click="d.setSection('blockers')">
                <div class="text-[10px] uppercase tracking-wide opacity-60">Blocked</div>
                <div class="text-2xl font-bold leading-tight" :class="d.metrics.blocked ? 'text-error' : ''">{{ d.metrics.blocked }}</div>
                <div class="text-[11px] opacity-60">
                  {{ d.metrics.blocked ? 'oldest ' + d.oldestBlocker + 'd' : 'nothing blocked' }}
                </div>
              </button>
              <button class="rounded-box border bg-base-200 p-2.5 text-left hover:border-primary/50"
                      :class="d.metrics.overdue ? 'border-error/40' : 'border-base-300'"
                      @click="d.setSection('blockers')">
                <div class="text-[10px] uppercase tracking-wide opacity-60">Overdue</div>
                <div class="text-2xl font-bold leading-tight" :class="d.metrics.overdue ? 'text-error' : ''">{{ d.metrics.overdue }}</div>
                <div class="text-[11px] opacity-60">{{ d.metrics.due_today }} due today</div>
              </button>
              <button class="rounded-box border border-base-300 bg-base-200 p-2.5 text-left hover:border-primary/50"
                      @click="d.setSection('work')">
                <div class="text-[10px] uppercase tracking-wide opacity-60">Completed</div>
                <div class="text-2xl font-bold leading-tight text-success">{{ d.metrics.done }}</div>
                <div class="text-[11px] opacity-60">{{ d.metrics.completion }}% of scope</div>
              </button>
              <button class="rounded-box border bg-base-200 p-2.5 text-left hover:border-primary/50"
                      :class="d.atRiskBoards.length ? 'border-warning/40' : 'border-base-300'"
                      @click="d.setSection('delivery')">
                <div class="text-[10px] uppercase tracking-wide opacity-60">Demos in window</div>
                <div class="text-2xl font-bold leading-tight">{{ d.milestones.length }}</div>
                <div class="text-[11px] opacity-60">
                  {{ d.nextDemo ? 'next ' + d.fmtDate(d.nextDemo.demo_date) : 'none scheduled' }}
                </div>
              </button>
              <button class="rounded-box border bg-base-200 p-2.5 text-left hover:border-primary/50"
                      :class="d.data.cost && d.data.cost.budget.pct > 100 ? 'border-error/40' : 'border-base-300'"
                      @click="d.setSection('cost')">
                <div class="text-[10px] uppercase tracking-wide opacity-60">AI spend</div>
                <div class="text-2xl font-bold leading-tight">{{ d.fmtCoins(d.data.cost?.total.total_cxjcoins) }}</div>
                <div class="text-[11px] opacity-60">{{ d.data.cost?.budget.pct ?? 0 }}% of weekly budget</div>
              </button>
            </div>

            <div class="grid gap-3 xl:grid-cols-3 items-start">
              <div class="xl:col-span-2 space-y-3">
                <!-- delivering now -->
                <section class="rounded-box border border-base-300 bg-base-200 p-3">
                  <div class="flex items-center gap-2 mb-2">
                    <h2 class="text-sm font-semibold flex items-center gap-2">
                      <i class="fa-solid fa-rocket text-primary"></i> Delivering now
                    </h2>
                    <div class="flex-1"></div>
                    <button class="btn btn-xs btn-ghost" @click="d.setSection('delivery')">
                      Forecast <i class="fa-solid fa-chevron-right ml-1"></i>
                    </button>
                  </div>
                  <p v-if="!d.forecast.length" class="text-xs opacity-60">Nothing scheduled in this window.</p>
                  <button v-for="board in d.forecast.slice(0, 5)" :key="board.board_id"
                          class="w-full text-left rounded-lg px-2 py-1.5 hover:bg-base-300/60"
                          @click="d.setSection('delivery')">
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-semibold truncate flex-1">{{ board.board }}</span>
                      <span class="badge badge-xs" :class="forecastBadge(board.status)">{{ forecastLabel(board.status) }}</span>
                      <i class="fa-solid fa-chevron-right text-[10px] opacity-40"></i>
                    </div>
                    <div class="flex items-center gap-1 min-w-0 text-[11px] opacity-60">
                      <ProjectTag :project-id="board.project_id" :name="board.project_name" size="xxs" class="shrink-0" />
                      <span class="truncate">· {{ board.done }}/{{ board.committed }} done · ETA {{ d.fmtDate(board.eta_date) }}</span>
                    </div>
                    <progress class="progress w-full h-1.5" :class="forecastProgress(board.status)"
                              :value="board.percentage" max="100"></progress>
                  </button>
                </section>

                <!-- attention -->
                <section class="rounded-box border border-base-300 bg-base-200 p-3">
                  <div class="flex items-center gap-2 mb-2">
                    <h2 class="text-sm font-semibold flex items-center gap-2">
                      <i class="fa-solid fa-circle-exclamation text-warning"></i> Needs attention
                    </h2>
                    <span class="badge badge-xs badge-ghost">{{ d.attention.length }}</span>
                    <div class="flex-1"></div>
                    <button class="btn btn-xs btn-ghost" @click="d.setSection('blockers')">
                      See all <i class="fa-solid fa-chevron-right ml-1"></i>
                    </button>
                  </div>
                  <p v-if="!d.attention.length" class="text-xs opacity-60">
                    No overdue, blocked or unowned work in this window.
                  </p>
                  <button v-for="item in d.attention.slice(0, 6)" :key="'a-' + item.task.id"
                          class="w-full flex items-center gap-2 text-left rounded-lg px-2 py-1.5 hover:bg-base-300/60"
                          @click="d.openTask(item.task.id)">
                    <span class="min-w-0 flex-1">
                      <span class="block text-xs font-medium truncate">{{ item.task.name }}</span>
                      <span class="flex items-center gap-1 min-w-0 text-[11px] opacity-60">
                        <ProjectTag :project-id="item.task.project_id" :name="item.task.project_name"
                                    :color="item.task.project_color" size="xxs" class="shrink-0" />
                        <span class="truncate">
                          · {{ item.task.board }} · {{ item.task.assignee_names[0] || 'unassigned' }} ·
                          {{ d.dueLabel(item.task).text }}
                        </span>
                      </span>
                    </span>
                    <span class="badge badge-xs" :class="d.REASON_META[item.reason]?.badge">{{ reasonLabel(item.reason) }}</span>
                  </button>
                </section>
              </div>

              <div class="space-y-3">
                <!-- team load -->
                <section class="rounded-box border border-base-300 bg-base-200 p-3">
                  <div class="flex items-center gap-2 mb-2">
                    <h2 class="text-sm font-semibold flex items-center gap-2">
                      <i class="fa-solid fa-people-group text-info"></i> Team load
                    </h2>
                    <div class="flex-1"></div>
                    <button class="btn btn-xs btn-ghost" @click="d.setSection('team')">
                      Team <i class="fa-solid fa-chevron-right ml-1"></i>
                    </button>
                  </div>
                  <div v-for="person in topLoadedPeople" :key="person.id" class="py-1">
                    <div class="flex items-center gap-2">
                      <span class="w-6 h-6 rounded-full grid place-items-center text-[9px] font-bold text-white shrink-0"
                            :style="{ background: d.personColor(person.id) }">{{ d.initials(person.name) }}</span>
                      <span class="min-w-0 flex-1">
                        <span class="block text-xs font-medium truncate">{{ person.name }}</span>
                        <span class="block text-[10px] opacity-60 truncate">
                          {{ person.role }} · {{ person.active }} active<template v-if="person.blocked"> · {{ person.blocked }} blocked</template>
                        </span>
                      </span>
                      <span class="text-[11px] font-mono" :class="loadTone(person.load_pct)">{{ person.load_pct }}%</span>
                    </div>
                    <progress class="progress w-full h-1" :class="loadProgress(person.load_pct)"
                              :value="Math.min(100, person.load_pct)" max="100"></progress>
                    <div class="flex flex-wrap items-center gap-1 mt-0.5">
                      <ProjectTag v-for="project in d.memberProjects(person)" :key="project.id"
                                  :project="project" size="xxs" muted />
                    </div>
                  </div>
                </section>

                <!-- activity -->
                <section class="rounded-box border border-base-300 bg-base-200 p-3">
                  <h2 class="text-sm font-semibold flex items-center gap-2 mb-2">
                    <i class="fa-solid fa-clock-rotate-left text-primary"></i> Activity
                  </h2>
                  <p v-if="!d.activity.length" class="text-xs opacity-60">Nothing changed in this window.</p>
                  <button v-for="entry in d.activity.slice(0, 7)" :key="entry.id"
                          class="w-full flex items-center gap-2 text-left rounded-lg px-1 py-1 hover:bg-base-300/60"
                          @click="d.openTask(entry.task_id)">
                    <span class="w-1.5 h-1.5 rounded-full shrink-0" :class="toneDot(entry.tone)"></span>
                    <span class="min-w-0 flex-1">
                      <span class="block text-[11px] truncate">
                        <strong>{{ entry.actor }}</strong> {{ entry.action }}
                      </span>
                      <span class="flex items-center gap-1 min-w-0 text-[10px] opacity-60">
                        <ProjectTag :project-id="entry.project_id" :name="entry.project_name"
                                    :color="entry.project_color" size="xxs" class="shrink-0" />
                        <span class="truncate">· {{ entry.task_name }} · {{ entry.board }}</span>
                      </span>
                    </span>
                    <span class="text-[10px] opacity-50 whitespace-nowrap">{{ d.relTime(entry.timestamp) }}</span>
                  </button>
                </section>

                <!-- AI spend -->
                <section class="rounded-box border border-base-300 bg-base-200 p-3">
                  <div class="flex items-center gap-2 mb-2">
                    <h2 class="text-sm font-semibold flex items-center gap-2">
                      <i class="fa-solid fa-coins text-warning"></i> AI spend trend
                    </h2>
                    <div class="flex-1"></div>
                    <button class="btn btn-xs btn-ghost" @click="d.setSection('cost')">
                      Cost <i class="fa-solid fa-chevron-right ml-1"></i>
                    </button>
                  </div>
                  <div class="text-lg font-bold">{{ d.fmtCoins(d.data.cost?.total.total_cxjcoins) }}</div>
                  <div class="text-[11px] opacity-60 mb-2">{{ d.rangeLabel }}</div>
                  <div class="flex items-end gap-1 h-14" aria-hidden="true">
                    <i v-for="(point, index) in spendBars" :key="index"
                       class="flex-1 rounded-t bg-primary/70" :style="{ height: point }"></i>
                  </div>
                </section>
              </div>
            </div>
          </div>

          <!-- ════════════════════ WORK ════════════════════ -->
          <div v-else-if="d.state.section === 'work'" class="space-y-3">
            <section class="rounded-box border border-base-300 bg-base-200 p-3">
              <div class="flex items-center gap-2 mb-2">
                <h2 class="text-sm font-semibold">All work in the window</h2>
                <span class="badge badge-xs badge-ghost">{{ d.data.tasks?.total || 0 }}</span>
                <div class="flex-1"></div>
                <button class="btn btn-xs" @click="d.setSection('blockers')">
                  <i class="fa-solid fa-triangle-exclamation"></i> Blockers
                </button>
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <label class="input input-sm input-bordered flex items-center gap-2 grow min-w-40">
                  <i class="fa-solid fa-magnifying-glass opacity-50"></i>
                  <input type="search" class="grow" placeholder="Search tasks…" :value="d.state.filters.work.search"
                         @input="onWorkSearch($event)" />
                </label>
                <select class="select select-sm select-bordered" :value="d.state.filters.work.project_id"
                        aria-label="Project" @change="applyFilter('work', { project_id: $event.target.value })">
                  <option value="">All projects in scope</option>
                  <option v-for="project in d.data.projects" :key="project.id" :value="project.id">{{ project.name }}</option>
                </select>
                <select class="select select-sm select-bordered" :value="d.state.filters.work.board_id"
                        aria-label="Board" @change="applyFilter('work', { board_id: $event.target.value })">
                  <option value="">All boards</option>
                  <option v-for="board in d.data.boards" :key="board.id" :value="board.id">{{ board.name }}</option>
                </select>
                <select class="select select-sm select-bordered" :value="d.state.filters.work.status"
                        aria-label="Status" @change="applyFilter('work', { status: $event.target.value })">
                  <option value="">All statuses</option>
                  <option v-for="(meta, key) in d.STATUS_META" :key="key" :value="key">{{ meta.label }}</option>
                </select>
                <select class="select select-sm select-bordered" :value="d.state.filters.work.priority"
                        aria-label="Priority" @change="applyFilter('work', { priority: $event.target.value })">
                  <option value="">All priorities</option>
                  <option v-for="(meta, key) in d.PRIORITY_META" :key="key" :value="key">{{ meta.label }}</option>
                </select>
                <select class="select select-sm select-bordered" :value="d.state.filters.work.assignee"
                        aria-label="Assignee" @change="applyFilter('work', { assignee: $event.target.value })">
                  <option value="">Anyone</option>
                  <option v-for="person in d.data.people" :key="person.id" :value="person.id">{{ person.name }}</option>
                </select>
                <button class="btn btn-sm btn-ghost" @click="d.clearFilters('work')">
                  <i class="fa-solid fa-eraser"></i> Clear
                </button>
              </div>
            </section>

            <section class="rounded-box border border-base-300 bg-base-200 overflow-hidden">
              <p v-if="!d.workTasks.length" class="p-6 text-center text-sm opacity-60">
                No tasks match these filters. Widen the time range, add projects to the filter or clear the filters.
              </p>

              <!-- table (wide) -->
              <div v-else-if="!compact" class="overflow-x-auto">
                <table class="table table-sm w-full">
                  <thead>
                    <tr>
                      <th scope="col" class="cursor-pointer" @click="sortWork('name')">Task <i v-if="d.state.filters.work.sort === 'name'" :class="sortIcon()"></i></th>
                      <th scope="col" class="cursor-pointer" @click="sortWork('project')">Project <i v-if="d.state.filters.work.sort === 'project'" :class="sortIcon()"></i></th>
                      <th scope="col">Board</th>
                      <th scope="col" class="cursor-pointer" @click="sortWork('status')">Status <i v-if="d.state.filters.work.sort === 'status'" :class="sortIcon()"></i></th>
                      <th scope="col" class="cursor-pointer" @click="sortWork('priority')">Priority <i v-if="d.state.filters.work.sort === 'priority'" :class="sortIcon()"></i></th>
                      <th scope="col">Owner</th>
                      <th scope="col" class="cursor-pointer" @click="sortWork('due_date')">Due <i v-if="d.state.filters.work.sort === 'due_date'" :class="sortIcon()"></i></th>
                      <th scope="col">Progress</th>
                      <th scope="col" class="cursor-pointer" @click="sortWork('updated_at')">Updated <i v-if="d.state.filters.work.sort === 'updated_at'" :class="sortIcon()"></i></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="task in d.workTasks" :key="task.id" class="hover cursor-pointer" @click="d.openTask(task.id)">
                      <td class="max-w-72">
                        <div class="text-xs font-semibold truncate">{{ task.name }}</div>
                        <div class="text-[10px] opacity-60 truncate">
                          {{ task.blocked ? '⛔ ' + task.block_reason : (task.tags || []).join(' · ') || '—' }}
                        </div>
                      </td>
                      <td>
                        <ProjectTag :project-id="task.project_id" :name="task.project_name"
                                    :color="task.project_color" size="xs" />
                      </td>
                      <td class="text-[11px] opacity-60">{{ task.board }}</td>
                      <td><span class="badge badge-xs" :class="d.STATUS_META[task.status]?.badge">{{ d.STATUS_META[task.status]?.label }}</span></td>
                      <td><span class="badge badge-xs" :class="d.PRIORITY_META[task.priority]?.badge">{{ d.PRIORITY_META[task.priority]?.label }}</span></td>
                      <td class="text-[11px]">{{ task.assignee_names[0] || 'unassigned' }}</td>
                      <td class="text-[11px]" :class="d.dueLabel(task).tone">{{ d.dueLabel(task).text }}</td>
                      <td class="min-w-20">
                        <div class="flex items-center gap-1">
                          <progress class="progress w-16 h-1.5" :class="task.progress === 100 ? 'progress-success' : 'progress-primary'"
                                    :value="task.progress" max="100"></progress>
                          <span class="text-[10px] opacity-60 font-mono">{{ task.progress }}%</span>
                        </div>
                      </td>
                      <td class="text-[10px] opacity-60 whitespace-nowrap">{{ d.relTime(task.updated_at) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- cards (narrow) -->
              <div v-else class="p-2 space-y-2">
                <button v-for="task in d.workTasks" :key="'c-' + task.id"
                        class="w-full text-left rounded-lg border border-base-300 bg-base-100 p-2.5"
                        @click="d.openTask(task.id)">
                  <div class="flex items-start gap-2">
                    <span class="text-xs font-semibold flex-1 min-w-0">{{ task.name }}</span>
                    <span class="badge badge-xs" :class="d.PRIORITY_META[task.priority]?.badge">{{ d.PRIORITY_META[task.priority]?.label }}</span>
                  </div>
                  <div class="flex flex-wrap items-center gap-1.5 mt-1.5">
                    <span class="badge badge-xs" :class="d.STATUS_META[task.status]?.badge">{{ d.STATUS_META[task.status]?.label }}</span>
                    <ProjectTag :project-id="task.project_id" :name="task.project_name"
                                :color="task.project_color" size="xxs" />
                    <span class="text-[10px]" :class="d.dueLabel(task).tone">{{ d.dueLabel(task).text }}</span>
                    <span class="text-[10px] opacity-60">{{ task.assignee_names[0] || 'unassigned' }}</span>
                  </div>
                  <div v-if="task.blocked" class="mt-1.5 text-[10px] text-error">⛔ {{ task.block_reason }}</div>
                </button>
              </div>

              <!-- pager -->
              <div v-if="d.data.tasks?.total" class="flex flex-wrap items-center gap-2 p-2 border-t border-base-300">
                <span class="text-[11px] opacity-60">
                  Showing <strong>{{ d.workPager.start }}–{{ d.workPager.end }}</strong> of {{ d.workPager.total }}
                </span>
                <div class="flex-1"></div>
                <div class="join">
                  <button class="btn btn-xs join-item" :disabled="!d.workPager.hasPrev" @click="goToPage(d.workPager.page - 1)">
                    <i class="fa-solid fa-chevron-left"></i>
                  </button>
                  <template v-for="(page, index) in d.workPager.pages" :key="index">
                    <button v-if="page !== '…'" class="btn btn-xs join-item"
                            :class="page === d.workPager.page ? 'btn-primary' : ''"
                            @click="goToPage(page)">{{ page }}</button>
                    <span v-else class="btn btn-xs join-item btn-disabled">…</span>
                  </template>
                  <button class="btn btn-xs join-item" :disabled="!d.workPager.hasNext" @click="goToPage(d.workPager.page + 1)">
                    <i class="fa-solid fa-chevron-right"></i>
                  </button>
                </div>
              </div>
            </section>
          </div>

          <!-- ════════════════════ BLOCKERS ════════════════════ -->
          <div v-else-if="d.state.section === 'blockers'" class="space-y-3">
            <section class="rounded-box border border-base-300 bg-base-200 p-3">
              <div class="flex flex-wrap items-center gap-2 mb-2">
                <div class="min-w-0 flex-1">
                  <h2 class="text-sm font-semibold">Attention queue</h2>
                  <p class="text-[11px] opacity-60">Blocked, overdue, due today, stalled or unowned work — most severe first</p>
                </div>
                <select class="select select-sm select-bordered" :value="d.state.filters.blockers.project_id"
                        aria-label="Project" @change="applyFilter('blockers', { project_id: $event.target.value })">
                  <option value="">All projects in scope</option>
                  <option v-for="project in d.data.projects" :key="project.id" :value="project.id">{{ project.name }}</option>
                </select>
              </div>
              <div class="flex flex-wrap gap-1.5">
                <button class="btn btn-xs" :class="d.state.filters.blockers.reason === 'all' ? 'btn-primary' : 'btn-ghost'"
                        @click="d.setFilter('blockers', { reason: 'all' })">
                  All ({{ d.attention.length }})
                </button>
                <button v-for="(meta, key) in d.REASON_META" :key="key" class="btn btn-xs"
                        :class="d.state.filters.blockers.reason === key ? 'btn-primary' : 'btn-ghost'"
                        @click="d.setFilter('blockers', { reason: key })">
                  {{ meta.label }} ({{ d.attentionCounts[key] || 0 }})
                </button>
              </div>
            </section>

            <p v-if="!d.filteredAttention.length" class="rounded-box border border-base-300 bg-base-200 p-6 text-center text-sm opacity-60">
              No items match this filter.
            </p>

            <article v-for="item in d.filteredAttention" :key="'b-' + item.task.id"
                     class="rounded-box border bg-base-200 p-3"
                     :class="item.reason === 'blocked' || item.reason === 'overdue' ? 'border-error/40' : 'border-base-300'">
              <div class="flex items-start gap-2">
                <span class="w-2 h-2 rounded-full mt-1.5 shrink-0"
                      :class="item.severity >= 3 ? 'bg-error' : item.severity >= 2 ? 'bg-warning' : 'bg-info'"></span>
                <div class="min-w-0 flex-1">
                  <button class="text-sm font-semibold text-left" @click="d.openTask(item.task.id)">{{ item.task.name }}</button>
                  <div class="flex flex-wrap items-center gap-1.5 mt-1.5">
                    <span class="badge badge-xs" :class="d.REASON_META[item.reason]?.badge">{{ reasonLabel(item.reason) }}</span>
                    <span class="badge badge-xs" :class="d.STATUS_META[item.task.status]?.badge">{{ d.STATUS_META[item.task.status]?.label }}</span>
                    <span class="badge badge-xs" :class="d.PRIORITY_META[item.task.priority]?.badge">{{ d.PRIORITY_META[item.task.priority]?.label }}</span>
                    <ProjectTag :project-id="item.task.project_id" :name="item.task.project_name"
                                :color="item.task.project_color" size="xs" muted />
                    <span class="text-[11px] opacity-60">{{ item.task.board }}</span>
                  </div>
                  <div v-if="item.task.block_reason"
                       class="mt-2 text-[11px] text-error bg-error/10 border border-error/20 rounded-lg px-2 py-1.5">
                    ⛔ {{ item.task.block_reason }}
                  </div>
                  <div class="flex flex-wrap items-center gap-2 mt-2 text-[11px] opacity-70">
                    <span>{{ item.task.assignee_names.join(', ') || 'unassigned' }}</span>
                    <span>· {{ item.task.blocked ? 'blocked ' + blockerAge(item.task) + 'd' : d.dueLabel(item.task).text }}</span>
                    <span>· updated {{ d.relTime(item.task.updated_at) }}</span>
                  </div>
                  <div class="flex flex-wrap items-center gap-1.5 mt-2.5">
                    <button class="btn btn-xs" @click="d.openTask(item.task.id)">Open</button>
                    <button class="btn btn-xs btn-ghost" @click="d.ask('What is blocking ' + item.task.name + '?')">
                      <i class="fa-solid fa-wand-magic-sparkles"></i> Ask for update
                    </button>
                    <button class="btn btn-xs btn-ghost" @click="startAssign(item.task.id)">
                      <i class="fa-solid fa-user"></i> Reassign
                    </button>
                    <button v-if="item.task.blocked" class="btn btn-xs btn-error btn-outline"
                            @click="d.patchTask(item.task.id, { blocked: false }, 'Unblocked')">
                      Unblock
                    </button>
                  </div>
                </div>
              </div>
            </article>
          </div>

          <!-- ════════════════════ DELIVERY ════════════════════ -->
          <div v-else-if="d.state.section === 'delivery'" class="space-y-3">
            <div class="grid grid-cols-2 md:grid-cols-3 gap-2.5">
              <div class="rounded-box border border-base-300 bg-base-200 p-2.5">
                <div class="text-[10px] uppercase tracking-wide opacity-60">Boards tracked</div>
                <div class="text-2xl font-bold">{{ d.forecast.length }}</div>
                <div class="text-[11px] opacity-60">across {{ d.projects.length }} projects</div>
              </div>
              <div class="rounded-box border bg-base-200 p-2.5" :class="d.atRiskBoards.length ? 'border-warning/40' : 'border-base-300'">
                <div class="text-[10px] uppercase tracking-wide opacity-60">At risk</div>
                <div class="text-2xl font-bold" :class="d.atRiskBoards.length ? 'text-warning' : ''">{{ d.atRiskBoards.length }}</div>
                <div class="text-[11px] opacity-60">behind target or blocked</div>
              </div>
              <div class="rounded-box border border-base-300 bg-base-200 p-2.5">
                <div class="text-[10px] uppercase tracking-wide opacity-60">Next demo</div>
                <div class="text-2xl font-bold">{{ d.nextDemo ? d.fmtDate(d.nextDemo.demo_date) : '—' }}</div>
                <div class="text-[11px] opacity-60">management walkthrough</div>
              </div>
            </div>

            <section class="rounded-box border border-base-300 bg-base-200 p-3">
              <h2 class="text-sm font-semibold mb-1">Forecast per board</h2>
              <p class="text-[11px] opacity-60 mb-3">
                Velocity is measured inside the selected window ({{ d.rangeLabel }}) — the dates below are based on it.
              </p>
              <div class="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
                <article v-for="board in d.forecast" :key="board.board_id"
                         class="rounded-lg border border-base-300 bg-base-100 p-2.5">
                  <div class="flex items-start gap-2">
                    <div class="min-w-0 flex-1">
                      <div class="text-xs font-bold truncate">{{ board.board }}</div>
                      <div class="flex items-center gap-1 min-w-0 text-[10px] opacity-60">
                        <ProjectTag :project-id="board.project_id" :name="board.project_name" size="xxs" class="shrink-0" />
                        <span class="truncate">· {{ board.type }}</span>
                      </div>
                    </div>
                    <span class="badge badge-xs" :class="forecastBadge(board.status)">{{ forecastLabel(board.status) }}</span>
                  </div>
                  <progress class="progress w-full h-2 my-2" :class="forecastProgress(board.status)"
                            :value="board.percentage" max="100"></progress>
                  <div class="flex items-center justify-between text-[11px] opacity-70">
                    <span>{{ board.done }}/{{ board.committed }} done</span>
                    <span class="font-mono">{{ board.percentage }}%</span>
                  </div>
                  <div class="grid grid-cols-2 gap-1.5 mt-2 text-[11px]">
                    <div><span class="opacity-50">ETA</span> {{ d.fmtDate(board.eta_date) }}</div>
                    <div><span class="opacity-50">Target</span> {{ d.fmtDate(board.target_date) }}</div>
                    <div><span class="opacity-50">Velocity</span> {{ board.velocity }}/wk</div>
                    <div><span class="opacity-50">Confidence</span> {{ board.confidence }}</div>
                  </div>
                  <div class="mt-2 text-[11px]" :class="board.blocked ? 'text-error' : 'opacity-60'">
                    {{ board.blocked ? '⛔ ' + board.blocked + ' blocked task(s) drag the forecast' : 'Remaining: ' + board.remaining + ' task(s), no blockers' }}
                  </div>
                  <div v-if="board.demo_date" class="mt-1.5">
                    <span class="badge badge-xs badge-primary">Demo {{ d.fmtDate(board.demo_date) }}</span>
                  </div>
                </article>
              </div>
            </section>

            <div class="grid gap-3 xl:grid-cols-2 items-start">
              <section class="rounded-box border border-base-300 bg-base-200 p-3">
                <div class="flex items-center gap-2 mb-2">
                  <div class="min-w-0 flex-1">
                    <h2 class="text-sm font-semibold">Burndown</h2>
                    <p class="text-[11px] opacity-60">
                      {{ d.data.burndown?.board }} · last 14 days · {{ d.data.burndown?.total || 0 }} tasks
                    </p>
                  </div>
                  <select class="select select-xs select-bordered w-40" :value="d.state.filters.delivery.board_id"
                          aria-label="Board" @change="applyFilter('delivery', { board_id: $event.target.value })">
                    <option v-for="board in d.forecast" :key="board.board_id" :value="board.board_id">{{ board.board }}</option>
                  </select>
                </div>
                <svg :viewBox="`0 0 ${d.burndownChart.width} ${d.burndownChart.height}`" class="w-full h-40">
                  <line x1="10" y1="10" :x2="d.burndownChart.width - 10" y2="10" class="stroke-base-content/10" stroke-width="1" />
                  <line x1="10" :y1="d.burndownChart.height / 2" :x2="d.burndownChart.width - 10" :y2="d.burndownChart.height / 2"
                        class="stroke-base-content/10" stroke-width="1" />
                  <path :d="d.burndownChart.ideal" fill="none" class="stroke-base-content/40" stroke-width="2" stroke-dasharray="5 5" />
                  <path :d="d.burndownChart.actual" fill="none" class="stroke-primary" stroke-width="2.5" stroke-linejoin="round" />
                </svg>
                <div class="flex items-center gap-3 text-[11px] opacity-70">
                  <span class="inline-flex items-center gap-1"><span class="w-2 h-2 rounded-sm bg-base-content/40"></span>Ideal</span>
                  <span class="inline-flex items-center gap-1"><span class="w-2 h-2 rounded-sm bg-primary"></span>Actual remaining</span>
                </div>
              </section>

              <section class="rounded-box border border-base-300 bg-base-200 p-3">
                <h2 class="text-sm font-semibold mb-2">Milestones &amp; demos</h2>
                <p v-if="!d.milestones.length" class="text-xs opacity-60">No demos scheduled in this window.</p>
                <div v-else class="overflow-x-auto">
                  <table class="table table-xs w-full">
                    <thead>
                      <tr>
                        <th scope="col">Sprint</th>
                        <th scope="col">Project</th>
                        <th scope="col">Demo</th>
                        <th scope="col">Done</th>
                        <th scope="col">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="board in d.milestones" :key="'m-' + board.board_id" class="hover">
                        <td class="font-semibold max-w-40 truncate">{{ board.board }}</td>
                        <td><ProjectTag :project-id="board.project_id" :name="board.project_name" size="xxs" muted /></td>
                        <td class="text-[11px]">{{ d.fmtDate(board.demo_date) }}</td>
                        <td class="text-[11px]">{{ board.done }}/{{ board.committed }}</td>
                        <td><span class="badge badge-xs" :class="forecastBadge(board.status)">{{ forecastLabel(board.status) }}</span></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          </div>

          <!-- ════════════════════ TEAM ════════════════════ -->
          <div v-else-if="d.state.section === 'team'" class="space-y-3">
            <section class="rounded-box border border-base-300 bg-base-200 p-3">
              <div class="flex flex-wrap items-center gap-2">
                <div class="min-w-0 flex-1">
                  <h2 class="text-sm font-semibold">Capacity</h2>
                  <p class="text-[11px] opacity-60">
                    Average human load {{ d.teamSummary.averageLoad }}% ·
                    {{ d.teamSummary.overloaded }} above 85% ·
                    {{ d.teamSummary.agents }} AI agent(s) ·
                    {{ d.fmtCoins(d.teamSummary.cost) }} attributed AI cost
                  </p>
                </div>
                <select class="select select-sm select-bordered" :value="d.state.filters.team.type"
                        aria-label="Member type" @change="d.setFilter('team', { type: $event.target.value })">
                  <option value="all">Everyone</option>
                  <option value="human">Humans</option>
                  <option value="agent">AI agents</option>
                </select>
                <select class="select select-sm select-bordered" :value="d.state.filters.team.project_id"
                        aria-label="Project" @change="d.setFilter('team', { project_id: $event.target.value })">
                  <option value="">All projects in scope</option>
                  <option v-for="project in d.data.projects" :key="project.id" :value="project.id">{{ project.name }}</option>
                </select>
                <button class="btn btn-sm" :class="d.state.filters.team.onlyHot ? 'btn-primary' : 'btn-ghost'"
                        @click="d.setFilter('team', { onlyHot: !d.state.filters.team.onlyHot })">
                  <i class="fa-solid fa-triangle-exclamation"></i> Overloaded only
                </button>
                <button class="btn btn-sm btn-ghost" @click="d.clearFilters('team')">Clear</button>
              </div>
            </section>

            <p v-if="!d.teamMembers.length" class="rounded-box border border-base-300 bg-base-200 p-6 text-center text-sm opacity-60">
              No team member matches these filters.
            </p>

            <div v-else class="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
              <button v-for="person in d.teamMembers" :key="person.id"
                      class="text-left rounded-box border border-base-300 bg-base-200 p-3 hover:border-primary/50"
                      @click="d.openMember(person.id)">
                <div class="flex items-center gap-2">
                  <span class="w-8 h-8 rounded-full grid place-items-center text-[11px] font-bold text-white shrink-0"
                        :style="{ background: person.type === 'agent' ? '#7c3aed' : d.personColor(person.id) }">
                    {{ d.initials(person.name) }}
                  </span>
                  <div class="min-w-0 flex-1">
                    <div class="text-xs font-bold truncate">{{ person.name }}</div>
                    <div class="text-[10px] opacity-60 truncate">
                      {{ person.role }}<template v-if="person.type === 'agent'"> · AI</template>
                    </div>
                  </div>
                  <span class="text-xs font-bold font-mono" :class="loadTone(person.load_pct)">{{ person.load_pct }}%</span>
                </div>
                <progress class="progress w-full h-1.5 my-2" :class="loadProgress(person.load_pct)"
                          :value="Math.min(100, person.load_pct)" max="100"></progress>
                <div class="flex flex-wrap items-center gap-1 mb-2">
                  <ProjectTag v-for="project in d.memberProjects(person)" :key="'p-' + project.id"
                              :project="project" size="xxs" muted />
                </div>
                <div class="grid grid-cols-3 gap-1 text-center">
                  <div class="rounded bg-base-100 py-1">
                    <div class="text-sm font-bold font-mono">{{ person.active }}</div>
                    <div class="text-[9px] uppercase opacity-50">active</div>
                  </div>
                  <div class="rounded bg-base-100 py-1">
                    <div class="text-sm font-bold font-mono" :class="person.blocked ? 'text-error' : ''">{{ person.blocked }}</div>
                    <div class="text-[9px] uppercase opacity-50">blocked</div>
                  </div>
                  <div class="rounded bg-base-100 py-1">
                    <div class="text-sm font-bold font-mono text-success">{{ person.done }}</div>
                    <div class="text-[9px] uppercase opacity-50">done</div>
                  </div>
                </div>
                <div class="mt-2 text-[10px] opacity-60">
                  {{ person.type === 'human' ? person.hours + 'h / ' + person.capacity_h + 'h allocated' : 'agent · ' + person.active + ' tasks' }}
                  · {{ d.fmtCoins(person.cost_cxjcoins) }}
                </div>
              </button>
            </div>
          </div>

          <!-- ════════════════════ COST & AI ════════════════════ -->
          <!-- The whole spend/AI screen is the shared analytics dashboard, so the
               product keeps ONE implementation of totals, tokens, models,
               per-user/per-project breakdowns and pricing. It brings its own
               header, filters and scroll area, hence the full-bleed slot. -->
          <div v-else-if="d.state.section === 'cost'" class="h-full min-h-0">
            <MetricsDashboard />
          </div>
        </template>
      </main>
    </div>

    <!-- ════════════════ TASK DRAWER ════════════════ -->
    <div v-if="d.selectedTask" class="fixed inset-0 z-50 flex justify-end">
      <div class="absolute inset-0 bg-black/60" @click="d.closeOverlays()"></div>
      <aside class="relative w-full max-w-md h-full bg-base-100 border-l border-base-300 flex flex-col shadow-2xl">
        <header class="flex items-start gap-2 p-3 border-b border-base-300">
          <div class="min-w-0 flex-1">
            <div class="text-sm font-bold leading-snug">{{ d.selectedTask.name }}</div>
            <div class="flex items-center gap-1 min-w-0 text-[11px] opacity-60 mt-1">
              <ProjectTag :project-id="d.selectedTask.project_id" :name="d.selectedTask.project_name"
                          :color="d.selectedTask.project_color" size="xxs" class="shrink-0" />
              <span class="truncate">
                · {{ d.selectedTask.board }} · updated {{ d.relTime(d.selectedTask.updated_at) }}
              </span>
            </div>
          </div>
          <button class="btn btn-ghost btn-sm btn-square" aria-label="Close" @click="d.closeOverlays()">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </header>

        <div class="flex-1 overflow-y-auto p-3 space-y-3">
          <div v-if="d.selectedTask.blocked" class="alert alert-error py-2 text-xs">
            <i class="fa-solid fa-triangle-exclamation"></i>
            <div>
              <div class="font-bold">Blocked</div>
              <div class="opacity-80">{{ d.selectedTask.block_reason }}</div>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-2">
            <label class="block">
              <span class="text-[10px] uppercase opacity-60">Status</span>
              <select class="select select-sm select-bordered w-full" :value="d.selectedTask.status"
                      @change="d.patchTask(d.selectedTask.id, { status: $event.target.value }, 'Status updated')">
                <option v-for="(meta, key) in d.STATUS_META" :key="key" :value="key">{{ meta.label }}</option>
              </select>
            </label>
            <label class="block">
              <span class="text-[10px] uppercase opacity-60">Priority</span>
              <select class="select select-sm select-bordered w-full" :value="d.selectedTask.priority"
                      @change="d.patchTask(d.selectedTask.id, { priority: $event.target.value }, 'Priority updated')">
                <option v-for="(meta, key) in d.PRIORITY_META" :key="key" :value="key">{{ meta.label }}</option>
              </select>
            </label>
            <label class="block">
              <span class="text-[10px] uppercase opacity-60">Due date</span>
              <input type="date" class="input input-sm input-bordered w-full" :value="d.selectedTask.due_date"
                     @change="d.patchTask(d.selectedTask.id, { due_date: $event.target.value }, 'Due date updated')" />
            </label>
            <div>
              <span class="text-[10px] uppercase opacity-60">Due</span>
              <div class="text-sm font-semibold" :class="d.dueLabel(d.selectedTask).tone">{{ d.dueLabel(d.selectedTask).text }}</div>
              <div class="text-[10px] opacity-60">
                {{ d.selectedTask.column || d.selectedTask.board || '—' }}
              </div>
            </div>
          </div>

          <div>
            <div class="flex items-center justify-between text-[10px] uppercase opacity-60">
              <span>Progress</span>
              <span>{{ d.selectedTask.progress }}%</span>
            </div>
            <input type="range" min="0" max="100" step="5" class="range range-xs range-primary w-full"
                   :value="d.selectedTask.progress"
                   @change="d.patchTask(d.selectedTask.id, { progress: Number($event.target.value) }, 'Progress updated')" />
          </div>

          <div>
            <div class="text-[10px] uppercase opacity-60 mb-1">Assignees</div>
            <div class="flex flex-wrap items-center gap-1.5">
              <span v-for="(person, index) in d.selectedTask.assignees_info" :key="index" class="badge badge-sm badge-primary">
                {{ person.name }}
              </span>
              <span v-if="!d.selectedTask.assignees_info.length" class="badge badge-sm badge-ghost">unassigned</span>
              <button class="btn btn-xs btn-ghost" @click="startAssign(d.selectedTask.id)">
                <i class="fa-solid fa-user"></i> Change
              </button>
            </div>
          </div>

          <div class="text-[11px] opacity-60">
            Tags: {{ (d.selectedTask.tags || []).join(', ') || '—' }} ·
            {{ d.selectedTask.overdue ? 'overdue' : d.selectedTask.due_today ? 'due today' : 'on schedule' }}
          </div>
        </div>

        <footer class="p-3 border-t border-base-300 flex flex-wrap gap-1.5">
          <button class="btn btn-sm btn-primary" :disabled="d.selectedTask.status === 'done'"
                  @click="d.patchTask(d.selectedTask.id, { status: 'done', progress: 100 }, 'Marked as done')">
            <i class="fa-solid fa-check"></i> Mark done
          </button>
          <button class="btn btn-sm" @click="d.ask('What is blocking ' + d.selectedTask.name + '?')">
            <i class="fa-solid fa-wand-magic-sparkles"></i> Ask for update
          </button>
          <button v-if="d.selectedTask.blocked" class="btn btn-sm btn-error btn-outline"
                  @click="d.patchTask(d.selectedTask.id, { blocked: false }, 'Unblocked')">Unblock</button>
          <button class="btn btn-sm btn-ghost" @click="d.closeOverlays()">Close</button>
        </footer>
      </aside>
    </div>

    <!-- ════════════════ MEMBER DRAWER ════════════════ -->
    <div v-if="d.selectedMember" class="fixed inset-0 z-50 flex justify-end">
      <div class="absolute inset-0 bg-black/60" @click="d.closeOverlays()"></div>
      <aside class="relative w-full max-w-md h-full bg-base-100 border-l border-base-300 flex flex-col shadow-2xl">
        <header class="flex items-center gap-2 p-3 border-b border-base-300">
          <span class="w-9 h-9 rounded-full grid place-items-center text-xs font-bold text-white"
                :style="{ background: d.selectedMember.type === 'agent' ? '#7c3aed' : d.personColor(d.selectedMember.id) }">
            {{ d.initials(d.selectedMember.name) }}
          </span>
          <div class="min-w-0 flex-1">
            <div class="text-sm font-bold truncate">{{ d.selectedMember.name }}</div>
            <div class="text-[11px] opacity-60">
              {{ d.selectedMember.role }}<template v-if="d.selectedMember.type === 'agent'"> · AI agent</template>
            </div>
          </div>
          <button class="btn btn-ghost btn-sm btn-square" aria-label="Close" @click="d.closeOverlays()">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </header>
        <div class="flex-1 overflow-y-auto p-3 space-y-3">
          <div class="flex flex-wrap items-center gap-1">
            <span class="text-[10px] uppercase opacity-50">Projects</span>
            <ProjectTag v-for="project in d.memberProjects(d.selectedMember)" :key="'mp-' + project.id"
                        :project="project" size="xs" />
            <span v-if="!d.memberProjects(d.selectedMember).length" class="text-[11px] opacity-50">—</span>
          </div>

          <div class="grid grid-cols-2 gap-2 text-xs">
            <div><span class="opacity-50 text-[10px] uppercase">Load</span><div class="font-semibold">{{ d.selectedMember.load_pct }}%</div></div>
            <div>
              <span class="opacity-50 text-[10px] uppercase">Allocated</span>
              <div class="font-semibold">
                {{ d.selectedMember.type === 'human' ? d.selectedMember.hours + 'h / ' + d.selectedMember.capacity_h + 'h' : 'n/a' }}
              </div>
            </div>
            <div><span class="opacity-50 text-[10px] uppercase">Active</span><div class="font-semibold">{{ d.selectedMember.active }}</div></div>
            <div><span class="opacity-50 text-[10px] uppercase">Blocked</span><div class="font-semibold">{{ d.selectedMember.blocked }}</div></div>
            <div><span class="opacity-50 text-[10px] uppercase">Done</span><div class="font-semibold">{{ d.selectedMember.done }}</div></div>
            <div><span class="opacity-50 text-[10px] uppercase">AI cost</span><div class="font-semibold">{{ d.fmtCoins(d.selectedMember.cost_cxjcoins) }}</div></div>
          </div>

          <div>
            <div class="text-[10px] uppercase opacity-60 mb-1">Assigned work in this window</div>
            <p v-if="!d.selectedMemberTasks.length" class="text-xs opacity-60">No assigned tasks in this window.</p>
            <button v-for="task in d.selectedMemberTasks" :key="'mt-' + task.id"
                    class="w-full flex items-center gap-2 text-left rounded-lg px-1.5 py-1.5 hover:bg-base-200"
                    @click="d.openTask(task.id)">
              <span class="min-w-0 flex-1">
                <span class="block text-xs truncate">{{ task.name }}</span>
                <span class="flex items-center gap-1 min-w-0 text-[10px] opacity-60">
                  <ProjectTag :project-id="task.project_id" :name="task.project_name" size="xxs" class="shrink-0" />
                  <span class="truncate">· {{ task.board }}</span>
                </span>
              </span>
              <span class="badge badge-xs" :class="d.STATUS_META[task.status]?.badge">{{ d.STATUS_META[task.status]?.label }}</span>
            </button>
          </div>
        </div>
        <footer class="p-3 border-t border-base-300">
          <button class="btn btn-sm btn-ghost" @click="d.closeOverlays()">Close</button>
        </footer>
      </aside>
    </div>

    <!-- ════════════════ ASSIGN MODAL ════════════════ -->
    <div v-if="assigningTaskId" class="fixed inset-0 z-[60] grid place-items-center p-3">
      <div class="absolute inset-0 bg-black/60" @click="assigningTaskId = null"></div>
      <div class="relative w-full max-w-sm rounded-box bg-base-100 border border-base-300 p-3 shadow-2xl">
        <h3 class="text-sm font-bold">Assign this task</h3>
        <p class="text-[11px] opacity-60 mb-2">Pick one owner — shared ownership is an unowned task.</p>
        <div class="max-h-72 overflow-y-auto space-y-0.5">
          <button v-for="person in d.data.people" :key="'as-' + person.id"
                  class="w-full flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-base-200 text-left"
                  @click="assignTo(person.id)">
            <span class="w-6 h-6 rounded-full grid place-items-center text-[9px] font-bold text-white"
                  :style="{ background: person.type === 'agent' ? '#7c3aed' : d.personColor(person.id) }">
              {{ d.initials(person.name) }}
            </span>
            <span class="min-w-0 flex-1">
              <span class="block text-xs font-medium truncate">{{ person.name }}</span>
              <span class="flex items-center gap-1 min-w-0 text-[10px] opacity-60">
                <span class="truncate">{{ person.role }}</span>
                <ProjectTag v-for="project in d.memberProjectTags(person, 1).visible" :key="'ap-' + project.id"
                            :project="project" size="xxs" icon-only />
              </span>
            </span>
          </button>
        </div>
        <div class="flex justify-end mt-2">
          <button class="btn btn-sm btn-ghost" @click="assigningTaskId = null">Cancel</button>
        </div>
      </div>
    </div>

    <!-- ════════════════ AI ASSISTANT ════════════════ -->
    <button v-if="!d.state.assistant.open"
            class="fixed bottom-4 right-4 z-40 w-12 h-12 rounded-full text-white shadow-lg grid place-items-center bg-gradient-to-br from-primary to-secondary"
            aria-label="Ask the AI assistant" @click="d.toggleAssistant(true)">
      <i class="fa-solid fa-wand-magic-sparkles"></i>
    </button>

    <section v-if="d.state.assistant.open"
             class="fixed z-50 flex flex-col bg-base-100 border border-base-300 shadow-2xl"
             :class="compact ? 'inset-x-0 bottom-0 h-[75vh] rounded-t-box' : 'right-4 bottom-4 w-96 h-[32rem] rounded-box'"
             aria-label="AI assistant">
      <header class="flex items-center gap-2 p-2.5 border-b border-base-300">
        <span class="w-7 h-7 rounded-full grid place-items-center text-[10px] font-bold text-white bg-gradient-to-br from-primary to-secondary">AI</span>
        <div class="min-w-0 flex-1">
          <div class="text-xs font-bold">Ask about this dashboard</div>
          <div class="text-[10px] opacity-60 truncate">Answers come from the same data the screen renders — {{ d.projectScopeLabel }}</div>
        </div>
        <button class="btn btn-ghost btn-xs btn-square" aria-label="Close assistant" @click="d.toggleAssistant(false)">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </header>

      <div ref="messagesEl" class="flex-1 overflow-y-auto p-2.5 space-y-2">
        <div v-if="!d.state.assistant.messages.length" class="chat chat-start">
          <div class="chat-bubble chat-bubble-neutral text-xs">
            Ask me about blockers, costs, team load, what ships next, or what we finished.
          </div>
        </div>
        <div v-for="(message, index) in d.state.assistant.messages" :key="index"
             class="chat" :class="message.role === 'user' ? 'chat-end' : 'chat-start'">
          <div class="chat-bubble text-xs whitespace-pre-line"
               :class="message.role === 'user' ? 'chat-bubble-primary' : 'chat-bubble-neutral'">
            {{ message.text }}
            <div v-if="message.sources?.length" class="flex flex-wrap gap-1 mt-1.5">
              <button v-for="source in message.sources" :key="source.section"
                      class="btn btn-xs btn-ghost" @click="d.setSection(source.section)">
                {{ source.label }}
              </button>
            </div>
          </div>
        </div>
        <div v-if="d.state.assistant.thinking" class="chat chat-start">
          <div class="chat-bubble chat-bubble-neutral"><span class="loading loading-dots loading-xs"></span></div>
        </div>
      </div>

      <div class="px-2.5 pb-1 flex flex-wrap gap-1">
        <button v-for="suggestion in d.SUGGESTIONS" :key="suggestion" class="btn btn-xs btn-ghost"
                @click="d.ask(suggestion)">{{ suggestion }}</button>
      </div>

      <form class="flex items-center gap-1.5 p-2.5 border-t border-base-300" @submit.prevent="submitQuestion">
        <input v-model="question" type="text" class="input input-sm input-bordered flex-1"
               placeholder="e.g. what is blocking payments?" aria-label="Ask a question" />
        <button type="submit" class="btn btn-sm btn-primary btn-square" aria-label="Send question">
          <i class="fa-solid fa-paper-plane"></i>
        </button>
      </form>
    </section>

    <!-- ════════════════ TOASTS ════════════════ -->
    <div class="fixed left-1/2 -translate-x-1/2 bottom-20 z-[70] w-80 space-y-1.5">
      <div v-for="notice in d.notices.items" :key="notice.id"
           class="alert py-2 text-xs shadow-lg"
           :class="notice.tone === 'error' ? 'alert-error' : 'alert-success'">
        <i class="fa-solid" :class="notice.tone === 'error' ? 'fa-circle-exclamation' : 'fa-circle-check'"></i>
        <span>{{ notice.text }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { v4 as uuidv4 } from 'uuid'
import { useManagementDashboard } from './management/useManagementDashboard'
import ProjectFilter from '@/components/management/ProjectFilter.vue'
import ProjectTag from '@/components/management/ProjectTag.vue'
// The cost/AI screen is the product's analytics dashboard, reused as-is.
import MetricsDashboard from '@/components/analytics/MetricsDashboard.vue'

const d = useManagementDashboard()
const route = useRoute()

/* ── Project scope is driven by the URL ───────────────────────────────────
   The dashboard is the welcome screen of "/" and "/<project_name>":
   arriving on "/<project_name>" focuses it on THAT project, and switching the
   project in the URL re-focuses it. The composable owns the selection so the
   filter and every section stay in sync. */
watch(
  () => route.params.projectName,
  () => d.syncProjectFilterWithRoute(),
  { immediate: true }
)

/* ── Panel width (the view also lives inside a resizable dockview panel) ─── */
const rootEl = ref(null)
const width = ref(1200)
let observer = null
const compact = computed(() => width.value < 820)

/* ── Local UI state ──────────────────────────────────────────────────────── */
const question = ref('')
const assigningTaskId = ref(null)
const messagesEl = ref(null)

/* ── Header "more" menu ──────────────────────────────────────────────────────
   A native popover (same mechanism as the project filter): it is painted in the
   browser's TOP LAYER, so it never disappears behind the cards/tables/<select>
   of the section rendered below the header. The id/anchor pair keeps several
   dashboard instances (welcome page + dockview panel) independent. */
const menuPanelId = `dashboard-menu-${uuidv4()}`
const menuPanelEl = ref(null)
const menuOpen = ref(false)

/** Close the menu before running the action it triggered. */
function closeMenu() {
  menuOpen.value = false
  const panel = menuPanelEl.value
  if (panel?.hidePopover && panel.matches(':popover-open')) panel.hidePopover()
}

function runMenuAction(action) {
  closeMenu()
  if (typeof action === 'function') action()
}

const currentSection = computed(
  () => d.SECTIONS.find(section => section.id === d.state.section) || d.SECTIONS[0]
)

const loading = computed(() => !!d.state.loading[currentSection.value.id])

/** Whether the section already has data (avoids a skeleton over loaded data). */
const sectionReady = computed(() => {
  switch (currentSection.value.id) {
    case 'pulse': return !!d.data.dashboard
    case 'work': return !!d.data.tasks
    case 'blockers': return !!d.data.dashboard
    case 'delivery': return d.data.forecast.length > 0
    case 'team': return d.data.teamLoad.length > 0
    // The embedded analytics dashboard owns its own loading state.
    case 'cost': return true
    default: return true
  }
})

/** Four busiest humans for the Pulse "team load" card (inside the scope). */
const topLoadedPeople = computed(() => {
  return (d.teamRoster || [])
    .filter(person => person.type === 'human')
    .slice()
    .sort((a, b) => b.load_pct - a.load_pct)
    .slice(0, 4)
})

/** Last 14 days of AI spend as bar heights ("%" of the max). */
const spendBars = computed(() => {
  const daily = d.data.cost?.daily || []
  const values = daily.slice(-14).map(entry => entry.total_cxjcoins)
  const max = Math.max(1, ...values)
  return values.map(value => `${Math.max(4, Math.round((value / max) * 100))}%`)
})

/* ── Handlers ────────────────────────────────────────────────────────────── */
function applyFilter(scope, patch) {
  d.setFilter(scope, patch)
  d.load(scope)
}

function sortWork(field) {
  const filters = d.state.filters.work
  const dir = filters.sort === field && filters.dir === 'asc' ? 'desc' : 'asc'
  applyFilter('work', { sort: field, dir })
}

function sortIcon() {
  return d.state.filters.work.dir === 'asc' ? 'fa-solid fa-arrow-up text-[9px]' : 'fa-solid fa-arrow-down text-[9px]'
}

function goToPage(page) {
  if (!page || page === d.workPager.page) return
  applyFilter('work', { page })
}

let searchTimer = null
function onWorkSearch(event) {
  const value = event.target.value
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => applyFilter('work', { search: value }), 280)
}

async function startAssign(taskId) {
  assigningTaskId.value = taskId
  await d.ensurePeople()
}

async function assignTo(personId) {
  const taskId = assigningTaskId.value
  assigningTaskId.value = null
  if (taskId) await d.patchTask(taskId, { assignees: [personId] }, 'Task assigned')
}

async function submitQuestion() {
  const text = question.value
  question.value = ''
  await d.ask(text)
}

/* ── Labels ──────────────────────────────────────────────────────────────── */
function reasonLabel(reason) {
  return d.REASON_META[reason]?.label || reason
}

function forecastLabel(status) {
  return { on_track: 'On track', at_risk: 'At risk', late: 'Late' }[status] || status
}

function forecastBadge(status) {
  return { on_track: 'badge-success', at_risk: 'badge-warning', late: 'badge-error' }[status] || 'badge-ghost'
}

function forecastProgress(status) {
  return { on_track: 'progress-success', at_risk: 'progress-warning', late: 'progress-error' }[status] || 'progress-primary'
}

function loadTone(load) {
  if (load >= 95) return 'text-error'
  if (load >= 85) return 'text-warning'
  return 'text-success'
}

function loadProgress(load) {
  if (load >= 95) return 'progress-error'
  if (load >= 85) return 'progress-warning'
  return 'progress-success'
}

function toneDot(tone) {
  return { success: 'bg-success', primary: 'bg-primary', warning: 'bg-warning', error: 'bg-error' }[tone] || 'bg-info'
}

function blockerAge(task) {
  if (!task.blocked_since) return 0
  return Math.abs(Math.round((Date.now() - new Date(task.blocked_since).getTime()) / 86400000))
}

/* ── Lifecycle ───────────────────────────────────────────────────────────── */
watch(() => d.state.assistant.messages.length, async () => {
  await nextTick()
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
})

onMounted(() => {
  if (rootEl.value) {
    width.value = rootEl.value.clientWidth || width.value
    if (typeof ResizeObserver !== 'undefined') {
      observer = new ResizeObserver((entries) => {
        const entry = entries[0]
        if (entry) width.value = entry.contentRect.width
      })
      observer.observe(rootEl.value)
    }
  }
  d.load(d.state.section)
})

onBeforeUnmount(() => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
  clearTimeout(searchTimer)
})
</script>

<style scoped>
/* Header menus are anchored under their trigger and, because they are native
   popovers, painted in the top layer — above every card of the section below. */
.dashboard-menu {
  position: fixed;
  inset: auto;
  top: anchor(bottom);
  right: anchor(right);
  margin: 0.5rem 0 0 0;
  position-try-fallbacks: flip-block, flip-inline;
}
/* Author styles beat the UA `[popover]:not(:popover-open) { display: none }`,
   so the closed state has to be restored explicitly. */
.dashboard-menu:not(:popover-open) {
  display: none;
}
.dashboard-menu-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.375rem 0.5rem;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  text-align: left;
  transition: background-color 150ms ease;
}
.dashboard-menu-row:hover {
  background-color: color-mix(in srgb, currentColor 10%, transparent);
}
.dashboard-menu-row:focus-visible {
  outline: 2px solid color-mix(in srgb, currentColor 60%, transparent);
  outline-offset: 1px;
}

/* Inside a dockview panel the parent already scrolls; keep the local scrollbar
   thin so the six sections stay readable on a narrow panel. */
.management-dashboard {
  font-size: 0.9375rem;
}
.management-dashboard ::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
.management-dashboard ::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, currentColor 18%, transparent);
  border-radius: 999px;
}
</style>
