<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchCompany } from '../api/client'
import type { CompanyDetail } from '../types/company'
import LeadStatusBadge from '../components/LeadStatusBadge.vue'

const route = useRoute()
const router = useRouter()
const company = ref<CompanyDetail | null>(null)
const loading = ref(true)

async function loadCompany() {
  loading.value = true
  try {
    const id = Number(route.params.id)
    company.value = await fetchCompany(id)
  } catch (e) {
    console.error('Failed to load company', e)
  } finally {
    loading.value = false
  }
}

onMounted(loadCompany)
</script>

<template>
  <div class="detail-page">
    <button class="btn-back" @click="router.back()">&larr; Zurueck</button>

    <div v-if="loading" class="loading">Lade...</div>

    <template v-else-if="company">
      <div class="detail-header">
        <div>
          <h1>{{ company.name }}</h1>
          <p class="uid" v-if="company.uid">UID: {{ company.uid }}</p>
        </div>
        <div class="header-badges">
          <span class="badge" :class="company.status === 'ACTIVE' ? 'badge-success' : 'badge-muted'">
            {{ company.status }}
          </span>
          <LeadStatusBadge v-if="company.lead" :status="company.lead.lead_status" :score="company.lead.lead_score" />
        </div>
      </div>

      <div class="grid">
        <!-- Basic Info -->
        <section class="card">
          <h2>Firmeninformationen</h2>
          <dl class="info-grid">
            <dt>Rechtsform</dt>
            <dd>{{ company.legal_form || '-' }}</dd>
            <dt>Branche</dt>
            <dd>{{ company.industry_detail || company.industry || '-' }}</dd>
            <dt>NOGA-Code</dt>
            <dd>{{ company.noga_code || '-' }}</dd>
            <dt>Gruendung</dt>
            <dd>{{ company.founding_date || '-' }}</dd>
            <dt>Kapital</dt>
            <dd>{{ company.capital ? `${company.capital.toLocaleString('de-CH')} ${company.capital_currency}` : '-' }}</dd>
            <dt>Mitarbeiter (gesch.)</dt>
            <dd>{{ company.employee_count_est || '-' }}</dd>
            <dt>Sprachregion</dt>
            <dd>{{ company.language_region || '-' }}</dd>
          </dl>
        </section>

        <!-- Location -->
        <section class="card">
          <h2>Standort</h2>
          <div v-if="company.locations.length">
            <div v-for="loc in company.locations" :key="loc.id" class="location">
              <p v-if="loc.street">{{ loc.street }}</p>
              <p>{{ loc.zip_code }} {{ loc.city }}</p>
              <p v-if="loc.canton">Kanton {{ loc.canton }}</p>
            </div>
          </div>
          <p v-else class="empty">Keine Standortdaten</p>
        </section>

        <!-- Purpose -->
        <section class="card" v-if="company.purpose">
          <h2>Zweck</h2>
          <p class="purpose-text">{{ company.purpose }}</p>
        </section>

        <!-- Enrichment -->
        <section class="card" v-if="company.enrichment">
          <h2>Enrichment</h2>
          <dl class="info-grid">
            <dt>Webseite</dt>
            <dd>
              <a v-if="company.enrichment.website" :href="company.enrichment.website" target="_blank">
                {{ company.enrichment.website }}
              </a>
              <span v-else>-</span>
            </dd>
            <dt>E-Mail</dt>
            <dd>{{ company.enrichment.email_general || '-' }}</dd>
            <dt>Telefon</dt>
            <dd>{{ company.enrichment.phone || '-' }}</dd>
            <dt>Digital Score</dt>
            <dd>{{ company.enrichment.digital_maturity_score ?? '-' }}</dd>
          </dl>
        </section>

        <!-- Lead Info -->
        <section class="card" v-if="company.lead">
          <h2>Lead-Status</h2>
          <dl class="info-grid">
            <dt>Status</dt>
            <dd><LeadStatusBadge :status="company.lead.lead_status" :score="company.lead.lead_score" /></dd>
            <dt>Score</dt>
            <dd>{{ company.lead.lead_score }}/100</dd>
            <dt>Temperatur</dt>
            <dd>{{ company.lead.lead_temperature || '-' }}</dd>
            <dt>Sales Owner</dt>
            <dd>{{ company.lead.sales_owner || '-' }}</dd>
            <dt>Baunex Kunde</dt>
            <dd>{{ company.lead.is_baunex_customer ? 'Ja' : 'Nein' }}</dd>
          </dl>
        </section>

        <!-- Identifiers -->
        <section class="card" v-if="company.identifiers.length">
          <h2>Identifikatoren</h2>
          <div v-for="ident in company.identifiers" :key="ident.identifier_value" class="identifier">
            <span class="ident-type">{{ ident.identifier_type }}</span>
            <span class="mono">{{ ident.identifier_value }}</span>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.btn-back {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  font-size: 14px;
  padding: 4px 0;
  margin-bottom: 16px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

h1 {
  font-size: 28px;
  font-weight: 700;
}

.uid {
  color: #64748b;
  font-family: monospace;
  font-size: 14px;
  margin-top: 4px;
}

.header-badges {
  display: flex;
  gap: 8px;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.card h2 {
  font-size: 15px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-grid {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 6px 12px;
  font-size: 14px;
}

.info-grid dt {
  color: #64748b;
  font-weight: 500;
}

.info-grid dd {
  color: #1e293b;
}

.purpose-text {
  font-size: 14px;
  line-height: 1.5;
  color: #334155;
}

.location {
  font-size: 14px;
  line-height: 1.5;
}

.empty {
  color: #94a3b8;
  font-size: 14px;
}

.identifier {
  display: flex;
  gap: 12px;
  padding: 4px 0;
  font-size: 14px;
}

.ident-type {
  background: #f1f5f9;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.mono {
  font-family: monospace;
}

.badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
}

.badge-success {
  background: #dcfce7;
  color: #166534;
}

.badge-muted {
  background: #f1f5f9;
  color: #475569;
}

.loading {
  text-align: center;
  padding: 48px;
  color: #666;
}

@media (max-width: 768px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
