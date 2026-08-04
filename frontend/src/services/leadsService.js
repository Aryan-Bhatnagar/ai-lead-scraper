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
  return api
    .get('/api/leads/search', {
      params: {
        ...filters,
        sort_by: sortBy,
        sort_desc: sortDesc,
        limit,
        offset,
      },
    })
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
