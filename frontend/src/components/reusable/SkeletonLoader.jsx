export function SkeletonLine({ className = '' }) {
  return (
    <div
      className={`skeleton-shimmer rounded ${className}`}
    />
  )
}

export function SkeletonCard() {
  return (
    <div className="glass-card rounded-2xl p-5 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 space-y-3">
          <div className="skeleton-shimmer h-3 rounded w-1/3" />
          <div className="skeleton-shimmer h-7 rounded w-1/2" />
          <div className="skeleton-shimmer h-3 rounded w-1/4" />
        </div>
        <div className="skeleton-shimmer w-10 h-10 rounded-xl shrink-0" />
      </div>
    </div>
  )
}

export function SkeletonTableRow({ columns = 5 }) {
  return (
    <tr className="border-b border-slate-100 dark:border-slate-800">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-4 py-3.5">
          <div
            className="skeleton-shimmer h-4 rounded"
            style={{ width: `${55 + ((i * 17) % 35)}%` }}
          />
        </td>
      ))}
    </tr>
  )
}

export function SkeletonListRow() {
  return (
    <div className="flex items-center gap-3 px-2 py-2.5">
      <div className="skeleton-shimmer w-8 h-8 rounded-lg shrink-0" />
      <div className="flex-1 space-y-2">
        <div className="skeleton-shimmer h-3.5 rounded w-2/3" />
        <div className="skeleton-shimmer h-2.5 rounded w-1/3" />
      </div>
      <div className="skeleton-shimmer h-5 w-10 rounded-full shrink-0" />
    </div>
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

  if (variant === 'list') {
    return (
      <div className="space-y-1">
        {Array.from({ length: rows }).map((_, i) => (
          <SkeletonListRow key={i} />
        ))}
      </div>
    )
  }

  if (variant === 'chart') {
    return (
      <div className="rounded-2xl h-64 flex items-end gap-3 px-1 pb-1">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="skeleton-shimmer flex-1 rounded-t-md"
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
