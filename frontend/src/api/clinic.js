import api from './axios'

export const clinicApi = {
  settings: () => api.get('/clinic/settings/'),
  services: () => api.get('/clinic/services/'),
  patients: (q = '') => api.get('/clinic/patients/', { params: { q } }),
  setPatientTdeeVisibility: (userId, show_tdee_calculator) =>
    api.patch(`/clinic/patients/${userId}/tdee-visibility/`, { show_tdee_calculator }),
  setPatientEnergyTargets: (userId, payload) =>
    api.patch(`/clinic/patients/${userId}/energy-targets/`, payload),
  invoices: (params = {}) => api.get('/clinic/invoices/', { params }),
  invoice: (id) => api.get(`/clinic/invoices/${id}/`),
  createInvoice: (payload) => api.post('/clinic/invoices/', payload),
  payInvoice: (id, payload) => api.post(`/clinic/invoices/${id}/pay/`, payload),
  discountInvoice: (id, payload) => api.post(`/clinic/invoices/${id}/discount/`, payload),
  cancelRefund: (id, payload) => api.post(`/clinic/invoices/${id}/cancel-refund/`, payload),
  revenueReport: (params = {}) => api.get('/clinic/reports/revenue/', { params }),
}

export const nutritionPlansApi = {
  list: (params = {}) => api.get('/nutrition-plans/', { params }),
  get: (id) => api.get(`/nutrition-plans/${id}/`),
  create: (payload) => api.post('/nutrition-plans/', payload),
  approve: (id) => api.post(`/nutrition-plans/${id}/approve/`),
  revise: (id, payload = {}) => api.post(`/nutrition-plans/${id}/revise/`, payload),
  archive: (id) => api.post(`/nutrition-plans/${id}/archive/`),
  mine: () => api.get('/nutrition-plans/mine/'),
  energyPreview: (payload) => api.post('/nutrition-plans/energy-preview/', payload),
  macroPreview: (payload) => api.post('/nutrition-plans/macro-preview/', payload),
}

export function formatIqd(value) {
  const n = Number(value || 0)
  return `${Math.round(n).toLocaleString('en-IQ')} د.ع`
}
