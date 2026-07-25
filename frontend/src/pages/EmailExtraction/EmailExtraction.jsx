import { Mail } from 'lucide-react'
import PageHeader from '../../components/layout/PageHeader'
import EmptyState from '../../components/layout/EmptyState'

export default function EmailExtraction() {
  return (
    <div>
      <PageHeader
        title="Email Extraction"
        subtitle="Extract email addresses from lead websites."
      />

      <div className="bg-white rounded-xl border border-slate-200 p-8">
        <EmptyState
          icon={Mail}
          title="Email Extraction Pipeline"
          description="Submit websites and extract valid email addresses. Supports batch processing with duplicate detection and validation."
        >
          <p className="text-xs text-slate-400">
            API integration coming in Phase 13B
          </p>
        </EmptyState>
      </div>
    </div>
  )
}
