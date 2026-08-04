export function SkeletonLine({ className = '' }) {
  return (
    <div
      className={`animate-pulse bg-slate-200 dark:bg-slate-700/60 rounded ${className}`}
    />
  )
}

export function SkeletonCard() {
  return (
    <div className="glass-card rounded-2xl p-5 space-y-3 animate-pulse">
      <div className="h-3 bg-slate-200 dark:bg-slate-700/60 rounded w-1/3" />
      <div className="h-7 bg-slate-200 dark:bg-slate-700/60 rounded w-1/2" />
      <div className="h-3 bg-slate-200 dark:bg-slate-700/60 rounded w-1/4" />
    </div>
  )
}

export function SkeletonTableRow({ columns = 5 }) {
  return (
    <tr className="border-b border-slate-100 dark:border-slate-800">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 animate-pulse bg-slate-200 dark:bg-slate-700/60 rounded w-3/4" />
        </td>
      ))}
    </tr>
  )
}

export default function SkeletonLoader({ variant = 'table', rows = 5 }) {
  if (variant === 'cards') {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    )
  }

  if (variant === 'chart') {
    return (
      <div className="glass-card rounded-2xl p-5 h-64 flex items-end gap-3 animate-pulse">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="flex-1 bg-slate-200 dark:bg-slate-700/60 rounded-t"
            style={{ height: `${20 + ((i * 13) % 70)}%` }}
          />
        ))}
      </div>
    )
  }

  return (
    <table className="w-full">
      <tbody>
        {Array.from({ length: rows }).map((_, i) => (
          <SkeletonTableRow key={i} />
        ))}
      </tbody>
    </table>
  )
}
