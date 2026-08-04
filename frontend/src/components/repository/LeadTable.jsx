import { useMemo, useState } from 'react'
import {
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
  Eye,
  Building2,
  Download,
} from 'lucide-react'
import ScoreBadge from '../reusable/badges/ScoreBadge'
import LifecycleBadge from '../reusable/badges/LifecycleBadge'
import SourceBadge from '../reusable/badges/SourceBadge'
import Pagination from '../reusable/Pagination'
import { SkeletonTableRow } from '../reusable/SkeletonLoader'

export const PAGE_SIZE = 8

function sortIndicator(active, direction) {
  if (!active) return <ArrowUpDown className="w-3.5 h-3.5 text-slate-300 dark:text-slate-600" />
  return direction === 'asc' ? (
    <ArrowUp className="w-3.5 h-3.5 text-primary-500" />
  ) : (
    <ArrowDown className="w-3.5 h-3.5 text-primary-500" />
  )
}

/**
 * LeadTable
 * ---------
 * Controlled table. The parent owns sorting (sortBy / sortDesc / onSort),
 * pagination (page / totalPages / totalItems / onPageChange) and the rows
 * themselves (already filtered). Selection stays local (UI-only) until an
 * action is performed, then cleared via onExport.
 */
export default function LeadTable({
  leads,
  loading = false,
  onView,
  // server-driven props (all optional — fall back to internal defaults)
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
              onClick={() => setSelected(new Set())}
              className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-white/60 dark:hover:bg-slate-800 rounded-lg transition-colors"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[900px]">
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
              {headerCell('company_name', 'Company')}
              {headerCell('website', 'Website')}
              {headerCell('country', 'Country')}
              {headerCell('quality_score', 'Score', true)}
              {headerCell('data_quality', 'Quality')}
              {headerCell('lead_status', 'Lifecycle')}
              {headerCell('source', 'Source')}
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 text-right">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading
              ? Array.from({ length: PAGE_SIZE }).map((_, i) => <SkeletonTableRow key={i} columns={9} />)
              : pageLeads.map((lead) => {
                  const isSelected = selected.has(lead.id)
                  const domain = lead.website?.replace(/^https?:\/\//, '').replace(/\/$/, '')
                  return (
                    <tr
                      key={lead.id}
                      onClick={() => onView?.(lead)}
                      className={`group cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-primary-50/60 dark:bg-primary-500/10'
                          : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
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
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5 max-w-[230px]">
                          <div className="w-8 h-8 rounded-lg bg-primary-50 dark:bg-primary-500/10 flex items-center justify-center text-primary-600 dark:text-primary-400 shrink-0">
                            <Building2 className="w-4 h-4" />
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-slate-800 dark:text-slate-100 truncate">
                              {lead.company_name}
                            </p>
                            {lead.industry && (
                              <p className="text-xs text-slate-400 truncate">{lead.industry}</p>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm max-w-[200px]">
                        <a
                          href={lead.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="text-primary-600 dark:text-primary-400 hover:underline truncate block"
                        >
                          {domain}
                        </a>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">
                        {lead.country || '—'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <ScoreBadge score={lead.score} />
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs font-medium capitalize text-slate-600 dark:text-slate-300">
                          {lead.quality_tier === 'unknown' ? '—' : lead.quality_tier}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <LifecycleBadge state={lead.lifecycle} />
                      </td>
                      <td className="px-4 py-3">
                        <SourceBadge source={lead.source} />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            onView?.(lead)
                          }}
                          className="p-1.5 text-slate-400 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-500/10 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                          title="View details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  )
                })}
          </tbody>
        </table>
      </div>

      <div className="px-4 pb-2">
        <Pagination
          page={pageProp}
          totalPages={totalPagesProp}
          totalItems={totalItems}
          pageSize={PAGE_SIZE}
          onPageChange={onPageChange}
        />
      </div>
    </div>
  )
}
