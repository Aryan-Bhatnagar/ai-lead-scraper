import api from './api'

/**
 * Campaign service — wraps the backend /api/campaigns endpoints.
 *
 * Contract (per Phase 23 spec):
 *   POST /api/campaigns/start
 *   GET  /api/campaigns
 *   GET  /api/campaigns/<id>
 *   GET  /api/campaigns/<id>/progress
 *   POST /api/campaigns/<id>/pause
 *   POST /api/campaigns/<id>/resume
 *   POST /api/campaigns/<id>/cancel
 *
 * Responses are normalized defensively: backend field names may be
 * snake_case or camelCase, and list payloads may be a bare array or
 * wrapped in { campaigns }. No mock data is ever fabricated here.
 */

const pick = (obj, ...keys) => {
  for (const k of keys) {
    if (obj && obj[k] !== undefined && obj[k] !== null) return obj[k]
  }
  return undefined
}

function toIso(value) {
  if (!value) return null
  try {
    const d = new Date(value)
    return Number.isNaN(d.getTime()) ? null : d.toISOString()
  } catch {
    return null
  }
}

export function normalizeCampaign(raw) {
  if (!raw || typeof raw !== 'object') return null
  const progressRaw = raw.progress
  const progress =
    typeof progressRaw === 'number'
      ? { percent: progressRaw }
      : progressRaw && typeof progressRaw === 'object'
        ? normalizeProgress(progressRaw)
        : null

  const status = String(pick(raw, 'status', 'state') || 'unknown').toLowerCase()

  return {
    id: pick(raw, 'id', 'campaign_id', 'campaignId'),
    name: pick(raw, 'name', 'title') || `Campaign #${pick(raw, 'id', 'campaign_id', 'campaignId')}`,
    status,
    industries: pick(raw, 'industries') || [],
    cities: pick(raw, 'cities') || [],
    countries: pick(raw, 'countries') || [],
    providers: pick(raw, 'providers') || [],
    maxResults: pick(raw, 'max_results', 'maxResults') ?? null,
    retryCount: pick(raw, 'retry_count', 'retryCount') ?? null,

    queriesCompleted: pick(raw, 'queries_completed', 'queriesCompleted') ?? progress?.queriesCompleted ?? 0,
    queriesTotal: pick(raw, 'queries_total', 'queriesTotal') ?? progress?.queriesTotal ?? 0,
    leadsDiscovered: pick(raw, 'leads_discovered', 'leadsDiscovered', 'leads_found', 'leadsFound') ?? 0,
    averageScore: pick(raw, 'average_score', 'averageScore', 'avg_score', 'avgScore') ?? null,
    progressPercent: pick(raw, 'progress_percent', 'progressPercent') ?? progress?.percent ?? null,

    startedAt: toIso(pick(raw, 'started_at', 'startedAt', 'created_at', 'createdAt')),
    completedAt: toIso(pick(raw, 'completed_at', 'completedAt', 'finished_at', 'finishedAt')),
    progress,
  }
}

export function normalizeProgress(raw) {
  if (!raw || typeof raw !== 'object') return null
  const completed = pick(raw, 'queries_completed', 'queriesCompleted', 'completed_queries') ?? 0
  let total = pick(raw, 'queries_total', 'queriesTotal', 'total_queries') ?? 0
  let percent = pick(raw, 'percent', 'progress_percent', 'progressPercent')
  if (percent == null && total > 0) percent = Math.round((completed / total) * 100)
  if ((total === 0 || total == null) && percent != null && percent > 0) {
    total = Math.round((completed * 100) / percent)
  }
  return {
    status: String(pick(raw, 'status', 'state') || '').toLowerCase() || null,
    currentQuery: pick(raw, 'current_query', 'currentQuery', 'query') || null,
    currentProvider: pick(raw, 'current_provider', 'currentProvider', 'provider') || null,
    currentIndustry: pick(raw, 'current_industry', 'currentIndustry', 'industry') || null,
    currentCity: pick(raw, 'current_city', 'currentCity', 'city') || null,
    currentCountry: pick(raw, 'current_country', 'currentCountry', 'country') || null,
    queriesCompleted: completed,
    queriesTotal: total ?? 0,
    percent: percent ?? 0,
    leadsDiscovered: pick(raw, 'leads_discovered', 'leadsDiscovered', 'leads_found', 'leadsFound') ?? 0,
    averageScore: pick(raw, 'average_score', 'averageScore', 'avg_score', 'avgScore') ?? null,
    elapsedSeconds: pick(raw, 'elapsed_seconds', 'elapsedSeconds', 'elapsed') ?? null,
    estimatedRemainingSeconds: pick(raw, 'estimated_remaining_seconds', 'estimatedRemainingSeconds', 'eta_seconds', 'etaSeconds', 'eta') ?? null,
  }
}

export async function listCampaigns() {
  const res = await api.get('/api/campaigns')
  const data = res.data
  const list = Array.isArray(data) ? data : data?.campaigns || data?.items || data?.results || []
  return list.map(normalizeCampaign).filter(Boolean)
}

export async function startCampaign(payload) {
  const res = await api.post('/api/campaigns/start', payload)
  return normalizeCampaign(res.data?.campaign || res.data)
}

export async function getCampaign(id) {
  const res = await api.get(`/api/campaigns/${id}`)
  return normalizeCampaign(res.data?.campaign || res.data)
}

export async function getCampaignProgress(id) {
  const res = await api.get(`/api/campaigns/${id}/progress`)
  return normalizeProgress(res.data?.progress || res.data) || {}
}

export async function pauseCampaign(id) {
  const res = await api.post(`/api/campaigns/${id}/pause`)
  return res.data
}

export async function resumeCampaign(id) {
  const res = await api.post(`/api/campaigns/${id}/resume`)
  return res.data
}

export async function cancelCampaign(id) {
  const res = await api.post(`/api/campaigns/${id}/cancel`)
  return res.data
}
