import { useEffect } from 'react'
import {
  X,
  Globe,
  MapPin,
  Mail,
  Phone,
  User,
  Clock,
  Tag,
} from 'lucide-react'
import ScoreBadge from '../reusable/badges/ScoreBadge'
import LifecycleBadge from '../reusable/badges/LifecycleBadge'
import SourceBadge from '../reusable/badges/SourceBadge'

function DrawerRow({ icon: Icon, label, children }) {
  return (
    <div className="flex items-start gap-3 py-2.5">
      <Icon className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</p>
        <div className="text-sm text-slate-800 dark:text-slate-200">{children}</div>
      </div>
    </div>
  )
}

export default function LeadDetailsDrawer({ lead, onClose }) {
  useEffect(() => {
    if (!lead) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') onClose?.()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [lead, onClose])

  const open = !!lead

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-40 transition-opacity duration-300 ${
          open ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
      />

      {/* Panel */}
      <aside
        className={`fixed top-0 right-0 h-full w-full max-w-md z-50 bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700/60 shadow-2xl transition-transform duration-300 ease-out ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
        aria-hidden={!open}
      >
        {lead && (
          <div className="h-full flex flex-col">
            {/* Header */}
            <div className="flex items-start justify-between p-5 border-b border-slate-200 dark:border-slate-700/60">
              <div className="min-w-0 flex-1 pr-4">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white truncate">
                  {lead.company_name}
                </h2>
                <div className="mt-1.5 flex flex-wrap items-center gap-2">
                  <ScoreBadge score={lead.score} />
                  <LifecycleBadge state={lead.lifecycle} />
                  <SourceBadge source={lead.source} />
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                aria-label="Close drawer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Scrollable body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-6">
              {/* Core info */}
              <section>
                <div className="divide-y divide-slate-100 dark:divide-slate-800">
                  <DrawerRow icon={Globe} label="Website">
                    <a
                      href={lead.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-600 dark:text-primary-400 hover:underline break-all"
                    >
                      {lead.website}
                    </a>
                  </DrawerRow>
                  <DrawerRow icon={MapPin} label="Location">
                    {[lead.city, lead.country].filter(Boolean).join(', ')}
                    {lead.industry && <span className="text-slate-400"> · {lead.industry}</span>}
                  </DrawerRow>
                  <DrawerRow icon={User} label="Contact">
                    {lead.contact_name || '—'}
                  </DrawerRow>
                  <DrawerRow icon={Mail} label="Email">
                    {lead.email ? (
                      <a href={`mailto:${lead.email}`} className="text-primary-600 dark:text-primary-400 hover:underline break-all">
                        {lead.email}
                      </a>
                    ) : (
                      '—'
                    )}
                  </DrawerRow>
                  <DrawerRow icon={Phone} label="Phone">
                    {lead.phone || '—'}
                  </DrawerRow>
                </div>
                {lead.description && (
                  <div className="mt-4 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60">
                    <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5">
                      Description
                    </p>
                    <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                      {lead.description}
                    </p>
                  </div>
                )}
              </section>

              {/* Score breakdown */}
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-3">
                  Score Breakdown
                </h3>
                <div className="space-y-2.5">
                  {lead.score_breakdown.map((b) => {
                    const pct = Math.round((b.contribution / b.max) * 100)
                    return (
                      <div key={b.feature}>
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="font-medium text-slate-600 dark:text-slate-300">
                            {b.label}
                          </span>
                          <span className="text-slate-400 tabular-nums">
                            +{b.contribution} / {b.max}
                          </span>
                        </div>
                        <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-primary-500 to-primary-400 transition-all duration-500"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                  <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800">
                    <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                      Quality Tier
                    </span>
                    <span className="text-xs font-semibold capitalize text-primary-600 dark:text-primary-400">
                      {lead.quality_tier}
                    </span>
                  </div>
                </div>
              </section>

              {/* Timeline */}
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5" />
                  Lifecycle Timeline
                </h3>
                <ol className="relative space-y-4 pl-6">
                  <span className="absolute left-[9px] top-1 bottom-1 w-px bg-slate-200 dark:bg-slate-700" />
                  {[...lead.timeline].reverse().map((event, i) => (
                    <li key={`${event.status}-${event.at}`} className="relative">
                      <span
                        className={`absolute -left-6 top-1 w-[13px] h-[13px] rounded-full ring-4 ring-white dark:ring-slate-900 ${
                          i === 0 ? 'bg-primary-500 animate-pulse-ring' : 'bg-slate-300 dark:bg-slate-600'
                        }`}
                      />
                      <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                        {event.status}
                      </p>
                      <p className="text-xs text-slate-400">
                        {new Date(event.at).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}{' '}
                        · {event.note}
                      </p>
                    </li>
                  ))}
                </ol>
              </section>

              {/* Provenance */}
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
                  <Tag className="w-3.5 h-3.5" />
                  Discovery
                </h3>
                <div className="rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 p-3.5 text-sm space-y-1.5">
                  <p className="flex justify-between">
                    <span className="text-slate-500 dark:text-slate-400">Source</span>
                    <span className="font-medium text-slate-800 dark:text-slate-200">{lead.source}</span>
                  </p>
                  <p className="flex justify-between">
                    <span className="text-slate-500 dark:text-slate-400">Discovered</span>
                    <span className="font-medium text-slate-800 dark:text-slate-200">
                      {new Date(lead.discovered_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })}
                    </span>
                  </p>
                  <p className="flex justify-between">
                    <span className="text-slate-500 dark:text-slate-400">Last Updated</span>
                    <span className="font-medium text-slate-800 dark:text-slate-200">
                      {new Date(lead.lifecycle_updated_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })}
                    </span>
                  </p>
                </div>
              </section>
            </div>
          </div>
        )}
      </aside>
    </>
  )
}
