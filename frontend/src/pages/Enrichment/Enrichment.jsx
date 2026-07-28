import { Sparkles } from 'lucide-react'
import PageHeader from '../../components/layout/PageHeader'
import EmptyState from '../../components/layout/EmptyState'

export default function Enrichment() {
  return (
    <div>
      <PageHeader
        title="Prospect Enrichment"
        subtitle="Enhance prospect data with additional information from web intelligence."
      />

      <div className="bg-white rounded-xl border border-slate-200 p-8">
        <EmptyState
          icon={Sparkles}
          title="Prospect Enrichment"
          description="Select prospects and enrich their data with company details, contact information, and more using intelligent web intelligence."
        >
          <p className="text-xs text-slate-400">
            API integration coming in Phase 13B
          </p>
        </EmptyState>
      </div>
    </div>
  )
}
