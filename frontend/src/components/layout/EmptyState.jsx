export default function EmptyState({ icon: Icon, title, description, children }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 sm:py-20 text-center animate-fade-in">
      {Icon && (
        <div className="relative mb-5">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-slate-100 to-slate-50 dark:from-slate-800 dark:to-slate-800/60 ring-1 ring-slate-200/80 dark:ring-slate-700/60 flex items-center justify-center">
            <Icon className="w-8 h-8 text-slate-400 dark:text-slate-500" />
          </div>
          <div className="absolute -inset-2.5 rounded-3xl bg-primary-500/5 dark:bg-primary-400/5 -z-10" />
        </div>
      )}
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white">{title}</h3>
      {description && (
        <p className="mt-1.5 text-sm text-slate-500 dark:text-slate-400 max-w-sm leading-relaxed">{description}</p>
      )}
      {children && <div className="mt-6">{children}</div>}
    </div>
  )
}
