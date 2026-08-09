import api from './api'

/**
 * Analytics service — wraps the backend /api/analytics endpoints.
 */

function cacheBustUrl(url) {
  const separator = url.includes('?') ? '&' : '?'
  return `${url}${separator}_t=${Date.now()}`
}

export function getOverview() {
  return api.get(cacheBustUrl('/api/analytics/overview')).then((res) => res.data)
}

export function getTrends() {
  return api.get(cacheBustUrl('/api/analytics/trends')).then((res) => res.data)
}

export function getProviders() {
  return api.get(cacheBustUrl('/api/analytics/providers')).then((res) => res.data) // array
}

export function getLifecycle() {
  return api.get(cacheBustUrl('/api/analytics/lifecycle')).then((res) => res.data) // dict: {STATUS: count}
}

export function getQuality() {
  return api
    .get(cacheBustUrl('/api/analytics/quality'))
    .then((res) => res.data) // {excellent, good, average, unknown}
}

export function getInsights() {
  return api.get(cacheBustUrl('/api/analytics/insights')).then((res) => res.data)
}
