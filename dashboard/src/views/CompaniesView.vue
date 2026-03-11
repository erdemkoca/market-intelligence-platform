<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchCompanies } from '../api/client'
import type { Company } from '../types/company'
import CompanyFilters from '../components/CompanyFilters.vue'
import CompanyTable from '../components/CompanyTable.vue'

const router = useRouter()
const companies = ref<Company[]>([])
const total = ref(0)
const offset = ref(0)
const limit = 50
const loading = ref(false)

const filters = ref({
  q: '',
  canton: '',
  industry: '',
  legal_form: '',
  status: '',
  has_email: '',
  has_phone: '',
})

async function loadCompanies() {
  loading.value = true
  try {
    const params: Record<string, string | number> = { offset: offset.value, limit }
    if (filters.value.q) params.q = filters.value.q
    if (filters.value.canton) params.canton = filters.value.canton
    if (filters.value.industry) params.industry = filters.value.industry
    if (filters.value.legal_form) params.legal_form = filters.value.legal_form
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.has_email) params.has_email = filters.value.has_email
    if (filters.value.has_phone) params.has_phone = filters.value.has_phone

    const res = await fetchCompanies(params)
    companies.value = res.items
    total.value = res.total
  } catch (e) {
    console.error('Failed to load companies', e)
  } finally {
    loading.value = false
  }
}

function onFiltersChanged(newFilters: typeof filters.value) {
  filters.value = newFilters
  offset.value = 0
  loadCompanies()
}

function onPageChange(newOffset: number) {
  offset.value = newOffset
  loadCompanies()
}

function onRowClick(company: Company) {
  router.push(`/companies/${company.id}`)
}

onMounted(loadCompanies)
</script>

<template>
  <div class="companies-page">
    <h1>Firmen</h1>
    <p class="subtitle">{{ total }} Firmen gefunden</p>

    <CompanyFilters :filters="filters" @change="onFiltersChanged" />

    <div v-if="loading" class="loading">Lade...</div>

    <CompanyTable
      v-else
      :companies="companies"
      :total="total"
      :offset="offset"
      :limit="limit"
      @row-click="onRowClick"
      @page-change="onPageChange"
    />
  </div>
</template>

<style scoped>
h1 {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 4px;
}

.subtitle {
  color: #64748b;
  font-size: 14px;
  margin-bottom: 20px;
}

.loading {
  text-align: center;
  padding: 48px;
  color: #666;
}
</style>
