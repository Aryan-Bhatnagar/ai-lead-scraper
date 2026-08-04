import api from './api'

/**
 * Campaign service — wraps the backend /api/campaigns endpoints.
 * Returns response.data directly so hooks stay lean.
 */

export function startCampaign(payload) {
  // payload: { industries, cities, countries, providers, max_results, retry_count }
  return api.post('/api/campaigns/start', payload).then((res) => res.data)
}

export function getCampaigns(params = {}) {
  return api.get('/api/campaigns', { params }).then((res) => res.data)
}

export function getCampaign(id) {
  return api.get(`/api/campaigns/${id}`).then((res) => res.data)
}

export function getCampaignProgress(id) {
  return api.get(`/api/campaigns/${id}/progress`).then((res) => res.data)
}

export function pauseCampaign(id) {
  return api.post(`/api/campaigns/${id}/pause`).then((res) => res.data)
}

export function resumeCampaign(id) {
  return api.post(`/api/campaigns/${id}/resume`).then((res) => res.data)
}

export function cancelCampaign(id) {
  return api.post(`/api/campaigns/${id}/cancel`).then((res) => res.data)
}
