export default function ScoreBadge({ score = 0, size = 'md' }) {
  const tier =
    score >= 80 ? 'excellent' : score >= 70 ? 'high' : score >= 40 ? 'medium' : score > 0 ? 'low' : 'none'

  const styles = {
    excellent:
      'bg-emerald-50 text-emerald-700 ring-emerald-600/25 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-500/30',
    high: 'bg-success-50 text-success-700 ring-success-600/20 dark:bg-success-500/10 dark:text-success-500 dark:ring-success-500/30',
    medium:
      'bg-warning-50 text-warning-700 ring-warning-600/20 dark:bg-warning-500/10 dark:text-warning-500 dark:ring-warning-500/30',
    low: 'bg-danger-50 text-danger-700 ring-danger-600/20 dark:bg-danger-500/10 dark:text-danger-500 dark:ring-danger-500/30',
    none: 'bg-slate-100 text-slate-500 ring-slate-500/20 dark:bg-slate-500/10 dark:text-slate-400 dark:ring-slate-400/20',
  }

  const barColors = {
    excellent: 'bg-emerald-500',
    high: 'bg-success-500',
    medium: 'bg-warning-500',
    low: 'bg-danger-500',
    none: 'bg-slate-400',
  }

  const sizeMap = {
    sm: 'text-[11px] px-1.5 py-0.5',
    md: 'text-xs px-2 py-1',
    lg: 'text-sm px-3 py-1.5',
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold ring-1 ring-inset transition-shadow hover:shadow-sm ${styles[tier]} ${sizeMap[size]}`}
      title={`Quality score: ${score}/100`}
    >
      <span className="relative w-8 h-1.5 rounded-full bg-slate-200/80 dark:bg-slate-700/80 overflow-hidden hidden sm:inline-block">
        <span
          className={`absolute inset-y-0 left-0 rounded-full transition-[width] duration-500 ${barColors[tier]}`}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </span>
      {score}
    </span>
  )
}
