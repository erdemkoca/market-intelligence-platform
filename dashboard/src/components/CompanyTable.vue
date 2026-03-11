<script setup lang="ts">
import type { Company } from '../types/company'

defineProps<{
  companies: Company[]
  total: number
  offset: number
  limit: number
}>()

const emit = defineEmits<{
  rowClick: [company: Company]
  pageChange: [offset: number]
}>()
</script>

<template>
  <table class="table">
    <thead>
      <tr>
        <th>Name</th>
        <th>UID</th>
        <th>Rechtsform</th>
        <th>Branche</th>
        <th>Kanton</th>
        <th>Ort</th>
        <th>Status</th>
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="company in companies"
        :key="company.id"
        class="clickable"
        @click="emit('rowClick', company)"
      >
        <td class="name-cell">{{ company.name }}</td>
        <td class="mono">{{ company.uid || '-' }}</td>
        <td>{{ company.legal_form || '-' }}</td>
        <td>{{ company.industry_detail || company.industry || '-' }}</td>
        <td>{{ company.canton || '-' }}</td>
        <td>{{ company.city || '-' }}</td>
        <td>
          <span class="badge" :class="company.status === 'ACTIVE' ? 'badge-success' : 'badge-muted'">
            {{ company.status }}
          </span>
        </td>
      </tr>
    </tbody>
  </table>

  <div v-if="total > limit" class="pagination">
    <button :disabled="offset === 0" @click="emit('pageChange', offset - limit)">Zurueck</button>
    <span>{{ offset + 1 }}-{{ Math.min(offset + limit, total) }} von {{ total }}</span>
    <button :disabled="offset + limit >= total" @click="emit('pageChange', offset + limit)">Weiter</button>
  </div>
</template>

<style scoped>
.table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.table th, .table td { padding: 10px 14px; text-align: left; font-size: 13px; }
.table th { background: #f8fafc; font-weight: 600; color: #475569; border-bottom: 1px solid #e2e8f0; }
.table td { border-bottom: 1px solid #f1f5f9; }
.clickable { cursor: pointer; transition: background 0.1s; }
.clickable:hover { background: #f8fafc; }
.name-cell { font-weight: 500; }
.mono { font-family: monospace; font-size: 12px; color: #64748b; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.badge-success { background: #dcfce7; color: #166534; }
.badge-muted { background: #f1f5f9; color: #94a3b8; }
.pagination { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 16px; }
.pagination button { padding: 6px 16px; border: 1px solid #d1d5db; border-radius: 6px; background: white; cursor: pointer; font-size: 13px; }
.pagination button:disabled { opacity: 0.5; cursor: not-allowed; }
.pagination span { font-size: 13px; color: #64748b; }
</style>
