<script setup>
import Chart from 'chart.js/auto'
import { markRaw } from 'vue'
</script>

<template>
  <div ref="wrapEl" class="relative w-full h-full">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script>
/**
 * Chart.js wrapper for the API monitoring charts.
 *
 * Same library and SAME palette/typography as the infrastructure charts
 * (`src/views/infra/MonitoringChart.vue`) and the analytics ones, so the three
 * dashboards look like one product:
 *   text #e5e7eb · secondary text #9ca3af · border #374151
 *   grid rgba(55,65,81,.25) · tooltip rgba(17,24,39,.95)
 *
 * Three differences with the infra chart, all required by API metrics:
 *   • labels come from `row.label`, already formatted by useApiMonitoring
 *     (backend buckets are "YYYY-MM-DD HH:MM[:SS]", not ISO timestamps);
 *   • each axis carries its OWN unit, because throughput (calls), latency (ms)
 *     and the client-side local counts (requests) are drawn side by side;
 *   • a metric may be a BAR (`type: 'bar'`) or dashed (`dash: [6, 4]`). The
 *     client-side series are bars — they are counts per bucket, and a line would
 *     imply continuity between buckets that the data does not have.
 *
 * THREE AXES
 * ----------
 * `y`  left  — server call counts (and errors).
 * `y1` right — server latency in ms.
 * `y2` right — this browser's local/LAN requests (done / in flight / failed),
 *              kept on their own axis because they are per tab: sharing the
 *              server axis would rescale it and hide the backend numbers.
 * Both right axes stack automatically (Chart.js lays out same-side axes in
 * order), `y2` outermost.
 *
 * READING ORDER ON THE CANVAS
 * ---------------------------
 * The client bars are painted FIRST (`order`), so the server lines stay on top
 * and are never hidden behind a bar. The bar axis is the same zero line, so a
 * tall bar still reads as "this tab had that many requests open".
 *
 * REFRESH CONTRACT (why three things are done exactly this way)
 * ------------------------------------------------------------
 * 1. THE INSTANCE IS NOT REACTIVE. `data()` is wrapped by Vue with a deep proxy,
 *    and Chart.js holds identity-sensitive internals (`_metasets`, dataset
 *    controllers, WeakMap keys, animation state). Reading a proxied instance
 *    makes `update()` run against proxies instead of the raw objects: the call
 *    succeeds, the canvas keeps the previous frame and nothing visibly refreshes.
 *    The instance is therefore stored with `markRaw()`.
 * 2. DATA IS PATCHED IN PLACE. The SAME dataset objects are kept and only their
 *    `data` array/colors are replaced, then `chart.update('none')` is called
 *    (Chart.js docs: "Updating Charts"). Assigning a brand new `chart.data`
 *    leaves the metasets pointing at the previous objects.
 * 3. THE INSTANCE IS REBUILT ONLY ON CONFIGURATION CHANGES, because Chart.js
 *    resolves scale options and tick callbacks at construction time; series,
 *    axes, units and chart types are fingerprinted by `optionsSignature`.
 *
 * Rendering also re-measures the canvas: the chart lives inside a resizable
 * dockview panel measured after mount, so every render compares the canvas
 * against its container and calls `resize()` when they differ, and a
 * ResizeObserver on the wrapper handles the panel moves between two polls.
 *
 * Presentation only: it renders whatever `rows` + `metrics` receive and never
 * fetches anything.
 */
