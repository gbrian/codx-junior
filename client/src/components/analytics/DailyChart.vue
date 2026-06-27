<script setup>
import Chart from 'chart.js/auto'
</script>

<template>
  <div class="w-full h-full bg-base-900 rounded-lg">
    <div class="flex-1 w-full h-full relative bg-base-800 rounded-lg">
      <canvas ref="chartCanvas"></canvas>
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
    },
    grouping: {
      type: String,
      default: 'day',
      validator: (v) => ['minute', 'hour', 'day'].includes(v)
    }
  },
  data() {
    return {
      chart: null,
      visibleMetrics: ['input_tokens', 'output_tokens', 'calls', 'total_cxjcoins'],
      availableMetrics: [
        { key: 'input_tokens', label: 'Input Tokens', color: '#10b981', type: 'line' },
        { key: 'output_tokens', label: 'Output Tokens', color: '#f59e0b', type: 'line' },
        { key: 'calls', label: 'Calls', color: '#3b82f6', type: 'bar' },
        { key: 'total_cxjcoins', label: 'CXJ Coins', color: '#8b5cf6', type: 'bar' }
      ]
    }
  },
  computed: {
    chartData() {
      if (!this.data || this.data.length === 0) {
        return { labels: [], datasets: [] }
      }

      const labels = this.data.map(d => d.period || d.date)
      const datasets = []

      this.availableMetrics.forEach(metric => {
        if (!this.visibleMetrics.includes(metric.key)) return

        const values = this.data.map(d => d[metric.key] || 0)
        const isBar = metric.type === 'bar'

        datasets.push({
          label: metric.label,
          data: values,
          borderColor: metric.color,
          backgroundColor: isBar ? metric.color : `rgba(${this.hexToRgb(metric.color)}, 0.15)`,
          borderWidth: isBar ? 0 : 2,
          tension: isBar ? 0 : 0.4,
          fill: !isBar,
          pointRadius: isBar ? 0 : 4,
          pointBackgroundColor: metric.color,
          pointBorderColor: '#374151',
          pointBorderWidth: 2,
          type: metric.type,
          yAxisID: this.getYAxisId(metric.key)
        })
      })

      return { labels, datasets }
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
      return result ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}` : '0, 0, 0'
    },

    getYAxisId(metricKey) {
      return ['input_tokens', 'output_tokens'].includes(metricKey) ? 'y' : 'y1'
    },

    formatTokenValue(value) {
      if (!value) return '0'
      if (value >= 1_000_000) return (value / 1_000_000).toFixed(1) + 'M'
      if (value >= 1_000) return (value / 1_000).toFixed(1) + 'K'
      return value.toFixed(1)
    },

    updateChart() {
      if (!this.$refs.chartCanvas) return

      if (this.chart) {
        this.chart.data = this.chartData
        this.chart.options = this.getChartOptions()
        this.chart.update()
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
      const baseColors = {
        bg: '#1f2937',
        border: '#374151',
        text: '#e5e7eb',
        textSecondary: '#9ca3af',
        gridColor: 'rgba(55, 65, 81, 0.2)'
      }

      return {
        responsive: true,
        maintainAspectRatio: false,
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
              padding: 15,
              font: { size: 14, weight: '600', family: "'Inter', sans-serif" },
              color: baseColors.text
            }
          },
          tooltip: {
            backgroundColor: `rgba(${this.hexToRgb('#111827')}, 0.95)`,
            padding: 14,
            titleFont: { size: 14, weight: '600', family: "'Inter', sans-serif" },
            bodyFont: { size: 13, weight: '500', family: "'Inter', sans-serif" },
            borderColor: baseColors.border,
            borderWidth: 1,
            mode: 'index',
            intersect: false,
            titleColor: baseColors.text,
            bodyColor: baseColors.textSecondary,
            callbacks: {
              label: (context) => {
                const label = context.dataset.label || ''
                const value = context.parsed.y
                const formatted = this.formatTokenValue(value)
                return `${label}: ${formatted}`
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
            grid: { color: baseColors.gridColor },
            ticks: {
              font: { size: 13, weight: '600', family: "'Inter', sans-serif" },
              color: baseColors.textSecondary,
              callback: (value) => this.formatTokenValue(value)
            },
            title: {
              display: true,
              text: 'Tokens',
              font: { size: 14, weight: '600', family: "'Inter', sans-serif" },
              color: baseColors.text
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            beginAtZero: true,
            grid: { drawOnChartArea: false },
            ticks: {
              font: { size: 13, weight: '600', family: "'Inter', sans-serif" },
              color: baseColors.textSecondary
            },
            title: {
              display: true,
              text: 'Calls / CXJ Coins',
              font: { size: 14, weight: '600', family: "'Inter', sans-serif" },
              color: baseColors.text
            }
          },
          x: {
            display: false
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
    }
  }
}
</script>