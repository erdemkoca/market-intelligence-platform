<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchLeads } from '../api/client'
import type { Lead } from '../types/company'
import LeadStatusBadge from '../components/LeadStatusBadge.vue'

const leads = ref<Lead[]>([])
const total = ref(0)
const offset = ref(0)
const limit = 50
const loading = ref(false)
const statusFilter = ref('')
const temperatureFilter = ref('')

const statuses = ['NEW', 'RESEARCHING', 'QUALIFIED', 'CONTACTED', 'INTERESTED', 'DEMO_SCHEDULED', 'TRIAL', 'WON', 'LOST', 'DISQUALIFIED']
const temperatures = ['HOT', 'WARM', 'COLD']

async function loadLeads() {
  loading.value = true
  try {
    const params: Record<string, string | number> = { offset: offset.value, limit }
    if (statusFilter.value) params.lead_status = statusFilter.value
    if (temperatureFilter.value) params.lead_temperature = temperatureFilter.value

    const res = await fetchLeads(params)
    leads.value = res.items
    total.value = res.total
  } catch (e) {
    console.error('Failed to load leads', e)
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  offset.value = 0
  loadLeads()
}

onMounted(loadLeads)
</script>

<template>
  <div class="leads-page">
    <h1>Leads</h1>
    <p class="subtitle">{{ total }} Leads</p>

    <div class="filters">
      <select v-model="statusFilter" @change="onFilterChange">
        <option value="">Alle Status</option>
        <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
      </select>
      <select v-model="temperatureFilter" @change="onFilterChange">
        <option value="">Alle Temperaturen</option>
        <option v-for="t in temperatures" :key="t" :value="t">{{ t }}</option>
      </select>
    </div>

    <div v-if="loading" class="loading">Lade...</div>

    <table v-else class="table">
      <thead>
        <tr>
          <th>Firma</th>
          <th>Branche</th>
          <th>Kanton</th>
          <th>Status</th>
          <th>Score</th>
          <th>Temperatur</th>
          <th>Owner</th>
          <th>Baunex</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="lead in leads" :key="lead.id">
          <td>
            <router-link :to="`/companies/${lead.company_id}`" class="company-link">
              {{ lead.company_name }}
            </router-link>
            <div class="uid-small" v-if="lead.company_uid">{{ lead.company_uid }}</div>
          </td>
          <td>{{ lead.industry_detail || lead.industry || '-' }}</td>
          <td>{{ lead.canton || '-' }}</td>
          <td><LeadStatusBadge :status="lead.lead_status" :score="lead.lead_score" /></td>
          <td>
            <div class="score-bar">
              <div class="score-fill" :style="{ width: lead.lead_score + '%' }"></div>
              <span class="score-label">{{ lead.lead_score }}</span>
            </div>
          </td>
          <td>
            <span
              v-if="lead.lead_temperature"
              class="temp-badge"
              :class="{
                'temp-hot': lead.lead_temperature === 'HOT',
                'temp-warm': lead.lead_temperature === 'WARM',
                'temp-cold': lead.lead_temperature === 'COLD',
              }"
            >
              {{ lead.lead_temperature }}
            </span>
          </td>
          <td>{{ lead.sales_owner || '-' }}</td>
          <td>
            <span v-if="lead.is_baunex_customer" class="badge badge-success">Kunde</span>
            <span v-else-if="lead.is_baunex_trial" class="badge badge-warning">Trial</span>
            <span v-else class="badge badge-muted">-</span>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-if="total > limit" class="pagination">
      <button :disabled="offset === 0" @click="offset -= limit; loadLeads()">Zurueck</button>
      <span>{{ offset + 1 }}-{{ Math.min(offset + limit, total) }} von {{ total }}</span>
      <button :disabled="offset + limit >= total" @click="offset += limit; loadLeads()">Weiter</button>
    </div>
  </div>
</template>

<style scoped>
h1 { font-size: 24px; font-weight: 700; margin-bottom: 4px; }
.subtitle { color: #64748b; font-size: 14px; margin-bottom: 16px; }

.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.filters select {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  background: white;
}

.table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.table th, .table td { padding: 10px 14px; text-align: left; font-size: 13px; }
.table th { background: #f8fafc; font-weight: 600; color: #475569; border-bottom: 1px solid #e2e8f0; }
.table td { border-bottom: 1px solid #f1f5f9; }

.company-link { color: #2563eb; text-decoration: none; font-weight: 500; }
.company-link:hover { text-decoration: underline; }
.uid-small { font-family: monospace; font-size: 11px; color: #94a3b8; }

.score-bar { position: relative; width: 80px; height: 20px; background: #f1f5f9; border-radius: 4px; overflow: hidden; }
.score-fill { height: 100%; background: linear-gradient(90deg, #fbbf24, #22c55e); border-radius: 4px; transition: width 0.3s; }
.score-label { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 11px; font-weight: 600; }

.temp-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; }
.temp-hot { background: #fce4ec; color: #c62828; }
.temp-warm { background: #fff3e0; color: #e65100; }
.temp-cold { background: #e3f2fd; color: #1565c0; }

.badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.badge-success { background: #dcfce7; color: #166534; }
.badge-warning { background: #fff3e0; color: #e65100; }
.badge-muted { background: #f1f5f9; color: #94a3b8; }

.pagination { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 16px; }
.pagination button { padding: 6px 16px; border: 1px solid #d1d5db; border-radius: 6px; background: white; cursor: pointer; font-size: 13px; }
.pagination button:disabled { opacity: 0.5; cursor: not-allowed; }
.pagination span { font-size: 13px; color: #64748b; }

.loading { text-align: center; padding: 48px; color: #666; }
</style>
