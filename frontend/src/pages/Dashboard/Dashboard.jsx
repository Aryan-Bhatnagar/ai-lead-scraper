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
import EmptyState from '../../components/reusable/EmptyState'
import LeadCard from '../../components/repository/LeadCard'
import LeadDetailsDrawer from '../../components/repository/LeadDetailsDrawer'
import DiscoveryPipeline from '../../components/repository/DiscoveryPipeline'
import SkeletonLoader, { SkeletonCard } from '../../components/reusable/SkeletonLoader'
import { useAnalytics } from '../../hooks/useAnalytics'
import { useLeads } from '../../hooks/useLeads'
import { Database } from 'lucide-react'

const PIE_COLORS = {
  excellent: '#22c55e',
  good: '#84cc16',
  average: '#f59e0b',
  poor: '#f43f5e',
  unknown: '#94a3b8',
}

const BAR_COLORS = ['#f43f5e', '#fbbf24', '#a5b4fc', '#6366f1', '#22c55e', '#84cc16']

const tooltipStyle = {
  borderRadius: '12px',
  border: '1px solid #e2e8f0',
  background: 'rgba(255,255,255,0.95)',
  fontSize: '12px',
  boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
}

export default function Dashboard() {
  const { analytics, loading, error, refetch } = useAnalytics()
  const { leads: recentLeads } = useLeads({ sortBy: 'id', sortDesc: true, limit: 3 })
  const [selectedLead, setSelectedLead] = useState(null)

  if (error && !analytics.kpis) {
    return (
      <div>
        <PageHeader title="Dashboard" subtitle="Strategic overview of your lead discovery engine." />
        <div className="glass-card rounded-2xl p-12 text-center animate-fade-up">
          <EmptyState
            icon={Database}
            title="Unable to load analytics"
            description={String(error) || 'The API server could not be reached.'}
          >
            <button
              onClick={refetch}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
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
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <ChartCard title="Discovery Timeline" subtitle="New leads per day" className="lg:col-span-2 animate-fade-up stagger-1">
          {loading ? (
            <SkeletonLoader variant="chart" />
          ) : analytics.discoveryTimeline.length === 0 ? (
            <EmptyState compact title="No leads yet" description="Run discovery to populate discovery trends." />
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
                <Tooltip contentStyle={tooltipStyle} />
                <Area type="monotone" dataKey="leads" stroke="#6366f1" strokeWidth={2} fill="url(#areaGradient)" />
              </AreaChart>
            </ResponsiveContainer>
          )}
          {!loading && analytics.discoveryTimeline.length > 0 && (
            <p className="text-xs text-slate-400 mt-2 text-right">
              Peak: {maxDiscovery} leads/day
            </p>
          )}
        </ChartCard>

        <ChartCard title="Lead Sources" subtitle="Where leads originate" className="animate-fade-up stagger-2">
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-6 animate-pulse bg-slate-200 dark:bg-slate-700/60 rounded" />
              ))}
            </div>
          ) : analytics.leadSources.length === 0 ? (
            <EmptyState compact title="No source data" description="Sources will appear once leads are scraped." />
          ) : (
            <ul className="space-y-3">
              {analytics.leadSources.slice(0, 6).map((s) => {
                const total = analytics.leadSources.reduce((sum, x) => sum + x.value, 0)
                const pct = total ? Math.round((s.value / total) * 100) : 0
                return (
                  <li key={s.name}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="font-medium text-slate-600 dark:text-slate-300 truncate mr-2">{s.name || 'unknown'}</span>
                      <span className="text-slate-400 tabular-nums shrink-0">{s.value} · {pct}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary-500 transition-all duration-700"
                        style={{ width: `${pct}%` }}
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <ChartCard title="Score Distribution" subtitle="Quality score buckets" className="animate-fade-up stagger-1">
          {loading ? (
            <SkeletonLoader variant="chart" />
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={analytics.scoreDistribution} margin={{ top: 4, right: 8, left: -26, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="range" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'rgba(148,163,184,0.1)' }} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {analytics.scoreDistribution.map((entry, i) => (
                    <Cell key={entry.key} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard title="Quality Breakdown" subtitle="Excellent / good / average / poor" className="animate-fade-up stagger-2">
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
                  >
                    {analytics.qualityBreakdown.map((entry) => (
                      <Cell key={entry.tier} fill={PIE_COLORS[entry.tier] || '#94a3b8'} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex items-center justify-center flex-wrap gap-3 -mt-2">
                {analytics.qualityBreakdown.map((q) => (
                  <span key={q.tier} className="inline-flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: PIE_COLORS[q.tier] || '#94a3b8' }} />
                    {q.label} ({q.count})
                  </span>
                ))}
              </div>
            </>
          )}
        </ChartCard>

        <ChartCard title="Lifecycle Distribution" subtitle="Where leads sit in the funnel" className="animate-fade-up stagger-3">
          {loading ? (
            <SkeletonLoader variant="chart" />
          ) : analytics.lifecycleDistribution.length === 0 ? (
            <EmptyState compact title="No lifecycle data" description="Leads will flow through the lifecycle as they progress." />
          ) : (
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
                >
                  {analytics.lifecycleDistribution.map((entry, i) => (
                    <Cell key={entry.state} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard title="Provider Performance" subtitle="Leads per discovery source" className="animate-fade-up stagger-4">
          {loading ? (
            <SkeletonLoader variant="chart" />
          ) : analytics.providerPerformance.length === 0 ? (
            <EmptyState compact title="No provider data" description="Provider metrics appear after discovery runs." />
          ) : (
            <ul className="space-y-2.5">
              {analytics.providerPerformance.slice(0, 5).map((p) => (
                <li key={p.name} className="flex items-center justify-between gap-2">
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-300 truncate">{p.name}</span>
                  <span className="inline-flex items-center gap-2 text-xs shrink-0">
                    <span className="px-1.5 py-0.5 rounded bg-primary-50 dark:bg-primary-500/10 text-primary-600 dark:text-primary-400 font-medium tabular-nums">
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
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Activity Insights" subtitle="Latest pipeline events" className="animate-fade-up">
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-9 animate-pulse bg-slate-200 dark:bg-slate-700/60 rounded" />
              ))}
            </div>
          ) : analytics.activity.length === 0 ? (
            <EmptyState compact title="No recent activity" description="Actions like discovery runs and lifecycle moves will appear here." />
          ) : (
            <ul className="space-y-1">
              {analytics.activity.slice(0, 6).map((event) => (
                <li
                  key={event.id}
                  className="flex items-start gap-3 px-2 py-2.5 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                >
                  <span
                    className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${
                      event.type === 'discovery'
                        ? 'bg-primary-500'
                        : event.type === 'lifecycle'
                          ? 'bg-success-500'
                          : 'bg-slate-400'
                    }`}
                  />
                  <p className="text-sm text-slate-700 dark:text-slate-300 flex-1">{event.text}</p>
                  <span className="text-xs text-slate-400 shrink-0 pt-0.5">{event.time}</span>
                </li>
              ))}
            </ul>
          )}
        </ChartCard>

        <ChartCard
          title="Recent Leads"
          subtitle="Latest additions to the repository"
          className="animate-fade-up"
          actions={
            <Link
              to="/leads"
              className="text-xs font-medium text-primary-600 dark:text-primary-400 hover:underline"
            >
              View all
            </Link>
          }
        >
          <div className="grid grid-cols-1 gap-3">
            {loading
              ? Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="h-24 animate-pulse bg-slate-200 dark:bg-slate-700/60 rounded-2xl" />
                ))
              : recentLeads.length === 0
                ? <EmptyState compact title="No leads yet" description="New leads will appear here as they are persisted." />
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
