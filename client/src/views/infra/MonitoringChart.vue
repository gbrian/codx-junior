<script setup>
import Chart from 'chart.js/auto'
</script>

<template>
  <div class="relative w-full h-full">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script>
/**
 * Generic Chart.js wrapper used by the infrastructure monitoring panel.
 *
 * Uses the SAME library and the SAME palette/typography as the analytics
 * charts (`src/components/analytics/DailyChart.vue`) so both dashboards look
 * like they belong to the same product:
 *   text #e5e7eb · secondary text #9ca3af · border #374151
 *   grid rgba(55,65,81,.25) · tooltip rgba(17,24,39,.95)
 *
 * The component is presentation only: it renders whatever `samples` +
 * `metrics` receive and never fetches anything.
 */
export default {
  name: 'MonitoringChart',
  props: {
    /** Ordered time samples, e.g. `[{ t: ISO, cpu: 12.3, mem: 40 }, …]`. */
    samples: {
      type: Array,
      default: () => []
    },
    /**
     * Series descriptors:
     * `{ key, label, color, type: 'line'|'bar', axis: 'y'|'y1', fill: boolean }`
     */
    metrics: {
      type: Array,
      default: () => []
    },
    /** Fixed upper bound of the left axis (e.g. 100 for percentages). */
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
    /** Suffix appended to every value in the axis and the tooltip. */
    unit: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      chart: null
    }
  },
  computed: {
    chartData() {
      const samples = this.samples || []
      const labels = samples.map(sample => this.formatLabel(sample.t))
      const datasets = (this.metrics || []).map(metric => {
        const color = metric.color || '#6366f1'
        const isBar = metric.type === 'bar'

        return {
          label: metric.label,
          data: samples.map(sample => Number(sample[metric.key] || 0)),
          type: isBar ? 'bar' : 'line',
          borderColor: color,
          backgroundColor: isBar
            ? `rgba(${this.hexToRgb(color)}, 0.55)`
            : `rgba(${this.hexToRgb(color)}, 0.12)`,
          borderWidth: isBar ? 0 : 2,
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
    hasSecondaryAxis() {
      return (this.metrics || []).some(metric => (metric.axis || 'y') === 'y1')
    }
  },
  watch: {
    chartData: {
      handler() {
        this.updateChart()
      },
      deep: true
    }
  },
  methods: {
    hexToRgb(hex) {
      const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
      return result
        ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`
        : '99, 102, 241'
    },

    /** HH:MM:SS — the buffer never spans more than a few minutes. */
    formatLabel(iso) {
      if (!iso) return ''
      const date = new Date(iso)
      if (isNaN(date.getTime())) return ''
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    },

    formatValue(value) {
      const num = Number(value) || 0
      const text = Number.isInteger(num) ? String(num) : num.toFixed(1)
      return this.unit ? `${text}${this.unit}` : text
    },

    updateChart() {
      if (!this.$refs.chartCanvas) return

      if (this.chart) {
        // Replace data + options in place: recreating the chart on every poll
        // would reset the hover state and flicker the canvas.
        this.chart.data = this.chartData
        this.chart.options = this.getChartOptions()
        this.chart.update('none')
      } else {
        this.initChart()
      }
    },

    initChart() {
      const ctx = this.$refs.chartCanvas?.getContext('2d')
      if (!ctx) return

      this.chart = new Chart(ctx, {
        type: 'line',
        data: this.chartData,
        options: this.getChartOptions()
      })
    },

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
        // Live data: animation would fight with the 5s cadence.
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
          tooltip: {
            backgroundColor: palette.tooltip,
            padding: 10,
            borderColor: palette.border,
            borderWidth: 1,
            titleColor: palette.text,
            bodyColor: palette.textSecondary,
            titleFont,
            bodyFont: font,
            callbacks: {
              label: (context) => `${context.dataset.label}: ${this.formatValue(context.parsed.y)}`
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
              callback: (value) => this.formatValue(value)
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
              callback: (value) => this.formatValue(value)
            },
            title: this.y1Title
              ? { display: true, text: this.y1Title, font: titleFont, color: palette.text }
              : { display: false }
          },
          x: {
            grid: { display: false },
            ticks: {
              font,
              color: palette.textSecondary,
              maxRotation: 0,
              autoSkip: true,
              maxTicksLimit: 6
            }
          }
        }
      }
    }
  },
  mounted() {
    this.initChart()
  },
  beforeUnmount() {
    if (this.chart) {
      this.chart.destroy()
      this.chart = null
    }
  }
}
</script>
