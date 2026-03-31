<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-pangeia-roxo-profundo">WhatsApp</h1>
      <p class="text-sm text-gray-400 mt-0.5">Taxa de visualização, resposta e engajamento</p>
    </div>

    <LoadingState v-if="store.loading" />

    <template v-else>
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Disparados" :value="m.total_sent || 0" icon="💬" icon-bg="bg-apoio-verde-claro" />
        <KpiCard label="Entregues" :value="m.total_delivered || 0" icon="✅" icon-bg="bg-apoio-verde-claro" />
        <KpiCard label="Taxa de Leitura" :value="m.read_rate || 0" format="percent" icon="👁️" icon-bg="bg-pangeia-lilas-claro" />
        <KpiCard label="Taxa de Resposta" :value="m.reply_rate || 0" format="percent" icon="↩️" icon-bg="bg-apoio-laranja-claro" />
      </div>

      <!-- Engajamento geral -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="card">
          <h2 class="font-semibold text-pangeia-roxo-profundo mb-4">Funil de Engajamento</h2>
          <div class="space-y-4">
            <div v-for="item in funnelItems" :key="item.label">
              <div class="flex justify-between text-sm mb-1.5">
                <span class="text-gray-600 font-medium">{{ item.label }}</span>
                <span class="font-bold text-pangeia-roxo-medio">
                  {{ item.value.toLocaleString('pt-BR') }}
                  <span class="text-gray-400 font-normal text-xs ml-1">({{ item.rate }}%)</span>
                </span>
              </div>
              <div class="funnel-bar">
                <div class="funnel-bar-fill" :style="{ width: `${item.rate}%` }" :class="item.color"></div>
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <h2 class="font-semibold text-pangeia-roxo-profundo mb-4">Distribuição de Engajamento</h2>
          <DoughnutChart
            v-if="m.total_sent"
            :labels="['Lidos', 'Respondidos', 'Clicados', 'Apenas entregues']"
            :values="[m.total_read || 0, m.total_replied || 0, m.total_clicked || 0,
              Math.max(0, (m.total_delivered || 0) - (m.total_read || 0) - (m.total_replied || 0))]"
            :colors="['#AE76E5', '#609538', '#4896EF', '#DFDFDF']"
            :center-label="`${m.engagement_rate || 0}%`"
            center-sub="engajamento"
          />
          <EmptyState v-else icon="💬" title="Sem dados de WhatsApp" subtitle="Autentique-se com a RD Station para ver as métricas." />
        </div>
      </div>

      <!-- Timeline de disparos -->
      <div class="card" v-if="(m.by_day || []).length">
        <h2 class="font-semibold text-pangeia-roxo-profundo mb-4">Disparos por Dia</h2>
        <div class="h-56">
          <BarChart
            :labels="dayLabels"
            :datasets="dayDatasets"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useDashboardStore } from '@/store/dashboard'
import KpiCard from '@/components/KpiCard.vue'
import DoughnutChart from '@/components/DoughnutChart.vue'
import BarChart from '@/components/BarChart.vue'
import LoadingState from '@/components/LoadingState.vue'
import EmptyState from '@/components/EmptyState.vue'

const store = useDashboardStore()

onMounted(async () => {
  if (!store.whatsappMetrics) await store.fetchWhatsApp()
})

const m = computed(() => store.whatsappMetrics || {})

const funnelItems = computed(() => {
  const sent = m.value.total_sent || 0
  return [
    { label: 'Enviados', value: sent, rate: 100, color: 'bg-pangeia-roxo' },
    { label: 'Entregues', value: m.value.total_delivered || 0, rate: m.value.delivery_rate || 0, color: 'bg-apoio-azul' },
    { label: 'Lidos', value: m.value.total_read || 0, rate: m.value.read_rate || 0, color: 'bg-apoio-verde-escuro' },
    { label: 'Respondidos', value: m.value.total_replied || 0, rate: m.value.reply_rate || 0, color: 'bg-apoio-laranja' },
  ]
})

const dayLabels = computed(() =>
  (m.value.by_day || []).map(d => {
    const dt = new Date(d.date + 'T12:00:00')
    return dt.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
  })
)
const dayDatasets = computed(() => [{
  label: 'Disparos',
  data: (m.value.by_day || []).map(d => Object.values(d).filter(v => typeof v === 'number').reduce((a, b) => a + b, 0)),
  color: '#AE76E5',
}])
</script>
