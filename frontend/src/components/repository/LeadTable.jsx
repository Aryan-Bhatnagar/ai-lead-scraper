import { useMemo, useState } from 'react'
import {
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
  Eye,
  Building2,
  Download,
  Trash2,
  AlertCircle,
  Send,
} from 'lucide-react'
import ScoreBadge from '../reusable/badges/ScoreBadge'
import OpportunityScoreBadge from '../reusable/badges/OpportunityScoreBadge'
import LifecycleBadge from '../reusable/badges/LifecycleBadge'
import SourceBadge from '../reusable/badges/SourceBadge'
import Pagination from '../reusable/Pagination'
import { SkeletonTableRow } from '../reusable/SkeletonLoader'
import api from '../../services/api'
import toast from 'react-hot-toast'

export const PAGE_SIZE = 8

function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function CompanyLogo({ lead, className = 'w-8 h-8 rounded-lg' }) {
  const { company_logo: logo, company_name: name } = lead
  if (logo && logo.startsWith('http')) {
    return (
      <img
        src={logo}
        alt={name}
        className={`${className} bg-white object-contain p-1 ring-1 ring-slate-200 dark:ring-slate-700 shrink-0`}
        onError={(e) => { e.currentTarget.style.display = 'none' }}
      />
    )
  }
  return (
    <div className={`${className} bg-primary-50 dark:bg-primary-500/10 flex items-center justify-center text-primary-600 dark:text-primary-400 shrink-0`}>
      <Building2 className="w-4 h-4" />
    </div>
  )
}

function sortIndicator(active, direction) {
  if (!active) return <ArrowUpDown className="w-3.5 h-3.5 text-slate-300 dark:text-slate-600" />
  return direction === 'asc' ? (
    <ArrowUp className="w-3.5 h-3.5 text-primary-500" />
  ) : (
    <ArrowDown className="w-3.5 h-3.5 text-primary-500" />
  )
}

