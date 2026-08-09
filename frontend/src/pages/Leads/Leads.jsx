import { useEffect, useMemo, useState } from 'react'
import { Users, Trophy, Gauge, Star, RefreshCcw } from 'lucide-react'
import toast from 'react-hot-toast'
import PageHeader from '../../components/layout/PageHeader'
import StatCard from '../../components/reusable/StatCard'
import SearchBar from '../../components/reusable/SearchBar'
import FilterPanel, { FilterSelect } from '../../components/reusable/FilterPanel'
import LeadTable from '../../components/repository/LeadTable'
import LeadDetailsDrawer from '../../components/repository/LeadDetailsDrawer'
import EmptyState from '../../components/reusable/EmptyState'
import { Database } from 'lucide-react'
import { useLeads, useAllLeads } from '../../hooks/useLeads'
import { getLeadStatistics, bulkDeleteLeads } from '../../services/leadsService'
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
  const [cityFilter, setCityFilter] = useState('All')
  const [qualityFilter, setQualityFilter] = useState('All')
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
  }, [search, sourceFilter, lifecycleFilter, countryFilter, cityFilter, qualityFilter])

  const isSearching = !!search

  const { leads, total, loading, error, refetch } = useLeads({
    search,
    source: sourceFilter === 'All' ? null : sourceFilter,
    lifecycle: lifecycleFilter === 'All' ? null : lifecycleFilter,
    country: countryFilter === 'All' ? null : countryFilter,
    city: cityFilter === 'All' ? null : cityFilter,
    quality: qualityFilter === 'All' ? null : qualityFilter,
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
        const distribution = s.lifecycle_distribution || []
        // lifecycle_distribution is an array of {status, count} objects
        const totalScored = Array.isArray(distribution)
          ? distribution.reduce((sum, item) => sum + (item.count || 0), 0)
          : Object.values(distribution).reduce((a, b) => a + b, 0)
        // quality_distribution uses data_quality (HIGH/MEDIUM/LOW/UNKNOWN), not quality_tier (excellent/good/average/poor/unknown)
        const qualityDist = s.quality_distribution || []
        const highQuality = qualityDist
          .filter(q => ['HIGH', 'MEDIUM', 'high', 'medium'].includes(q.quality?.toUpperCase()))
          .reduce((sum, q) => sum + (q.count || 0), 0)
        setStats({
          total: s.total_leads ?? 0,
          scored: totalScored,
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
    if (cityFilter !== 'All') rows = rows.filter((l) => l.city === cityFilter)
    if (qualityFilter !== 'All') rows = rows.filter((l) => l.quality_tier === qualityFilter)
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
  }, [isSearching, leads, clientLeads, sourceFilter, lifecycleFilter, countryFilter, cityFilter, qualityFilter, sortBy, sortDesc])

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
  const cities = useMemo(
    () => [...new Set(filterPool.map((l) => l.city).filter(Boolean))].sort(),
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
  const qualities = ['excellent', 'good', 'average', 'unknown']

  const activeFilterCount = [
    sourceFilter !== 'All',
    lifecycleFilter !== 'All',
    countryFilter !== 'All',
    cityFilter !== 'All',
    qualityFilter !== 'All',
  ].filter(Boolean).length

  const resetFilters = () => {
    setSourceFilter('All')
    setLifecycleFilter('All')
    setCountryFilter('All')
    setCityFilter('All')
    setQualityFilter('All')
    setSearchInput('')
  }

  const handleRefresh = () => {
    refetch()
    loadStats()
  }

  const handleBulkDelete = async (leadIds) => {
    try {
      await bulkDeleteLeads(leadIds)
      toast.success(`Deleted ${leadIds.length} lead${leadIds.length === 1 ? '' : 's'}`)
      refetch()
      loadStats()
    } catch (error) {
      console.error('Bulk delete failed:', error)
      toast.error('Failed to delete leads')
      throw error
    }
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
        <div className="glass-card rounded-2xl p-8 sm:p-12 text-center animate-fade-up ring-1 ring-danger-500/10">
          <EmptyState
            icon={Database}
            title="Unable to reach the backend"
            description={String(error) || 'Check that the API server is running, then retry.'}
          >
            <button
              onClick={handleRefresh}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:scale-[0.98] transition-all"
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
          <FilterSelect label="City" value={cityFilter} onChange={setCityFilter} options={cities} allLabel="All Cities" />
          <FilterSelect label="Quality" value={qualityFilter} onChange={setQualityFilter} options={qualities} allLabel="All Quality" />
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
              className="px-4 py-2 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:scale-[0.98] transition-all"
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
          onDelete={handleBulkDelete}
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
