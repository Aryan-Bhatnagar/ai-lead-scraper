import { useEffect, useState, useMemo } from 'react'
import {
  Send,
  RefreshCcw,
  Play,
  Clock,
  AlertCircle,
  CheckCircle2,
  Mail,
  MessageSquare,
  UserPlus,
  Filter,
  Search,
  X,
  Layers,
  Calendar,
  Sparkles,
  Building2,
  Globe,
  Trash2,
  CheckSquare,
} from 'lucide-react'
import PageHeader from '../../components/layout/PageHeader'
import LoadingSpinner from '../../components/layout/LoadingSpinner'
import api from '../../services/api'
import toast from 'react-hot-toast'

export default function Outreach() {
  const [stats, setStats] = useState(null)
  const [queue, setQueue] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [options, setOptions] = useState({ sources: [], industries: [], quality_tiers: [] })

  // Selection state
  const [selectedIds, setSelectedIds] = useState(new Set())

  // Filters state
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [channelFilter, setChannelFilter] = useState('ALL')
  const [stepFilter, setStepFilter] = useState('ALL')
  const [sourceFilter, setSourceFilter] = useState('ALL')
  const [industryFilter, setIndustryFilter] = useState('ALL')
  const [qualityFilter, setQualityFilter] = useState('ALL')
  const [dateFilter, setDateFilter] = useState('ALL')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    fetchOutreachOptions()
  }, [])

  useEffect(() => {
    fetchOutreachData()
    setSelectedIds(new Set()) // Reset selection when filters change
  }, [statusFilter, channelFilter, stepFilter, sourceFilter, industryFilter, qualityFilter, dateFilter, searchQuery])

  const fetchOutreachOptions = async () => {
    try {
      const resp = await api.get('/api/outreach/options')
      if (resp.data) {
        setOptions({
          sources: resp.data.sources || [],
          industries: resp.data.industries || [],
          quality_tiers: resp.data.quality_tiers || [],
        })
      }
    } catch (err) {
      console.error('Failed to load outreach filter options', err)
    }
  }

  const fetchOutreachData = async () => {
    setLoading(true)
    try {
      // Fetch stats
      const statsResp = await api.get('/api/outreach/stats')
      setStats(statsResp.data)

      // Fetch queue items with all active filters
      const params = {}
      if (statusFilter !== 'ALL') params.outreach_status = statusFilter
      if (channelFilter !== 'ALL') params.outreach_channel = channelFilter
      if (stepFilter !== 'ALL') params.outreach_step = stepFilter
      if (sourceFilter !== 'ALL') params.source = sourceFilter
      if (industryFilter !== 'ALL') params.industry = industryFilter
      if (qualityFilter !== 'ALL') params.quality_tier = qualityFilter
      if (dateFilter !== 'ALL') params.date_preset = dateFilter
      if (searchQuery.trim()) params.search = searchQuery.trim()

      const queueResp = await api.get('/api/outreach', { params })
      setQueue(queueResp.data.outreach || [])
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Failed to load outreach queue'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleToggleSelectAll = () => {
    if (selectedIds.size === queue.length && queue.length > 0) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(queue.map((item) => item.id)))
    }
  }

  const handleToggleSelectRow = (id) => {
    const next = new Set(selectedIds)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
    }
    setSelectedIds(next)
  }

  const handleEnqueueAll = async () => {
    if (!window.confirm('Enqueue all qualified leads with email or phone for outreach?')) return
    setActionLoading(true)
    try {
      const resp = await api.post('/api/outreach/enqueue_all')
      toast.success(`Enqueued ${resp.data.enqueued} leads (${resp.data.skipped} already queued)`)
      fetchOutreachData()
      fetchOutreachOptions()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to enqueue leads')
    } finally {
      setActionLoading(false)
    }
  }

  const handleClearQueue = async () => {
    if (!window.confirm('Clear all enqueued leads from the outreach queue? (Leaves test lead #2131)')) return
    setActionLoading(true)
    try {
      const resp = await api.post('/api/outreach/clear_all')
      toast.success(`Cleared ${resp.data.cleared} leads from outreach queue`)
      handleClearFilters()
      fetchOutreachData()
      fetchOutreachOptions()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to clear outreach queue')
    } finally {
      setActionLoading(false)
    }
  }

  // Strict Dual-Mode Batch Processing
  const handleProcessBatch = async () => {
    setActionLoading(true)
    try {
      let payload = {}

      if (selectedIds.size > 0) {
        // CASE A: Explicit Checkbox Selection Mode (Strictly process ONLY checked IDs)
        payload = { queue_ids: Array.from(selectedIds) }
      } else {
        // CASE B: Filter-Aware Batch Mode (Strictly process ONLY leads matching active screen filters)
        payload = {
          outreach_status: statusFilter,
          outreach_channel: channelFilter,
          outreach_step: stepFilter,
          source: sourceFilter,
          industry: industryFilter,
          quality_tier: qualityFilter,
          date_preset: dateFilter,
          search: searchQuery.trim(),
        }
      }

      const resp = await api.post('/api/outreach/process', payload)
      toast.success(`Processed: ${resp.data.processed}, Sent: ${resp.data.sent}, Failed: ${resp.data.failed}`)
      setSelectedIds(new Set())
      fetchOutreachData()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Batch processing failed')
    } finally {
      setActionLoading(false)
    }
  }

  const handleSingleDispatch = async (queueId) => {
    try {
      await api.post(`/api/outreach/${queueId}/dispatch`)
      toast.success('Dispatched outreach entry')
      fetchOutreachData()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Dispatch failed')
    }
  }

  const handleClearFilters = () => {
    setStatusFilter('ALL')
    setChannelFilter('ALL')
    setStepFilter('ALL')
    setSourceFilter('ALL')
    setIndustryFilter('ALL')
    setQualityFilter('ALL')
    setDateFilter('ALL')
    setSearchQuery('')
    setSelectedIds(new Set())
  }

  const activeFiltersCount = useMemo(() => {
    let count = 0
    if (statusFilter !== 'ALL') count++
    if (channelFilter !== 'ALL') count++
    if (stepFilter !== 'ALL') count++
    if (sourceFilter !== 'ALL') count++
    if (industryFilter !== 'ALL') count++
    if (qualityFilter !== 'ALL') count++
    if (dateFilter !== 'ALL') count++
    if (searchQuery.trim()) count++
    return count
  }, [statusFilter, channelFilter, stepFilter, sourceFilter, industryFilter, qualityFilter, dateFilter, searchQuery])

  const formatDateTime = (str) => {
    if (!str) return '-'
    try {
      return new Date(str).toLocaleString()
    } catch {
      return str
    }
  }

  return (
    <div className="p-4 lg:p-8 space-y-6">
      <PageHeader
        title="Outreach Queue & Cadence Dashboard"
        subtitle="Automated 3-Day Multi-touch outreach via Email and WhatsApp n8n workflows."
      >
        <div className="flex items-center space-x-3">
          <button
            onClick={fetchOutreachData}
            disabled={loading || actionLoading}
            className="flex items-center space-x-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm font-medium transition"
          >
            <RefreshCcw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleEnqueueAll}
            disabled={actionLoading}
            className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition"
          >
            <UserPlus className="h-4 w-4" />
            <span>Enqueue All Leads</span>
          </button>

          <button
            onClick={handleClearQueue}
            disabled={actionLoading}
            className="flex items-center space-x-2 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-sm font-medium transition"
          >
            <Trash2 className="h-4 w-4" />
            <span>Clear Queue</span>
          </button>

          {/* Strict Hybrid Action Button */}
          <button
            onClick={handleProcessBatch}
            disabled={actionLoading || queue.length === 0}
            className={`flex items-center space-x-2 px-4 py-2 text-white rounded-lg text-sm font-medium transition ${
              selectedIds.size > 0
                ? 'bg-emerald-600 hover:bg-emerald-700 ring-2 ring-emerald-300'
                : 'bg-indigo-600 hover:bg-indigo-700'
            }`}
          >
            {selectedIds.size > 0 ? (
              <>
                <CheckSquare className="h-4 w-4" />
                <span>Dispatch Selected ({selectedIds.size})</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4 fill-current" />
                <span>Process Batch Now {activeFiltersCount > 0 ? '(Filtered)' : ''}</span>
              </>
            )}
          </button>
        </div>
      </PageHeader>

      {/* KPI Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <div className="text-xs text-slate-500 font-medium">Total Enqueued</div>
            <div className="text-2xl font-bold text-slate-800 mt-1">{stats.total_enqueued}</div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <div className="text-xs text-slate-500 font-medium">Pending Queue</div>
            <div className="text-2xl font-bold text-amber-600 mt-1">{stats.pending}</div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <div className="text-xs text-blue-600 font-medium">Day 1 Sent</div>
            <div className="text-2xl font-bold text-blue-700 mt-1">{stats.step1_sent}</div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <div className="text-xs text-indigo-600 font-medium">Day 2 Sent</div>
            <div className="text-2xl font-bold text-indigo-700 mt-1">{stats.step2_sent}</div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <div className="text-xs text-emerald-600 font-medium">Day 3 / Completed</div>
            <div className="text-2xl font-bold text-emerald-700 mt-1">{stats.step3_completed}</div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
            <div className="text-xs text-red-500 font-medium">Failed</div>
            <div className="text-2xl font-bold text-red-600 mt-1">{stats.failed}</div>
          </div>
        </div>
      )}

      {/* Main Outreach Queue Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden space-y-0">
        
        {/* Comprehensive Multi-Filter Bar Header */}
        <div className="p-4 border-b border-slate-200 bg-slate-50/50 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center space-x-2 font-semibold text-slate-800">
              <Send className="h-5 w-5 text-indigo-600" />
              <span>Outreach Queue ({queue.length})</span>
              {activeFiltersCount > 0 && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800">
                  {activeFiltersCount} filter{activeFiltersCount > 1 ? 's' : ''} active
                </span>
              )}
              {selectedIds.size > 0 && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                  {selectedIds.size} selected
                </span>
              )}
            </div>

            {/* Global Search Box */}
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search by company, contact, email, or phone..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-8 py-1.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Dynamic Dropdown Filters Controls */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3 text-xs">
            {/* Status Filter */}
            <div>
              <label className="block text-slate-500 font-medium mb-1 flex items-center">
                <Filter className="h-3 w-3 mr-1 text-slate-400" /> Status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium text-slate-700"
              >
                <option value="ALL">All Statuses</option>
                <option value="PENDING">Pending</option>
                <option value="PROCESSING">Processing</option>
                <option value="SENT">Sent (Active)</option>
                <option value="COMPLETED">Completed</option>
                <option value="FAILED">Failed</option>
              </select>
            </div>

            {/* Channel Filter */}
            <div>
              <label className="block text-slate-500 font-medium mb-1 flex items-center">
                <Mail className="h-3 w-3 mr-1 text-slate-400" /> Channel
              </label>
              <select
                value={channelFilter}
                onChange={(e) => setChannelFilter(e.target.value)}
                className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium text-slate-700"
              >
                <option value="ALL">All Channels</option>
                <option value="EMAIL">Email</option>
                <option value="WHATSAPP">WhatsApp</option>
              </select>
            </div>

            {/* Cadence Step Filter */}
            <div>
              <label className="block text-slate-500 font-medium mb-1 flex items-center">
                <Layers className="h-3 w-3 mr-1 text-slate-400" /> Cadence Step
              </label>
              <select
                value={stepFilter}
                onChange={(e) => setStepFilter(e.target.value)}
                className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium text-slate-700"
              >
                <option value="ALL">All Steps</option>
                <option value="1">Step 1 (Day 1)</option>
                <option value="2">Step 2 (Day 2)</option>
                <option value="3">Step 3 (Day 3)</option>
              </select>
            </div>

            {/* Lead Source Filter */}
            <div>
              <label className="block text-slate-500 font-medium mb-1 flex items-center">
                <Globe className="h-3 w-3 mr-1 text-slate-400" /> Lead Source
              </label>
              <select
                value={sourceFilter}
                onChange={(e) => setSourceFilter(e.target.value)}
                className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium text-slate-700"
              >
                <option value="ALL">All Sources</option>
                {options.sources?.map((src) => (
                  <option key={src} value={src}>{src}</option>
                ))}
              </select>
            </div>

            {/* Industry / Category Filter */}
            <div>
              <label className="block text-slate-500 font-medium mb-1 flex items-center">
                <Building2 className="h-3 w-3 mr-1 text-slate-400" /> Industry / Niche
              </label>
              <select
                value={industryFilter}
                onChange={(e) => setIndustryFilter(e.target.value)}
                className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium text-slate-700"
              >
                <option value="ALL">All Industries</option>
                {options.industries?.map((ind) => (
                  <option key={ind} value={ind}>{ind}</option>
                ))}
              </select>
            </div>

            {/* Extraction Date Filter */}
            <div>
              <label className="block text-slate-500 font-medium mb-1 flex items-center">
                <Calendar className="h-3 w-3 mr-1 text-slate-400" /> Extracted Date
              </label>
              <select
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
                className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium text-slate-700"
              >
                <option value="ALL">All Time</option>
                <option value="TODAY">Extracted Today</option>
                <option value="LAST_7_DAYS">Last 7 Days</option>
                <option value="LAST_30_DAYS">Last 30 Days</option>
              </select>
            </div>

            {/* Quality Tier Filter */}
            <div>
              <label className="block text-slate-500 font-medium mb-1 flex items-center">
                <Sparkles className="h-3 w-3 mr-1 text-slate-400" /> Quality Tier
              </label>
              <select
                value={qualityFilter}
                onChange={(e) => setQualityFilter(e.target.value)}
                className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium text-slate-700"
              >
                <option value="ALL">All Tiers</option>
                <option value="excellent">Excellent</option>
                <option value="good">Good</option>
                <option value="average">Average</option>
              </select>
            </div>
          </div>

          {/* Reset Filters Bar */}
          {activeFiltersCount > 0 && (
            <div className="flex items-center justify-between pt-1 border-t border-slate-200/60 text-xs">
              <span className="text-slate-500">
                Showing results matching active filters
              </span>
              <button
                onClick={handleClearFilters}
                className="flex items-center text-indigo-600 hover:text-indigo-800 font-semibold"
              >
                <X className="h-3.5 w-3.5 mr-1" /> Clear all filters
              </button>
            </div>
          )}
        </div>

        {/* Table Content */}
        {loading ? (
          <div className="p-12 flex justify-center items-center text-slate-500">
            <LoadingSpinner className="h-6 w-6 mr-2" /> Loading outreach queue...
          </div>
        ) : queue.length === 0 ? (
          <div className="p-12 text-center text-slate-500 space-y-3">
            <Filter className="h-8 w-8 text-slate-300 mx-auto" />
            <div className="font-medium text-slate-700">No outreach entries match your filter criteria</div>
            {activeFiltersCount > 0 && (
              <button
                onClick={handleClearFilters}
                className="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg text-xs font-semibold transition"
              >
                Reset Filters
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 w-8">
                    <input
                      type="checkbox"
                      checked={selectedIds.size === queue.length && queue.length > 0}
                      onChange={handleToggleSelectAll}
                      className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                    />
                  </th>
                  <th className="px-4 py-3">Lead / Company</th>
                  <th className="px-4 py-3">Contact</th>
                  <th className="px-4 py-3">Source & Niche</th>
                  <th className="px-4 py-3">Channel</th>
                  <th className="px-4 py-3">Cadence Step</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Last Contacted</th>
                  <th className="px-4 py-3">Next Follow-Up</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {queue.map((item) => (
                  <tr key={item.id} className={`hover:bg-slate-50 transition ${selectedIds.has(item.id) ? 'bg-indigo-50/40' : ''}`}>
                    <td className="px-4 py-3 w-8">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(item.id)}
                        onChange={() => handleToggleSelectRow(item.id)}
                        className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                      />
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-900">
                      <div>{item.company_name || `Lead #${item.lead_id}`}</div>
                      {item.contact_name && (
                        <div className="text-xs text-slate-500 font-normal">{item.contact_name}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      {item.email || item.phone || '-'}
                    </td>
                    <td className="px-4 py-3 text-xs space-y-0.5">
                      <div className="font-medium text-slate-700">{item.source || 'Scrape'}</div>
                      {item.industry && (
                        <div className="text-slate-400 max-w-[140px] truncate" title={item.industry}>
                          {item.industry}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {item.outreach_channel === 'EMAIL' ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                          <Mail className="h-3 w-3 mr-1" /> Email
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <MessageSquare className="h-3 w-3 mr-1" /> WhatsApp
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-800 border border-slate-300">
                        Step {item.outreach_step || 1} of 3
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {item.outreach_status === 'SENT' && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                          <CheckCircle2 className="h-3 w-3 mr-1" /> Sent
                        </span>
                      )}
                      {item.outreach_status === 'PENDING' && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800">
                          <Clock className="h-3 w-3 mr-1" /> Pending
                        </span>
                      )}
                      {item.outreach_status === 'COMPLETED' && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-800">
                          <CheckCircle2 className="h-3 w-3 mr-1" /> Completed
                        </span>
                      )}
                      {item.outreach_status === 'FAILED' && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                          <AlertCircle className="h-3 w-3 mr-1" /> Failed
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {formatDateTime(item.last_contacted_at)}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {formatDateTime(item.next_follow_up_at)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {(item.outreach_status === 'PENDING' || item.outreach_status === 'FAILED') && (
                        <button
                          onClick={() => handleSingleDispatch(item.id)}
                          className="px-2 py-1 text-xs font-medium bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded border border-indigo-200 transition"
                        >
                          Dispatch
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
