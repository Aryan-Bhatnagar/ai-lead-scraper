import {
  Users,
  Gauge,
  Clock,
  ListChecks,
  ArrowRight,
} from 'lucide-react'
import CampaignStatusBadge from './CampaignStatusBadge'
import CampaignProgressBar from './CampaignProgressBar'
import SourceBadge from '../reusable/badges/SourceBadge'
import { PROVIDERS } from './ProviderMultiSelect'
import { campaignDurationMs, formatDurationMs, formatStartedAt } from '../../utils/formatDuration'

function providerLabel(id) {
  return PROVIDERS.find((p) => p.id === id)?.label || id
}

/**
 * CampaignCard
 * ------------
 * Summary card for one campaign. All values are server-derived.
 */
export default function CampaignCard({ campaign, onView }) {
  const c = campaign
  const percent =
    c.progressPercent != null
      ? c.progressPercent
      : c.queriesTotal > 0
        ? Math.round((c.queriesCompleted / c.queriesTotal) * 100)
        : 0

  const isLive = c.status === 'running' || c.status === 'pending' || c.status === 'queued' || c.status === 'in_progress'
  const durationMs = campaignDurationMs(c.startedAt, isLive ? null : c.completedAt)

  return (
    <div
      onClick={() => onView?.(c)}
      className="glass-card rounded-2xl p-5 h-full flex flex-col cursor-pointer transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-slate-900/[0.04] dark:hover:shadow-black/20 group animate-fade-up"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white truncate group-hover:text-primary-700 dark:group-hover:text-primary-300 transition-colors">
            {c.name}
          </h3>
          <p className="mt-0.5 text-xs text-slate-400 dark:text-slate-500">
            Started {formatStartedAt(c.startedAt)}
          </p>
        </div>
        <CampaignStatusBadge status={c.status} />
      </div>

      {/* Targeting chips */}
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {(c.providers || []).slice(0, 3).map((p) => (
          <SourceBadge key={p} source={providerLabel(p)} />
        ))}
        {(c.providers || []).length > 3 && (
          <span className="text-[11px] text-slate-400">+{c.providers.length - 3} more</span>
        )}
      </div>

      <div className="mt-4">
        <CampaignProgressBar percent={percent} status={c.status} />
      </div>

      {/* Metrics */}
      <div className="mt-4 grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
        <div className="inline-flex items-center gap-1.5 text-slate-500 dark:text-slate-400 min-w-0">
          <ListChecks className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate">
            <span className="font-semibold text-slate-700 dark:text-slate-200 tabular-nums">{c.queriesCompleted}</span>
            {' / '}
            <span className="tabular-nums">{c.queriesTotal || '—'}</span> queries
          </span>
        </div>
        <div className="inline-flex items-center gap-1.5 text-slate-500 dark:text-slate-400 min-w-0">
          <Users className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate">
            <span className="font-semibold text-slate-700 dark:text-slate-200 tabular-nums">{c.leadsDiscovered}</span> leads
          </span>
        </div>
        <div className="inline-flex items-center gap-1.5 text-slate-500 dark:text-slate-400 min-w-0">
          <Gauge className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate">
            Avg score{' '}
            <span className="font-semibold text-slate-700 dark:text-slate-200 tabular-nums">
              {c.averageScore != null ? Math.round(c.averageScore) : '—'}
            </span>
          </span>
        </div>
        <div className="inline-flex items-center gap-1.5 text-slate-500 dark:text-slate-400 min-w-0">
          <Clock className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate tabular-nums">{formatDurationMs(durationMs)}</span>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-end mt-auto">
        <span className="inline-flex items-center gap-1 text-xs font-medium text-primary-600 dark:text-primary-400 opacity-0 group-hover:opacity-100 transition-opacity">
          View progress
          <ArrowRight className="w-3 h-3" />
        </span>
      </div>
    </div>
  )
}