export default {
  name: 'ApiMonitoringChart',
  props: {
    /** Ordered buckets, e.g. `[{ label: '14:00:10', calls: 42, avg_ms: 310 }, …]`. */
    rows: {
      type: Array,
      default: () => []
    },
    /**
     * Series descriptors:
     * `{ key, label, color, type: 'line'|'bar', axis: 'y'|'y1'|'y2', fill, dash }`
     */
    metrics: {
      type: Array,
      default: () => []
    },
    /**
     * Monotonic counter bumped by the store on every committed refresh and on
     * every configuration change.
     *
     * The `chartData` watcher already catches the usual case (a brand new
     * `rows` array), but the counter makes the redraw deterministic: it fires
     * even when two consecutive payloads produce identical values, so "the
     * numbers changed" can never be missed by the canvas.
     */
    revision: {
      type: Number,
      default: 0
    },
    /** Fixed upper bound of the left axis (rarely needed: counts are relative). */
    maxY: {
      type: Number,
      default: null
    },
    yTitle: {
      type: String,
      default: ''
    },
    y1Title: {
      type: String,
      default: ''
    },
    /** Title of the third axis (this browser's local requests). */
    y2Title: {
      type: String,
      default: ''
    },
    /** Suffix appended to the left axis values and their tooltip entries. */
    yUnit: {
      type: String,
      default: ''
    },
    /** Suffix appended to the right axis values and their tooltip entries. */
    y1Unit: {
      type: String,
      default: ''
    },
    /** Suffix appended to the third axis values and their tooltip entries. */
    y2Unit: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      /**
       * Chart.js instance, always assigned through `markRaw()` (see the REFRESH
       * CONTRACT above): a proxied instance stops repainting.
       */
      chart: null,
      // Option signature the live instance was built with.
      chartSignature: '',
      // Coalesces the watchers of a single tick into one render.
      renderPending: false
    }
  },
  computed: {
    chartData() {
      return this.buildChartData()
    },
    hasSecondaryAxis() {
      return (this.metrics || []).some(metric => (metric.axis || 'y') === 'y1')
    },
    hasTertiaryAxis() {
      return (this.metrics || []).some(metric => (metric.axis || 'y') === 'y2')
    },
    /** True when at least one series is a bar (the client-side ones are). */
    hasBarSeries() {
      return (this.metrics || []).some(metric => metric.type === 'bar')
    },
    /**
     * Everything that forces a NEW chart instance (Chart.js resolves scales and
     * tick callbacks at construction time, so these cannot be patched in place).
     */
    optionsSignature() {
      const metrics = (this.metrics || []).map(metric => ([
        metric.key,
        metric.label,
        metric.color,
        metric.type || 'line',
        metric.axis || 'y',
        !!metric.fill,
        metric.dash || null,
        // Drawing order is a constructor-time decision (bars behind the lines).
        metric.type === 'bar' ? 1 : 2
      ]))
      return JSON.stringify({
        metrics,
        maxY: this.maxY,
        yTitle: this.yTitle,
        y1Title: this.y1Title,
        y2Title: this.y2Title,
        yUnit: this.yUnit,
        y1Unit: this.y1Unit,
        y2Unit: this.y2Unit
      })
    }
  },
  watch: {
    /** Data changed: repaint (no rebuild needed). */
    chartData: {
      handler() {
        this.scheduleRender()
      },
      deep: true
    },
    /** Explicit refresh signal from the store (see the prop documentation). */
    revision() {
      this.scheduleRender()
    },
    /** Configuration changed: axes/units/series → rebuild the instance. */
    optionsSignature() {
      this.scheduleRender()
    }
  },
  methods: {
    hexToRgb(hex) {
      const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
      return result
        ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`
        : '99, 102, 241'
    },

    /** Compact value formatter ("1.2K", "480 ms"…) for one axis. */
    formatValue(value, unit = '') {
      const num = Number(value) || 0
      if (Math.abs(num) >= 1000) {
        const short = Math.abs(num) >= 1_000_000
          ? `${(num / 1_000_000).toFixed(1)}M`
          : `${(num / 1_000).toFixed(1)}K`
        return unit ? `${short}${unit}` : short
      }
      const text = Number.isInteger(num) ? String(num) : num.toFixed(1)
      return unit ? `${text}${unit}` : text
    },

    /** Fresh plain objects: Chart.js is free to decorate them in place. */
    buildChartData() {
      const rows = this.rows || []
      const labels = rows.map(row => row.label)
      const datasets = (this.metrics || []).map((metric) => {
        const color = metric.color || '#6366f1'
        const isBar = metric.type === 'bar'

        return {
          // `null` entries are "no sample" (a bucket outside the local window):
          // Chart.js breaks the line / skips the bar there instead of drawing a
          // fake zero.
          label: metric.label,
          data: rows.map((row) => {
            const value = row[metric.key]
            return value === null || value === undefined ? null : Number(value) || 0
          }),
          type: isBar ? 'bar' : 'line',
          /**
           * Drawing order: Chart.js paints datasets by ASCENDING `order`, so the
           * client bars (1) land behind the server lines (2). The lines are the
           * reference — they must never disappear behind a bar.
           */
          order: isBar ? 1 : 2,
          borderColor: color,
          backgroundColor: isBar
            ? `rgba(${this.hexToRgb(color)}, 0.45)`
            : `rgba(${this.hexToRgb(color)}, 0.12)`,
          borderWidth: isBar ? 0 : 2,
          // Bars: soft corners and a width cap, so a dense selection (hundreds of
          // buckets) does not turn into a solid colour block.
          borderRadius: isBar ? 3 : 0,
          maxBarThickness: isBar ? 16 : undefined,
          borderDash: isBar ? [] : (metric.dash || []),
          tension: 0.35,
          fill: !!metric.fill && !isBar,
          pointRadius: 0,
          pointHoverRadius: 4,
          pointBackgroundColor: color,
          pointBorderWidth: 0,
          yAxisID: metric.axis || 'y'
        }
      })

      return { labels, datasets }
    },

    /**
     * Copies the current `rows`/`metrics` into the LIVE chart.
     *
     * The dataset objects are reused on purpose: Chart.js keeps one controller
     * per dataset entry, so replacing the array (or `chart.data`) detaches them
     * from the drawing loop. Only the values and the resolved colors change.
     */
    applyData() {
      const { labels, datasets } = this.buildChartData()
      const chart = this.chart
      const current = chart.data.datasets || []

      chart.data.labels = labels

      if (current.length !== datasets.length) {
        // Series added/removed without a signature change (e.g. empty metrics).
        chart.data.datasets = datasets
        return
      }

      datasets.forEach((next, index) => {
        const dataset = current[index]
        dataset.label = next.label
        dataset.data = next.data
        dataset.order = next.order
        dataset.borderColor = next.borderColor
        dataset.backgroundColor = next.backgroundColor
        dataset.borderWidth = next.borderWidth
        dataset.borderRadius = next.borderRadius
        dataset.borderDash = next.borderDash
        dataset.fill = next.fill
        dataset.yAxisID = next.yAxisID
      })
    },

    /** True when the canvas no longer matches the box it paints into. */
    hasSizeChanged() {
      const parent = this.$refs.chartCanvas?.parentElement
      if (!parent || !this.chart) return false

      const width = Math.round(parent.clientWidth)
      const height = Math.round(parent.clientHeight)
      // Hidden panel: nothing to measure yet, the observer/next refresh handles it.
      if (!width || !height) return false

      return Math.round(this.chart.width || 0) !== width
        || Math.round(this.chart.height || 0) !== height
    },

    /** One render per tick, whatever combination of watchers fired. */
    scheduleRender() {
      if (this.renderPending) return
      this.renderPending = true
      this.$nextTick(() => {
        this.renderPending = false
        this.render()
      })
    },

    render() {
      if (!this.$refs.chartCanvas) return

      if (!this.chart) {
        this.createChart()
        return
      }

      // Different axes/units/series: the resolved scale config of the running
      // instance is stale, so patch nothing — build a new one.
      if (this.optionsSignature !== this.chartSignature) {
        this.recreateChart()
        return
      }

      this.applyData()

      if (this.hasSizeChanged()) {
        // The container changed since the last frame (panel resized, or the
        // chart was born before dockview measured it). `update()` would keep
        // painting the old frame — `resize()` re-reads the container and
        // repaints, exactly what manually resizing the panel used to do.
        this.chart.resize()
      } else {
        // 'none' skips the animation: this chart refreshes on a fixed cadence.
        this.chart.update('none')
      }
    },

    createChart() {
      const ctx = this.$refs.chartCanvas?.getContext('2d')
      if (!ctx) return

      this.chartSignature = this.optionsSignature
      // markRaw: never let Vue proxy the instance (see the REFRESH CONTRACT).
      this.chart = markRaw(new Chart(ctx, {
        type: 'line',
        data: this.buildChartData(),
        options: this.getChartOptions()
      }))

      // The first frame may have been measured against a panel that was still
      // hidden (0×0 canvas): re-measure as soon as the layout is final.
      this.$nextTick(() => {
        if (this.chart && this.hasSizeChanged()) this.chart.resize()
      })
    },

    recreateChart() {
      this.destroyChart()
      this.createChart()
    },

    destroyChart() {
      if (this.chart) {
        this.chart.destroy()
        this.chart = null
      }
    },

    /* ── Options ────────────────────────────────────────────────────────── */

    getChartOptions() {
      const palette = {
        text: '#e5e7eb',
        textSecondary: '#9ca3af',
        border: '#374151',
        grid: 'rgba(55, 65, 81, 0.25)',
        tooltip: 'rgba(17, 24, 39, 0.95)'
      }
      const font = { size: 12, family: "'Inter', sans-serif" }
      const titleFont = { size: 12, weight: '600', family: "'Inter', sans-serif" }

      return {
        responsive: true,
        maintainAspectRatio: false,
        // Live data: animation would fight with the refresh cadence.
        animation: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              usePointStyle: true,
              boxWidth: 8,
              boxHeight: 8,
              padding: 12,
              font: titleFont,
              color: palette.text
            }
          },
          /**
           * Native Chart.js tooltip: drawn on the canvas, so it is never lost to
           * a CSS stacking/`v-if` problem. `mode: 'index'` lists ALL series of
           * the hovered bucket at once — server aggregates and the local overlay
           * side by side, which is exactly how a slow moment gets explained.
           */
          tooltip: {
            enabled: true,
            mode: 'index',
            intersect: false,
            position: 'nearest',
            backgroundColor: palette.tooltip,
            padding: 10,
            cornerRadius: 8,
            borderColor: palette.border,
            borderWidth: 1,
            titleColor: palette.text,
            bodyColor: palette.textSecondary,
            footerColor: palette.textSecondary,
            titleFont,
            bodyFont: font,
            footerFont: { size: 11, family: "'Inter', sans-serif" },
            footerMarginTop: 6,
            boxWidth: 8,
            boxHeight: 8,
            usePointStyle: true,
            displayColors: true,
            callbacks: {
              // Each dataset is formatted with the unit of ITS axis.
              label: (context) => {
                const label = context.dataset.label || ''
                const value = context.parsed ? context.parsed.y : null
                // "No local sample" would otherwise read as "0 requests".
                if (value === null || value === undefined) return `${label}: —`
                const axis = context.dataset.yAxisID
                const unit = axis === 'y1' ? this.y1Unit : axis === 'y2' ? this.y2Unit : this.yUnit
                return `${label}: ${this.formatValue(value, unit)}`
              },
              /**
               * Local summary of the hovered bucket: the three bar values in one
               * line plus the average local latency (which is NOT plotted, so the
               * bars stay countable). This is what turns "calls: 3, avg: 210 ms"
               * into "the backend was fast, this tab had 6 requests open".
               */
              footer: (items) => {
                if (!items || !items.length) return ''
                const row = (this.rows || [])[items[0].dataIndex]
                if (!row) return ''

                const done = row.local_done
                if (done === null || done === undefined) {
                  // Outside the retained client window: a gap, not a zero.
                  return 'Local: no sample (client log keeps 1 h)'
                }

                const inflight = Number(row.local_inflight) || 0
                const failed = Number(row.local_errors) || 0
                const avg = Number(row.local_avg_ms) || 0
                const unit = this.y2Unit ? ` ${this.y2Unit}` : ''

                return [
                  `Local: ${done}${unit} done · ${inflight}${unit} in flight · ${failed}${unit} failed`,
                  `Local avg latency: ${avg} ms`
                ]
              }
            }
          }
        },
        scales: {
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            beginAtZero: true,
            ...(this.maxY ? { max: this.maxY } : {}),
            grid: { color: palette.grid },
            ticks: {
              font,
              color: palette.textSecondary,
              callback: (value) => this.formatValue(value, this.yUnit)
            },
            title: this.yTitle
              ? { display: true, text: this.yTitle, font: titleFont, color: palette.text }
              : { display: false }
          },
          y1: {
            type: 'linear',
            display: this.hasSecondaryAxis,
            position: 'right',
            beginAtZero: true,
            grid: { drawOnChartArea: false },
            ticks: {
              font,
              color: palette.textSecondary,
              callback: (value) => this.formatValue(value, this.y1Unit)
            },
            title: this.y1Title
              ? { display: true, text: this.y1Title, font: titleFont, color: palette.text }
              : { display: false }
          },
          y2: {
            type: 'linear',
            display: this.hasTertiaryAxis,
            position: 'right',
            beginAtZero: true,
            // Its own scale: local counts are per tab and must never push the
            // server series around.
            grid: { drawOnChartArea: false },
            ticks: {
              font,
              color: palette.textSecondary,
              // Counts only: "3.0 requests" would be noise.
              precision: 0,
              callback: (value) => this.formatValue(value, this.y2Unit)
            },
            title: this.y2Title
              ? { display: true, text: this.y2Title, font: titleFont, color: palette.text }
              : { display: false }
          },
          x: {
            grid: { display: false },
            // Bars need an empty half-slot at both ends, otherwise the first and
            // the last one are clipped in half by the chart area.
            offset: this.hasBarSeries,
            ticks: {
              font,
              color: palette.textSecondary,
              maxRotation: 0,
              autoSkip: true,
              maxTicksLimit: 8
            }
          }
        }
      }
    }
  },
  mounted() {
    // One tick: dockview mounts the panel and only then measures the group, so
    // creating the chart synchronously can leave it with a 0×0 canvas.
    this.$nextTick(() => this.createChart())

    // The panel can be resized/shown long after the last refresh; without this
    // the graph would keep the frame measured while it was hidden.
    if (typeof ResizeObserver !== 'undefined') {
      this.resizeObserver = new ResizeObserver(() => this.scheduleRender())
      if (this.$refs.wrapEl) this.resizeObserver.observe(this.$refs.wrapEl)
    }
  },
  beforeUnmount() {
    if (this.resizeObserver) {
      this.resizeObserver.disconnect()
      this.resizeObserver = null
    }
    this.destroyChart()
  }
}
</script>