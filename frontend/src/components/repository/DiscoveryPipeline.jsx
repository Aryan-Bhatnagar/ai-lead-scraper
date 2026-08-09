import { useEffect, useState } from 'react'
import {
  Search,
  Filter,
  Copy,
  Trophy,
  Database,
  Send,
  Check,
  Loader2,
  ChevronDown,
} from 'lucide-react'

const STAGES = [
  { id: 'discovery', label: 'Discovery', icon: Search, description: 'Providers fetch candidates' },
  { id: 'normalization', label: 'Normalization', icon: Filter, description: 'Unified schema mapping' },
  { id: 'deduplication', label: 'Deduplication', icon: Copy, description: 'Cross-source matching' },
  { id: 'scoring', label: 'Scoring', icon: Trophy, description: 'Weighted feature scoring' },
  { id: 'repository', label: 'Repository', icon: Database, description: 'Persisted leads' },
  { id: 'crm', label: 'CRM', icon: Send, description: 'Downstream sync' },
]

export default function DiscoveryPipeline({ stageCounts = {}, className = '' }) {
  const [current, setCurrent] = useState(0)

  // Animate through stages cyclically to simulate live pipeline activity
  useEffect(() => {
    const t = setInterval(() => {
      setCurrent((c) => (c + 1) % STAGES.length)
    }, 1600)
    return () => clearInterval(t)
  }, [])

  return (
    <div className={`glass-card rounded-2xl p-5 ${className}`}>
      <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-1">
        Discovery Pipeline
      </h3>
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-5">
        Real-time lead processing flow
      </p>

      <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-0">
        {STAGES.map((stage, i) => {
          const Icon = stage.icon
          const isDone = i < current
          const isActive = i === current
          const isPending = i > current

          return (
            <div key={stage.id} className="flex flex-col sm:flex-row sm:items-center flex-1">
              <div
                className={`flex items-center gap-3 sm:flex-col sm:items-center sm:text-center flex-1 rounded-xl px-3 py-2.5 transition-all duration-500 ${
                  isActive
                    ? 'bg-primary-50 dark:bg-primary-500/10 ring-1 ring-primary-200 dark:ring-primary-500/30'
                    : ''
                }`}
              >
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-500 ${
                    isDone
                      ? 'bg-success-500 text-white'
                      : isActive
                        ? 'bg-primary-600 text-white animate-pulse-ring'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500'
                  }`}
                >
                  {isDone ? (
                    <Check className="w-5 h-5" />
                  ) : isActive ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Icon className="w-5 h-5" />
                  )}
                </div>
                <div className="min-w-0">
                  <p
                    className={`text-xs font-semibold ${
                      isPending
                        ? 'text-slate-400 dark:text-slate-500'
                        : 'text-slate-800 dark:text-slate-100'
                    }`}
                  >
                    {stage.label}
                  </p>
                  <p className="text-[11px] text-slate-400 dark:text-slate-500 hidden sm:block">
                    {stage.description}
                  </p>
                  {stageCounts[stage.id] != null && (
                    <p className="text-[11px] font-semibold text-primary-600 dark:text-primary-400 tabular-nums">
                      {stageCounts[stage.id]}
                    </p>
                  )}
                </div>
              </div>

              {i < STAGES.length - 1 && (
                <div className="flex justify-center py-0.5 sm:py-0 sm:px-1">
                  <ChevronDown
                    className={`w-4 h-4 rotate-0 sm:-rotate-90 transition-colors duration-500 ${
                      i < current
                        ? 'text-success-500'
                        : 'text-slate-300 dark:text-slate-600'
                    }`}
                  />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