export default function LeadTable({
  leads,
  loading = false,
  onView,
  onDelete,
  page: pageProp = 1,
  totalPages: totalPagesProp = 1,
  totalItems: totalItemsProp,
  onPageChange = () => {},
  sortBy: sortByProp = 'score',
  sortDesc: sortDescProp = true,
  onSort = () => {},
  onExport,
}) {
  const [selected, setSelected] = useState(() => new Set())
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const pageLeads = leads
  const totalItems = totalItemsProp ?? leads.length

  const allOnPageSelected = pageLeads.length > 0 && pageLeads.every((l) => selected.has(l.id))
  const toggleAllOnPage = () => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (allOnPageSelected) pageLeads.forEach((l) => next.delete(l.id))
      else pageLeads.forEach((l) => next.add(l.id))
      return next
    })
  }
  const toggleRow = (id) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleExport = () => {
    const toExport = leads.filter((l) => selected.has(l.id))
    if (toExport.length === 0) return
    onExport?.(toExport)
    setSelected(new Set())
  }

  const handleBulkDelete = () => {
    if (selected.size === 0) return
    setShowDeleteConfirm(true)
  }

  const confirmBulkDelete = async () => {
    const toDelete = leads.filter((l) => selected.has(l.id))
    if (toDelete.length === 0) return
    const leadIds = toDelete.map((l) => l.id)
    try {
      await onDelete?.(leadIds)
      setSelected(new Set())
      setShowDeleteConfirm(false)
    } catch (error) {
      console.error('Bulk delete failed:', error)
      setShowDeleteConfirm(false)
    }
  }

  const handleEnqueueLead = async (e, lead) => {
    e.stopPropagation()
    const channel = lead.email ? 'EMAIL' : lead.phone ? 'WHATSAPP' : null
    if (!channel) {
      toast.error('Lead has neither email nor phone number')
      return
    }
    try {
      await api.post('/api/outreach', {
        lead_id: lead.id,
        outreach_channel: channel,
      })
      toast.success(`Queued #${lead.id} (${lead.company_name || 'Lead'}) for ${channel} outreach!`)
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to queue lead for outreach')
    }
  }

  const headerCell = (key, label, numeric = false) => (
    <th
      onClick={() => onSort(key)}
      className={`px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 cursor-pointer select-none hover:text-slate-700 dark:hover:text-slate-200 transition-colors ${numeric ? 'text-right' : 'text-left'}`}
    >
      <span className={`inline-flex items-center gap-1 ${numeric ? 'flex-row-reverse' : ''}`}>
        {label}
        {sortIndicator(sortByProp === key, sortDescProp ? 'desc' : 'asc')}
      </span>
    </th>
  )

  return (
    <div className="glass-card rounded-2xl overflow-hidden animate-fade-up">
      {/* Selection toolbar */}
      {selected.size > 0 && (
        <div className="px-4 py-2.5 bg-primary-50 dark:bg-primary-500/10 border-b border-primary-100 dark:border-primary-500/20 flex items-center justify-between animate-fade-in">
          <span className="text-sm font-medium text-primary-700 dark:text-primary-400">
            {selected.size} lead{selected.size === 1 ? '' : 's'} selected
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={handleExport}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Export CSV
            </button>
            <button
              onClick={handleBulkDelete}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Delete
            </button>
            <button
              onClick={() => setSelected(new Set())}
              className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-white/60 dark:hover:bg-slate-800 rounded-lg transition-colors"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Bulk Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 animate-fade-in">
          <div className="glass-card rounded-2xl p-6 w-full max-w-md mx-4 animate-slide-up">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-500/20 flex items-center justify-center">
                <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
              </div>
              <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Delete {selected.size} lead{selected.size === 1 ? '' : 's'}?</h3>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-300 mb-6">
              This action cannot be undone. The selected leads will be permanently removed from the database.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-white/60 dark:hover:bg-slate-800 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmBulkDelete}
                disabled={loading}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                <Trash2 className="w-4 h-4" />
                Delete Permanently
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[1240px]">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700/60 bg-slate-50/60 dark:bg-slate-800/40">
              <th className="w-10 px-4 py-3">
                <input
                  type="checkbox"
                  checked={allOnPageSelected}
                  onChange={toggleAllOnPage}
                  className="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500 cursor-pointer"
                  aria-label="Select all on page"
                />
              </th>
              {headerCell('id', 'ID')}
              {headerCell('company_name', 'Company')}
              {headerCell('contact_name', 'Contact')}
              {headerCell('email', 'Email')}
              {headerCell('phone', 'Phone')}
              {headerCell('website', 'Website')}
              {headerCell('country', 'Location')}
              {headerCell('company_size_estimate', 'Company Size')}
              {headerCell('source', 'Source')}
              {headerCell('opportunity_score', 'AI Score', true)}
              {headerCell('quality_score', 'Quality', true)}
              {headerCell('lead_status', 'Lifecycle')}
              {headerCell('updated_at', 'Last Updated')}
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 text-right">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading
              ? Array.from({ length: PAGE_SIZE }).map((_, i) => <SkeletonTableRow key={i} columns={14} />)
              : pageLeads.map((lead) => {
                  const isSelected = selected.has(lead.id)
                  const domain = lead.website?.replace(/^https?:\/\//, '').replace(/\/$/, '')
                  const location = [lead.city, lead.region, lead.country].filter(Boolean).join(', ') || '—'
                  return (
                    <tr
                      key={lead.id}
                      onClick={() => onView?.(lead)}
                      className={`group cursor-pointer transition-colors duration-150 ${
                        isSelected
                          ? 'bg-primary-50/70 dark:bg-primary-500/10 hover:bg-primary-50 dark:hover:bg-primary-500/15'
                          : 'hover:bg-primary-50/40 dark:hover:bg-slate-800/60'
                      }`}
                    >
                      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleRow(lead.id)}
                          className="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500 cursor-pointer"
                          aria-label={`Select ${lead.company_name}`}
                        />
                      </td>
                      <td className="px-4 py-3 text-xs font-mono font-bold text-indigo-600 dark:text-indigo-400">
                        #{lead.id}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5 max-w-[230px]">
                          <CompanyLogo lead={lead} />
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-slate-800 dark:text-slate-100 truncate group-hover:text-primary-700 dark:group-hover:text-primary-300 transition-colors">
                              {lead.company_name}
                            </p>
                            {lead.industry && (
                              <p className="text-xs text-slate-400 truncate">{lead.industry}</p>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 max-w-[160px]">
                        <p className="text-sm text-slate-600 dark:text-slate-300 truncate">
                          {lead.contact_name || '—'}
                        </p>
                        {lead.job_title && (
                          <p className="text-xs text-slate-400 truncate">{lead.job_title}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300 truncate max-w-[200px]">
                        {lead.email || '—'}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300 truncate max-w-[150px]">
                        {lead.phone || '—'}
                      </td>
                      <td className="px-4 py-3 text-sm max-w-[180px]">
                        <a
                          href={lead.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="text-primary-600 dark:text-primary-400 hover:underline underline-offset-2 truncate block"
                        >
                          {domain || '—'}
                        </a>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300 truncate max-w-[160px]">
                        {location}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">
                        {lead.company_size_estimate || '—'}
                      </td>
                      <td className="px-4 py-3">
                        <SourceBadge source={lead.source} />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <OpportunityScoreBadge score={lead.score} />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <ScoreBadge tier={lead.quality_tier} score={lead.score} />
                      </td>
                      <td className="px-4 py-3">
                        <LifecycleBadge status={lead.lifecycle} />
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-400 whitespace-nowrap">
                        {formatDate(lead.updated_at)}
                      </td>
                      <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={(e) => handleEnqueueLead(e, lead)}
                            className="p-1 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-500/20 rounded transition-colors"
                            title="Queue for Outreach"
                          >
                            <Send size={15} />
                          </button>
                          <button
                            onClick={() => onView?.(lead)}
                            className="p-1 text-slate-500 hover:text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-500/20 rounded transition-colors"
                            title="View Details"
                          >
                            <Eye size={15} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
          </tbody>
        </table>
      </div>

      <Pagination
        page={pageProp}
        totalPages={totalPagesProp}
        totalItems={totalItems}
        pageSize={PAGE_SIZE}
        onPageChange={onPageChange}
      />
    </div>
  )
}
