<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-pangeia-roxo-profundo">Receita e Vendas</h1>
        <p class="text-sm text-gray-400 mt-0.5">Análise de receita por fluxo, etapa e canal</p>
      </div>
      <DateRangeFilter @change="reload" />
    </div>

    <LoadingState v-if="loading" message="Carregando dados de receita..." />

    <template v-else>
      <!-- KPIs de receita -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Receita Total" :value="data?.attribution?.total_revenue || 0" format="currency" icon="💰" icon-bg="bg-apoio-laranja-claro" />
        <KpiCard label="Pedidos Pagos" :value="data?.attribution?.total_paid_orders || 0" icon="🛒" icon-bg="bg-apoio-verde-claro" />
        <KpiCard label="Ticket Médio" :value="data?.nuvemshop_summary?.average_ticket || 0" format="currency" icon="🎯" icon-bg="bg-pangeia-lilas-claro" />
        <KpiCard label="Clientes Únicos" :value="data?.nuvemshop_summary?.unique_customers || 0" icon="👥" icon-bg="bg-apoio-azul-claro" />
      </div>

      <!-- Timeline de receita -->
      <div class="card">
        <div class="flex items-center justify-between mb-4">
          <h2 class="font-semibold text-pangeia-roxo-profundo">Evolução da Receita</h2>
          <div class="flex gap-2">
            <button
              v-for="view in ['Diário', 'Semanal']"
              :key="view"
              class="text-xs px-3 py-1.5 rounded-lg font-medium transition-colors"
              :class="timeView === view ? 'bg-pangeia-roxo text-white' : 'bg-pangeia-lilas-claro/40 text-pangeia-roxo-medio'"
              @click="timeView = view"
            >
              {{ view }}
            </button>
          </div>
        </div>
        <div class="h-72">
          <LineChart
            v-if="timelineLabels.length"
            :labels="timelineLabels"
            :datasets="timelineDatasets"
            y-prefix="R$ "
          />
          <EmptyState v-else icon="📈" title="Sem dados no período selecionado" />
        </div>
      </div>

      <!-- Receita por fluxo + por canal -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Receita por fluxo (barras horizontais) -->
        <div class="card">
          <h2 class="font-semibold text-pangeia-roxo-profundo mb-4">Receita por Fluxo de Automação</h2>
          <div class="h-64" v-if="autoLabels.length">
            <BarChart
              :labels="autoLabels"
              :datasets="autoDatasets"
              :horizontal="true"
              y-prefix="R$ "
            />
          </div>
          <EmptyState v-else icon="🔄" title="Dados disponíveis após autenticação com a RD Station" />
        </div>

        <!-- Receita por canal -->
        <div class="card">
          <h2 class="font-semibold text-pangeia-roxo-profundo mb-4">Receita por Canal</h2>
          <DoughnutChart
            v-if="channelLabels.length"
            :labels="channelLabels"
            :values="channelValues"
            :center-label="totalFormatted"
            center-sub="total"
            format="currency"
          />
          <EmptyState v-else icon="📊" title="Dados disponíveis após autenticação com a RD Station" />
        </div>
      </div>

      <!-- Tabela detalhada de fluxos -->
      <div class="card" v-if="autoList.length">
        <div class="flex items-center justify-between mb-4">
          <h2 class="font-semibold text-pangeia-roxo-profundo">Detalhamento por Fluxo</h2>
          <button class="btn-secondary text-xs" @click="exportCSV">
            ⬇ Exportar CSV
          </button>
        </div>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Fluxo</th>
                <th>Receita</th>
                <th>Vendas</th>
                <th>Ticket Médio</th>
                <th>Clientes</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(a, i) in autoList" :key="a.automation_id">
                <td class="font-bold text-pangeia-roxo-medio">{{ i + 1 }}</td>
                <td class="font-medium">{{ a.automation_name }}</td>
                <td class="font-semibold text-apoio-verde-escuro">{{ fmt(a.revenue) }}</td>
                <td>{{ a.orders_count }}</td>
                <td>{{ fmt(a.average_ticket) }}</td>
                <td>{{ a.customers_count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDashboardStore } from '@/store/dashboard'
import KpiCard from '@/components/KpiCard.vue'
import DateRangeFilter from '@/components/DateRangeFilter.vue'
import LineChart from '@/components/LineChart.vue'
import BarChart from '@/components/BarChart.vue'
import DoughnutChart from '@/components/DoughnutChart.vue'
import LoadingState from '@/components/LoadingState.vue'
import EmptyState from '@/components/EmptyState.vue'
import axios from 'axios'

const store = useDashboardStore()
const loading = ref(false)
const data = ref(null)
const timeView = ref('Diário')
const API_BASE = import.meta.env.VITE_API_URL || '/api'

onMounted(reload)

async function reload() {
  loading.value = true
  try {
    const [salesRes, timelineRes] = await Promise.all([
      axios.get(`${API_BASE}/metrics/sales`, { params: { date_from: store.dateFrom, date_to: store.dateTo } }),
      axios.get(`${API_BASE}/metrics/timeline`, { params: { date_from: store.dateFrom, date_to: store.dateTo } }),
    ])
    data.value = salesRes.data
    store.timeline = timelineRes.data.timeline || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

// Timeline
const timelineLabels = computed(() =>
  (store.timeline || []).map(d => {
    const dt = new Date(d.date + 'T12:00:00')
    return dt.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
  })
)
const timelineDatasets = computed(() => [
  { label: 'Receita (R$)', data: (store.timeline || []).map(d => d.revenue) },
  { label: 'Pedidos', data: (store.timeline || []).map(d => d.orders), color: '#EF9837', fill: false },
])

// Automações
const autoList = computed(() => data.value?.attribution?.revenue_by_automation || [])
const autoLabels = computed(() => autoList.value.slice(0, 8).map(a => a.automation_name))
const autoDatasets = computed(() => [{
  label: 'Receita (R$)',
  data: autoList.value.slice(0, 8).map(a => a.revenue),
}])

// Canal
const channelLabels = computed(() => {
  const ch = data.value?.attribution?.revenue_by_channel || {}
  return Object.keys(ch).map(k => ({ email: '📧 E-mail', whatsapp: '💬 WhatsApp', organico: '🌱 Orgânico' }[k] || k))
})
const channelValues = computed(() => {
  const ch = data.value?.attribution?.revenue_by_channel || {}
  return Object.values(ch).map(v => v.revenue || 0)
})

const totalFormatted = computed(() =>
  fmt(data.value?.attribution?.total_revenue || 0)
)

function fmt(v) {
  return Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function exportCSV() {
  const rows = [['#', 'Fluxo', 'Receita', 'Vendas', 'Ticket Médio', 'Clientes']]
  autoList.value.forEach((a, i) => {
    rows.push([i + 1, a.automation_name, a.revenue, a.orders_count, a.average_ticket, a.customers_count])
  })
  const csv = rows.map(r => r.join(';')).join('\n')
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `receita_por_fluxo_${store.dateFrom}_${store.dateTo}.csv`
  a.click()
}
</script>
