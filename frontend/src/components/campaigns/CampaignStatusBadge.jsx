const STATUS_META = {
  running: {
    label: 'Running',
    classes: 'bg-success-50 text-success-700 ring-success-600/20 dark:bg-success-500/10 dark:text-success-500 dark:ring-success-500/30',
    dot: 'bg-success-500 animate-pulse-dot',
  },
  paused: {
    label: 'Paused',
    classes: 'bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/20',
    dot: 'bg-amber-500',
  },
  pending: {
    label: 'Pending',
    classes: 'bg-blue-50 text-blue-700 ring-blue-600/20 dark:bg-blue-500/10 dark:text-blue-400 dark:ring-blue-500/20',
    dot: 'bg-blue-500 animate-pulse-dot',
  },
  queued: {
    label: 'Queued',
    classes: 'bg-blue-50 text-blue-700 ring-blue-600/20 dark:bg-blue-500/10 dark:text-blue-400 dark:ring-blue-500/20',
    dot: 'bg-blue-500 animate-pulse-dot',
  },
  in_progress: {
    label: 'Running',
    classes: 'bg-success-50 text-success-700 ring-success-600/20 dark:bg-success-500/10 dark:text-success-500 dark:ring-success-500/30',
    dot: 'bg-success-500 animate-pulse-dot',
  },
  completed: {
    label: 'Completed',
    classes: 'bg-primary-50 text-primary-700 ring-primary-600/20 dark:bg-primary-500/10 dark:text-primary-400 dark:ring-primary-500/20',
    dot: 'bg-primary-500',
  },
  failed: {
    label: 'Failed',
    classes: 'bg-danger-50 text-danger-700 ring-danger-600/20 dark:bg-danger-500/10 dark:text-danger-500 dark:ring-danger-500/30',
    dot: 'bg-danger-500',
  },
  cancelled: {
    label: 'Cancelled',
    classes: 'bg-slate-100 text-slate-600 ring-slate-500/20 dark:bg-slate-500/10 dark:text-slate-400 dark:ring-slate-400/20',
    dot: 'bg-slate-400',
  },
  canceled: {
    label: 'Cancelled',
    classes: 'bg-slate-100 text-slate-600 ring-slate-500/20 dark:bg-slate-500/10 dark:text-slate-400 dark:ring-slate-400/20',
    dot: 'bg-slate-400',
  },
}

export default function CampaignStatusBadge({ status }) {
  const meta = STATUS_META[status] || {
    label: status ? status.replace(/_/g, ' ') : 'Unknown',
    classes:
      'bg-slate-100 text-slate-600 ring-slate-500/20 dark:bg-slate-500/10 dark:text-slate-400 dark:ring-slate-400/20',
    dot: 'bg-slate-400',
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold capitalize ring-1 ring-inset transition-shadow hover:shadow-sm ${meta.classes}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${meta.dot}`} />
      {meta.label}
    </span>
  )
}
