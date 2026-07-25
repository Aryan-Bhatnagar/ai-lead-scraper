import { BarChart3 } from 'lucide-react'
import PageHeader from '../../components/layout/PageHeader'
import EmptyState from '../../components/layout/EmptyState'

export default function Analytics() {
  return (
    <div>
      <PageHeader
        title="Analytics"
        subtitle="Insights and performance metrics across your pipeline."
      />

      <div className="bg-white rounded-xl border border-slate-200 p-8">
        <EmptyState
          icon={BarChart3}
          title="Analytics Dashboard"
          description="Visualize pipeline performance, conversion rates, and outreach effectiveness with interactive Recharts charts."
        >
          <p className="text-xs text-slate-400">
            Charts and analytics logic coming in Phase 13C
          </p>
        </EmptyState>
      </div>
    </div>
  )
}
