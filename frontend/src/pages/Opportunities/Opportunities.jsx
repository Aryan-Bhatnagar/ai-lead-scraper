import { useEffect, useState } from 'react'
import { RefreshCcw, Search, Filter, List, BarChart3, PieChart, TrendingUp } from 'lucide-react'
import toast from 'react-hot-toast'
import PageHeader from '../../components/layout/PageHeader'
import StatCard from '../../components/reusable/StatCard'
import SearchBar from '../../components/reusable/SearchBar'
import FilterPanel, { FilterSelect } from '../../components/reusable/FilterPanel'
import OpportunityTable from '../../components/repository/OpportunityTable'
import OpportunityDetailsDrawer from '../../components/repository/OpportunityDetailsDrawer'
import EmptyState from '../../components/reusable/EmptyState'
import { useOpportunities } from '../../hooks/useOpportunities'
import { downloadCsv } from '../../utils/exportCsv'
import { mapOpportunityForExport } from '../../services/adapters'

export default function Opportunities() {
  const [selectedOpportunitySummary, setSelectedOpportunitySummary] = useState(null)

  // Search + filters (debounced for the server round-trip)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [providerFilter, setProviderFilter] = useState('All')
  const [categoryFilter, setCategoryFilter] = useState('All')
  const [countryFilter, setCountryFilter] = useState('All')
  const [skillsFilter, setSkillsFilter] = useState('')
  const [minBudget, setMinBudget] = useState(null)
  const [maxBudget, setMaxBudget] = useState(null)
  const [page, setPage] = useState(1)
  const [sortBy, setSortBy] = useState('posted_time')
  const [sortDesc, setSortDesc] = useState(true)

  const PAGE_SIZE = 10

  useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput), 350)
    return () => clearTimeout(t)
  }, [searchInput])

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1)
  }, [search, providerFilter, categoryFilter, countryFilter, skillsFilter, minBudget, maxBudget])

  const isSearching = !!search

  const { opportunities, total, loading, error, refetch } = useOpportunities({
    search,
    provider: providerFilter === 'All' ? null : providerFilter,
    category: categoryFilter === 'All' ? null : categoryFilter,
    skills: skillsFilter,
    minBudget,
    maxBudget,
    sortBy,
    sortDesc,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  })

  // Stats from the statistics endpoint
  const [stats, setStats] = useState({ total: 0, providers: {}, categories: {}, countries: {} })
  const loadStats = () => {
    fetch(`/api/opportunities/statistics`)
      .then(res => res.json())
      .then((s) => {
        setStats({
          total: s.total_opportunities ?? 0,
          providers: s.providers || {},
          categories: s.categories || {},
          countries: s.countries || {}
        })
      })
      .catch(() => {})
  }
  useEffect(loadStats, [total])

  // Non-search mode: client-side filter/sort/paginate over the unpaginated list
  const { opportunities: clientOpportunities } = useOpportunities({ enabled: !isSearching })
  const processedOpportunities = useMemo(() => {
    if (isSearching) return opportunities
    let rows = [...clientOpportunities]
    if (providerFilter !== 'All') rows = rows.filter((o) => o.provider === providerFilter)
    if (categoryFilter !== 'All') rows = rows.filter((o) => o.category === categoryFilter)
    if (countryFilter !== 'All') rows = rows.filter((o) => o.client_country === countryFilter)
    if (skillsFilter) {
      const skillsLower = skillsFilter.toLowerCase().split(',').map(s => s.trim())
      rows = rows.filter((o) =>
        skillsLower.some(skill =>
          o.skills.some(s => s.toLowerCase().includes(skill))
        )
      )
    }
    if (minBudget != null) rows = rows.filter((o) => o.budget_max !== null && o.budget_max >= minBudget)
    if (maxBudget != null) rows = rows.filter((o) => o.budget_min !== null && o.budget_min <= maxBudget)
    rows.sort((a, b) => {
      const get = (k) => {
        if (k === 'posted_time') return new Date(a.posted_time || 0)
        if (k === 'title') return a.project_title.toLowerCase()
        if (k === 'provider') return a.provider
        if (k === 'category') return a.category
        if (k === 'country') return b.client_country
        if (k === 'budget') return a.budget_max || 0
        return a[k] || 0
      }
      const getB = (k) => {
        if (k === 'posted_time') return new Date(b.posted_time || 0)
        if (k === 'title') return b.project_title.toLowerCase()
        if (k === 'provider') return b.provider
        if (k === 'category') return b.category
        if (k === 'country') return b.client_country
        if (k === 'budget') return b.budget_max || 0
        return b[k] || 0
      }
      const av = get(sortBy)
      const bv = getB(sortBy)
      if (av == null) return 1
      if (bv == null) return -1
      if (typeof av === 'string') return sortDesc ? bv.localeCompare(av) : av.localeCompare(bv)
      return sortDesc ? bv - av : av - bv
    })
    return rows
  }, [isSearching, opportunities, clientOpportunities, providerFilter, categoryFilter, countryFilter, skillsFilter, minBudget, maxBudget, sortBy, sortDesc])

  const totalRows = isSearching ? total : processedOpportunities.length
  const pageOpportunities = isSearching ? opportunities : processedOpportunities.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  // Drawer
  const openOpportunity = (opportunity) => setSelectedOpportunitySummary(opportunity)

  // Filter options derived from the loaded set
  const filterPool = isSearching ? opportunities : clientOpportunities
  const providers = useMemo(
    () => [...new Set(filterPool.map((o) => o.provider).filter(Boolean))].sort(),
    [filterPool]
  )
  const categories = useMemo(
    () => [...new Set(filterPool.map((o) => o.category).filter(Boolean))].sort(),
    [filterPool]
  )
  const countries = useMemo(
    () => [...new Set(filterPool.map((o) => o.client_country).filter(Boolean))].sort(),
    [filterPool]
  )

  const activeFilterCount = [
    providerFilter !== 'All',
    categoryFilter !== 'All',
    countryFilter !== 'All',
    !!skillsFilter,
    minBudget != null,
    maxBudget != null,
  ].filter(Boolean).length

  const resetFilters = () => {
    setProviderFilter('All')
    setCategoryFilter('All')
    setCountryFilter('All')
    setSkillsFilter('')
    setMinBudget(null)
    setMaxBudget(null)
    setSearchInput('')
  }

  const handleRefresh = () => {
    refetch()
    loadStats()
  }

  const statCards = [
    { title: 'Total Opportunities', value: stats.total, icon: List, color: 'primary' },
    { title: 'Providers', value: Object.keys(stats.providers).length, icon: Filter, color: 'success' },
    { title: 'Categories', value: Object.keys(stats.categories).length, icon: BarChart3, color: 'warning' },
    { title: 'Countries', value: Object.keys(stats.countries).length, icon: TrendingUp, color: 'danger' },
  ]

  if (error && !loading && pageOpportunities.length === 0) {
    return (
      <div>
        <PageHeader title="Opportunity Discovery" subtitle="Discover freelance opportunities from Upwork, Freelancer, Guru, and PeoplePerHour." />
        <div className="glass-card rounded-2xl p-12 text-center animate-fade-up">
          <EmptyState
            icon={Search}
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
        title="Opportunity Discovery"
        subtitle="Discover freelance opportunities from Upwork, Freelancer, Guru, and PeoplePerHour."
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
            placeholder="Search project title, description, skills…"
            className="w-full lg:max-w-md"
          />
          <p className="text-xs text-slate-500 dark:text-slate-400">
            <span className="font-semibold text-slate-700 dark:text-slate-200">{totalRows}</span> opportunities
            {isSearching && ' (filtered)'}
          </p>
        </div>

        <FilterPanel onReset={resetFilters} activeCount={activeFilterCount}>
          <FilterSelect label="Provider" value={providerFilter} onChange={setProviderFilter} options={providers} allLabel="All Providers" />
          <FilterSelect label="Category" value={categoryFilter} onChange={setCategoryFilter} options={categories} allLabel="All Categories" />
          <FilterSelect label="Country" value={countryFilter} onChange={setCountryFilter} options={countries} allLabel="All Countries" />
          <div className="flex-1 min-w-0">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Skills (comma-separated)</label>
            <input
              type="text"
              value={skillsFilter}
              onChange={(e) => setSkillsFilter(e.target.value)}
              className="block w-full rounded-md border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              placeholder="e.g., Python, React, AWS"
            />
          </div>
          <div className="flex-1 min-w-0">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Min Budget ($)</label>
            <input
              type="number"
              value={minBudget ?? ''}
              onChange={(e) => setMinBudget(e.target.value === '' ? null : parseFloat(e.target.value))}
              className="block w-full rounded-md border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              placeholder="Minimum"
            />
          </div>
          <div className="flex-1 min-w-0">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">Max Budget ($)</label>
            <input
              type="number"
              value={maxBudget ?? ''}
              onChange={(e) => setMaxBudget(e.target.value === '' ? null : parseFloat(e.target.value))}
              className="block w-full rounded-md border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              placeholder="Maximum"
            />
          </div>
        </FilterPanel>
      </div>

      {/* Table */}
      {!loading && pageOpportunities.length === 0 ? (
        <div className="glass-card rounded-2xl animate-fade-up">
          <EmptyState
            icon={List}
            title="No opportunities match your filters"
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
        <OpportunityTable
          opportunities={pageOpportunities}
          loading={loading}
          onView={openOpportunity}
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
            downloadCsv(rows.map(mapOpportunityForExport), 'opportunities-export.csv')
            toast.success(`Exported ${rows.length} opportunity${rows.length === 1 ? '' : 's'} to CSV`)
          }}
        />
      )}

      <OpportunityDetailsDrawer opportunity={selectedOpportunitySummary} onClose={() => setSelectedOpportunitySummary(null)} />
    </div>
  )
}