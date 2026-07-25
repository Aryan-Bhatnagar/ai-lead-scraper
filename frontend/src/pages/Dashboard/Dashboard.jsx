import { Users, Mail, UserCheck, Send } from 'lucide-react'
import PageHeader from '../../components/layout/PageHeader'
import StatCard from '../../components/layout/StatCard'
import LoadingSpinner from '../../components/layout/LoadingSpinner'
import EmptyState from '../../components/layout/EmptyState'
import { useState, useEffect } from 'react'

const statCards = [
  { title: 'Total Leads', value: '—', icon: Users, color: 'primary', trend: null },
  { title: 'Emails Extracted', value: '—', icon: Mail, color: 'success', trend: null },
  { title: 'Qualified Leads', value: '—', icon: UserCheck, color: 'warning', trend: null },
  { title: 'Outreach Sent', value: '—', icon: Send, color: 'danger', trend: null },
]

export default function Dashboard() {
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Simulated load — will be replaced with real API calls in Phase 13B
    const timer = setTimeout(() => setLoading(false), 800)
    return () => clearTimeout(timer)
  }, [])

  if (loading) return <LoadingSpinner text="Loading dashboard..." />

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Overview of your lead generation pipeline."
      />

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards.map((card) => (
          <StatCard key={card.title} {...card} />
        ))}
      </div>

      {/* Placeholder sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Lead Discovery Trend */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">
            Lead Discovery Trend
          </h3>
          <div className="h-64 flex items-center justify-center bg-slate-50 rounded-lg border border-dashed border-slate-300">
            <p className="text-sm text-slate-400">Chart placeholder — Recharts integration coming soon</p>
          </div>
        </div>

        {/* Lead Quality Distribution */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">
            Lead Quality Distribution
          </h3>
          <div className="h-64 flex items-center justify-center bg-slate-50 rounded-lg border border-dashed border-slate-300">
            <p className="text-sm text-slate-400">Chart placeholder — Recharts integration coming soon</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">
            Recent Activity
          </h3>
          <EmptyState
            title="No recent activity"
            description="Actions like discovery runs and outreach dispatches will appear here."
          />
        </div>

        {/* Recent Leads */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">
            Recent Leads
          </h3>
          <EmptyState
            title="No leads yet"
            description="Start a discovery run to populate your leads database."
          />
        </div>
      </div>
    </div>
  )
}
