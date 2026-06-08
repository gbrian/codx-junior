<template>
  <div class="daily-chart w-full h-full relative" ref="container">
    <svg
      v-if="width && height && data.length"
      :viewBox="`0 0 ${width} ${height}`"
      class="w-full h-full"
      @mousemove="onMouseMove"
      @mouseleave="tooltip.visible = false"
    >
      <!-- Grid lines -->
      <g class="grid">
        <line
          v-for="(tick, i) in yTicks"
          :key="'hgrid-' + i"
          :x1="padding.left"
          :y1="yScale(tick)"
          :x2="width - padding.right"
          :y2="yScale(tick)"
          stroke="currentColor"
          stroke-opacity="0.08"
          stroke-width="1"
        />
      </g>

      <!-- Y axis ticks -->
      <g class="y-axis">
        <text
          v-for="(tick, i) in yTicks"
          :key="'ytick-' + i"
          :x="padding.left - 6"
          :y="yScale(tick) + 4"
          text-anchor="end"
          class="fill-current opacity-40"
          font-size="10"
        >
          {{ formatTick(tick) }}
        </text>
      </g>

      <!-- X axis ticks -->
      <g class="x-axis">
        <text
          v-for="(point, i) in xTickPoints"
          :key="'xtick-' + i"
          :x="xScale(point.index)"
          :y="height - padding.bottom + 14"
          text-anchor="middle"
          class="fill-current opacity-40"
          font-size="9"
        >
          {{ formatDate(point.date) }}
        </text>
      </g>

      <!-- Area fills -->
      <!-- Total tokens area -->
      <defs>
        <linearGradient id="totalGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#6366f1" stop-opacity="0.3" />
          <stop offset="100%" stop-color="#6366f1" stop-opacity="0.02" />
        </linearGradient>
        <linearGradient id="inputGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#22c55e" stop-opacity="0.2" />
          <stop offset="100%" stop-color="#22c55e" stop-opacity="0.01" />
        </linearGradient>
        <linearGradient id="outputGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#f59e0b" stop-opacity="0.2" />
          <stop offset="100%" stop-color="#f59e0b" stop-opacity="0.01" />
        </linearGradient>
      </defs>

      <path :d="areaPath('total_tokens')" fill="url(#totalGrad)" />
      <path :d="areaPath('input_tokens')" fill="url(#inputGrad)" />
      <path :d="areaPath('output_tokens')" fill="url(#outputGrad)" />

      <!-- Lines -->
      <path
        :d="linePath('total_tokens')"
        fill="none"
        stroke="#6366f1"
        stroke-width="2"
        stroke-linejoin="round"
        stroke-linecap="round"
      />
      <path
        :d="linePath('input_tokens')"
        fill="none"
        stroke="#22c55e"
        stroke-width="1.5"
        stroke-linejoin="round"
        stroke-linecap="round"
        stroke-dasharray="none"
      />
      <path
        :d="linePath('output_tokens')"
        fill="none"
        stroke="#f59e0b"
        stroke-width="1.5"
        stroke-linejoin="round"
        stroke-linecap="round"
      />

      <!-- Data points -->
      <g v-for="(point, i) in chartPoints" :key="'point-' + i">
        <circle
          :cx="xScale(i)"
          :cy="yScale(point.total_tokens)"
          r="3"
          fill="#6366f1"
          class="opacity-0 hover:opacity-100"
        />
      </g>

      <!-- Hover vertical line -->
      <line
        v-if="tooltip.visible"
        :x1="tooltip.x"
        :y1="padding.top"
        :x2="tooltip.x"
        :y2="height - padding.bottom"
        stroke="currentColor"
        stroke-opacity="0.3"
        stroke-width="1"
        stroke-dasharray="4,4"
      />

      <!-- Hover dots -->
      <template v-if="tooltip.visible && tooltip.point">
        <circle :cx="tooltip.x" :cy="yScale(tooltip.point.total_tokens)" r="4" fill="#6366f1" />
        <circle :cx="tooltip.x" :cy="yScale(tooltip.point.input_tokens)" r="3.5" fill="#22c55e" />
        <circle :cx="tooltip.x" :cy="yScale(tooltip.point.output_tokens)" r="3.5" fill="#f59e0b" />
      </template>
    </svg>

    <!-- Tooltip -->
    <div
      v-if="tooltip.visible && tooltip.point"
      class="absolute pointer-events-none bg-base-100 border border-base-300 rounded-lg shadow-lg p-2 z-10 text-xs"
      :style="tooltipStyle"
    >
      <p class="font-bold text-base-content mb-1">{{ tooltip.point.date }}</p>
      <div class="space-y-0.5">
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-[#6366f1] inline-block"></span>
          <span class="text-base-content/70">Total:</span>
          <span class="font-semibold">{{ formatNumber(tooltip.point.total_tokens) }}</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-[#22c55e] inline-block"></span>
          <span class="text-base-content/70">Input:</span>
          <span class="font-semibold text-success">{{ formatNumber(tooltip.point.input_tokens) }}</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-[#f59e0b] inline-block"></span>
          <span class="text-base-content/70">Output:</span>
          <span class="font-semibold text-warning">{{ formatNumber(tooltip.point.output_tokens) }}</span>
        </div>
        <div class="flex items-center gap-2 border-t border-base-300 pt-0.5 mt-0.5">
          <span class="text-base-content/70">Calls:</span>
          <span class="font-semibold">{{ tooltip.point.calls }}</span>
        </div>
      </div>
    </div>

    <!-- Legend -->
    <div class="absolute top-0 right-0 flex items-center gap-3 text-xs">
      <div class="flex items-center gap-1">
        <span class="w-3 h-0.5 bg-[#6366f1] inline-block"></span>
        <span class="text-base-content/60">Total</span>
      </div>
      <div class="flex items-center gap-1">
        <span class="w-3 h-0.5 bg-[#22c55e] inline-block"></span>
        <span class="text-base-content/60">Input</span>
      </div>
      <div class="flex items-center gap-1">
        <span class="w-3 h-0.5 bg-[#f59e0b] inline-block"></span>
        <span class="text-base-content/60">Output</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DailyChart',
  props: {
    data: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      width: 0,
      height: 0,
      padding: { top: 20, right: 20, bottom: 30, left: 55 },
      tooltip: {
        visible: false,
        x: 0,
        y: 0,
        point: null
      },
      resizeObserver: null
    }
  },
  computed: {
    chartPoints() {
      return [...this.data].sort((a, b) => a.date > b.date ? 1 : -1)
    },
    maxValue() {
      return Math.max(...this.chartPoints.map(p => p.total_tokens), 1)
    },
    yTicks() {
      const max = this.maxValue
      const step = Math.pow(10, Math.floor(Math.log10(max)))
      const nice = Math.ceil(max / step) * step
      return [0, nice * 0.25, nice * 0.5, nice * 0.75, nice].map(Math.round)
    },
    xTickPoints() {
      const n = this.chartPoints.length
      if (n === 0) return []
      const maxTicks = 7
      const step = Math.max(1, Math.floor(n / maxTicks))
      const ticks = []
      for (let i = 0; i < n; i += step) {
        ticks.push({ index: i, date: this.chartPoints[i].date })
      }
      if (ticks[ticks.length - 1]?.index !== n - 1) {
        ticks.push({ index: n - 1, date: this.chartPoints[n - 1].date })
      }
      return ticks
    },
    tooltipStyle() {
      const { x, y } = this.tooltip
      const left = x > (this.width / 2) ? `${x - 140}px` : `${x + 12}px`
      return {
        top: `${this.padding.top}px`,
        left
      }
    }
  },
  methods: {
    xScale(i) {
      const n = this.chartPoints.length
      if (n <= 1) return (this.width - this.padding.left - this.padding.right) / 2 + this.padding.left
      const range = this.width - this.padding.left - this.padding.right
      return this.padding.left + (i / (n - 1)) * range
    },
    yScale(value) {
      const range = this.height - this.padding.top - this.padding.bottom
      const max = this.yTicks[this.yTicks.length - 1] || 1
      return this.height - this.padding.bottom - (value / max) * range
    },
    linePath(key) {
      if (this.chartPoints.length === 0) return ''
      return this.chartPoints.map((p, i) => {
        const x = this.xScale(i)
        const y = this.yScale(p[key])
        return `${i === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
      }).join(' ')
    },
    areaPath(key) {
      if (this.chartPoints.length === 0) return ''
      const bottom = this.height - this.padding.bottom
      const points = this.chartPoints.map((p, i) => ({
        x: this.xScale(i),
        y: this.yScale(p[key])
      }))
      const line = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(' ')
      const close = `L ${points[points.length - 1].x.toFixed(2)} ${bottom} L ${points[0].x.toFixed(2)} ${bottom} Z`
      return `${line} ${close}`
    },
    formatTick(v) {
      if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + 'M'
      if (v >= 1_000) return (v / 1_000).toFixed(0) + 'K'
      return v
    },
    formatDate(dateStr) {
      if (!dateStr) return ''
      const [, month, day] = dateStr.split('-')
      return `${month}/${day}`
    },
    formatNumber(num) {
      if (!num) return '0'
      if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M'
      if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K'
      return num.toString()
    },
    onMouseMove(event) {
      const rect = this.$el.getBoundingClientRect()
      const svgX = event.clientX - rect.left
      const innerWidth = this.width - this.padding.left - this.padding.right
      const n = this.chartPoints.length

      if (n === 0) return

      const relX = svgX - this.padding.left
      const idx = Math.round((relX / innerWidth) * (n - 1))
      const clampedIdx = Math.max(0, Math.min(n - 1, idx))

      this.tooltip.visible = true
      this.tooltip.x = this.xScale(clampedIdx)
      this.tooltip.y = event.clientY - rect.top
      this.tooltip.point = this.chartPoints[clampedIdx]
    },
    updateSize() {
      if (!this.$refs.container) return
      this.width = this.$refs.container.clientWidth
      this.height = this.$refs.container.clientHeight
    }
  },
  mounted() {
    this.updateSize()
    this.resizeObserver = new ResizeObserver(this.updateSize)
    this.resizeObserver.observe(this.$refs.container)
  },
  beforeUnmount() {
    if (this.resizeObserver) {
      this.resizeObserver.disconnect()
    }
  }
}
</script>