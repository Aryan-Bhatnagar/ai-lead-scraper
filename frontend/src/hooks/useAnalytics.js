import { useMemo, useEffect, useRef } from 'react'
import useQuery, { invalidateCache } from './useQuery'
import {
  getOverview,
  getTrends,
  getProviders,
  getLifecycle,
  getQuality,
  getInsights,
} from '../services/analyticsService'

/**
 * useAnalytics
 * ------------
 * One hook that fans out to all analytics endpoints in parallel,
 * shares the in-flight requests via the useQuery cache, and
 * normalizes the responses for the Dashboard components.
 */
export function useAnalytics() {
  // Invalidate cache synchronously before hooks read it
  const invalidated = useRef(false)
  if (!invalidated.current) {
    invalidateCache('analytics')
    invalidated.current = true
  }

  const overviewQ = useQuery({ queryKey: ['analytics', 'overview'], queryFn: getOverview })
  const trendsQ = useQuery({ queryKey: ['analytics', 'trends'], queryFn: getTrends })
  const providersQ = useQuery({ queryKey: ['analytics', 'providers'], queryFn: getProviders })
  const lifecycleQ = useQuery({ queryKey: ['analytics', 'lifecycle'], queryFn: getLifecycle })
  const qualityQ = useQuery({ queryKey: ['analytics', 'quality'], queryFn: getQuality })
  const insightsQ = useQuery({ queryKey: ['analytics', 'insights'], queryFn: getInsights })

  const loading =
    overviewQ.loading || trendsQ.loading || providersQ.loading || lifecycleQ.loading || qualityQ.loading
  const error =
    overviewQ.error || trendsQ.error || providersQ.error || lifecycleQ.error || qualityQ.error || insightsQ.error

  // Debug: log the raw data from each query
  console.log('[useAnalytics] overviewQ.data:', overviewQ.data)
  console.log('[useAnalytics] trendsQ.data:', trendsQ.data)
  console.log('[useAnalytics] providersQ.data:', providersQ.data)
  console.log('[useAnalytics] lifecycleQ.data:', lifecycleQ.data)
  console.log('[useAnalytics] qualityQ.data:', qualityQ.data)
  console.log('[useAnalytics] insightsQ.data:', insightsQ.data)

  const analytics = useMemo(() => {
    const overview = overviewQ.data
    const trends = trendsQ.data
    // Backend may return a plain array or {providers: [...]} — normalize both.
    const providersRaw = providersQ.data || []
    const providers = Array.isArray(providersRaw) ? providersRaw : providersRaw.providers || []
    const lifecycle = lifecycleQ.data || {}
    const quality = qualityQ.data || {}
    const insights = insightsQ.data || {}

    // KPI cards — every value coerced to a finite number (never [object Object]).
    const num = (v) => {
      const n = Number(v)
      return Number.isFinite(n) ? n : 0
    }
    const kpis = overview
      ? {
          totalLeads: num(overview.total_leads ?? 0),
          aiScoredLeads: num(overview.ai_scored_leads ?? 0),
          averageScore: Math.round(num(overview.average_score ?? 0)),
          highQualityLeads: num(overview.high_quality_leads ?? 0),
          totalCompanies: num(overview.total_companies ?? 0),
        }
      : null

    // Lead sources bar list - ensure we handle objects properly
    const leadSources = overview
      ? Object.entries(overview.lead_sources || {})
          .map(([name, value]) => ({ name, value: num(value) }))
          .sort((a, b) => b.value - a.value)
      : []

    // Discovery timeline (daily series)
    const discoveryTimeline = (trends?.daily || []).map((p) => ({
      date: new Date(p.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      leads: p.count,
    }))
    console.log('[useAnalytics] trends raw:', trends?.daily?.length, 'entries')
    console.log('[useAnalytics] discoveryTimeline:', discoveryTimeline.length, 'entries, non-zero:', discoveryTimeline.filter(d => d.leads > 0).length)

    // Score histogram from quality buckets (server buckets)
    const scoreDistribution = [
      { range: 'Excellent', count: quality.excellent ?? 0, key: 'excellent' },
      { range: 'Good', count: quality.good ?? 0, key: 'good' },
      { range: 'Average', count: quality.average ?? 0, key: 'average' },
    ]

    // Lifecycle funnel
    const lifecycleDistribution = Object.entries(lifecycle)
      .map(([state, count]) => ({ state, count }))
      .sort((a, b) => b.count - a.count)

    // Quality pie
    const qualityBreakdown = [
      { tier: 'excellent', label: 'Excellent', count: num(quality.excellent ?? 0) },
      { tier: 'good', label: 'Good', count: num(quality.good ?? 0) },
      { tier: 'average', label: 'Average', count: num(quality.average ?? 0) },
    ]

    // Provider performance
    const providerPerformance = providers.map((p) => ({
      name: p.provider_name || 'Unknown',
      leads: num(p.total_leads ?? 0),
      successRate: Math.round(num(p.success_rate ?? 0)), // already a percentage from backend
      duplicates: Math.round(num(p.duplicate_percentage ?? 0)), // already a percentage from backend
    }))

    // Activity feed: derive from insights + recent stats where possible
    const activity = []
    if (insights.most_contacted_leads?.length) {
      const top = insights.most_contacted_leads[0]
      const companyName = top.company_name
      activity.push({
        id: 'contacted',
        type: 'lifecycle',
        text: `${companyName ? `${companyName} has` : 'A lead has'} ${top.contact_attempts} outreach attempts`,
        time: 'recent',
      })
    }
    if (insights.most_valuable_sources?.length) {
      const s = insights.most_valuable_sources[0]
      activity.push({
        id: 'source',
        type: 'discovery',
        text: `Top performing source: ${s.source} (avg score ${s.average_score})`,
        time: 'insight',
      })
    }
    if (overview) {
      activity.push({
        id: 'total',
        type: 'stats',
        text: `${overview.total_leads} leads across ${Object.keys(overview.lead_sources || {}).length} sources`,
        time: 'now',
      })
      const countries = overview.countries ? Object.keys(overview.countries).length : 0
      activity.push({
        id: 'countries',
        type: 'stats',
        text: `Presence in ${countries} markets`,
        time: 'now',
      })
    }

    return {
      kpis,
      leadSources,
      discoveryTimeline,
      scoreDistribution,
      lifecycleDistribution,
      qualityBreakdown,
      providerPerformance,
      activity,
      raw: { overview, trends, providers, lifecycle, quality, insights },
    }
  }, [overviewQ.data, trendsQ.data, providersQ.data, lifecycleQ.data, qualityQ.data, insightsQ.data])

  return {
    analytics,
    loading,
    error,
    refetch: () => {
      invalidateCache('analytics')
      return Promise.all([
        overviewQ.refetch(),
        trendsQ.refetch(),
        providersQ.refetch(),
        lifecycleQ.refetch(),
        qualityQ.refetch(),
        insightsQ.refetch(),
      ])
    },
  }
}
