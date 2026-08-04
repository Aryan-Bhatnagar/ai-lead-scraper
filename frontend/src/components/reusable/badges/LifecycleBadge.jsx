const LIFECYCLE_META = {
  NEW: {
    classes: 'bg-slate-100 text-slate-700 ring-slate-600/20 dark:bg-slate-500/10 dark:text-slate-400 dark:ring-slate-400/20',
    dot: 'bg-slate-400',
  },
  DISCOVERED: {
    classes: 'bg-blue-50 text-blue-700 ring-blue-600/20 dark:bg-blue-500/10 dark:text-blue-400 dark:ring-blue-500/20',
    dot: 'bg-blue-500',
  },
  ENRICHED: {
    classes: 'bg-primary-50 text-primary-700 ring-primary-600/20 dark:bg-primary-500/10 dark:text-primary-400 dark:ring-primary-500/20',
    dot: 'bg-primary-500',
  },
  SCORED: {
    classes: 'bg-indigo-50 text-indigo-700 ring-indigo-600/20 dark:bg-indigo-500/10 dark:text-indigo-400 dark:ring-indigo-500/20',
    dot: 'bg-indigo-500',
  },
  CONTACTED: {
    classes: 'bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/20',
    dot: 'bg-amber-500',
  },
  RESPONDED: {
    classes: 'bg-cyan-50 text-cyan-700 ring-cyan-600/20 dark:bg-cyan-500/10 dark:text-cyan-400 dark:ring-cyan-500/20',
    dot: 'bg-cyan-500',
  },
  QUALIFIED: {
    classes: 'bg-success-50 text-success-700 ring-success-600/20 dark:bg-success-500/10 dark:text-success-500 dark:ring-success-500/30',
    dot: 'bg-success-500',
  },
  LOST: {
    classes: 'bg-danger-50 text-danger-700 ring-danger-600/20 dark:bg-danger-500/10 dark:text-danger-500 dark:ring-danger-500/30',
    dot: 'bg-danger-500',
  },
  CUSTOMER: {
    classes: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-500/20',
    dot: 'bg-emerald-500',
  },
}

export const LIFECYCLE_ORDER = [
  'NEW',
  'DISCOVERED',
  'ENRICHED',
  'SCORED',
  'CONTACTED',
  'RESPONDED',
  'QUALIFIED',
  'CUSTOMER',
  'LOST',
]

export function getLifecycleColor(state, fallback = '#94a3b8') {
  const colors = {
    NEW: '#94a3b8',
    DISCOVERED: '#3b82f6',
    ENRICHED: '#6366f1',
    SCORED: '#6366f1',
    CONTACTED: '#f59e0b',
    RESPONDED: '#06b6d4',
    QUALIFIED: '#22c55e',
    LOST: '#f43f5e',
    CUSTOMER: '#10b981',
  }
  return colors[state] || fallback
}

export default function LifecycleBadge({ state }) {
  if (!state) return null
  const meta = LIFECYCLE_META[state] || LIFECYCLE_META.NEW

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset transition-shadow hover:shadow-sm ${meta.classes}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${meta.dot}`} />
      {state}
    </span>
  )
}
