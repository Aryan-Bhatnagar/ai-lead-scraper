import { Database } from 'lucide-react'
import PageHeader from '../../components/layout/PageHeader'
import EmptyState from '../../components/layout/EmptyState'

export default function Leads() {
  return (
    <div>
      <PageHeader
        title="Leads Database"
        subtitle="Manage and view all collected leads."
      />

      <div className="bg-white rounded-xl border border-slate-200 p-8">
        <EmptyState
          icon={Database}
          title="Leads Database"
          description="View, filter, and manage all leads collected from discovery and enrichment runs. Table powered by TanStack Table."
        >
          <p className="text-xs text-slate-400">
            Table and API integration coming in Phase 13B
          </p>
        </EmptyState>
      </div>
    </div>
  )
}
