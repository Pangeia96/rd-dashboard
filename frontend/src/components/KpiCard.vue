<template>
  <div class="kpi-card">
    <!-- Skeleton loading state -->
    <div v-if="loading" class="animate-pulse">
      <div class="h-3 bg-gray-200 rounded w-24 mb-3"></div>
      <div class="h-7 bg-gray-200 rounded w-32 mb-2"></div>
    </div>
    <div v-else class="flex items-start justify-between">
      <div class="flex-1">
        <p class="kpi-label">{{ label }}</p>
        <p class="kpi-value mt-1">{{ formattedValue }}</p>
        <p v-if="subtitle" class="text-xs text-gray-400 mt-1">{{ subtitle }}</p>
      </div>
      <div
        v-if="icon"
        class="w-12 h-12 rounded-xl flex items-center justify-center text-2xl flex-shrink-0"
        :class="iconBg"
      >
        {{ icon }}
      </div>
    </div>
    <div v-if="delta !== undefined" class="mt-2">
      <span class="kpi-delta" :class="delta >= 0 ? 'positive' : 'negative'">
        {{ delta >= 0 ? '▲' : '▼' }} {{ Math.abs(delta) }}%
        <span class="text-gray-400 font-normal">vs. período anterior</span>
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label:    { type: String, required: true },
  loading:  { type: Boolean, default: false },
  value:    { type: [Number, String], default: 0 },
  format:   { type: String, default: 'number' }, // 'number' | 'currency' | 'percent'
  icon:     { type: String, default: '' },
  iconBg:   { type: String, default: 'bg-pangeia-lilas-claro' },
  subtitle: { type: String, default: '' },
  delta:    { type: Number, default: undefined },
})

const formattedValue = computed(() => {
  const v = Number(props.value) || 0
  if (props.format === 'currency') {
    return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
  }
  if (props.format === 'percent') {
    return `${v.toFixed(1)}%`
  }
  return v.toLocaleString('pt-BR')
})
</script>
