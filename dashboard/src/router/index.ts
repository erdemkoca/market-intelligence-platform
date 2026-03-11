import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('../views/DashboardView.vue'),
    },
    {
      path: '/companies',
      name: 'companies',
      component: () => import('../views/CompaniesView.vue'),
    },
    {
      path: '/companies/:id',
      name: 'company-detail',
      component: () => import('../views/CompanyDetailView.vue'),
    },
    {
      path: '/leads',
      name: 'leads',
      component: () => import('../views/LeadsView.vue'),
    },
  ],
})

export default router
