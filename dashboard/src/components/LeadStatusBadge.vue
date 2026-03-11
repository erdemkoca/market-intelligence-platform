<script setup lang="ts">
defineProps<{
  status: string
  score?: number
}>()

const statusColors: Record<string, string> = {
  NEW: 'badge-new',
  RESEARCHING: 'badge-research',
  QUALIFIED: 'badge-qualified',
  CONTACTED: 'badge-contacted',
  INTERESTED: 'badge-interested',
  DEMO_SCHEDULED: 'badge-demo',
  TRIAL: 'badge-trial',
  WON: 'badge-won',
  LOST: 'badge-lost',
  DISQUALIFIED: 'badge-disqualified',
}
</script>

<template>
  <span class="lead-badge" :class="statusColors[status] || 'badge-default'">
    {{ status }}
  </span>
</template>

<style scoped>
.lead-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.3px;
}

.badge-new { background: #e0f2fe; color: #0369a1; }
.badge-research { background: #f3e8ff; color: #7c3aed; }
.badge-qualified { background: #dbeafe; color: #1d4ed8; }
.badge-contacted { background: #fef3c7; color: #b45309; }
.badge-interested { background: #fed7aa; color: #c2410c; }
.badge-demo { background: #ede9fe; color: #6d28d9; }
.badge-trial { background: #fae8ff; color: #a21caf; }
.badge-won { background: #dcfce7; color: #166534; }
.badge-lost { background: #fce4ec; color: #c62828; }
.badge-disqualified { background: #f1f5f9; color: #64748b; }
.badge-default { background: #f1f5f9; color: #64748b; }
</style>
