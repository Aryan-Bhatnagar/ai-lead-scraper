import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import useAnimatedCounter from '../../hooks/useAnimatedCounter'

const COLOR_MAP = {
  primary: {
    icon: 'bg-primary-50 text-primary-600 dark:bg-primary-500/15 dark:text-primary-400',
    glow: 'hover:shadow-primary-500/10',
  },
  success: {
    icon: 'bg-success-50 text-success-600 dark:bg-success-500/15 dark:text-success-500',
    glow: 'hover:shadow-success-500/10',
  },
  warning: {
    icon: 'bg-warning-50 text-warning-600 dark:bg-warning-500/15 dark:text-warning-500',
    glow: 'hover:shadow-warning-500/10',
  },
  danger: {
    icon: 'bg-danger-50 text-danger-600 dark:bg-danger-500/15 dark:text-danger-500',
    glow: 'hover:shadow-danger-500/10',
  },
  slate: {
    icon: 'bg-slate-100 text-slate-600 dark:bg-slate-500/15 dark:text-slate-400',
    glow: 'hover:shadow-slate-500/10',
  },
}

export default function StatCard({ title, value, icon: Icon, trend, trendValue, color = 'primary', className = '' }) {
  const c = COLOR_MAP[color] || COLOR_MAP.primary
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus
  const trendColor =
    trend === 'up'
      ? 'text-success-600 dark:text-success-500'
      : trend === 'down'
        ? 'text-danger-600 dark:text-danger-500'
        : 'text-slate-400'

  const isNumeric = typeof value === 'number' && Number.isFinite(value)
  const animated = useAnimatedCounter(isNumeric ? value : 0)
  const displayValue = isNumeric ? animated.toLocaleString() : value

  return (
    <div
      className={`glass-card rounded-2xl p-5 h-full transition-all duration-300 hover:-translate-y-1 hover:shadow-lg ${c.glow} ${className}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400 truncate">
            {title}
          </p>
          <p className="mt-2 text-2xl font-bold text-slate-900 dark:text-white tabular-nums">
            {displayValue}
          </p>
          {trend && (
            <div className="mt-1.5 flex items-center gap-1">
              <TrendIcon className={`w-3.5 h-3.5 ${trendColor}`} />
              <span className={`text-xs font-medium ${trendColor}`}>{trendValue}</span>
              <span className="text-xs text-slate-400 dark:text-slate-500">vs last week</span>
            </div>
          )}
        </div>
        {Icon && (
          <div className={`p-2.5 rounded-xl shrink-0 transition-transform duration-300 hover:scale-105 ${c.icon}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>
    </div>
  )
}
