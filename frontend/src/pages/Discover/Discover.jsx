import { Search } from 'lucide-react'
import PageHeader from '../../components/layout/PageHeader'
import EmptyState from '../../components/layout/EmptyState'

export default function Discover() {
  return (
    <div>
      <PageHeader
        title="Discover Leads"
        subtitle="Find new business leads by industry and location."
      />

      <div className="bg-white rounded-xl border border-slate-200 p-8">
        <EmptyState
          icon={Search}
          title="Lead Discovery"
          description="Search for leads across the web using multiple discovery sources. Configure industry, location, and result limits to find your ideal prospects."
        >
          <p className="text-xs text-slate-400">
            Form and API integration coming in Phase 13B
          </p>
        </EmptyState>
      </div>
    </div>
  )
}
