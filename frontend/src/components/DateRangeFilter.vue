<template>
  <div class="flex flex-wrap items-center gap-3 bg-white rounded-xl px-4 py-3 border border-pangeia-lilas-claro/40 shadow-card">
    <span class="text-sm font-medium text-gray-500">Período:</span>

    <!-- Atalhos rápidos -->
    <div class="flex gap-2 flex-wrap">
      <button
        v-for="preset in presets"
        :key="preset.label"
        class="text-xs px-3 py-1.5 rounded-lg font-medium transition-colors"
        :class="activePreset === preset.label
          ? 'bg-pangeia-roxo text-white'
          : 'bg-pangeia-lilas-claro/40 text-pangeia-roxo-medio hover:bg-pangeia-lilas-claro'"
        @click="applyPreset(preset)"
      >
        {{ preset.label }}
      </button>
    </div>

    <div class="flex items-center gap-2 ml-auto">
      <input
        type="date"
        v-model="localFrom"
        class="text-sm border border-pangeia-lilas-claro rounded-lg px-3 py-1.5 text-gray-700 focus:outline-none focus:ring-2 focus:ring-pangeia-roxo/30"
      />
      <span class="text-gray-400 text-sm">até</span>
      <input
        type="date"
        v-model="localTo"
        class="text-sm border border-pangeia-lilas-claro rounded-lg px-3 py-1.5 text-gray-700 focus:outline-none focus:ring-2 focus:ring-pangeia-roxo/30"
      />
      <button class="btn-primary text-xs px-4 py-1.5" @click="apply">
        Aplicar
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useDashboardStore } from '@/store/dashboard'

const store = useDashboardStore()
const emit = defineEmits(['change'])

const localFrom = ref(store.dateFrom)
const localTo = ref(store.dateTo)
const activePreset = ref('Set/25 – Hoje')

const today = new Date().toISOString().split('T')[0]

const presets = [
  { label: 'Set/25 – Hoje', from: '2025-09-01', to: today },
  { label: 'Últimos 30 dias', from: daysAgo(30), to: today },
  { label: 'Últimos 90 dias', from: daysAgo(90), to: today },
  { label: 'Este ano', from: `${new Date().getFullYear()}-01-01`, to: today },
]

function daysAgo(n) {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().split('T')[0]
}

function applyPreset(preset) {
  activePreset.value = preset.label
  localFrom.value = preset.from
  localTo.value = preset.to
  apply()
}

function apply() {
  store.setDateRange(localFrom.value, localTo.value)
  emit('change', { from: localFrom.value, to: localTo.value })
}
</script>
