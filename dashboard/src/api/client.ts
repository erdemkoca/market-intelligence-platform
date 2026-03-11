import axios from 'axios'
import type { Company, CompanyDetail, CompanyStats, Lead, PaginatedResponse, IngestionJob } from '../types/company'

const api = axios.create({
  baseURL: '/api',
})

export async function fetchCompanies(params: Record<string, string | number | undefined> = {}): Promise<PaginatedResponse<Company>> {
  const { data } = await api.get('/companies', { params })
  return data
}

export async function fetchCompany(id: number): Promise<CompanyDetail> {
  const { data } = await api.get(`/companies/${id}`)
  return data
}

export async function fetchCompanyStats(): Promise<CompanyStats> {
  const { data } = await api.get('/companies/stats')
  return data
}

export async function fetchLeads(params: Record<string, string | number | undefined> = {}): Promise<PaginatedResponse<Lead>> {
  const { data } = await api.get('/leads', { params })
  return data
}

export async function updateLead(id: number, updates: Partial<Lead>): Promise<Lead> {
  const { data } = await api.patch(`/leads/${id}`, updates)
  return data
}

export async function triggerZefixIngestion(): Promise<{ message: string; job_id: string }> {
  const { data } = await api.post('/ingestion/zefix')
  return data
}

export async function fetchIngestionJobs(): Promise<IngestionJob[]> {
  const { data } = await api.get('/ingestion/jobs')
  return data
}

export async function searchCompanies(q: string, params: Record<string, string | number> = {}): Promise<PaginatedResponse<Company>> {
  const { data } = await api.get('/search', { params: { q, ...params } })
  return data
}
