<template>
  <div class="relative">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement,
  Title, Tooltip, Legend, Filler
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const props = defineProps({
  labels:   { type: Array, default: () => [] },
  datasets: { type: Array, default: () => [] },
  title:    { type: String, default: '' },
  yPrefix:  { type: String, default: '' }, // ex: 'R$ '
})

const chartData = computed(() => ({
  labels: props.labels,
  datasets: props.datasets.map((ds, i) => ({
    ...ds,
    borderColor: ds.color || ['#AE76E5', '#EF9837', '#4896EF', '#A4D462'][i % 4],
    backgroundColor: ds.color
      ? `${ds.color}22`
      : ['#AE76E522', '#EF983722', '#4896EF22', '#A4D46222'][i % 4],
    borderWidth: 2.5,
    pointRadius: 3,
    pointHoverRadius: 6,
    tension: 0.4,
    fill: ds.fill ?? true,
  })),
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: {
      position: 'top',
      labels: { font: { size: 12, family: 'Inter' }, color: '#532194' },
    },
    tooltip: {
      callbacks: {
        label: (ctx) => {
          const val = ctx.parsed.y
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
      grid: { color: '#E3D4F920' },
      ticks: { font: { size: 11, family: 'Inter' }, color: '#888', maxTicksLimit: 10 },
    },
    y: {
      grid: { color: '#E3D4F940' },
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
