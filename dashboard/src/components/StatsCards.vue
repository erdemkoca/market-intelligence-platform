<script setup lang="ts">
import type { CompanyStats } from '../types/company'

defineProps<{ stats: CompanyStats }>()
</script>

<template>
  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-value">{{ stats.total_companies.toLocaleString('de-CH') }}</div>
      <div class="stat-label">Firmen gesamt</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ stats.active_companies.toLocaleString('de-CH') }}</div>
      <div class="stat-label">Aktive Firmen</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ stats.new_this_week }}</div>
      <div class="stat-label">Neu diese Woche</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ Object.keys(stats.by_canton).length }}</div>
      <div class="stat-label">Kantone abgedeckt</div>
    </div>
  </div>

  <div class="breakdown-grid" v-if="Object.keys(stats.by_industry).length">
    <div class="breakdown-card">
      <h3>Nach Branche</h3>
      <div v-for="(count, industry) in stats.by_industry" :key="industry" class="breakdown-row">
        <span>{{ industry }}</span>
        <span class="count">{{ count }}</span>
      </div>
    </div>
    <div class="breakdown-card">
      <h3>Nach Kanton (Top 10)</h3>
      <div
        v-for="(count, canton) in Object.fromEntries(
          Object.entries(stats.by_canton)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 10)
        )"
        :key="canton"
        class="breakdown-row"
      >
        <span>{{ canton }}</span>
        <span class="count">{{ count }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #1e293b;
}

.stat-label {
  font-size: 13px;
  color: #64748b;
  margin-top: 4px;
}

.breakdown-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
}

.breakdown-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.breakdown-card h3 {
  font-size: 14px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 12px;
}

.breakdown-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 13px;
  border-bottom: 1px solid #f8fafc;
}

.count {
  font-weight: 600;
  color: #1e293b;
}

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .breakdown-grid { grid-template-columns: 1fr; }
}
</style>
