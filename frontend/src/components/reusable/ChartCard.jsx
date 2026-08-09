export default function ChartCard({ title, subtitle, actions, children, className = '' }) {
  return (
    <div
      className={`glass-card rounded-2xl p-5 h-full transition-all duration-300 hover:shadow-lg hover:shadow-slate-900/[0.04] dark:hover:shadow-black/20 ${className}`}
    >
      <div className="flex items-start justify-between gap-2 mb-4">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white truncate">{title}</h3>
          {subtitle && (
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </div>
      {children}
    </div>
  )
}
