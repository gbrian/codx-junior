<template>
  <!-- ── Responsive shell ────────────────────────────────────────────────────
       Rendered inside a RESIZABLE dockview panel, so "mobile" means "this panel
       is narrow". The width is measured by `observePanelWidth()` (shared with
       Infrastructure → Monitoring) and every layout decision reads `layout.*`. -->
  <div ref="rootEl" class="api-monitoring w-full h-full overflow-auto"
       :class="layout.compact ? 'p-4' : 'p-6'">
    <!-- ── Header ───────────────────────────────────────────────────────── -->
    <div class="flex flex-wrap items-start gap-3 mb-4">
      <div class="min-w-0">
        <h1 class="text-2xl font-bold leading-tight flex items-center gap-2">
          <i class="fas fa-gauge-high text-primary"></i>
          API monitoring
        </h1>
        <p class="text-sm opacity-60 mt-0.5">
          Latency, throughput and error rate of every call handled by the API — recorded per request.
        </p>
      </div>
      <div class="flex-1"></div>

      <div class="flex flex-wrap items-center gap-2">
        <label class="flex items-center gap-1" :class="layout.compact ? 'w-full' : ''">
          <span class="sr-only">Time grouping</span>
          <select class="select select-bordered select-sm" :class="layout.compact ? 'grow' : 'w-40'"
                  title="Bucket size used by the chart and the aggregations"
                  :value="state.filters.grouping" @change="onGroupingChange">
            <option v-for="g in GROUPINGS" :key="g.id" :value="g.id">{{ g.label }}</option>
          </select>
        </label>

        <!-- Sampling cadence. Disabled (not hidden) while Live is off, so the
             preference stays visible without resuming polling. -->
        <label class="flex items-center gap-1">
          <span class="sr-only">Refresh interval</span>
          <select class="select select-bordered select-xs w-20"
                  :value="state.interval"
                  :disabled="!state.live"
                  :title="state.live ? 'How often the metrics are reloaded' : 'Enable Live to reload automatically'"
                  @change="onRefreshInterval">
            <option v-for="opt in REFRESH_INTERVALS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </label>

        <label class="label cursor-pointer gap-2 py-0" title="Reload the metrics on the selected interval">
          <span class="label-text text-xs">Live</span>
          <input type="checkbox" class="toggle toggle-sm toggle-primary"
                 :checked="state.live" @change="onLive" />
        </label>

        <label v-if="$storex.users.isAdmin" class="label cursor-pointer gap-2 py-0"
               title="Include the calls made by every user (admin endpoints)">
          <span class="label-text text-xs">All users</span>
          <input type="checkbox" class="toggle toggle-sm"
                 :checked="state.allUsers" @change="onAllUsers" />
        </label>

        <button class="btn btn-sm btn-primary" :disabled="loading" @click="refresh()">
          <span v-if="loading" class="loading loading-spinner loading-xs"></span>
          <i v-else class="fas fa-arrows-rotate"></i>
          Refresh
        </button>
      </div>
    </div>

    <!-- ── Filters ──────────────────────────────────────────────────────── -->
    <div class="card bg-base-200 border border-base-300 shadow-sm mb-4">
      <div class="card-body p-3 gap-3">
        <div class="flex flex-wrap items-center gap-2">
          <!-- range shortcuts -->
          <div class="join">
            <button v-for="preset in DATE_PRESETS" :key="preset.id"
                    class="btn btn-xs join-item"
                    :class="activePreset === preset.id ? 'btn-primary' : 'btn-ghost'"
                    :aria-pressed="activePreset === preset.id"
                    @click="onPreset(preset.id)">
              {{ preset.label }}
            </button>
          </div>

          <label class="flex items-center gap-1">
            <span class="text-xs opacity-60">From</span>
            <input type="date" class="input input-bordered input-xs"
                   :value="state.filters.startDate" @change="onDate('startDate', $event)" />
          </label>
          <label class="flex items-center gap-1">
            <span class="text-xs opacity-60">To</span>
            <input type="date" class="input input-bordered input-xs"
                   :value="state.filters.endDate" @change="onDate('endDate', $event)" />
          </label>

          <label class="flex items-center gap-1">
            <span class="sr-only">HTTP method</span>
            <select class="select select-bordered select-xs w-28"
                    :value="state.filters.method" @change="onMethod">
              <option value="">All methods</option>
              <option v-for="method in METHODS" :key="method" :value="method">{{ method }}</option>
            </select>
          </label>

          <!-- endpoint selector: populated from by-endpoint so it never goes
               empty once a path filter is applied -->
          <label class="flex items-center gap-1" :class="layout.compact ? 'w-full' : ''">
            <span class="sr-only">Endpoint</span>
            <select class="select select-bordered select-xs font-mono"
                    :class="layout.compact ? 'grow' : 'w-72'"
                    :value="state.filters.path" @change="onPath">
              <option value="">All endpoints</option>
              <option v-for="path in state.endpointOptions" :key="path" :value="path">{{ path }}</option>
            </select>
          </label>

          <label class="flex items-center gap-1">
            <span class="sr-only">Status code</span>
            <input type="number" min="100" max="599" placeholder="Status"
                   class="input input-bordered input-xs w-24"
                   :value="state.filters.statusCode" @change="onStatus" />
          </label>

          <label class="flex items-center gap-1">
            <span class="sr-only">Minimum duration in seconds</span>
            <input type="number" min="0" step="0.1" placeholder="Min s"
                   class="input input-bordered input-xs w-24"
                   :value="state.filters.minDurationSeconds"
                   title="Only show calls slower than this many seconds"
                   @change="onMinDuration" />
          </label>

          <label v-if="state.allUsers" class="flex items-center gap-1">
            <span class="sr-only">Username</span>
            <input type="text" placeholder="User" class="input input-bordered input-xs w-28"
                   :value="state.filters.username" @change="onUser" />
          </label>

          <label v-if="state.allUsers" class="flex items-center gap-1">
            <span class="sr-only">Project name</span>
            <input type="text" placeholder="Project" class="input input-bordered input-xs w-32"
                   :value="state.filters.projectName" @change="onProject" />
          </label>

          <div class="flex-1"></div>

          <button class="btn btn-xs btn-ghost" :disabled="!filtersActive && !state.filters.startDate"
                  title="Clear every filter" @click="onClearFilters">
            <i class="fas fa-eraser"></i> Clear
          </button>
        </div>

        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs opacity-60">
          <span class="inline-flex items-center gap-1.5">
            <i class="fas fa-wave-square" :class="state.live ? 'text-success animate-pulse' : 'opacity-40'"></i>
            {{ state.live ? 'Live every ' + state.interval + 's' : 'Live paused' }}
          </span>
          <span><i class="fas fa-clock mr-1"></i>{{ state.lastUpdated ? fmtTimestamp(state.lastUpdated.getTime() / 1000) : 'Not loaded' }}</span>
          <span><i class="fas fa-database mr-1"></i>{{ state.dates.length }} day(s) with data</span>
          <span><i class="fas fa-route mr-1"></i>{{ endpointCount }} endpoint(s)</span>
          <span>
            <i class="fas fa-plug-circle-bolt mr-1" :class="socketTotals.connected ? 'text-success' : 'text-warning'"></i>
            {{ fmtNum(socketTotals.total) }} socket event(s)
          </span>
          <span><i class="fas fa-network-wired mr-1"></i>{{ fmtNum(localNetworkTotals.calls) }} local call(s)</span>
          <span v-if="state.allUsers"><i class="fas fa-users mr-1"></i>All users</span>
        </div>
      </div>
    </div>

    <!-- ── States ───────────────────────────────────────────────────────── -->
    <div v-if="state.error" class="alert alert-error mb-4">
      <i class="fas fa-circle-exclamation"></i>
      <span class="text-sm">{{ state.error }}</span>
      <button class="btn btn-xs btn-ghost" @click="state.error = null">Dismiss</button>
    </div>

    <!-- Loading placeholder: SAME geometry as the strip below — one row of six
         tiles that scrolls sideways on a narrow panel. A column placeholder
         would make the page jump when the data lands in a row. -->
    <div v-if="loading && !state.summary" class="flex gap-3 overflow-x-auto pb-1 mb-4">
      <div v-for="i in 6" :key="i" class="skeleton h-24 min-w-40 flex-1"></div>
    </div>

    <!-- ── KPI strip ──────────────────────────────────────────────────────
         ALWAYS one row: `stats-vertical` is never applied. The six values are a
         comparison strip — stacking them turned it into a long column that
         pushed the chart below the fold, and the reading order changed with the
         panel width. daisyUI `.stats` is `grid-flow-col` + `overflow-x-auto`, so
         a panel narrower than the strip scrolls sideways instead of wrapping;
         `min-w-40` on each stat is the hard floor that keeps the numbers
         readable while scrolling (`layout.compact` only tightens the padding). -->
    <div v-if="state.summary"
         class="stats stats-horizontal w-full bg-base-200 border border-base-300 shadow-sm mb-4">
      <div v-for="kpi in kpis" :key="kpi.id" class="stat min-w-40"
           :class="layout.compact ? 'px-4' : ''">
        <div class="stat-title text-xs">{{ kpi.label }}</div>
        <div class="stat-value text-2xl" :class="toneText(kpi.tone)">
          {{ kpi.value }}<span v-if="kpi.unit" class="text-base opacity-50 ml-0.5">{{ kpi.unit }}</span>
        </div>
        <div class="stat-desc truncate" :title="kpi.sub">{{ kpi.sub }}</div>
      </div>
    </div>

    <div v-if="!loading && !hasData" class="alert alert-info mb-4">
      <i class="fas fa-circle-info"></i>
      <span class="text-sm">
        No API calls recorded for this range yet. Traffic is captured per request — widen the dates or
        generate some activity, then refresh.
      </span>
    </div>

    <!-- ── Throughput & latency ─────────────────────────────────────────── -->
    <div class="card bg-base-200 border border-base-300 shadow-sm mb-4">
      <div class="card-body p-3 gap-2">
        <div class="flex items-center justify-between gap-2">
          <h3 class="text-sm font-semibold flex items-center gap-2">
            <i class="fas fa-chart-line text-primary"></i> Throughput &amp; latency
          </h3>
          <div class="flex items-center gap-2">
            <!-- Live in-flight value: the number the purple bar converges to at
                 the last bucket, read straight from the client log so it does not
                 wait for the next refresh. -->
            <span v-if="localNetworkTotals.inFlight" class="badge badge-xs badge-info"
                  :title="localNetworkTotals.inFlight + ' request(s) still open in this tab'">
              {{ localNetworkTotals.inFlight }} in flight
            </span>
            <span class="text-[11px] opacity-50">{{ groupingLabel }} · {{ chartRows.length }} buckets</span>
          </div>
        </div>
        <div class="h-64">
          <ApiMonitoringChart v-if="chartRows.length"
                              :rows="chartRows" :metrics="chartMetrics"
                              :revision="state.revision"
                              y-title="Calls" y1-title="Latency (ms)"
                              y2-title="Local requests" />
          <div v-else class="h-full flex items-center justify-center text-sm opacity-50">
            Nothing to chart for this selection
          </div>
        </div>
        <p class="text-[11px] opacity-50">
          Lines, left axis: server calls and errors. Lines, first right axis: server latency (ms).
          Bars, second right axis (cyan / purple / rose): this browser's local and LAN requests per
          bucket — <strong>done</strong>, <strong>in flight</strong> (still open when the bucket ended,
          see the live count next to the title) and <strong>failed</strong>. Hover a bucket: the
          tooltip lists both sides and adds the local average latency.
          A backend that answers slowly with nothing in flight is overloaded; many requests in flight
          means the wait is on this tab's side. The local bars are client-side, keep the last hour only
          and never rescale the server axes (empty = no sample).
        </p>
      </div>
    </div>

    <!-- ── In flight (realtime) ────────────────────────────────────────────
         The calls open in THIS tab right now, longest first, with an elapsed
         time that ticks every second (`clientNow`). Elapsed is derived, never
         stored: a request that never settles keeps counting instead of freezing
         at a stale value. Captured in the browser by `@/api/telemetry`, so it
         describes what the user actually waits for. -->
    <div class="card bg-base-200 border border-base-300 shadow-sm mb-4">
      <div class="card-body p-3 gap-2">
        <div class="flex items-center justify-between gap-2">
          <h3 class="text-sm font-semibold flex items-center gap-2">
            <span class="inline-block w-1.5 h-1.5 rounded-full"
                  :class="inFlightCalls.length ? 'bg-info animate-pulse' : 'bg-base-content/30'"></span>
            <i class="fas fa-spinner text-info"></i> In flight
            <span class="text-[11px] font-normal opacity-50">realtime</span>
          </h3>
          <div class="flex items-center gap-2">
            <span class="badge badge-xs" :class="inFlightCalls.length ? 'badge-info' : 'badge-ghost'">
              {{ inFlightCalls.length }} open
            </span>
            <span class="text-[11px] opacity-50 font-mono">{{ fmtClock(clientNow) }}</span>
          </div>
        </div>

        <p v-if="!inFlightCalls.length" class="text-sm opacity-60">
          No request in flight — this tab is idle. Requests appear here the moment they leave and
          disappear when they answer.
        </p>

        <div v-else class="overflow-x-auto">
          <table class="table table-xs w-full">
            <thead>
              <tr>
                <th scope="col">Endpoint</th>
                <th scope="col">Started</th>
                <th scope="col" class="text-right">Elapsed</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="call in inFlightCalls" :key="call.id" class="hover">
                <td class="max-w-[22rem]">
                  <div class="flex items-center gap-1.5">
                    <span class="badge badge-xs badge-ghost font-mono shrink-0">{{ call.method }}</span>
                    <span class="font-mono text-xs truncate" :title="call.path">{{ call.path }}</span>
                  </div>
                </td>
                <td class="font-mono text-xs opacity-60 whitespace-nowrap">{{ fmtClock(call.startedAt) }}</td>
                <td class="text-right font-mono text-xs whitespace-nowrap"
                    :class="toneText(latencyTone(call.elapsedMs / 1000))">
                  {{ fmtElapsed(call.elapsedMs) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <p class="text-[11px] opacity-50">
          Longest first: the top row is what this tab has been waiting for the longest. An endpoint
          that keeps reappearing here (open for seconds at a time) is the one making the UI feel slow,
          even when the server-side latency looks healthy.
        </p>
      </div>
    </div>

    <!-- ── Slowest endpoints + status codes ─────────────────────────────── -->
    <div class="grid gap-3 mb-4" :class="layout.compact ? 'grid-cols-1' : 'grid-cols-2'">
      <div class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-3 gap-2">
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-sm font-semibold flex items-center gap-2">
              <i class="fas fa-route text-info"></i> Endpoints
            </h3>
            <label class="flex items-center gap-1">
              <span class="text-[11px] opacity-60">Sort</span>
              <select class="select select-bordered select-xs w-24"
                      :value="state.sortBy" @change="onSort">
                <option value="p95">p95</option>
                <option value="avg">Average</option>
                <option value="max">Max</option>
                <option value="calls">Calls</option>
                <option value="errors">Errors</option>
              </select>
            </label>
          </div>

          <p v-if="!topEndpoints.length" class="text-sm opacity-60">No endpoint recorded in this range.</p>

          <div v-else class="overflow-x-auto">
            <table class="table table-xs w-full">
              <thead>
                <tr>
                  <th scope="col">Endpoint</th>
                  <th scope="col" class="text-right">Calls</th>
                  <th scope="col" class="text-right">Err</th>
                  <th scope="col" class="text-right">Avg</th>
                  <th scope="col" class="text-right">p95</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in topEndpoints" :key="row.path" class="hover">
                  <td class="max-w-[18rem]">
                    <button class="font-mono text-xs truncate text-left w-full hover:text-primary"
                            :title="'Filter by ' + row.path"
                            @click="onEndpointSelect(row.path)">
                      {{ row.path }}
                    </button>
                  </td>
                  <td class="text-right font-mono text-xs">{{ fmtNum(row.calls) }}</td>
                  <td class="text-right font-mono text-xs"
                      :class="Number(row.errors) ? 'text-error' : 'opacity-50'">
                    {{ fmtNum(row.errors) }}
                  </td>
                  <td class="text-right font-mono text-xs" :class="toneText(latencyTone(row.avg_duration_seconds))">
                    {{ fmtMs(row.avg_duration_seconds) }}
                  </td>
                  <td class="text-right font-mono text-xs" :class="toneText(latencyTone(row.p95_duration_seconds))">
                    {{ fmtMs(row.p95_duration_seconds) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-3 gap-2">
          <h3 class="text-sm font-semibold flex items-center gap-2">
            <i class="fas fa-circle-half-stroke text-success"></i> Status codes
          </h3>

          <p v-if="!statusRows.length" class="text-sm opacity-60">No response recorded in this range.</p>

          <ul v-else class="space-y-2.5">
            <li v-for="row in statusRows" :key="row.code">
              <div class="flex items-center justify-between gap-2 text-xs mb-1">
                <span class="badge badge-sm" :class="badgeClass(row.code)">{{ row.code }}</span>
                <span class="opacity-60 font-mono">
                  {{ fmtNum(row.calls) }} · {{ fmtPct(row.error_rate) }} err · p95 {{ fmtMs(row.p95_duration_seconds) }}
                </span>
              </div>
              <progress class="progress w-full h-1.5"
                        :class="meterClass(statusTone(row.code))"
                        :value="share(row)" max="100"></progress>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- ── Diagnostics + slowest calls ──────────────────────────────────── -->
    <div class="grid gap-3 mb-4" :class="layout.compact ? 'grid-cols-1' : 'grid-cols-2'">
      <div class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-3 gap-2">
          <div class="flex items-center gap-2">
            <h3 class="text-sm font-semibold flex items-center gap-2">
              <i class="fas" :class="issues.length ? 'fa-triangle-exclamation text-warning' : 'fa-circle-check text-success'"></i>
              Possible problems
            </h3>
            <span v-if="issues.length" class="badge badge-sm badge-warning">{{ issues.length }}</span>
          </div>

          <p v-if="!issues.length" class="text-sm opacity-60">
            Nothing stands out — the error rate and the latency percentiles are within range.
          </p>

          <ul v-else class="space-y-1.5">
            <li v-for="issue in issues" :key="issue.id"
                class="flex items-start gap-2 rounded-lg px-2 py-1.5" :class="rowClass(issue.tone)">
              <i class="fas mt-0.5 shrink-0" :class="[issue.icon, toneText(issue.tone)]"></i>
              <div class="min-w-0">
                <div class="text-sm font-medium">{{ issue.title }}</div>
                <div class="text-xs opacity-70 break-words">{{ issue.detail }}</div>
              </div>
            </li>
          </ul>
        </div>
      </div>

      <div class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-3 gap-2">
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-sm font-semibold flex items-center gap-2">
              <i class="fas fa-fire text-error"></i> Slowest calls
            </h3>
            <span class="text-[11px] opacity-50">top {{ TOP_SLOWEST }}</span>
          </div>

          <p v-if="!state.slowest.length" class="text-sm opacity-60">No call recorded in this range.</p>

          <ul v-else class="space-y-2">
            <li v-for="(call, index) in slowestCalls" :key="index"
                class="flex items-center justify-between gap-2 text-xs">
              <div class="min-w-0">
                <div class="flex items-center gap-1.5">
                  <span class="badge badge-xs badge-ghost font-mono">{{ call.method }}</span>
                  <span class="font-mono truncate" :title="call.path">{{ call.path }}</span>
                </div>
                <div class="opacity-50 font-mono">
                  {{ fmtTimestamp(call.timestamp) }} · {{ call.status_code }}
                  <span v-if="call.username"> · {{ call.username }}</span>
                </div>
              </div>
              <span class="shrink-0 font-mono" :class="toneText(latencyTone(call.duration_seconds))">
                {{ fmtMs(call.duration_seconds) }}
              </span>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- ── Failed calls ─────────────────────────────────────────────────── -->
    <div class="card bg-base-200 border border-base-300 shadow-sm mb-4">
      <div class="card-body p-3 gap-2">
        <div class="flex items-center justify-between gap-2">
          <h3 class="text-sm font-semibold flex items-center gap-2">
            <i class="fas fa-circle-exclamation text-error"></i> Failed calls
          </h3>
          <span class="text-[11px] opacity-50">{{ state.errors.length }} shown</span>
        </div>

        <p v-if="!state.errors.length" class="text-sm opacity-60">
          No failed call (error or 5xx) in this range.
        </p>

        <div v-else class="overflow-x-auto">
          <table class="table table-xs w-full">
            <thead>
              <tr>
                <th scope="col">When</th>
                <th scope="col">Method</th>
                <th scope="col">Endpoint</th>
                <th scope="col" class="text-right">Status</th>
                <th scope="col" class="text-right">Duration</th>
                <th scope="col">Error</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(call, index) in state.errors" :key="index" class="hover">
                <td class="font-mono text-xs whitespace-nowrap opacity-70">{{ fmtTimestamp(call.timestamp) }}</td>
                <td class="font-mono text-xs">{{ call.method }}</td>
                <td class="font-mono text-xs max-w-[18rem] truncate" :title="call.path">{{ call.path }}</td>
                <td class="text-right">
                  <span class="badge badge-xs" :class="badgeClass(call.status_code)">{{ call.status_code }}</span>
                </td>
                <td class="text-right font-mono text-xs">{{ fmtMs(call.duration_seconds) }}</td>
                <td class="text-xs max-w-[20rem] truncate" :title="call.error || ''">{{ call.error || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ── Socket events + local network (client-side logs) ────────────────
         These two streams are captured in this browser (`@/api/telemetry`)
         because they never reach a route handler: the socket delivery of this
         client, and the LAN round trip the browser sees. They keep one hour of
         history — the same window the chart overlay covers. -->
    <div class="grid gap-3 mb-4" :class="layout.compact ? 'grid-cols-1' : 'grid-cols-2'">
      <!-- Socket events -->
      <div class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-3 gap-2">
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-sm font-semibold flex items-center gap-2">
              <i class="fas fa-plug-circle-bolt text-info"></i> Socket events
            </h3>
            <div class="flex items-center gap-1">
              <span class="badge badge-xs" :class="socketTotals.connected ? 'badge-success' : 'badge-warning'">
                {{ socketTotals.connected ? 'Connected' : 'Disconnected' }}
              </span>
              <button class="btn btn-xs btn-ghost"
                      title="Clear the socket event log"
                      aria-label="Clear the socket event log"
                      @click="clearClientLogs('socket')">
                <i class="fas fa-eraser"></i>
              </button>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] opacity-60">
            <span><i class="fas fa-arrow-up mr-1"></i>{{ fmtNum(socketTotals.sent) }} sent</span>
            <span><i class="fas fa-arrow-down mr-1"></i>{{ fmtNum(socketTotals.received) }} received</span>
            <span :class="socketTotals.errors ? 'text-error' : ''">
              <i class="fas fa-bolt mr-1"></i>{{ fmtNum(socketTotals.errors) }} error(s)
            </span>
            <span v-if="socketTotals.avgAckMs">
              <i class="fas fa-stopwatch mr-1"></i>ack {{ fmtMs(socketTotals.avgAckMs / 1000) }}
            </span>
          </div>

          <p v-if="!socketEventRows.length" class="text-sm opacity-60">
            No socket event yet — the log starts as soon as this tab connects.
          </p>

          <div v-else class="overflow-x-auto">
            <table class="table table-xs w-full">
              <thead>
                <tr>
                  <th scope="col">Event</th>
                  <th scope="col" class="text-right">Sent</th>
                  <th scope="col" class="text-right">Recv</th>
                  <th scope="col" class="text-right">Err</th>
                  <th scope="col" class="text-right">Last</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in socketEventRows.slice(0, TOP_CLIENT_ROWS)" :key="row.event" class="hover">
                  <td class="max-w-[16rem]">
                    <span class="font-mono text-xs truncate inline-block w-full align-middle"
                          :title="row.event">{{ row.event }}</span>
                  </td>
                  <td class="text-right font-mono text-xs">{{ row.sent ? fmtNum(row.sent) : '—' }}</td>
                  <td class="text-right font-mono text-xs">{{ row.received ? fmtNum(row.received) : '—' }}</td>
                  <td class="text-right font-mono text-xs"
                      :class="row.errors ? 'text-error' : 'opacity-50'">
                    {{ row.errors ? fmtNum(row.errors) : '—' }}
                  </td>
                  <td class="text-right font-mono text-[11px] opacity-60 whitespace-nowrap">
                    {{ fmtClock(row.lastAt) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <p class="text-[11px] opacity-50">
            Captured in this browser tab, last hour only: event name, payload size, ack latency and
            lifecycle. Payloads are never stored.
          </p>
        </div>
      </div>

      <!-- Local network statistics -->
      <div class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-3 gap-2">
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-sm font-semibold flex items-center gap-2">
              <i class="fas fa-network-wired text-success"></i> Local network
            </h3>
            <div class="flex items-center gap-1">
              <label class="flex items-center gap-1">
                <span class="sr-only">Sort the local requests</span>
                <select class="select select-bordered select-xs w-28"
                        :value="state.localSortBy" @change="onLocalSort"
                        title="Which local requests cost the most time / repeat the most">
                  <option v-for="option in LOCAL_SORTS" :key="option.id" :value="option.id">
                    {{ option.label }}
                  </option>
                </select>
              </label>
              <span v-if="localNetworkTotals.inFlight" class="badge badge-xs badge-info"
                    :title="localNetworkTotals.inFlight + ' request(s) still open in this tab'">
                {{ localNetworkTotals.inFlight }} in flight
              </span>
              <button class="btn btn-xs btn-ghost"
                      title="Clear the local network log"
                      aria-label="Clear the local network log"
                      @click="clearClientLogs('network')">
                <i class="fas fa-eraser"></i>
              </button>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] opacity-60">
            <span><i class="fas fa-right-left mr-1"></i>{{ fmtNum(localNetworkTotals.calls) }} call(s)</span>
            <span :class="localNetworkTotals.errorRate >= 0.05 ? 'text-error' : localNetworkTotals.errors ? 'text-warning' : ''">
              <i class="fas fa-circle-exclamation mr-1"></i>{{ fmtNum(localNetworkTotals.errors) }} failed
            </span>
            <span><i class="fas fa-stopwatch mr-1"></i>avg {{ fmtMs(localNetworkTotals.avgMs / 1000) }}</span>
            <span v-if="localNetworkTotals.slow">
              <i class="fas fa-hourglass-half mr-1"></i>{{ fmtNum(localNetworkTotals.slow) }} over 1s
            </span>
          </div>

          <p v-if="!localNetworkRows.length" class="text-sm opacity-60">
            No local network call yet — requests to localhost / LAN hosts are logged here.
          </p>

          <div v-else class="overflow-x-auto">
            <table class="table table-xs w-full">
              <thead>
                <tr>
                  <th scope="col">Endpoint</th>
                  <th scope="col" class="text-right">Calls</th>
                  <th scope="col" class="text-right">Err</th>
                  <th scope="col" class="text-right">Avg</th>
                  <th scope="col" class="text-right">p95</th>
                  <th scope="col" class="text-right"
                      title="Total time spent in this endpoint and its share of the local time">
                    Total
                  </th>
                  <th scope="col" class="text-right">Last</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in topLocalRows" :key="row.key" class="hover">
                  <td class="max-w-[14rem]">
                    <div class="flex items-center gap-1.5">
                      <span class="badge badge-xs badge-ghost font-mono shrink-0">{{ row.method }}</span>
                      <span class="font-mono text-xs truncate" :title="row.path">{{ row.path }}</span>
                      <span v-if="row.open" class="badge badge-xs badge-info shrink-0"
                            :title="row.open + ' still open right now'">{{ row.open }}</span>
                    </div>
                  </td>
                  <td class="text-right">
                    <div class="font-mono text-xs">{{ fmtNum(row.calls) }}</div>
                    <div class="text-[10px] opacity-50">{{ row.callsPerMin.toFixed(1) }}/min</div>
                  </td>
                  <td class="text-right font-mono text-xs"
                      :class="row.errors ? 'text-error' : 'opacity-50'">
                    {{ fmtNum(row.errors) }}
                  </td>
                  <td class="text-right font-mono text-xs" :class="toneText(latencyTone(row.avgMs / 1000))">
                    {{ fmtMs(row.avgMs / 1000) }}
                  </td>
                  <td class="text-right font-mono text-xs" :class="toneText(latencyTone(row.p95Ms / 1000))">
                    {{ fmtMs(row.p95Ms / 1000) }}
                  </td>
                  <td class="text-right">
                    <div class="font-mono text-xs">{{ fmtMs(row.totalMs / 1000) }}</div>
                    <progress class="progress block w-14 h-1 ml-auto"
                              :class="meterClass(latencyTone(row.avgMs / 1000))"
                              :value="Math.round(row.share * 100)" max="100"
                              :title="Math.round(row.share * 100) + '% of the local time'"></progress>
                  </td>
                  <td class="text-right font-mono text-[11px] opacity-60 whitespace-nowrap">
                    {{ fmtClock(row.lastAt) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <p class="text-[11px] opacity-50">
            Wall-clock latency measured by this browser, last hour only — DNS and the LAN round trip
            included, which is the part the server-side aggregates cannot see.
            <strong>Total</strong> and its bar are the share of the local time: that is the request
            costing the most, while <strong>Calls/min</strong> shows the one repeating the most.
            Open requests are counted (badge) but never averaged.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  useApiMonitoring,
  GROUPINGS,
  REFRESH_INTERVALS,
  DATE_PRESETS,
  METHODS,
  LOCAL_SORTS,
  TOP_SLOWEST,
  TOP_CLIENT_ROWS
} from './useApiMonitoring'
import { layout, observePanelWidth } from '../infra/useInfraLayout'
import ApiMonitoringChart from './ApiMonitoringChart.vue'

const {
  state, setFilter, applyFilters, applyPreset, clearFilters,
  loadDates, loadAll, setLive, setIntervalSeconds, setAllUsers,
  endpointRows, statusRows, chartRows, chartMetrics, hasData, issues,
  filtersActive, activePreset, groupingLabel, setLocalSortBy,
  clientNow, startClientClock, stopClientClock,
  socketEventRows, localNetworkRows, socketTotals, localNetworkTotals,
  inFlightCalls, clearClientLogs,
  fmtMs, fmtElapsed, fmtNum, fmtPct, fmtTimestamp, fmtClock, fmtDuration,
  latencyTone, statusTone, errorTone, TOP_ENDPOINTS
} = useApiMonitoring()

/* ── panel width tracking (this view lives in a resizable dockview panel) ─── */
const rootEl = ref(null)
let disposeLayout = null

/* ── derived ──────────────────────────────────────────────────────────────── */
const loading = computed(() => state.status === 'loading')
const endpointCount = computed(() => Object.keys(state.endpoints || {}).length)
const topEndpoints = computed(() => endpointRows.value.slice(0, TOP_ENDPOINTS))
const slowestCalls = computed(() => state.slowest.slice(0, TOP_SLOWEST))
/** Local statistics rows shown by the card (already ordered by `localSortBy`). */
const topLocalRows = computed(() => localNetworkRows.value.slice(0, TOP_CLIENT_ROWS))

/** Highest call count, used as the 100% of the status share bars. */
const maxCalls = computed(
  () => statusRows.value.reduce((max, row) => Math.max(max, Number(row.calls) || 0), 0)
)

function share(row) {
  if (!maxCalls.value) return 0
  return Math.round(((Number(row.calls) || 0) / maxCalls.value) * 100)
}

const kpis = computed(() => {
  const summary = state.summary || {}
  const calls = Number(summary.calls) || 0
  const worst = endpointRows.value[0]

  return [
    {
      id: 'calls',
      label: 'Calls',
      value: fmtNum(calls),
      sub: `${groupingLabel.value} · ${chartRows.value.length} buckets`
    },
    {
      id: 'error',
      label: 'Error rate',
      value: fmtPct(summary.error_rate),
      tone: errorTone(summary.error_rate),
      sub: `${fmtNum(summary.errors)} failed of ${fmtNum(calls)}`
    },
    {
      id: 'avg',
      label: 'Avg latency',
      value: fmtMs(summary.avg_duration_seconds),
      tone: latencyTone(summary.avg_duration_seconds),
      sub: `min ${fmtMs(summary.min_duration_seconds)}`
    },
    {
      id: 'p95',
      label: 'p95 latency',
      value: fmtMs(summary.p95_duration_seconds),
      tone: latencyTone(summary.p95_duration_seconds),
      sub: `max ${fmtMs(summary.max_duration_seconds)}`
    },
    {
      id: 'time',
      label: 'Total time',
      value: fmtDuration(summary.total_duration_seconds),
      sub: 'sum of the request time'
    },
    {
      id: 'endpoints',
      label: 'Endpoints',
      value: endpointCount.value,
      sub: worst ? `slowest: ${worst.path}` : 'no endpoint recorded'
    }
  ]
})

/* ── tone helpers ─────────────────────────────────────────────────────────── */
function toneText(tone) {
  return {
    success: 'text-success',
    warning: 'text-warning',
    error: 'text-error',
    info: 'text-info'
  }[tone] || ''
}

function rowClass(tone) {
  return {
    success: 'bg-success/10',
    warning: 'bg-warning/10',
    error: 'bg-error/10',
    info: 'bg-info/10'
  }[tone] || 'bg-base-300'
}

function meterClass(tone) {
  return {
    success: 'progress-success',
    warning: 'progress-warning',
    error: 'progress-error',
    info: 'progress-info'
  }[tone] || 'progress-primary'
}

function badgeClass(code) {
  return {
    success: 'badge-success',
    warning: 'badge-warning',
    error: 'badge-error',
    info: 'badge-info'
  }[statusTone(code)] || 'badge-ghost'
}

/* ── handlers ─────────────────────────────────────────────────────────────── */
function refresh() {
  return loadAll()
}

function onGroupingChange(event) {
  // `setFilter` bumps the revision (immediate redraw) and `applyFilters`
  // replaces the running round, so the new bucket size is fetched right away.
  setFilter({ grouping: event.target.value })
  applyFilters()
}

function onDate(key, event) {
  setFilter({ [key]: event.target.value })
  applyFilters()
}

function onMethod(event) {
  setFilter({ method: event.target.value })
  applyFilters()
}

function onPath(event) {
  setFilter({ path: event.target.value })
  applyFilters()
}

function onStatus(event) {
  setFilter({ statusCode: event.target.value })
  applyFilters()
}

function onMinDuration(event) {
  setFilter({ minDurationSeconds: event.target.value })
  applyFilters()
}

function onUser(event) {
  setFilter({ username: event.target.value })
  applyFilters()
}

function onProject(event) {
  setFilter({ projectName: event.target.value })
  applyFilters()
}

function onPreset(id) {
  applyPreset(id)
}

function onEndpointSelect(path) {
  // Clicking an endpoint narrows the whole view to it (same as the select).
  setFilter({ path })
  applyFilters()
}

function onSort(event) {
  state.sortBy = event.target.value
}

/** Local statistics ordering — pure client-side, no fetch involved. */
function onLocalSort(event) {
  setLocalSortBy(event.target.value)
}

function onLive(event) {
  setLive(event.target.checked)
}

function onRefreshInterval(event) {
  setIntervalSeconds(event.target.value)
}

function onAllUsers(event) {
  setAllUsers(event.target.checked)
}

function onClearFilters() {
  clearFilters()
}

/* ── lifecycle ────────────────────────────────────────────────────────────── */
onMounted(async () => {
  disposeLayout = observePanelWidth(rootEl.value)
  // Heartbeat for the realtime "in flight" table: elapsed times keep counting
  // between refreshes. Reference counted, so a remount cannot stack timers.
  startClientClock()
  // Data first (the panels render from it), then the available-dates hint.
  await loadAll()
  loadDates()
})

onBeforeUnmount(() => {
  if (disposeLayout) {
    disposeLayout()
    disposeLayout = null
  }
  // Never leave a timer running behind a closed panel; the live preference is
  // kept so the next mount resumes with the operator's choice.
  setLive(false)
  stopClientClock()
})
</script>