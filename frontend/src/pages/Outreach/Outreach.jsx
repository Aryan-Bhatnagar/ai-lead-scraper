import { Send } from 'lucide-react'
import PageHeader from '../../components/layout/PageHeader'
import EmptyState from '../../components/layout/EmptyState'

export default function Outreach() {
  return (
    <div>
      <PageHeader
        title="Outreach Queue"
        subtitle="Manage outreach campaigns across email, WhatsApp, and calls."
      />

      <div className="bg-white rounded-xl border border-slate-200 p-8">
        <EmptyState
          icon={Send}
          title="Outreach Queue"
          description="Track and manage outreach entries for qualified leads. Dispatch campaigns via webhook integration."
        >
          <p className="text-xs text-slate-400">
            API integration coming in Phase 13B
          </p>
        </EmptyState>
      </div>
    </div>
  )
}
