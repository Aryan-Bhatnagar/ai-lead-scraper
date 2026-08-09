import { Inbox } from 'lucide-react'

export default function EmptyState({ icon: Icon = Inbox, title, description, children, compact = false }) {
  return (
    <div
      className={`flex flex-col items-center justify-center text-center animate-fade-in ${
        compact ? 'py-10' : 'py-20'
      }`}
    >
      <div className="relative mb-4">
        <div
          className={`rounded-2xl bg-gradient-to-br from-slate-100 to-slate-50 dark:from-slate-800 dark:to-slate-800/60 ring-1 ring-slate-200/80 dark:ring-slate-700/60 flex items-center justify-center ${
            compact ? 'w-12 h-12' : 'w-16 h-16'
          }`}
        >
          <Icon className={`${compact ? 'w-6 h-6' : 'w-8 h-8'} text-slate-400 dark:text-slate-500`} />
        </div>
        <div className="absolute -inset-2 rounded-3xl bg-primary-500/5 dark:bg-primary-400/5 -z-10" />
      </div>
      <h3 className={`${compact ? 'text-sm' : 'text-base'} font-semibold text-slate-900 dark:text-white`}>
        {title}
      </h3>
      {description && (
        <p className="mt-1.5 text-sm text-slate-500 dark:text-slate-400 max-w-sm leading-relaxed">
          {description}
        </p>
      )}
      {children && <div className="mt-5">{children}</div>}
    </div>
  )
}
