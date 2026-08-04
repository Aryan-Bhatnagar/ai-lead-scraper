import { useEffect, useMemo, useState } from 'react'
import { Users, Trophy, Gauge, Star, RefreshCcw } from 'lucide-react'
import toast from 'react-hot-toast'
import PageHeader from '../../components/layout/PageHeader'
import StatCard from '../../components/reusable/StatCard'
import SearchBar from '../../components/reusable/SearchBar'
import FilterPanel, { FilterSelect, ScoreRangeFilter } from '../../components/reusable/FilterPanel'
import LeadTable from '../../components/repository/LeadTable'
import LeadDetailsDrawer from '../../components/repository/LeadDetailsDrawer'
import EmptyState from '../../components/reusable/EmptyState'
import { Database } from 'lucide-react'
import { useLeads, useAllLeads } from '../../hooks/useLeads'
import { getLeadStatistics } from '../../services/leadsService'
import { downloadCsv } from '../../utils/exportCsv'
import { mapLeadForExport } from '../../services/adapters'

export default function Leads() {
  const [selectedLeadSummary, setSelectedLeadSummary] = useState(null)

  // Search + filters (debounced for the server round-trip)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [sourceFilter, setSourceFilter] = useState('All')
  const [lifecycleFilter, setLifecycleFilter] = useState('All')
  const [countryFilter, setCountryFilter] = useState('All')
  const [qualityFilter, setQualityFilter] = useState('All')
  const [scoreMin, setScoreMin] = useState(null)
  const [scoreMax, setScoreMax] = useState(null)
  const [page, setPage] = useState(1)
  const [sortBy, setSortBy] = useState('quality_score')
  const [sortDesc, setSortDesc] = useState(true)

  const PAGE_SIZE = 8

  useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput), 350)
    return () => clearTimeout(t)
  }, [searchInput])

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1)
  }, [search, sourceFilter, lifecycleFilter, countryFilter, qualityFilter, scoreMin, scoreMax])

  const isSearching = !!search

  const { leads, total, loading, error, refetch } = useLeads({
    search,
    source: sourceFilter === 'All' ? null : sourceFilter,
    lifecycle: lifecycleFilter === 'All' ? null : lifecycleFilter,
    country: countryFilter === 'All' ? null : countryFilter,
    quality: qualityFilter === 'All' ? null : qualityFilter,
    scoreMin,
    scoreMax,
    sortBy,
    sortDesc,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  })

  // Stats from the statistics endpoint
  const [stats, setStats] = useState({ total: 0, scored: 0, avg: 0, high: 0 })
  const loadStats = () => {
    getLeadStatistics()
      .then((s) => {
        const distribution = s.lifecycle_distribution || {}
        const highQuality = (s.quality_distribution?.excellent || 0) + (s.quality_distribution?.good || 0)
        setStats({
          total: s.total_leads ?? 0,
          scored: Object.values(distribution).reduce((a, b) => a + b, 0),
          avg: Math.round(s.average_score ?? 0),
          high: highQuality,
        })
      })
      .catch(() => {})
  }
  useEffect(loadStats, [total])

  // Non-search mode: client-side filter/sort/paginate over the unpaginated list
  const { leads: clientLeads } = useAllLeads({ enabled: !isSearching })
  const processedLeads = useMemo(() => {
    if (isSearching) return leads
    let rows = [...clientLeads]
    if (sourceFilter !== 'All') rows = rows.filter((l) => l.source.includes(sourceFilter))
    if (lifecycleFilter !== 'All') rows = rows.filter((l) => l.lifecycle === lifecycleFilter)
    if (countryFilter !== 'All') rows = rows.filter((l) => l.country === countryFilter)
    if (qualityFilter !== 'All') rows = rows.filter((l) => l.quality_tier === qualityFilter)
    if (scoreMin != null) rows = rows.filter((l) => l.score >= scoreMin)
    if (scoreMax != null) rows = rows.filter((l) => l.score <= scoreMax)
    rows.sort((a, b) => {
      const get = (k) => (k === 'quality_score' ? a.score : k === 'company_name' ? a.company_name.toLowerCase() : a[k])
      const getB = (k) => (k === 'quality_score' ? b.score : k === 'company_name' ? b.company_name.toLowerCase() : b[k])
      const av = get(sortBy)
      const bv = getB(sortBy)
      if (av == null) return 1
      if (bv == null) return -1
      if (typeof av === 'string') return sortDesc ? bv.localeCompare(av) : av.localeCompare(bv)
      return sortDesc ? bv - av : av - bv
    })
    return rows
  }, [isSearching, leads, clientLeads, sourceFilter, lifecycleFilter, countryFilter, qualityFilter, scoreMin, scoreMax, sortBy, sortDesc])

  const totalRows = isSearching ? total : processedLeads.length
  const pageLeads = isSearching ? leads : processedLeads.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  // Drawer
  const openLead = (lead) => setSelectedLeadSummary(lead)

  // Filter options derived from the loaded set
  const filterPool = isSearching ? leads : clientLeads
  const countries = useMemo(
    () => [...new Set(filterPool.map((l) => l.country).filter(Boolean))].sort(),
    [filterPool]
  )
  const sources = useMemo(
    () => [...new Set(filterPool.map((l) => l.source).filter(Boolean))].sort(),
    [filterPool]
  )
  const lifecycles = useMemo(
    () => [...new Set(filterPool.map((l) => l.lifecycle).filter(Boolean))].sort(),
    [filterPool]
  )
  const qualities = ['high', 'medium', 'low', 'unknown']

  const activeFilterCount = [
    sourceFilter !== 'All',
    lifecycleFilter !== 'All',
    countryFilter !== 'All',
    qualityFilter !== 'All',
    scoreMin != null,
    scoreMax != null,
  ].filter(Boolean).length

  const resetFilters = () => {
    setSourceFilter('All')
    setLifecycleFilter('All')
    setCountryFilter('All')
    setQualityFilter('All')
    setScoreMin(null)
    setScoreMax(null)
    setSearchInput('')
  }

  const handleRefresh = () => {
    refetch()
    loadStats()
  }

  const statCards = [
    { title: 'Total Leads', value: stats.total, icon: Users, color: 'primary' },
    { title: 'Scored Leads', value: stats.scored, icon: Trophy, color: 'success' },
    { title: 'Average Score', value: stats.avg, icon: Gauge, color: 'warning' },
    { title: 'High Quality', value: stats.high, icon: Star, color: 'danger' },
  ]

  if (error && !loading && pageLeads.length === 0) {
    return (
      <div>
        <PageHeader title="Lead Repository" subtitle="Persisted, scored and deduplicated leads across every discovery source." />
        <div className="glass-card rounded-2xl p-12 text-center animate-fade-up">
          <EmptyState
            icon={Database}
            title="Unable to reach the backend"
            description={String(error) || 'Check that the API server is running, then retry.'}
          >
            <button
              onClick={handleRefresh}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              <RefreshCcw className="w-4 h-4" />
              Retry
            </button>
          </EmptyState>
        </div>
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Lead Repository"
        subtitle="Persisted, scored and deduplicated leads across every discovery source."
      >
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors disabled:opacity-50"
        >
          <RefreshCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </PageHeader>

      {/* Summary stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {statCards.map((card, i) => (
          <div key={card.title} className={`animate-fade-up stagger-${i + 1}`}>
            <StatCard {...card} />
          </div>
        ))}
      </div>

      {/* Controls */}
      <div className="glass-card rounded-2xl p-4 mb-6 space-y-4 animate-fade-up">
        <div className="flex flex-col lg:flex-row lg:items-center gap-4 justify-between">
          <SearchBar
            value={searchInput}
            onChange={setSearchInput}
            placeholder="Search company, website, contact, location…"
            className="w-full lg:max-w-md"
          />
          <p className="text-xs text-slate-500 dark:text-slate-400">
            <span className="font-semibold text-slate-700 dark:text-slate-200">{totalRows}</span> leads
            {isSearching && ' (filtered)'}
          </p>
        </div>

        <FilterPanel onReset={resetFilters} activeCount={activeFilterCount}>
          <FilterSelect label="Source" value={sourceFilter} onChange={setSourceFilter} options={sources} allLabel="All Sources" />
          <FilterSelect label="Lifecycle" value={lifecycleFilter} onChange={setLifecycleFilter} options={lifecycles} allLabel="All Stages" />
          <FilterSelect label="Country" value={countryFilter} onChange={setCountryFilter} options={countries} allLabel="All Countries" />
          <FilterSelect label="Quality" value={qualityFilter} onChange={setQualityFilter} options={qualities} allLabel="All Quality" />
          <ScoreRangeFilter min={scoreMin} max={scoreMax} onMinChange={setScoreMin} onMaxChange={setScoreMax} />
        </FilterPanel>
      </div>

      {/* Table */}
      {!loading && pageLeads.length === 0 ? (
        <div className="glass-card rounded-2xl animate-fade-up">
          <EmptyState
            icon={Database}
            title="No leads match your filters"
            description="Try broadening the search or clearing some filters to see more results."
          >
            <button
              onClick={resetFilters}
              className="px-4 py-2 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              Clear all filters
            </button>
          </EmptyState>
        </div>
      ) : (
        <LeadTable
          leads={pageLeads}
          loading={loading}
          onView={openLead}
          page={page}
          totalPages={Math.max(1, Math.ceil(totalRows / PAGE_SIZE))}
          totalItems={totalRows}
          onPageChange={setPage}
          sortBy={sortBy}
          sortDesc={sortDesc}
          onSort={(key) => {
            if (sortBy === key) setSortDesc(!sortDesc)
            else {
              setSortBy(key)
              setSortDesc(true)
            }
          }}
          onExport={(rows) => {
            downloadCsv(rows.map(mapLeadForExport), 'leads-export.csv')
            toast.success(`Exported ${rows.length} lead${rows.length === 1 ? '' : 's'} to CSV`)
          }}
        />
      )}

      <LeadDetailsDrawer lead={selectedLeadSummary} onClose={() => setSelectedLeadSummary(null)} />
    </div>
  )
}
