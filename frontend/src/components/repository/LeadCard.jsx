import { Building2, MapPin, ArrowRight } from 'lucide-react'
import ScoreBadge from '../reusable/badges/ScoreBadge'
import LifecycleBadge from '../reusable/badges/LifecycleBadge'
import SourceBadge from '../reusable/badges/SourceBadge'

export default function LeadCard({ lead, onView, className = '' }) {
  const domain = lead.website?.replace(/^https?:\/\//, '').replace(/\/$/, '')

  return (
    <div
      onClick={() => onView?.(lead)}
      className={`glass-card rounded-2xl p-4 cursor-pointer transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-primary-500/5 group ${className}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-primary-50 dark:bg-primary-500/10 flex items-center justify-center text-primary-600 dark:text-primary-400 shrink-0">
            <Building2 className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white truncate">
              {lead.company_name}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
              {domain}
            </p>
          </div>
        </div>
        <ScoreBadge score={lead.score} size="sm" />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <LifecycleBadge state={lead.lifecycle} />
        <SourceBadge source={lead.source} />
      </div>

      <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
        <span className="inline-flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
          <MapPin className="w-3 h-3" />
          {[lead.city, lead.country].filter(Boolean).join(', ')}
        </span>
        <span className="inline-flex items-center gap-1 text-xs font-medium text-primary-600 dark:text-primary-400 opacity-0 group-hover:opacity-100 transition-opacity">
          Details
          <ArrowRight className="w-3 h-3" />
        </span>
      </div>
    </div>
  )
}
