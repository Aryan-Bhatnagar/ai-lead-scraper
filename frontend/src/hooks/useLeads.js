import { useCallback } from 'react'
import useQuery, { invalidateCache } from './useQuery'
import { searchLeads, getLeads, deleteLead, updateLeadLifecycle } from '../services/leadsService'
import { mapApiLead } from '../services/adapters'

/**
 * useLeads
 * --------
 * Server-driven lead repository hook.
 *
 * @param {Object} options
 * @param {string} options.search        - free-text (company/website/email/city…)
 * @param {string} options.source        - source filter (substring of source_url)
 * @param {string} options.lifecycle     - lead_status filter
 * @param {string} options.country       - country exact match
 * @param {string} options.quality       - data_quality exact match
 * @param {number|null} options.scoreMin
 * @param {number|null} options.scoreMax
 * @param {string} options.sortBy        - backend sort field (quality_score, company_name…)
 * @param {boolean} options.sortDesc
 * @param {number} options.limit
 * @param {number} options.offset
 */
export function useLeads({
  search = '',
  source = null,
  lifecycle = null,
  country = null,
  quality = null,
  scoreMin = null,
  scoreMax = null,
  sortBy = 'quality_score',
  sortDesc = true,
  limit = 8,
  offset = 0,
} = {}) {
  const useFast = !search // join fast list endpoint when not searching

  const query = useQuery({
    queryKey: useFast
      ? ['leads', 'list', { source, lifecycle, quality }]
      : ['leads', 'search', { search, source, lifecycle, country, quality, scoreMin, scoreMax, sortBy, sortDesc, limit, offset }],
    queryFn: async () => {
      if (useFast) {
        const params = {}
        if (source && source !== 'All') params.source = source
        if (lifecycle && lifecycle !== 'All') params.lead_status = lifecycle
        if (quality && quality !== 'All') params.data_quality = quality.toUpperCase()
        const data = await getLeads(params)
        return { leads: (data.leads || []).map(mapApiLead), total: data.count ?? data.leads?.length ?? 0 }
      }
      const filters = {}
      if (search) filters.company = search
      if (source && source !== 'All') filters.source = source
      if (lifecycle && lifecycle !== 'All') filters.lead_status = lifecycle
      if (country && country !== 'All') filters.country = country
      if (quality && quality !== 'All') filters.quality_tier = quality.toUpperCase()
      if (scoreMin != null) filters.min_score = scoreMin
      if (scoreMax != null) filters.max_score = scoreMax
      const data = await searchLeads({ filters, sortBy, sortDesc, limit, offset })
      return {
        leads: (data.leads || []).map(mapApiLead),
        total: data.total ?? data.leads?.length ?? 0,
        limit: data.limit,
        offset: data.offset,
      }
    },
    ttl: 30_000,
  })

  const refresh = useCallback(() => {
    invalidateCache('leads')
    invalidateCache('analytics')
    return query.refetch()
  }, [query])

  return {
    leads: query.data?.leads ?? [],
    total: query.data?.total ?? 0,
    loading: query.loading,
    error: query.error,
    refetch: refresh,
  }
}

/** All-leads hook used by stat badges and CSV export. */
export function useAllLeads({ enabled = true } = {}) {
  const query = useQuery({
    queryKey: ['leads', 'all'],
    queryFn: async () => {
      const data = await getLeads()
      return (data.leads || []).map(mapApiLead)
    },
    ttl: 30_000,
    enabled,
  })
  return {
    leads: query.data ?? [],
    loading: query.loading,
    error: query.error,
    refetch: query.refetch,
  }
}
