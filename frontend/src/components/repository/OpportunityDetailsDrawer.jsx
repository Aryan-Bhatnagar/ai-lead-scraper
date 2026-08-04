import { useEffect } from 'react'
import {
  X,
  Globe,
  MapPin,
  Mail,
  Phone,
  User,
  Clock,
  Tag,
  DollarSign,
  Briefcase,
  Calendar,
  List,
} from 'lucide-react'

function DrawerRow({ icon: Icon, label, children }) {
  return (
    <div className="flex items-start gap-3 py-2.5">
      <Icon className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</p>
        <div className="text-sm text-slate-800 dark:text-slate-200">{children}</div>
      </div>
    </div>
  )
}

export default function OpportunityDetailsDrawer({ opportunity, onClose }) {
  useEffect(() => {
    if (!opportunity) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') onClose?.()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [opportunity, onClose])

  const open = !!opportunity

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-40 transition-opacity duration-300 ${
          open ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
      />

      {/* Panel */}
      <aside
        className={`fixed top-0 right-0 h-full w-full max-w-md z-50 bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700/60 shadow-2xl transition-transform duration-300 ease-out ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
        aria-hidden={!open}
      >
        {opportunity && (
          <div className="h-full flex flex-col">
            {/* Header */}
            <div className="flex items-start justify-between p-5 border-b border-slate-200 dark:border-slate-700/60">
              <div className="min-w-0 flex-1 pr-4">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white truncate">
                  {opportunity.project_title}
                </h2>
                <div className="mt-1.5 flex flex-wrap items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-primary/10 text-primary text-xs font-medium">
                    {opportunity.provider.toUpperCase()}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-secondary/10 text-secondary text-xs font-medium">
                    {opportunity.experience_level}
                  </span>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                aria-label="Close drawer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Scrollable body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-6">
              {/* Core info */}
              <section>
                <div className="divide-y divide-slate-100 dark:divide-slate-800">
                  <DrawerRow icon={Globe} label="Project URL">
                    <a
                      href={opportunity.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-600 dark:text-primary-400 hover:underline break-all"
                    >
                      {opportunity.url}
                    </a>
                  </DrawerRow>
                  <DrawerRow icon={MapPin} label="Client Location">
                    {opportunity.client_country}
                  </DrawerRow>
                  <DrawerRow icon={Briefcase} label="Category">
                    {opportunity.category}
                  </DrawerRow>
                  <DrawerRow icon={DollarSign} label="Budget">
                    {opportunity.budget_min !== null || opportunity.budget_max !== null ? (
                      <>
                        ${opportunity.budget_min?.toLocaleString() ?? '0'} -
                        ${opportunity.budget_max?.toLocaleString() ?? '0'}
                        {opportunity.currency}
                      </>
                    ) : (
                      <span className="text-slate-500">Not specified</span>
                    )}
                  </DrawerRow>
                  <DrawerRow icon={Calendar} label="Posted">
                    {new Date(opportunity.posted_time).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </DrawerRow>
                  {opportunity.deadline && (
                    <DrawerRow icon={Calendar} label="Deadline">
                      {new Date(opportunity.deadline).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </DrawerRow>
                  )}
                  <DrawerRow icon={List} label="Proposals">
                    {opportunity.proposal_count} proposals
                  </DrawerRow>
                </div>
                {opportunity.description && (
                  <div className="mt-4 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60">
                    <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5">
                      Description
                    </p>
                    <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                      {opportunity.description}
                    </p>
                  </div>
                )}
              </section>

              {/* Skills */}
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
                  <Tag className="w-3.5 h-3.5" />
                  Skills
                </h3>
                <div className="flex flex-wrap gap-1 mb-4">
                  {opportunity.skills.map((skill, index) => (
                    <span
                      key={index}
                      className="px-2 py-0.5 rounded bg-secondary/10 text-secondary text-xs font-medium"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
                {opportunity.experience_level && (
                  <div className="text-sm text-slate-600 dark:text-slate-300">
                    Experience Level: <span className="font-medium">{opportunity.experience_level}</span>
                  </div>
                )}
              </section>

              {/* Provider Metadata */}
              {Object.keys(opportunity.provider_metadata).length > 0 && (
                <section>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-1.5">
                    <List className="w-3.5 h-3.5" />
                    Provider Details
                  </h3>
                  <div className="space-y-2">
                    {Object.entries(opportunity.provider_metadata).map(([key, value]) => (
                      <div key={key} className="flex justify-between text-sm text-slate-600 dark:text-slate-300">
                        <span className="font-medium">{key.replace('_', ' ').toUpperCase()}</span>
                        <span className="tabular-nums">
                          {typeof value === 'number' ? value.toLocaleString() : value}
                        </span>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </div>
          </div>
        )}
      </aside>
    </>
  )
}