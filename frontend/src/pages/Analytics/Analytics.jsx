import {
  Users,
  Trophy,
  Gauge,
  Globe,
  RefreshCcw,
  TrendingUp,
  Database,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import PageHeader from '../../components/layout/PageHeader'
import StatCard from '../../components/reusable/StatCard'
import ChartCard from '../../components/reusable/ChartCard'
import ChartTooltip from '../../components/reusable/ChartTooltip'
import EmptyState from '../../components/reusable/EmptyState'
import SkeletonLoader, { SkeletonCard } from '../../components/reusable/SkeletonLoader'
import { getLifecycleColor } from '../../components/reusable/badges/LifecycleBadge'
import { useAnalytics } from '../../hooks/useAnalytics'

const QUALITY_COLORS = {
  excellent: '#10b981',
  good: '#22c55e',
  average: '#f59e0b',
  poor: '#f43f5e',
}

export default function Analytics() {
  const { analytics, loading, error, refetch } = useAnalytics()

  if (error && !analytics.kpis) {
    return (
      <div>
        <PageHeader title="Analytics" subtitle="Insights and performance metrics across your pipeline." />
        <div className="glass-card rounded-2xl p-8 sm:p-12 text-center animate-fade-up ring-1 ring-danger-500/10">
          <EmptyState
            icon={Database}
            title="Unable to load analytics"
            description={String(error) || 'The API server could not be reached.'}
          >
            <button
              onClick={refetch}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 active:scale-[0.98] transition-all"
            >
              <RefreshCcw className="w-4 h-4" />
              Retry
            </button>
          </EmptyState>
        </div>
      </div>
    )
  }

  const kpis = analytics.kpis
    ? [
        { title: 'Total Leads', value: analytics.kpis.totalLeads, icon: Users, color: 'primary' },
        { title: 'Total Companies', value: analytics.kpis.totalCompanies, icon: Trophy, color: 'success' },
        { title: 'Average Score', value: analytics.kpis.averageScore, icon: Gauge, color: 'warning' },
        { title: 'Active Sources', value: analytics.kpis.sources, icon: Globe, color: 'danger' },
      ]
    : []

  const hasQuality = analytics.qualityBreakdown.some((q) => q.count > 0)

  return (
    <div>
      <PageHeader
        title="Analytics"
        subtitle="Insights and performance metrics across your pipeline."
      >
        <button
          onClick={refetch}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors disabled:opacity-50"
        >
          <RefreshCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </PageHeader>

      {/* KPI cards with animated counters */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6 items-stretch">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
          : kpis.map((kpi, i) => (
              <div key={kpi.title} className={`animate-fade-up stagger-${i + 1}`}>
                <StatCard {...kpi} />
              </div>
            ))}
      </div>

      {/* Trend + quality */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6 mb-6 items-stretch">
        <ChartCard
          title="Discovery Trend"
          subtitle="New leads per day"
          className="lg:col-span-2 animate-fade-up stagger-1 flex flex-col"
        >
          {loading ? (
            <SkeletonLoader variant="chart" />
          ) : analytics.discoveryTimeline.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <EmptyState compact icon={TrendingUp} title="No trend data" description="Discovery trends appear after leads are scraped." />
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={analytics.discoveryTimeline} margin={{ top: 4, right: 8, left: -18, bottom: 0 }}>
                <defs>
                  <linearGradient id="analyticsArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#6366f1', strokeOpacity: 0.2 }} />
                <Area type="monotone" dataKey="leads" name="Leads" stroke="#6366f1" strokeWidth={2} fill="url(#analyticsArea)" activeDot={{ r: 4, strokeWidth: 0 }} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard
          title="Quality Breakdown"
          subtitle="Lead quality tiers"
          className="animate-fade-up stagger-2 flex flex-col"
        >
          {loading ? (
            <SkeletonLoader variant="chart" />
          ) : !hasQuality ? (
            <div className="flex-1 flex items-center justify-center">
              <EmptyState compact title="No quality data" description="Scores will appear once leads are scored." />
            </div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={analytics.qualityBreakdown}
                    dataKey="count"
                    nameKey="label"
                    cx="50%"
                    cy="50%"
                    innerRadius={48}
                    outerRadius={76}
                    paddingAngle={3}
                    strokeWidth={0}
                  >
                    {analytics.qualityBreakdown.map((entry) => (
                      <Cell key={entry.tier} fill={QUALITY_COLORS[entry.tier] || '#94a3b8'} />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              {/* Aligned legend with shares */}
              <ul className="mt-1 space-y-1.5">
                {analytics.qualityBreakdown.map((q) => {
                  const total = analytics.qualityBreakdown.reduce((s, x) => s + x.count, 0)
                  const pct = total ? Math.round((q.count / total) * 100) : 0
                  return (
                    <li key={q.tier} className="flex items-center gap-2 text-xs">
                      <span
                        className="w-2 h-2 rounded-full ring-2 ring-white dark:ring-slate-900 shrink-0"
                        style={{ backgroundColor: QUALITY_COLORS[q.tier] || '#94a3b8' }}
                      />
                      <span className="text-slate-600 dark:text-slate-300 flex-1">{q.label}</span>
                      <span className="tabular-nums text-slate-400">{pct}%</span>
                      <span className="tabular-nums font-medium text-slate-700 dark:text-slate-200 w-10 text-right">
                        {q.count}
                      </span>
                    </li>
                  )
                })}
              </ul>
            </>
          )}
        </ChartCard>
      </div>

      {/* Lifecycle + providers + score buckets */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 items-stretch">
        <ChartCard
          title="Lifecycle Funnel"
          subtitle="Leads per stage"
          className="animate-fade-up stagger-1 flex flex-col"
        >
          {loading ? (
            <SkeletonLoader variant="list" rows={5} />
          ) : analytics.lifecycleDistribution.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <EmptyState compact title="No lifecycle data" description="Leads will flow through the lifecycle as they progress." />
            </div>
          ) : (
            <ul className="space-y-2.5 flex-1">
              {analytics.lifecycleDistribution.map((l, idx) => {
                const max = Math.max(...analytics.lifecycleDistribution.map((x) => x.count), 1)
                const pct = Math.max(4, Math.round((l.count / max) * 100))
                return (
                  <li key={l.state}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="inline-flex items-center gap-1.5 font-medium text-slate-600 dark:text-slate-300">
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: getLifecycleColor(l.state) }}
                        />
                        {l.state}
                      </span>
                      <span className="tabular-nums text-slate-400">{l.count}</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-700 ease-out"
                        style={{
                          width: `${pct}%`,
                          backgroundColor: getLifecycleColor(l.state),
                          transitionDelay: `${idx * 60}ms`,
                        }}
                      />
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </ChartCard>

        <ChartCard
          title="Score Buckets"
          subtitle="Quality score distribution"
          className="animate-fade-up stagger-2 flex flex-col"
        >
          {loading ? (
            <SkeletonLoader variant="chart" />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={analytics.scoreDistribution} margin={{ top: 4, right: 8, left: -26, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="range" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(148,163,184,0.1)' }} />
                <Bar dataKey="count" name="Leads" radius={[6, 6, 0, 0]}>
                  {analytics.scoreDistribution.map((entry) => (
                    <Cell key={entry.key} fill={QUALITY_COLORS[entry.key] || '#94a3b8'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard
          title="Provider Success"
          subtitle="Leads and success rate per source"
          className="animate-fade-up stagger-3 flex flex-col"
        >
          {loading ? (
            <SkeletonLoader variant="list" rows={5} />
          ) : analytics.providerPerformance.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <EmptyState compact title="No provider data" description="Provider metrics appear after discovery runs." />
            </div>
          ) : (
            <ul className="space-y-2 flex-1">
              {analytics.providerPerformance.map((p) => (
                <li
                  key={p.name}
                  className="flex items-center justify-between gap-2 px-2 py-2 -mx-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                >
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-300 truncate">{p.name}</span>
                  <span className="inline-flex items-center gap-2 text-xs shrink-0">
                    <span className="px-1.5 py-0.5 rounded-md bg-primary-50 dark:bg-primary-500/10 text-primary-600 dark:text-primary-400 font-medium tabular-nums">
                      {p.leads}
                    </span>
                    <span className="text-success-600 dark:text-success-500 font-medium tabular-nums">
                      {p.successRate}%
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </ChartCard>
      </div>
    </div>
  )
}
