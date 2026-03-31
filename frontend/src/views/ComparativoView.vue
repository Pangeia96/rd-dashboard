<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-pangeia-roxo-profundo">Comparativo de Canais</h1>
      <p class="text-sm text-gray-400 mt-0.5">E-mail vs WhatsApp — conversão, receita e ticket médio</p>
    </div>

    <LoadingState v-if="loading" />

    <template v-else>
      <!-- Cards comparativos lado a lado -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- E-mail -->
        <div class="card border-l-4 border-pangeia-roxo">
          <div class="flex items-center gap-3 mb-4">
            <span class="text-3xl">📧</span>
            <div>
              <h2 class="font-bold text-pangeia-roxo-profundo">E-mail</h2>
              <p class="text-xs text-gray-400">Campanhas e automações</p>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="bg-pangeia-lilas-claro/30 rounded-xl p-3 text-center">
              <p class="text-2xl font-bold text-pangeia-roxo-medio">{{ emailStats.open_rate }}%</p>
              <p class="text-xs text-gray-500 mt-0.5">Abertura</p>
            </div>
            <div class="bg-pangeia-lilas-claro/30 rounded-xl p-3 text-center">
              <p class="text-2xl font-bold text-pangeia-roxo-medio">{{ emailStats.click_rate }}%</p>
              <p class="text-xs text-gray-500 mt-0.5">Clique</p>
            </div>
            <div class="bg-apoio-laranja-claro/40 rounded-xl p-3 text-center">
              <p class="text-2xl font-bold text-yellow-700">{{ fmtCurrency(emailRevenue) }}</p>
              <p class="text-xs text-gray-500 mt-0.5">Receita</p>
            </div>
            <div class="bg-apoio-verde-claro rounded-xl p-3 text-center">
              <p class="text-2xl font-bold text-apoio-verde-escuro">{{ emailOrders }}</p>
              <p class="text-xs text-gray-500 mt-0.5">Vendas</p>
            </div>
          </div>
        </div>

        <!-- WhatsApp -->
        <div class="card border-l-4 border-apoio-verde-escuro">
          <div class="flex items-center gap-3 mb-4">
            <span class="text-3xl">💬</span>
            <div>
              <h2 class="font-bold text-pangeia-roxo-profundo">WhatsApp</h2>
              <p class="text-xs text-gray-400">Mensagens e automações</p>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="bg-apoio-verde-claro rounded-xl p-3 text-center">
              <p class="text-2xl font-bold text-apoio-verde-escuro">{{ wppStats.read_rate }}%</p>
              <p class="text-xs text-gray-500 mt-0.5">Leitura</p>
            </div>
            <div class="bg-apoio-verde-claro rounded-xl p-3 text-center">
              <p class="text-2xl font-bold text-apoio-verde-escuro">{{ wppStats.reply_rate }}%</p>
              <p class="text-xs text-gray-500 mt-0.5">Resposta</p>
            </div>
            <div class="bg-apoio-laranja-claro/40 rounded-xl p-3 text-center">
              <p class="text-2xl font-bold text-yellow-700">{{ fmtCurrency(wppRevenue) }}</p>
              <p class="text-xs text-gray-500 mt-0.5">Receita</p>
            </div>
            <div class="bg-apoio-verde-claro rounded-xl p-3 text-center">
              <p class="text-2xl font-bold text-apoio-verde-escuro">{{ wppOrders }}</p>
              <p class="text-xs text-gray-500 mt-0.5">Vendas</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Gráfico comparativo de métricas -->
      <div class="card">
        <h2 class="font-semibold text-pangeia-roxo-profundo mb-4">Comparativo de Métricas (%)</h2>
        <div class="h-64">
          <BarChart
            :labels="['Abertura/Leitura', 'Clique/Resposta', 'Engajamento']"
            :datasets="compareDatasets"
            :stacked="false"
          />
        </div>
      </div>

      <!-- Receita por canal (barras) -->
      <div class="card">
        <h2 class="font-semibold text-pangeia-roxo-profundo mb-4">Receita por Canal</h2>
        <div class="h-48">
          <BarChart
            :labels="channelRevenueLabels"
            :datasets="channelRevenueDatasets"
            y-prefix="R$ "
          />
        </div>
      </div>

      <!-- Insight automático -->
      <div class="card bg-pangeia-lilas-claro/20 border-pangeia-lilas-medio">
        <h2 class="font-semibold text-pangeia-roxo-profundo mb-3">💡 Insight Automático</h2>
        <p class="text-sm text-gray-700 leading-relaxed">{{ insight }}</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDashboardStore } from '@/store/dashboard'
