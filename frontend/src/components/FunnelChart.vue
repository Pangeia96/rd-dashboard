<template>
  <div class="space-y-3">
    <div v-if="!steps.length" class="text-center text-gray-400 py-8 text-sm">
      Nenhuma etapa disponível para este fluxo.
    </div>
    <div
      v-for="(step, i) in steps"
      :key="i"
      class="group"
    >
      <div class="flex items-center justify-between mb-1.5">
        <div class="flex items-center gap-2">
          <span class="w-6 h-6 rounded-full bg-pangeia-lilas-claro text-pangeia-roxo-medio text-xs font-bold flex items-center justify-center flex-shrink-0">
            {{ step.position || i + 1 }}
          </span>
          <span class="text-sm font-medium text-gray-700 truncate max-w-[200px]" :title="step.name">
            {{ step.name }}
          </span>
          <span class="badge badge-info text-[10px]">{{ step.type || 'etapa' }}</span>
        </div>
        <div class="flex items-center gap-3 text-right">
          <span class="text-sm font-semibold text-pangeia-roxo-medio">
            {{ (step.contacts || 0).toLocaleString('pt-BR') }} leads
          </span>
          <span
            v-if="step.advance_rate !== undefined"
            class="text-xs font-medium"
            :class="step.advance_rate >= 50 ? 'text-apoio-verde-escuro' : step.advance_rate >= 25 ? 'text-yellow-600' : 'text-apoio-vermelho'"
          >
            {{ step.advance_rate }}% avançaram
          </span>
        </div>
      </div>
      <!-- Barra de progresso -->
      <div class="funnel-bar">
        <div
          class="funnel-bar-fill"
          :style="{ width: `${Math.min(step.advance_rate || 100, 100)}%` }"
          :class="barColor(step.advance_rate)"
        ></div>
      </div>
      <!-- Seta de abandono entre etapas -->
      <div v-if="i < steps.length - 1 && step.drop_rate > 0" class="flex items-center gap-1 mt-1 ml-8">
        <span class="text-apoio-vermelho text-xs">↓ {{ step.drop_rate }}% abandonaram aqui</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  steps: { type: Array, default: () => [] },
})

function barColor(rate) {
  if (rate >= 60) return 'bg-apoio-verde-escuro'
  if (rate >= 30) return 'bg-pangeia-roxo'
  return 'bg-apoio-vermelho'
}
</script>
