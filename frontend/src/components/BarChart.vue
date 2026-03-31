<template>
  <div class="relative">
    <Bar :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS, CategoryScale, LinearScale,
  BarElement, Title, Tooltip, Legend
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const props = defineProps({
  labels:      { type: Array, default: () => [] },
  datasets:    { type: Array, default: () => [] },
  horizontal:  { type: Boolean, default: false },
  yPrefix:     { type: String, default: '' },
  stacked:     { type: Boolean, default: false },
})

const COLORS = ['#AE76E5', '#EF9837', '#4896EF', '#A4D462', '#EF62A9', '#4CC8F1']

const chartData = computed(() => ({
  labels: props.labels,
  datasets: props.datasets.map((ds, i) => ({
    ...ds,
    backgroundColor: ds.color || COLORS[i % COLORS.length],
    borderRadius: 6,
    borderSkipped: false,
  })),
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: props.horizontal ? 'y' : 'x',
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: {
      position: 'top',
      labels: { font: { size: 12, family: 'Inter' }, color: '#532194' },
    },
    tooltip: {
      callbacks: {
        label: (ctx) => {
          const val = ctx.parsed[props.horizontal ? 'x' : 'y']
          if (props.yPrefix === 'R$ ') {
            return ` ${ctx.dataset.label}: ${val.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}`
          }
          return ` ${ctx.dataset.label}: ${val.toLocaleString('pt-BR')}`
        },
      },
    },
  },
  scales: {
    x: {
      stacked: props.stacked,
      grid: { display: !props.horizontal, color: '#E3D4F930' },
      ticks: { font: { size: 11, family: 'Inter' }, color: '#888', maxTicksLimit: 12 },
    },
    y: {
      stacked: props.stacked,
      grid: { display: props.horizontal, color: '#E3D4F940' },
      ticks: {
        font: { size: 11, family: 'Inter' },
        color: '#888',
        callback: (v) => props.yPrefix === 'R$ '
          ? `R$ ${v.toLocaleString('pt-BR')}`
          : v.toLocaleString('pt-BR'),
      },
    },
  },
}))
</script>
