<script setup lang="ts">
import { reactive, watch } from 'vue'

const props = defineProps<{
  filters: {
    q: string
    canton: string
    industry: string
    legal_form: string
    status: string
  }
}>()

const emit = defineEmits<{
  change: [filters: typeof props.filters]
}>()

const local = reactive({ ...props.filters })

let debounceTimer: ReturnType<typeof setTimeout> | null = null

function onSearchInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => emit('change', { ...local }), 300)
}

function onSelectChange() {
  emit('change', { ...local })
}

const cantons = [
  'AG', 'AI', 'AR', 'BE', 'BL', 'BS', 'FR', 'GE', 'GL', 'GR',
  'JU', 'LU', 'NE', 'NW', 'OW', 'SG', 'SH', 'SO', 'SZ', 'TG',
  'TI', 'UR', 'VD', 'VS', 'ZG', 'ZH',
]

const industries = [
  'MALEREI', 'GIPSEREI', 'FASSADENBAU', 'VERPUTZEREI', 'STUCKATEUR',
  'GLASEREI', 'TAPEZIEREREI',
]

const legalForms = ['AG', 'GmbH', 'Einzelfirma', 'Genossenschaft', 'Kollektivgesellschaft']
</script>

<template>
  <div class="filters">
    <input
      v-model="local.q"
      type="text"
      placeholder="Firma suchen..."
      class="search-input"
      @input="onSearchInput"
    />
    <select v-model="local.canton" @change="onSelectChange">
      <option value="">Alle Kantone</option>
      <option v-for="c in cantons" :key="c" :value="c">{{ c }}</option>
    </select>
    <select v-model="local.industry" @change="onSelectChange">
      <option value="">Alle Branchen</option>
      <option v-for="i in industries" :key="i" :value="i">{{ i }}</option>
    </select>
    <select v-model="local.legal_form" @change="onSelectChange">
      <option value="">Alle Rechtsformen</option>
      <option v-for="lf in legalForms" :key="lf" :value="lf">{{ lf }}</option>
    </select>
    <select v-model="local.status" @change="onSelectChange">
      <option value="">Alle Status</option>
      <option value="ACTIVE">Aktiv</option>
      <option value="LIQUIDATED">Liquidiert</option>
    </select>
  </div>
</template>

<style scoped>
.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 200px;
  padding: 8px 14px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.search-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

select {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  background: white;
  cursor: pointer;
}
</style>
