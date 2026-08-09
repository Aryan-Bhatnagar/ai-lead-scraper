import { ChevronLeft, ChevronRight } from 'lucide-react'

export default function Pagination({ page, totalPages, totalItems, pageSize, onPageChange }) {
  if (totalPages <= 1) return null

  const start = (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, totalItems)

  const pages = []
  const maxVisible = 5
  let startPage = Math.max(1, page - Math.floor(maxVisible / 2))
  let endPage = Math.min(totalPages, startPage + maxVisible - 1)
  if (endPage - startPage < maxVisible - 1) {
    startPage = Math.max(1, endPage - maxVisible + 1)
  }
  for (let i = startPage; i <= endPage; i += 1) pages.push(i)

  const btnBase =
    'min-w-8 h-8 px-2 inline-flex items-center justify-center rounded-lg text-sm font-medium transition-colors'
  const btnIdle =
    'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
  const btnActive = 'bg-primary-600 text-white shadow-sm'
  const btnDisabled = 'opacity-40 cursor-not-allowed'

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4">
      <p className="text-xs text-slate-500 dark:text-slate-400">
        Showing <span className="font-medium text-slate-700 dark:text-slate-300">{start}–{end}</span> of{' '}
        <span className="font-medium text-slate-700 dark:text-slate-300">{totalItems}</span> leads
      </p>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
          className={`${btnBase} ${btnIdle} ${page === 1 ? btnDisabled : ''}`}
          aria-label="Previous page"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        {startPage > 1 && (
          <>
            <button onClick={() => onPageChange(1)} className={`${btnBase} ${btnIdle}`}>
              1
            </button>
            {startPage > 2 && <span className="text-slate-400 px-1">…</span>}
          </>
        )}
        {pages.map((p) => (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            className={`${btnBase} ${p === page ? btnActive : btnIdle}`}
          >
            {p}
          </button>
        ))}
        {endPage < totalPages && (
          <>
            {endPage < totalPages - 1 && <span className="text-slate-400 px-1">…</span>}
            <button onClick={() => onPageChange(totalPages)} className={`${btnBase} ${btnIdle}`}>
              {totalPages}
            </button>
          </>
        )}
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page === totalPages}
          className={`${btnBase} ${btnIdle} ${page === totalPages ? btnDisabled : ''}`}
          aria-label="Next page"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
