<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchCompanyStats, fetchIngestionJobs, triggerZefixIngestion } from '../api/client'
import type { CompanyStats, IngestionJob } from '../types/company'
import StatsCards from '../components/StatsCards.vue'

const stats = ref<CompanyStats | null>(null)
const jobs = ref<IngestionJob[]>([])
const loading = ref(true)
const ingesting = ref(false)

async function loadData() {
  loading.value = true
  try {
    const [s, j] = await Promise.all([fetchCompanyStats(), fetchIngestionJobs()])
    stats.value = s
    jobs.value = j
  } catch (e) {
    console.error('Failed to load dashboard data', e)
  } finally {
    loading.value = false
  }
}

async function runIngestion() {
  ingesting.value = true
  try {
    await triggerZefixIngestion()
    await loadData()
  } catch (e) {
    console.error('Ingestion failed', e)
  } finally {
    ingesting.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="dashboard">
    <div class="page-header">
      <h1>Dashboard</h1>
      <button class="btn btn-primary" :disabled="ingesting" @click="runIngestion">
        {{ ingesting ? 'Importiere...' : 'Zefix Import starten' }}
      </button>
    </div>

    <StatsCards v-if="stats" :stats="stats" />

    <div v-if="loading" class="loading">Lade Daten...</div>

    <section v-if="jobs.length" class="section">
      <h2>Letzte Import-Jobs</h2>
      <table class="table">
        <thead>
          <tr>
            <th>Job ID</th>
            <th>Quelle</th>
            <th>Status</th>
            <th>Geholt</th>
            <th>Neu</th>
            <th>Aktualisiert</th>
            <th>Gestartet</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="job in jobs" :key="job.id">
            <td class="mono">{{ job.id }}</td>
            <td>{{ job.source_type }}</td>
            <td>
              <span
                class="badge"
                :class="{
                  'badge-success': job.status === 'COMPLETED',
                  'badge-danger': job.status === 'FAILED',
                  'badge-warning': job.status === 'RUNNING',
                }"
              >
                {{ job.status }}
              </span>
            </td>
            <td>{{ job.records_fetched }}</td>
            <td>{{ job.records_created }}</td>
            <td>{{ job.records_updated }}</td>
            <td>{{ new Date(job.started_at).toLocaleString('de-CH') }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

h1 {
  font-size: 24px;
  font-weight: 700;
}

h2 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 12px;
}

.section {
  margin-top: 32px;
}

.loading {
  text-align: center;
  padding: 48px;
  color: #666;
}

.btn {
  padding: 8px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-primary {
  background: #2563eb;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.table th,
.table td {
  padding: 10px 14px;
  text-align: left;
  font-size: 13px;
}

.table th {
  background: #f8fafc;
  font-weight: 600;
  color: #475569;
  border-bottom: 1px solid #e2e8f0;
}

.table td {
  border-bottom: 1px solid #f1f5f9;
}

.mono {
  font-family: monospace;
  font-size: 12px;
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.badge-success {
  background: #dcfce7;
  color: #166534;
}

.badge-danger {
  background: #fce4ec;
  color: #c62828;
}

.badge-warning {
  background: #fff3e0;
  color: #e65100;
}
</style>
