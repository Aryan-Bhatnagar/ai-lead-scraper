import { ChevronDown, RotateCcw } from 'lucide-react'

export function FilterSelect({ label, value, onChange, options, allLabel = 'All' }) {
  return (
    <label className="flex flex-col gap-1 min-w-[140px]">
      <span className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</span>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full appearance-none pl-3 pr-8 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-400 cursor-pointer transition-all"
        >
          <option value="All">{allLabel}</option>
          {options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
      </div>
    </label>
  )
}

export function ScoreRangeFilter({ min, max, onMinChange, onMaxChange }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Score Range</span>
      <div className="flex items-center gap-2">
        <input
          type="number"
          min="0"
          max="100"
          value={min ?? ''}
          placeholder="Min"
          onChange={(e) => onMinChange(e.target.value === '' ? null : Number(e.target.value))}
          className="w-20 px-2.5 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-400 transition-all"
        />
        <span className="text-slate-400 text-xs">—</span>
        <input
          type="number"
          min="0"
          max="100"
          value={max ?? ''}
          placeholder="Max"
          onChange={(e) => onMaxChange(e.target.value === '' ? null : Number(e.target.value))}
          className="w-20 px-2.5 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-400 transition-all"
        />
      </div>
    </div>
  )
}

export default function FilterPanel({ children, onReset, activeCount = 0 }) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      {children}
      {activeCount > 0 && (
        <button
          onClick={onReset}
          className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-500/10 rounded-lg transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Reset ({activeCount})
        </button>
      )}
    </div>
  )
}