import BarChart from '@/components/BarChart.vue'
import LoadingState from '@/components/LoadingState.vue'
import axios from 'axios'

const store = useDashboardStore()
const loading = ref(false)
const salesData = ref(null)
const API_BASE = import.meta.env.VITE_API_URL || '/api'

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([
      store.fetchEmails(),
      store.fetchWhatsApp(),
      loadSales(),
    ])
  } finally {
    loading.value = false
  }
})

async function loadSales() {
  try {
    const res = await axios.get(`${API_BASE}/metrics/sales`, {
      params: { date_from: store.dateFrom, date_to: store.dateTo }
    })
    salesData.value = res.data
  } catch (e) { /* silencioso */ }
}

const emailStats = computed(() => {
  const campaigns = store.emailMetrics || []
  if (!campaigns.length) return { open_rate: 0, click_rate: 0 }
  return {
    open_rate: +(campaigns.reduce((s, c) => s + c.open_rate, 0) / campaigns.length).toFixed(1),
    click_rate: +(campaigns.reduce((s, c) => s + c.click_rate, 0) / campaigns.length).toFixed(1),
  }
})

const wppStats = computed(() => store.whatsappMetrics || { read_rate: 0, reply_rate: 0, engagement_rate: 0 })

const channels = computed(() => salesData.value?.attribution?.revenue_by_channel || {})
const emailRevenue = computed(() => channels.value?.email?.revenue || 0)
const emailOrders = computed(() => channels.value?.email?.orders_count || 0)
const wppRevenue = computed(() => channels.value?.whatsapp?.revenue || 0)
const wppOrders = computed(() => channels.value?.whatsapp?.orders_count || 0)

const compareDatasets = computed(() => [
  { label: '📧 E-mail', data: [emailStats.value.open_rate, emailStats.value.click_rate, emailStats.value.open_rate], color: '#AE76E5' },
  { label: '💬 WhatsApp', data: [wppStats.value.read_rate, wppStats.value.reply_rate, wppStats.value.engagement_rate || 0], color: '#609538' },
])

const channelRevenueLabels = computed(() =>
  Object.keys(channels.value).map(k => ({ email: '📧 E-mail', whatsapp: '💬 WhatsApp', organico: '🌱 Orgânico' }[k] || k))
)
const channelRevenueDatasets = computed(() => [{
  label: 'Receita (R$)',
  data: Object.values(channels.value).map(v => v.revenue || 0),
}])

const insight = computed(() => {
  if (!emailRevenue.value && !wppRevenue.value) {
    return 'Autentique-se com a RD Station para ver a comparação de canais com dados reais dos seus fluxos.'
  }
  if (emailRevenue.value > wppRevenue.value) {
    const diff = ((emailRevenue.value / (wppRevenue.value || 1)) * 100 - 100).toFixed(0)
    return `O canal de E-mail está gerando ${diff}% mais receita que o WhatsApp no período selecionado. Considere intensificar as automações de e-mail ou revisar a abordagem do WhatsApp.`
  } else if (wppRevenue.value > emailRevenue.value) {
    const diff = ((wppRevenue.value / (emailRevenue.value || 1)) * 100 - 100).toFixed(0)
    return `O WhatsApp está gerando ${diff}% mais receita que o E-mail no período. Isso indica que seus leads respondem melhor a mensagens diretas — considere aumentar o volume de automações via WhatsApp.`
  }
  return 'Os dois canais estão gerando receita similar. Analise o ticket médio de cada um para identificar qual traz clientes de maior valor.'
})

function fmtCurrency(v) {
  return Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}
</script>
