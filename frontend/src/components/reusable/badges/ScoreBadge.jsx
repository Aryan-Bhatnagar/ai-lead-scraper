export default function ScoreBadge({ score = 0, size = 'md' }) {
  const tier =
    score >= 70 ? 'high' : score >= 40 ? 'medium' : 'low'

  const styles = {
    high: 'bg-success-50 text-success-700 ring-success-600/20 dark:bg-success-500/10 dark:text-success-500 dark:ring-success-500/30',
    medium: 'bg-warning-50 text-warning-700 ring-warning-600/20 dark:bg-warning-500/10 dark:text-warning-500 dark:ring-warning-500/30',
    low: 'bg-danger-50 text-danger-700 ring-danger-600/20 dark:bg-danger-500/10 dark:text-danger-500 dark:ring-danger-500/30',
  }

  const barColors = {
    high: 'bg-success-500',
    medium: 'bg-warning-500',
    low: 'bg-danger-500',
  }

  const sizeMap = {
    sm: 'text-[11px] px-1.5 py-0.5',
    md: 'text-xs px-2 py-1',
    lg: 'text-sm px-3 py-1.5',
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold ring-1 ring-inset ${styles[tier]} ${sizeMap[size]}`}
    >
      <span className="relative w-8 h-1.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden hidden sm:inline-block">
        <span
          className={`absolute inset-y-0 left-0 rounded-full ${barColors[tier]}`}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </span>
      {score}
    </span>
  )
}
