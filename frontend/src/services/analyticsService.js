import api from './api'

/**
 * Analytics service — wraps the backend /api/analytics endpoints.
 */

export function getOverview() {
  return api.get('/api/analytics/overview').then((res) => res.data)
}

export function getTrends() {
  return api.get('/api/analytics/trends').then((res) => res.data)
}

export function getProviders() {
  return api.get('/api/analytics/providers').then((res) => res.data) // array
}

export function getLifecycle() {
  return api.get('/api/analytics/lifecycle').then((res) => res.data) // dict: {STATUS: count}
}

export function getQuality() {
  return api
    .get('/api/analytics/quality')
    .then((res) => res.data) // {excellent, good, average, poor, unknown}
}

export function getInsights() {
  return api.get('/api/analytics/insights').then((res) => res.data)
}
