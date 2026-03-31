<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-pangeia-roxo-profundo">Campanhas de E-mail</h1>
      <p class="text-sm text-gray-400 mt-0.5">Taxa de abertura, clique, conversão e descadastro</p>
    </div>

    <LoadingState v-if="store.loading" />

    <template v-else>
      <!-- KPIs -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Campanhas" :value="campaigns.length" icon="📧" />
        <KpiCard label="Média Abertura" :value="avgOpen" format="percent" icon="👁️" icon-bg="bg-pangeia-lilas-claro" />
        <KpiCard label="Média Clique" :value="avgClick" format="percent" icon="🖱️" icon-bg="bg-apoio-laranja-claro" />
        <KpiCard label="Melhor Campanha" :value="bestOpen" format="percent" icon="🏆" icon-bg="bg-apoio-verde-claro" subtitle="maior abertura" />
      </div>

      <!-- Gráfico de abertura por campanha -->
      <div class="card" v-if="campaigns.length">
        <h2 class="font-semibold text-pangeia-roxo-profundo mb-4">Taxa de Abertura por Campanha (Top 10)</h2>
        <div class="h-64">
          <BarChart
            :labels="top10Labels"
            :datasets="top10Datasets"
            :horizontal="true"
          />
        </div>
      </div>

      <!-- Tabela de campanhas -->
      <div class="card">
        <div class="flex items-center justify-between mb-4">
          <h2 class="font-semibold text-pangeia-roxo-profundo">Todas as Campanhas</h2>
          <div class="flex gap-2">
            <input
              v-model="search"
              placeholder="Buscar campanha..."
              class="text-sm border border-pangeia-lilas-claro rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-pangeia-roxo/30 w-48"
            />
            <button class="btn-secondary text-xs" @click="exportCSV">⬇ CSV</button>
          </div>
        </div>

        <div v-if="filtered.length" class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>Campanha</th>
                <th>Enviados</th>
                <th>Abertura</th>
                <th>Clique</th>
                <th>Bounce</th>
                <th>Descadastro</th>
                <th>Desempenho</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in filtered" :key="c.id">
                <td>
                  <div>
                    <p class="font-medium text-gray-800 text-sm">{{ c.name }}</p>
                    <p class="text-xs text-gray-400">{{ formatDate(c.sent_at) }}</p>
                  </div>
                </td>
                <td>{{ (c.sent || 0).toLocaleString('pt-BR') }}</td>
                <td>
                  <span class="font-semibold" :class="rateColor(c.open_rate, 25, 15)">
                    {{ c.open_rate }}%
                  </span>
                </td>
                <td>
                  <span class="font-semibold" :class="rateColor(c.click_rate, 3, 1.5)">
                    {{ c.click_rate }}%
                  </span>
                </td>
                <td class="text-apoio-vermelho">{{ c.bounce_rate }}%</td>
                <td class="text-gray-500">{{ c.unsubscribe_rate }}%</td>
                <td>
                  <span class="badge" :class="{
                    'badge-success': c.performance === 'excelente',
                    'badge-info': c.performance === 'bom',
                    'badge-warning': c.performance === 'regular',
                    'badge-danger': c.performance === 'abaixo_da_media',
                  }">
                    {{ perfLabel(c.performance) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <EmptyState
          v-else
          icon="📧"
          title="Nenhuma campanha encontrada"
          subtitle="Autentique-se com a RD Station para carregar as campanhas de e-mail."
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDashboardStore } from '@/store/dashboard'
import KpiCard from '@/components/KpiCard.vue'
import BarChart from '@/components/BarChart.vue'
import LoadingState from '@/components/LoadingState.vue'
import EmptyState from '@/components/EmptyState.vue'

const store = useDashboardStore()
const search = ref('')

onMounted(async () => {
  if (!store.emailMetrics.length) await store.fetchEmails()
})

const campaigns = computed(() => store.emailMetrics || [])
const filtered = computed(() =>
  campaigns.value.filter(c =>
    c.name.toLowerCase().includes(search.value.toLowerCase())
  )
)

const avgOpen = computed(() =>
  campaigns.value.length
    ? +(campaigns.value.reduce((s, c) => s + c.open_rate, 0) / campaigns.value.length).toFixed(1)
    : 0
)
const avgClick = computed(() =>
  campaigns.value.length
    ? +(campaigns.value.reduce((s, c) => s + c.click_rate, 0) / campaigns.value.length).toFixed(1)
    : 0
)
const bestOpen = computed(() =>
  campaigns.value.length ? Math.max(...campaigns.value.map(c => c.open_rate)) : 0
)

const top10 = computed(() =>
  [...campaigns.value].sort((a, b) => b.open_rate - a.open_rate).slice(0, 10)
)
const top10Labels = computed(() => top10.value.map(c => c.name.slice(0, 30)))
const top10Datasets = computed(() => [
  { label: 'Abertura (%)', data: top10.value.map(c => c.open_rate), color: '#AE76E5' },
  { label: 'Clique (%)', data: top10.value.map(c => c.click_rate), color: '#EF9837' },
])

function rateColor(val, good, ok) {
  if (val >= good) return 'text-apoio-verde-escuro'
  if (val >= ok) return 'text-yellow-600'
  return 'text-apoio-vermelho'
}

function perfLabel(p) {
  return { excelente: 'Excelente', bom: 'Bom', regular: 'Regular', abaixo_da_media: 'Abaixo' }[p] || p
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' })
}

function exportCSV() {
  const rows = [['Campanha', 'Enviados', 'Abertura%', 'Clique%', 'Bounce%', 'Descadastro%', 'Desempenho']]
  filtered.value.forEach(c => {
    rows.push([c.name, c.sent, c.open_rate, c.click_rate, c.bounce_rate, c.unsubscribe_rate, c.performance])
  })
  const csv = rows.map(r => r.join(';')).join('\n')
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = 'campanhas_email.csv'; a.click()
}
</script>
