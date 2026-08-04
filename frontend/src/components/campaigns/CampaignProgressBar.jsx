/**
 * CampaignProgressBar
 * -------------------
 * Visual completion indicator. Percent is always backend-derived
 * (queries_completed / queries_total or the reported percent).
 */
export default function CampaignProgressBar({ percent = 0, status = 'running', compact = false }) {
  const safe = Math.min(100, Math.max(0, Number(percent) || 0))

  const barColor =
    status === 'failed'
      ? 'bg-danger-500'
      : status === 'paused'
        ? 'bg-amber-500'
        : status === 'cancelled' || status === 'canceled'
          ? 'bg-slate-400'
          : status === 'completed'
            ? 'bg-primary-500'
            : 'bg-success-500'

  return (
    <div className="w-full">
      <div className={`w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden ${compact ? 'h-1.5' : 'h-2'}`}>
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${barColor} ${
            status === 'running' ? 'progress-stripes' : ''
          }`}
          style={{ width: `${safe}%` }}
          role="progressbar"
          aria-valuenow={safe}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      {!compact && (
        <div className="mt-1 flex items-center justify-between">
          <span className="text-[11px] text-slate-400">Progress</span>
          <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-300 tabular-nums">
            {safe}%
          </span>
        </div>
      )}
    </div>
  )
}
