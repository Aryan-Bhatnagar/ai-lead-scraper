import { useMemo } from 'react'
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
        }
      : null

    // Lead sources bar list
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

    // Score histogram from quality buckets (server buckets)
    const scoreDistribution = [
      { range: 'Excellent', count: quality.excellent ?? 0, key: 'excellent' },
      { range: 'Good', count: quality.good ?? 0, key: 'good' },
      { range: 'Average', count: quality.average ?? 0, key: 'average' },
      { range: 'Poor', count: quality.poor ?? 0, key: 'poor' },
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
      { tier: 'poor', label: 'Poor', count: num(quality.poor ?? 0) },
    ]

    // Provider performance
    const providerPerformance = providers.map((p) => ({
      name: p.provider_name || 'Unknown',
      leads: num(p.total_leads ?? 0),
      successRate: Math.round(num(p.success_rate ?? 0) * 100),
      duplicates: Math.round(num(p.duplicate_percentage ?? 0) * 100),
    }))

    // Activity feed: derive from insights + recent stats where possible
    const activity = []
    if (insights.most_contacted_leads?.length) {
      const top = insights.most_contacted_leads[0]
      activity.push({
        id: 'contacted',
        type: 'lifecycle',
        text: `${top.company_name} has ${top.contact_attempts} outreach attempts`,
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
