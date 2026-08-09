import api from './api'

/**
 * Leads service — wraps the backend /api/leads endpoints.
 * Returns response.data directly so hooks stay lean.
 */

export function getLeads(params = {}) {
  return api
    .get('/api/leads', { params })
    .then((res) => res.data)
}

export function searchLeads({ filters = {}, sortBy = 'id', sortDesc = false, limit = 20, offset = 0 } = {}) {
  // If filters has 'search', pass it as the global search parameter
  // Otherwise pass individual field filters
  const params = { ...filters }
  if (filters.search) {
    params.search = filters.search
    delete params.company
  }
  params.sort_by = sortBy
  params.sort_desc = sortDesc
  params.limit = limit
  params.offset = offset

  return api
    .get('/api/leads/search', { params })
    .then((res) => res.data) // { leads, count, total, limit, offset }
}

export function getLead(id) {
  return api.get(`/api/leads/${id}`).then((res) => res.data)
}

export function deleteLead(id) {
  return api.delete(`/api/leads/${id}`).then((res) => res.data)
}

export function updateLead(id, payload) {
  return api.put(`/api/leads/${id}`, payload).then((res) => res.data)
}

export function updateLeadLifecycle(id, leadStatus) {
  return api
    .patch(`/api/leads/${id}/lifecycle`, { lead_status: leadStatus })
    .then((res) => res.data)
}

export function getLeadStatistics() {
  return api.get('/api/leads/statistics').then((res) => res.data)
}

export function getCities() {
  return api.get('/api/leads/cities').then((res) => res.data) // { cities: [...], count: N }
}

export function bulkDeleteLeads(leadIds) {
  return api.delete('/api/leads/bulk', { data: { lead_ids: leadIds } }).then((res) => res.data)
}
