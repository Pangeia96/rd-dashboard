<template>
  <div class="relative flex flex-col items-center">
    <div class="relative w-full max-w-xs">
      <Doughnut :data="chartData" :options="chartOptions" />
      <!-- Valor central -->
      <div v-if="centerLabel" class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <p class="text-2xl font-bold text-pangeia-roxo-medio">{{ centerLabel }}</p>
        <p class="text-xs text-gray-400">{{ centerSub }}</p>
      </div>
    </div>
    <!-- Legenda customizada -->
    <div class="flex flex-wrap justify-center gap-4 mt-4">
      <div v-for="(item, i) in legendItems" :key="i" class="flex items-center gap-2">
        <span class="w-3 h-3 rounded-full" :style="{ background: item.color }"></span>
        <span class="text-sm text-gray-600">{{ item.label }}</span>
        <span class="text-sm font-semibold text-pangeia-roxo-medio">{{ item.value }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'

ChartJS.register(ArcElement, Tooltip, Legend)

const props = defineProps({
  labels:      { type: Array, default: () => [] },
  values:      { type: Array, default: () => [] },
  colors:      { type: Array, default: () => ['#AE76E5', '#EF9837', '#4896EF', '#A4D462', '#EF62A9'] },
  centerLabel: { type: String, default: '' },
  centerSub:   { type: String, default: '' },
  format:      { type: String, default: 'number' },
})

const chartData = computed(() => ({
  labels: props.labels,
  datasets: [{
    data: props.values,
    backgroundColor: props.colors,
    borderColor: '#fff',
    borderWidth: 3,
    hoverOffset: 8,
  }],
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: true,
  cutout: '68%',
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => {
          const total = ctx.dataset.data.reduce((a, b) => a + b, 0)
          const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0
          return ` ${ctx.label}: ${pct}%`
        },
      },
    },
  },
}

const legendItems = computed(() =>
  props.labels.map((label, i) => ({
    label,
    color: props.colors[i % props.colors.length],
    value: props.format === 'currency'
      ? Number(props.values[i] || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
      : Number(props.values[i] || 0).toLocaleString('pt-BR'),
  }))
)
</script>
