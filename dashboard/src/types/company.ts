export interface Company {
  id: number
  name: string
  uid: string | null
  legal_form: string | null
  status: string
  industry: string | null
  industry_detail: string | null
  canton: string | null
  city: string | null
  founding_date: string | null
  language_region: string | null
  created_at: string
  updated_at: string
}

export interface CompanyLocation {
  id: number
  location_type: string | null
  street: string | null
  zip_code: string | null
  city: string | null
  canton: string | null
  country: string
}

export interface CompanyIdentifier {
  identifier_type: string
  identifier_value: string
}

export interface Enrichment {
  website: string | null
  email_general: string | null
  phone: string | null
  has_contact_form: boolean
  services: string[] | null
  service_regions: string[] | null
  digital_maturity_score: number | null
  last_enriched_at: string | null
}

export interface LeadSummary {
  lead_status: string
  lead_score: number
  lead_temperature: string | null
  sales_owner: string | null
  is_baunex_customer: boolean
}

export interface CompanyDetail {
  id: number
  name: string
  legal_name: string | null
  uid: string | null
  hr_number: string | null
  legal_form: string | null
  status: string
  purpose: string | null
  founding_date: string | null
  capital: number | null
  capital_currency: string
  noga_code: string | null
  industry: string | null
  industry_detail: string | null
  employee_count_est: number | null
  size_class: string | null
  language_region: string | null
  created_at: string
  updated_at: string
  locations: CompanyLocation[]
  identifiers: CompanyIdentifier[]
  enrichment: Enrichment | null
  lead: LeadSummary | null
}

export interface CompanyStats {
  total_companies: number
  active_companies: number
  by_canton: Record<string, number>
  by_industry: Record<string, number>
  by_legal_form: Record<string, number>
  new_this_week: number
}

export interface Lead {
  id: number
  company_id: number
  company_name: string | null
  company_uid: string | null
  canton: string | null
  industry: string | null
  industry_detail: string | null
  is_baunex_customer: boolean
  is_baunex_trial: boolean
  had_demo: boolean
  lead_status: string
  lead_score: number
  lead_temperature: string | null
  sales_owner: string | null
  priority: string
  next_action: string | null
  next_action_date: string | null
  first_contacted_at: string | null
  last_contacted_at: string | null
  notes: string | null
  tags: string[] | null
  created_at: string
  updated_at: string
}

export interface IngestionJob {
  id: string
  source_type: string
  status: string
  started_at: string
  completed_at: string | null
  records_fetched: number
  records_created: number
  records_updated: number
  records_skipped: number
  error_message: string | null
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  offset: number
  limit: number
}
