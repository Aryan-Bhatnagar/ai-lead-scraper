import { TrendingUp } from 'lucide-react'

/**
 * OpportunityScoreBadge
 * ----------------------
 * Shows the AI opportunity score (0-100) with a tier-based color,
 * mirroring the opportunity_thresholds in config/lead_scoring.yaml:
 * high >= 64, medium >= 50, low >= 35.
 */
export default function OpportunityScoreBadge({ score = null, size = 'md' }) {
  const hasScore = typeof score === 'number' && Number.isFinite(score) && score > 0

  const tier = !hasScore ? 'none' : score >= 64 ? 'high' : score >= 50 ? 'medium' : score >= 35 ? 'low' : 'weak'
  const styles = {
    high: 'bg-emerald-50 text-emerald-700 ring-emerald-600/25 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-500/30',
    medium:
      'bg-amber-50 text-amber-700 ring-amber-600/25 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/30',
    low: 'bg-orange-50 text-orange-700 ring-orange-600/25 dark:bg-orange-500/10 dark:text-orange-400 dark:ring-orange-500/30',
    weak: 'bg-rose-50 text-rose-700 ring-rose-600/25 dark:bg-rose-500/10 dark:text-rose-400 dark:ring-rose-500/30',
    none: 'bg-slate-100 text-slate-500 ring-slate-500/20 dark:bg-slate-500/10 dark:text-slate-400 dark:ring-slate-400/20',
  }
  const sizeMap = {
    sm: 'text-[11px] px-1.5 py-0.5',
    md: 'text-xs px-2 py-1',
    lg: 'text-sm px-3 py-1.5',
  }

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-semibold ring-1 ring-inset transition-shadow hover:shadow-sm ${styles[tier]} ${sizeMap[size]}`}
      title={hasScore ? `AI Opportunity Score: ${score}/100` : 'No AI opportunity score yet'}
    >
      <TrendingUp className="w-3 h-3" />
      {hasScore ? score : '—'}
    </span>
  )
}
