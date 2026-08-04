import { useState } from 'react'
import { Users, Trophy, Gauge, Globe, RefreshCcw } from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
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
import LeadCard from '../../components/repository/LeadCard'
import LeadDetailsDrawer from '../../components/repository/LeadDetailsDrawer'
import DiscoveryPipeline from '../../components/repository/DiscoveryPipeline'
import SkeletonLoader, { SkeletonCard, SkeletonListRow } from '../../components/reusable/SkeletonLoader'
import { getLifecycleColor } from '../../components/reusable/badges/LifecycleBadge'
import { useAnalytics } from '../../hooks/useAnalytics'
import { useLeads } from '../../hooks/useLeads'
import { Database } from 'lucide-react'

const PIE_COLORS = {
  excellent: '#10b981',
  good: '#22c55e',
  average: '#f59e0b',
  poor: '#f43f5e',
  unknown: '#94a3b8',
}

export default function Dashboard() {
  const { analytics, loading, error, refetch } = useAnalytics()
  const { leads: recentLeads } = useLeads({ sortBy: 'id', sortDesc: true, limit: 3 })
  const [selectedLead, setSelectedLead] = useState(null)

  if (error && !analytics.kpis) {
    return (
      <div>
        <PageHeader title="Dashboard" subtitle="Strategic overview of your lead discovery engine." />
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

  const stageCounts = analytics.kpis
    ? {
        discovery: analytics.kpis.totalLeads,
        normalization: analytics.kpis.totalLeads,
        deduplication: analytics.kpis.totalCompanies,
        scoring: analytics.kpis.totalLeads,
        repository: analytics.kpis.totalLeads,
        crm: 0,
      }
    : {}

  const maxDiscovery = Math.max(...analytics.discoveryTimeline.map((d) => d.leads), 1)

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Strategic overview of your lead discovery engine."
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

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
          : kpis.map((kpi, i) => (
              <div key={kpi.title} className={`animate-fade-up stagger-${i + 1}`}>
                <StatCard {...kpi} />
              </div>
            ))}
      </div>

      {/* Pipeline */}
      <DiscoveryPipeline stageCounts={stageCounts} className="mb-6 animate-fade-up" />

      {/* Charts row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6 mb-6 items-stretch">
        <ChartCard title="Discovery Timeline" subtitle="New leads per day" className="lg:col-span-2 animate-fade-up stagger-1 flex flex-col">
          {loading ? (
            <SkeletonLoader variant="chart" />
          ) : analytics.discoveryTimeline.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <EmptyState compact title="No leads yet" description="Run discovery to populate discovery trends." />
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={analytics.discoveryTimeline} margin={{ top: 4, right: 8, left: -18, bottom: 0 }}>
                <defs>
                  <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#6366f1', strokeOpacity: 0.2 }} />
                <Area type="monotone" dataKey="leads" name="Leads" stroke="#6366f1" strokeWidth={2} fill="url(#areaGradient)" activeDot={{ r: 4, strokeWidth: 0 }} />
              </AreaChart>
            </ResponsiveContainer>
          )}
          {!loading && analytics.discoveryTimeline.length > 0 && (
            <p className="text-xs text-slate-400 mt-2 text-right tabular-nums">
              Peak: {maxDiscovery} leads/day
            </p>
          )}
        </ChartCard>

        <ChartCard title="Lead Sources" subtitle="Where leads originate" className="animate-fade-up stagger-2 flex flex-col">
          {loading ? (
            <div className="space-y-3 pt-1">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="skeleton-shimmer h-6 rounded" />
              ))}
            </div>
          ) : analytics.leadSources.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <EmptyState compact title="No source data" description="Sources will appear once leads are scraped." />
            </div>
          ) : (
            <ul className="space-y-3.5 flex-1">
              {analytics.leadSources.slice(0, 6).map((s, idx) => {
                const total = analytics.leadSources.reduce((sum, x) => sum + x.value, 0)
                const pct = total ? Math.round((s.value / total) * 100) : 0
                return (
                  <li key={s.name}>
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <span className="font-medium text-slate-600 dark:text-slate-300 truncate mr-2">{s.name || 'unknown'}</span>
                      <span className="text-slate-400 tabular-nums shrink-0">{s.value} · {pct}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-primary-500 to-primary-400 transition-all duration-700 ease-out"
                        style={{ width: `${pct}%`, transitionDelay: `${idx * 80}ms` }}
                      />
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </ChartCard>
      </div>

      {/* Charts row 2 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-6 items-stretch">
        <ChartCard title="Score Distribution" subtitle="Quality score buckets" className="animate-fade-up stagger-1 flex flex-col">
          {loading ? (
            <SkeletonLoader variant="chart" />
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={analytics.scoreDistribution} margin={{ top: 4, right: 8, left: -26, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="range" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(148,163,184,0.1)' }} />
                <Bar dataKey="count" name="Leads" radius={[6, 6, 0, 0]}>
                  {analytics.scoreDistribution.map((entry) => (
                    <Cell key={entry.key} fill={PIE_COLORS[entry.key] || '#94a3b8'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard title="Quality Breakdown" subtitle="Excellent / good / average / poor" className="animate-fade-up stagger-2 flex flex-col">
          {loading ? (
            <SkeletonLoader variant="chart" />
          ) : (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={analytics.qualityBreakdown}
                    dataKey="count"
                    nameKey="label"
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={70}
                    paddingAngle={3}
                    strokeWidth={0}
                  >
                    {analytics.qualityBreakdown.map((entry) => (
                      <Cell key={entry.tier} fill={PIE_COLORS[entry.tier] || '#94a3b8'} />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex items-center justify-center flex-wrap gap-x-3 gap-y-1.5 -mt-1">
                {analytics.qualityBreakdown.map((q) => (
                  <span key={q.tier} className="inline-flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                    <span className="w-2 h-2 rounded-full ring-2 ring-white dark:ring-slate-900" style={{ backgroundColor: PIE_COLORS[q.tier] || '#94a3b8' }} />
                    {q.label} <span className="tabular-nums font-medium text-slate-600 dark:text-slate-300">({q.count})</span>
                  </span>
                ))}
              </div>
            </>
          )}
        </ChartCard>

        <ChartCard title="Lifecycle Distribution" subtitle="Where leads sit in the funnel" className="animate-fade-up stagger-3 flex flex-col">
          {loading ? (
            <SkeletonLoader variant="chart" />
          ) : analytics.lifecycleDistribution.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <EmptyState compact title="No lifecycle data" description="Leads will flow through the lifecycle as they progress." />
            </div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={analytics.lifecycleDistribution}
                    dataKey="count"
                    nameKey="state"
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={70}
                    paddingAngle={3}
                    strokeWidth={0}
                  >
                    {analytics.lifecycleDistribution.map((entry) => (
                      <Cell key={entry.state} fill={getLifecycleColor(entry.state)} />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex items-center justify-center flex-wrap gap-x-3 gap-y-1.5 -mt-1">
                {analytics.lifecycleDistribution.slice(0, 5).map((l) => (
                  <span key={l.state} className="inline-flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                    <span className="w-2 h-2 rounded-full ring-2 ring-white dark:ring-slate-900" style={{ backgroundColor: getLifecycleColor(l.state) }} />
                    {l.state} <span className="tabular-nums font-medium text-slate-600 dark:text-slate-300">({l.count})</span>
                  </span>
                ))}
              </div>
            </>
          )}
        </ChartCard>

        <ChartCard title="Provider Performance" subtitle="Leads per discovery source" className="animate-fade-up stagger-4 flex flex-col">
          {loading ? (
            <SkeletonLoader variant="list" rows={5} />
          ) : analytics.providerPerformance.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <EmptyState compact title="No provider data" description="Provider metrics appear after discovery runs." />
            </div>
          ) : (
            <ul className="space-y-2 flex-1">
              {analytics.providerPerformance.slice(0, 5).map((p) => (
                <li
                  key={p.name}
                  className="flex items-center justify-between gap-2 px-2 py-1.5 -mx-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
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

      {/* Bottom row: activity + recent leads */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 items-stretch">
        <ChartCard title="Activity Insights" subtitle="Latest pipeline events" className="animate-fade-up flex flex-col">
          {loading ? (
            <div className="space-y-1 pt-1">
              {Array.from({ length: 4 }).map((_, i) => (
                <SkeletonListRow key={i} />
              ))}
            </div>
          ) : analytics.activity.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <EmptyState compact title="No recent activity" description="Actions like discovery runs and lifecycle moves will appear here." />
            </div>
          ) : (
            <ul className="space-y-1 flex-1">
              {analytics.activity.slice(0, 6).map((event) => (
                <li
                  key={event.id}
                  className="flex items-start gap-3 px-2 py-2.5 -mx-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                >
                  <span
                    className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ring-2 ring-white dark:ring-slate-900 ${
                      event.type === 'discovery'
                        ? 'bg-primary-500'
                        : event.type === 'lifecycle'
                          ? 'bg-success-500'
                          : 'bg-slate-400'
                    }`}
                  />
                  <p className="text-sm text-slate-700 dark:text-slate-300 flex-1 leading-snug">{event.text}</p>
                  <span className="text-xs text-slate-400 shrink-0 pt-0.5 tabular-nums">{event.time}</span>
                </li>
              ))}
            </ul>
          )}
        </ChartCard>

        <ChartCard
          title="Recent Leads"
          subtitle="Latest additions to the repository"
          className="animate-fade-up flex flex-col"
          actions={
            <Link
              to="/leads"
              className="inline-flex items-center gap-1 text-xs font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 transition-colors"
            >
              View all
            </Link>
          }
        >
          <div className="grid grid-cols-1 gap-3 flex-1 content-start">
            {loading
              ? Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="skeleton-shimmer h-24 rounded-2xl" />
                ))
              : recentLeads.length === 0
                ? (
                  <div className="flex-1 flex items-center justify-center">
                    <EmptyState compact title="No leads yet" description="New leads will appear here as they are persisted." />
                  </div>
                )
                : recentLeads.map((lead) => (
                    <LeadCard key={lead.id} lead={lead} onView={setSelectedLead} />
                  ))}
          </div>
        </ChartCard>
      </div>

      <LeadDetailsDrawer lead={selectedLead} onClose={() => setSelectedLead(null)} />
    </div>
  )
}
